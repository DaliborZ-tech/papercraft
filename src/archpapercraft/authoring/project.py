"""Experimental, generic authoring document and transactional commands."""

from __future__ import annotations

import copy
import json
import math
import os
import tempfile
import warnings
from dataclasses import asdict, fields
from functools import wraps
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from .bend import DEFAULT_MATERIAL_PROFILE, BendCommands
from .errors import ProjectFormatError, UnsupportedOperationError, ValidationError
from .geometry import (
    material_polygon,
    number,
    rigid_matrix,
    signed_area,
    triangulate,
    validate_rigid,
    vector,
)
from .interior import InteriorCommands
from .loft_surface import LoftCommands, validate_loft_params, world_loft_geometry
from .loft_surface import analysis as loft_analysis
from .model import (
    Attachment,
    Connector,
    CurveSegment,
    Joint,
    MaterialPart,
    Page,
    PaperFrame,
    Placement,
    Profile,
    SegmentedVariant,
    SketchPlane,
    SurfaceFeature,
    Vertex,
    identity,
    uuid,
)
from .paper import (
    ROLES,
    build_part,
    edge_world,
    validate_joint_contact,
    validate_layout,
)
from .profile_curves import ProfileCurveCommands, move_curve_endpoint
from .segmented_surface import SegmentedCommands

APPLICATION = "ArchPapercraft.AuthorProject"
SCHEMA_VERSION = 5
WRITER_VERSION = "0.3.0-pc008-segmented-variants-experimental"
_UNSET = object()


def atomic(method):
    @wraps(method)
    def command(self, *args, **kwargs):
        before = copy.deepcopy(self.__dict__)
        try:
            value = method(self, *args, **kwargs)
            self.validate()
            return value
        except Exception as exc:
            self.__dict__.clear()
            self.__dict__.update(before)
            if isinstance(
                exc, (KeyError, TypeError, ValueError, AttributeError, IndexError, OverflowError)
            ) and not isinstance(exc, ValidationError):
                raise ValidationError(f"Operaci nelze provést: {exc}") from exc
            raise

    return command


def _revision(value):
    if type(value) is not int or value < 1:
        raise ValidationError("Neplatná revize nebo pořadové číslo.")


def _record(cls, data):
    if not isinstance(data, dict) or set(data) != {f.name for f in fields(cls)}:
        raise ProjectFormatError(f"Neplatná pole {cls.__name__}.")
    return cls(**copy.deepcopy(data))


class AuthorProject(
    InteriorCommands, BendCommands, ProfileCurveCommands, LoftCommands, SegmentedCommands
):
    def __init__(self, name="Nový model", scale=0.01):
        self.project_id = identity()
        self.name, self.scale, self.revision = name, number(scale, "Měřítko", positive=True), 1
        self.next_part_number, self.next_joint_number = 1, 1
        self.profiles, self.surfaces, self.parts, self.joints, self.connectors = {}, {}, {}, {}, {}
        self.pages = [Page()]
        self.placements, self.acknowledgements = {}, {}
        self.attachments, self.next_attachment_number = {}, 1
        self.loaded_from_schema, self.requires_save_as, self.loaded_source_path = None, False, None
        self.material_profile = copy.deepcopy(DEFAULT_MATERIAL_PROFILE)
        self.segmented_variants = {}

    @classmethod
    def new(cls, name="Nový model", scale=0.01):
        project = cls(name, scale)
        project.validate()
        return project

    def _touch(self, surface_ids=()):
        self.revision += 1
        affected = set(surface_ids)
        pairs = [{j.surface_a, j.surface_b} for j in self.joints.values()]
        pairs.extend({a.source_surface_id, a.target_surface_id} for a in self.attachments.values())
        previous = None
        while previous != affected:
            previous = set(affected)
            for pair in pairs:
                if pair & affected:
                    affected.update(pair)
        for sid in surface_ids:
            surface = self.surfaces[sid]
            if surface.kind == "ruled_loft":
                for side, pid in zip(("first", "second"), surface.source_profile_ids()):
                    if {r[side + "_segment_id"] for r in surface.params["correspondences"]} != {
                        segment.id for segment in self.profiles[pid].segments
                    }:
                        surface.params["reference_state"] = "UNRESOLVED"
            self.surfaces[sid].revision += 1
        for part in self.parts.values():
            if set(part.surface_ids) & affected:
                part.stale = True

    def _profile_surfaces(self, profile_id):
        return [sid for sid, s in self.surfaces.items() if profile_id in s.source_profile_ids()]

    @atomic
    def add_profile(self, points=None, *, segments=None, closed=True, name="Obrys", plane=None):
        if not isinstance(closed, bool):
            raise ValidationError("Uzavření profilu musí být explicitní volba.")
        plane = (
            SketchPlane.named(plane)
            if isinstance(plane, str)
            else (
                _record(SketchPlane, plane)
                if isinstance(plane, dict)
                else copy.deepcopy(plane or SketchPlane())
            )
        )
        if (points is None) == (segments is None):
            raise ValidationError("Zadejte body nebo zdrojové segmenty profilu.")
        if segments is not None:
            if not isinstance(segments, list) or not segments:
                raise ValidationError("Profil nemá žádné segmenty.")
            points = [s["start"] for s in segments]
            if not closed:
                points.append(segments[-1]["end"])
            for index, segment in enumerate(segments):
                next_point = points[(index + 1) % len(points)]
                if not np.allclose(
                    vector(segment["end"], 2), vector(next_point, 2), atol=1e-9, rtol=0
                ):
                    raise ValidationError("Zdrojové křivky na sebe nenavazují.")
        else:
            points = [vector(p, 2) for p in points]
            if len(points) > 1 and points[0] == points[-1] and closed:
                points = points[:-1]
            segments = [{"kind": "line"} for _ in range(len(points) - (0 if closed else 1))]
        vertices = [Vertex(identity(), vector(p, 2)) for p in points]
        curves = []
        for index, source in enumerate(segments):
            kind = source.get("kind", "line")
            data = copy.deepcopy(
                source.get(
                    "data", {k: v for k, v in source.items() if k not in ("kind", "start", "end")}
                )
            )
            curves.append(
                CurveSegment(
                    identity(),
                    kind,
                    vertices[index].id,
                    vertices[(index + 1) % len(vertices)].id,
                    data,
                )
            )
        profile = Profile(identity(), name, vertices, curves, closed, plane)
        profile.validate()
        if closed and all(s.kind == "line" for s in curves):
            material_polygon(profile.points)
        self.profiles[profile.id] = profile
        self._touch()
        return profile.id

    @atomic
    def update_profile(self, profile_id, points=None, *, segments=None, closed=None):
        """Explicit contour replacement, with new topology IDs and no index fallback."""
        old = self.profiles[profile_id]
        new_id = self.add_profile(
            points,
            segments=segments,
            closed=old.closed if closed is None else closed,
            name=old.name,
            plane=old.plane,
        )
        replacement = self.profiles.pop(new_id)
        replacement.id, replacement.revision = profile_id, old.revision + 1
        self.profiles[profile_id] = replacement
        for surface in self.surfaces.values():
            if surface.kind == "ruled_loft" and profile_id in surface.source_profile_ids():
                surface.params["reference_state"] = "UNRESOLVED"
        for joint in self.joints.values():
            if any(
                self.surfaces[sid].profile_id == profile_id
                for sid in (joint.surface_a, joint.surface_b)
            ):
                joint.unresolved = True
        for attachment in self.attachments.values():
            if attachment.source_edge_id in {edge.id for edge in old.segments}:
                attachment.unresolved = True
        self._touch(self._profile_surfaces(profile_id))

    @atomic
    def move_vertex(self, profile_id, vertex_id, point):
        profile = self.profiles[profile_id]
        vertex = profile.vertex(vertex_id)
        if vertex is None:
            raise ValidationError("Vrchol už v profilu neexistuje.")
        value = vector(point, 2)
        if value == vertex.point:
            return
        move_curve_endpoint(profile, vertex_id, value)
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))

    @atomic
    def append_vertex(self, profile_id, point):
        """Extend an open source profile without replacing existing topology."""
        profile = self.profiles[profile_id]
        if profile.closed:
            raise ValidationError("Obrys je již uzavřený. Upravte jeho vrcholy místo pokračování.")
        vertex = Vertex(identity(), vector(point, 2))
        segment = CurveSegment(identity(), "line", profile.vertices[-1].id, vertex.id)
        profile.vertices.append(vertex)
        profile.segments.append(segment)
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))
        return vertex.id

    @atomic
    def close_profile(self, profile_id):
        """Explicit closure preserves every vertex and existing segment ID."""
        profile = self.profiles[profile_id]
        if profile.closed:
            return profile.id
        if len(profile.vertices) < 3:
            raise ValidationError("Pro uzavřený obrys přidejte alespoň třetí vrchol.")
        profile.segments.append(
            CurveSegment(identity(), "line", profile.vertices[-1].id, profile.vertices[0].id)
        )
        profile.closed = True
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))
        return profile.id

    @atomic
    def add_surface(self, profile_id, holes=(), *, name="Plocha"):
        profile = self.profiles[profile_id]
        hole_ids = list(holes)
        self._source_polygon(profile_id, hole_ids)
        sid, pid = identity(), identity()
        surface = SurfaceFeature(sid, name, profile_id, hole_ids, part_id=pid)
        frame = PaperFrame(sid, profile.vertices[0].id, profile.segments[0].id)
        part = MaterialPart(
            pid, f"P{self.next_part_number} · {name}", [sid], frame, number=self.next_part_number
        )
        index = self.next_part_number - 1
        self.next_part_number += 1
        self.surfaces[sid], self.parts[pid] = surface, part
        self.placements[pid] = Placement(x_mm=(index % 3) * 120.0, y_mm=(index // 3) * 120.0)
        self._touch([sid])
        self.parts[pid] = build_part(self, part)
        return sid

    def _source_polygon(self, profile_id, hole_ids):
        profiles = [self.profiles[p] for p in [profile_id, *hole_ids]]
        if any(not p.closed for p in profiles):
            raise ValidationError("Plocha potřebuje uzavřený vnější obrys i otvory.")
        first = asdict(profiles[0].plane)
        if any(asdict(p.plane) != first for p in profiles[1:]):
            raise ValidationError("Obrys a otvory musí být ve stejné pracovní rovině.")
        if any(s.kind != "line" for p in profiles for s in p.segments):
            self.curve_region_topology([p.id for p in profiles])
        return material_polygon(
            self.profile_outline(profiles[0].id),
            [self.profile_outline(p.id) for p in profiles[1:]],
        )

    @atomic
    def add_hole(self, surface_id, profile_id):
        surface = self.surfaces[surface_id]
        if profile_id in surface.hole_profile_ids:
            raise ValidationError("Otvor je již připojený.")
        surface.hole_profile_ids.append(profile_id)
        self._touch([surface_id])

    @atomic
    def set_transform(
        self, surface_id, position_mm=None, rotation_deg=None, *, parent_transforms=None
    ):
        surface = self.surfaces[surface_id]
        if position_mm is not None:
            surface.position_mm = vector(position_mm, 3)
        if rotation_deg is not None:
            surface.rotation_deg = vector(rotation_deg, 3)
        if parent_transforms is not None:
            surface.parent_transforms = [validate_rigid(m).tolist() for m in parent_transforms]
        self._touch([surface_id])

    def _surface_matrix(self, surface_id):
        surface = self.surfaces[surface_id]
        result = np.eye(4)
        for matrix in surface.parent_transforms:
            result = result @ validate_rigid(matrix)
        return result @ rigid_matrix(surface.position_mm, surface.rotation_deg)

    def _surface_world_points(self, surface_id, points):
        surface = self.surfaces[surface_id]
        plane = self.profiles[surface.profile_id].plane
        source = np.asarray(points, dtype=float)
        local = plane.world(points)
        matrix = self._surface_matrix(surface_id)
        world = local @ matrix[:3, :3].T + matrix[:3, 3]
        if not np.isfinite(world).all():
            raise ValidationError("Umístění dává nekonečnou geometrii.")
        for a, b, wa, wb in zip(
            source, np.roll(source, -1, axis=0), world, np.roll(world, -1, axis=0)
        ):
            reference, actual = (
                math.dist(a, b) * self.scale,
                math.dist(wa, wb) * self.scale,
            )
            if reference > 0 and (
                actual <= 0 or abs(reference - actual) > max(0.01, 1e-6 * reference)
            ):
                raise ValidationError("Umístění ztrácí požadovanou přesnost modelu.")
        return world

    def world_geometry(self, surface_id):
        surface = self.surfaces[surface_id]
        if surface.kind == "ruled_loft":
            return world_loft_geometry(self, surface)
        profile = self.profiles[surface.profile_id]
        outer = self.profile_outline(profile.id)
        holes = [self.profile_outline(h) for h in surface.hole_profile_ids]
        local, triangles = triangulate(outer, holes)
        vertices = self._surface_world_points(surface_id, local)
        normal = np.cross(profile.plane.u, profile.plane.v)
        normal = self._surface_matrix(surface_id)[:3, :3] @ normal
        if signed_area(outer) < 0:
            normal = -normal
        triangle_areas = []
        for face in triangles:
            a, b, c = vertices[face]
            cross = np.cross(b - a, c - a)
            area = math.hypot(*cross) / 2
            if not math.isfinite(area) or area <= 0 or np.dot(cross, normal) <= 0:
                raise ValidationError("Umístění ztrácí nenulovou orientovanou plochu materiálu.")
            triangle_areas.append(area)
        actual_area = math.fsum(triangle_areas) * self.scale * self.scale
        reference_area = (
            self._source_polygon(surface.profile_id, surface.hole_profile_ids).area
            * self.scale
            * self.scale
        )
        if (
            not math.isfinite(actual_area)
            or not math.isfinite(reference_area)
            or reference_area <= 0
            or abs(actual_area - reference_area) > max(0.01, 1e-6 * reference_area)
        ):
            raise ValidationError("Umístění ztrácí požadovanou plošnou přesnost materiálu.")
        boundary = []
        for p in [profile, *[self.profiles[h] for h in surface.hole_profile_ids]]:
            for edge in p.segments:
                samples = [p.vertex(edge.start_vertex_id).point, p.vertex(edge.end_vertex_id).point]
                if edge.kind != "line":
                    samples = next(
                        c["points"]
                        for c in self.profile_projection(p.id)["curves"]
                        if c["segment_id"] == edge.id
                    )
                points = self._surface_world_points(surface_id, samples)
                for first, second in zip(points, points[1:]):
                    boundary.append(
                        {"id": edge.id, "start": first.tolist(), "end": second.tolist()}
                    )
        return {
            "vertices": vertices.tolist(),
            "triangles": triangles.tolist(),
            "normal": normal.tolist(),
            "boundary": boundary,
        }

    def part_for_surface(self, surface_id):
        return self.surfaces[surface_id].part_id

    def surface_for_part(self, part_id):
        return self.parts[part_id].frame.root_surface_id

    def part_geometry(self, part_id):
        part = self.parts[part_id]
        return {
            "polygons": copy.deepcopy(part.polygons),
            "paths": copy.deepcopy(part.paths),
            "labels": copy.deepcopy(part.labels),
            "edges": copy.deepcopy(part.edges),
            "surface_ids": list(part.surface_ids),
            "stale": part.stale,
            "frame": asdict(part.frame),
        }

    @atomic
    def set_scale(self, scale):
        self.scale = number(scale, "Měřítko", positive=True)
        self._touch(self.surfaces)

    @atomic
    def recompute(self, part_ids=None):
        ids = list(self.material_part_ids() if part_ids is None else part_ids)
        built = {pid: build_part(self, self.parts[pid]) for pid in ids}
        self.parts.update(built)

    @atomic
    def set_anchor(self, part_id, root_surface_id, anchor_vertex_id=None, axis_segment_id=None):
        part = self.parts[part_id]
        if root_surface_id not in part.surface_ids:
            raise ValidationError("Kotva musí patřit do tohoto dílu.")
        profile = self.profiles[self.surfaces[root_surface_id].profile_id]
        part.frame = PaperFrame(
            root_surface_id,
            anchor_vertex_id or profile.vertices[0].id,
            axis_segment_id or profile.segments[0].id,
        )
        self._touch(part.surface_ids)
        self.parts[part_id] = build_part(self, part)

    @atomic
    def set_front_side(self, part_id, side):
        if side not in ("inside", "outside"):
            raise ValidationError("Zvolte lícovou nebo rubovou stranu.")
        part = self.parts[part_id]
        part.front_side = side
        self._touch(part.surface_ids)
        self.parts[part_id] = build_part(self, part)

    @atomic
    def add_page(self, *, landscape=False):
        page = Page(width_mm=297.0, height_mm=210.0) if landscape else Page()
        self.pages.append(page)
        self._touch()
        return page.id

    @atomic
    def set_page_orientation(self, page_id, *, landscape):
        if not isinstance(landscape, bool):
            raise ValidationError("Orientace stránky musí být explicitní volba.")
        page = next((p for p in self.pages if p.id == page_id), None)
        if page is None:
            raise ValidationError("Stránka neexistuje.")
        page.width_mm, page.height_mm = (297.0, 210.0) if landscape else (210.0, 297.0)
        self._touch()

    @atomic
    def delete_page(self, page_id):
        if len(self.pages) <= 1:
            raise ValidationError("V projektu musí zůstat alespoň jedna stránka.")
        if page_id not in {p.id for p in self.pages}:
            raise ValidationError("Stránka neexistuje.")
        self.pages = [p for p in self.pages if p.id != page_id]
        for placement in self.placements.values():
            if placement.page_id == page_id:
                placement.page_id = None
        self._touch()

    @atomic
    def set_placement(
        self,
        part_id,
        page_id=_UNSET,
        x_mm=None,
        y_mm=None,
        rotation_deg=None,
        *,
        position_locked=None,
        rotation_locked=None,
    ):
        placement = self.placements[part_id]
        new_page = placement.page_id if page_id is _UNSET else page_id
        x = placement.x_mm if x_mm is None else number(x_mm, "Poloha X")
        y = placement.y_mm if y_mm is None else number(y_mm, "Poloha Y")
        angle = placement.rotation_deg if rotation_deg is None else number(rotation_deg, "Úhel")
        if placement.position_locked and (
            new_page != placement.page_id or x != placement.x_mm or y != placement.y_mm
        ):
            raise ValidationError("Poloha dílu je zamčená. Nejprve zrušte zámek polohy.")
        if placement.rotation_locked and angle != placement.rotation_deg:
            raise ValidationError("Natočení dílu je zamčené. Nejprve zrušte zámek natočení.")
        placement.page_id, placement.x_mm, placement.y_mm, placement.rotation_deg = (
            new_page,
            x,
            y,
            angle,
        )
        if position_locked is not None:
            if not isinstance(position_locked, bool):
                raise ValidationError("Neplatný zámek polohy.")
            placement.position_locked = position_locked
        if rotation_locked is not None:
            if not isinstance(rotation_locked, bool):
                raise ValidationError("Neplatný zámek natočení.")
            placement.rotation_locked = rotation_locked
        self._touch()

    def _components(self):
        neighbors = {sid: set() for sid in self.surfaces}
        for joint in self.joints.values():
            if joint.mode == "fold":
                neighbors[joint.surface_a].add(joint.surface_b)
                neighbors[joint.surface_b].add(joint.surface_a)
        components = []
        while neighbors:
            pending, component = [next(iter(neighbors))], set()
            while pending:
                sid = pending.pop()
                if sid in component:
                    continue
                component.add(sid)
                pending.extend(neighbors[sid] - component)
            for sid in component:
                neighbors.pop(sid)
            components.append(component)
        return components

    @atomic
    def connect_edges(self, surface_a, edge_a, surface_b, edge_b, *, mode="cut"):
        if surface_a == surface_b:
            raise ValidationError("Spoj musí mít dva různé povrchy.")
        if any(
            (sid, edge) in [(j.surface_a, j.edge_a), (j.surface_b, j.edge_b)]
            for j in self.joints.values()
            for sid, edge in [(surface_a, edge_a), (surface_b, edge_b)]
        ):
            raise ValidationError("Tato hrana již má protikus.")
        joint = Joint(
            identity(), surface_a, edge_a, surface_b, edge_b, number=self.next_joint_number
        )
        validate_joint_contact(self, joint)
        self.next_joint_number += 1
        self.joints[joint.id] = joint
        self._touch((surface_a, surface_b))
        self.recompute([self.surfaces[surface_a].part_id, self.surfaces[surface_b].part_id])
        if mode != "cut":
            self.set_joint(joint.id, mode=mode)
        return joint.id

    @atomic
    def place_and_connect_edges(
        self, surface_a, edge_a, surface_b, edge_b, *, angle_deg=90.0, mode="cut"
    ):
        """Explicit author command: rigidly place the second face, then connect."""
        if surface_a == surface_b:
            raise ValidationError("Vyberte hrany dvou různých ploch.")
        if any(surface_b in (j.surface_a, j.surface_b) for j in self.joints.values()):
            raise ValidationError("Přesouvaná plocha již má spoje. Nejprve je výslovně upravte.")
        angle = number(angle_deg, "Úhel mezi plochami")
        a, b = edge_world(self, surface_a, edge_a), edge_world(self, surface_b, edge_b)
        length_a, length_b = np.linalg.norm(a[1] - a[0]), np.linalg.norm(b[1] - b[0])
        if abs(length_a - length_b) > max(1e-6, 1e-9 * length_a):
            raise ValidationError(
                "Hrany mají různou délku. Změňte rozměr protikusu před připojením."
            )
        x_a, x_b = (a[1] - a[0]) / length_a, (b[1] - b[0]) / length_b
        z_a = np.asarray(self.world_geometry(surface_a)["normal"])
        z_b = np.asarray(self.world_geometry(surface_b)["normal"])
        z_desired = Rotation.from_rotvec(x_a * np.deg2rad(angle)).apply(z_a)
        current_basis = np.column_stack([x_b, np.cross(z_b, x_b), z_b])
        desired_basis = np.column_stack([-x_a, np.cross(z_desired, -x_a), z_desired])
        rotation = desired_basis @ current_basis.T
        incremental = np.eye(4)
        incremental[:3, :3] = rotation
        incremental[:3, 3] = a[1] - rotation @ b[0]
        surface = self.surfaces[surface_b]
        parent = np.eye(4)
        for matrix in surface.parent_transforms:
            parent = parent @ validate_rigid(matrix)
        local = np.linalg.inv(parent) @ incremental @ self._surface_matrix(surface_b)
        validate_rigid(local)
        surface.position_mm = local[:3, 3].tolist()
        # Euler gimbal lock has nonunique coordinates, not an invalid rotation.
        # SciPy chooses an equivalent canonical zero-third-angle representation.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Gimbal lock detected.*", category=UserWarning
            )
            surface.rotation_deg = (
                Rotation.from_matrix(local[:3, :3]).as_euler("xyz", degrees=True).tolist()
            )
        self._touch([surface_b])
        return self.connect_edges(surface_a, edge_a, surface_b, edge_b, mode=mode)

    @atomic
    def set_joint(self, joint_id, *, mode, receiving_part_id=None):
        if mode not in ("cut", "fold"):
            raise ValidationError("Zvolte řez nebo přehyb.")
        joint = self.joints[joint_id]
        if joint.mode == mode:
            return
        old_parts, old_placements = copy.deepcopy(self.parts), copy.deepcopy(self.placements)
        affected = {self.surfaces[joint.surface_a].part_id, self.surfaces[joint.surface_b].part_id}
        if any(self.parts[pid].stale for pid in affected):
            raise ValidationError("Nejprve přepočítejte neaktuální rozvin dotčeného dílu.")
        if mode == "fold" and len(affected) == 1:
            raise ValidationError("Přehyb by uzavřel cyklus. Ponechte alespoň jeden řez.")
        if receiving_part_id is not None and receiving_part_id not in affected:
            raise ValidationError("Přijímací díl se tohoto spoje neúčastní.")
        joint.mode, joint.revision = mode, joint.revision + 1
        self._touch((joint.surface_a, joint.surface_b))
        receiver = receiving_part_id or self.surfaces[joint.surface_a].part_id
        new_parts, new_placements = {}, {}
        for component in self._components():
            candidates = [p for p in old_parts.values() if p.frame.root_surface_id in component]
            candidates.sort(key=lambda p: (p.id != receiver, p.name))
            source = (
                candidates[0]
                if candidates
                else old_parts[self.surfaces[next(iter(component))].part_id]
            )
            if candidates:
                part = copy.deepcopy(source)
                part.surface_ids = sorted(component)
                placement = copy.deepcopy(old_placements[part.id])
            else:
                sid = sorted(component)[0]
                profile = self.profiles[self.surfaces[sid].profile_id]
                part = MaterialPart(
                    identity(),
                    f"P{self.next_part_number} · {self.surfaces[sid].name}",
                    sorted(component),
                    PaperFrame(sid, profile.vertices[0].id, profile.segments[0].id),
                    lineage=[source.id],
                    number=self.next_part_number,
                )
                self.next_part_number += 1
                placement = copy.deepcopy(old_placements[source.id])
            part.lineage = list(
                dict.fromkeys(
                    [
                        *part.lineage,
                        *[
                            p.id
                            for p in old_parts.values()
                            if set(p.surface_ids) & component and p.id != part.id
                        ],
                    ]
                )
            )
            for sid in component:
                self.surfaces[sid].part_id = part.id
            new_parts[part.id], new_placements[part.id] = part, placement
        self.parts, self.placements = new_parts, new_placements
        self.recompute()
        for pid, part in self.parts.items():
            if pid in old_parts:
                continue
            sid = part.frame.root_surface_id
            source = next(p for p in old_parts.values() if sid in p.surface_ids)
            previous, current = np.array(source.polygons[sid][0]), np.array(part.polygons[sid][0])
            a, b = previous[1] - previous[0], current[1] - current[0]
            angle = np.arctan2(a[1], a[0]) - np.arctan2(b[1], b[0])
            old_place = old_placements[source.id]
            old_angle = np.deg2rad(old_place.rotation_deg)
            self.placements[pid].rotation_deg = old_place.rotation_deg + float(np.rad2deg(angle))
            new_angle = np.deg2rad(self.placements[pid].rotation_deg)

            def rotate(point, theta):
                return (
                    np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
                    @ point
                )

            offset = (
                np.array([old_place.x_mm, old_place.y_mm])
                + rotate(previous[0], old_angle)
                - rotate(current[0], new_angle)
            )
            self.placements[pid].x_mm, self.placements[pid].y_mm = map(float, offset)

    @atomic
    def set_tab(self, joint_id, *, owner=_UNSET, width_mm=None, taper=None, shape=None):
        joint = self.joints[joint_id]
        if joint.mode != "cut":
            raise ValidationError("Chlopeň lze přidat k lepenému řezu, ne k souvislému přehybu.")
        if owner is None:
            if joint.connector_id:
                self.connectors.pop(joint.connector_id)
                joint.connector_id = None
        else:
            if owner is _UNSET:
                chosen = (
                    self.connectors[joint.connector_id].owner_surface_id
                    if joint.connector_id
                    else joint.surface_a
                )
            else:
                chosen = owner
            if chosen not in (joint.surface_a, joint.surface_b):
                raise ValidationError("Chlopeň musí patřit jednomu z protikusů.")
            if not joint.connector_id:
                connector = Connector(identity(), joint.id, chosen)
                joint.connector_id = connector.id
                self.connectors[connector.id] = connector
            connector = self.connectors[joint.connector_id]
            if not connector.tab_ids:
                connector.tab_ids = [identity()]
            if connector.owner_surface_id != chosen:
                connector.receiver_side = "unknown"
            connector.owner_surface_id = chosen
            if width_mm is not None:
                connector.width_mm = number(width_mm, "Šířka chlopně", positive=True)
            if taper is not None:
                connector.taper = number(taper, "Zkosení")
            if shape is not None:
                connector.shape = shape
            connector.revision += 1
        joint.revision += 1
        self._touch()
        self.recompute(
            {self.surfaces[joint.surface_a].part_id, self.surfaces[joint.surface_b].part_id}
        )

    def validate_layout(self):
        return validate_layout(self)

    def connector_bend_clearance(self, connector_id):
        # Direct property-panel queries must use the same physical selection as
        # layout/snapshot. Retained targets and inactive generations are explicit
        # construction references, not extra coincident material obstacles.
        if self.segmented_variants and not getattr(self, "_is_print_material_view", False):
            self.validate()
            material = self.print_material_view()
            material._bend_cache = getattr(self, "_material_bend_cache", None)
            result = BendCommands.connector_bend_clearance(material, connector_id)
            self._material_bend_cache = getattr(material, "_bend_cache", None)
            return result
        return BendCommands.connector_bend_clearance(self, connector_id)

    @property
    def issues(self):
        return self.validate_layout()

    @atomic
    def acknowledge(self, issue_id):
        found = next((i for i in self.validate_layout() if i.id == issue_id), None)
        if found is None or found.severity != "warning":
            raise ValidationError("Lze přijmout pouze aktuální konkrétní varování.")
        self.acknowledgements[issue_id] = found.digest

    def snapshot(self):
        issues = self.validate_layout()
        blocking = [i for i in issues if i.severity == "error" or not i.acknowledged]
        if blocking:
            raise ValidationError(
                "Export vyžaduje opravu nebo potvrzení: " + "; ".join(i.message for i in blocking)
            )
        material = self.print_material_view()
        if not material.parts:
            raise ValidationError("Projekt zatím nemá žádný vystřihovaný díl.")
        pages = []
        for page in self.pages:
            parts = []
            for pid, part in material.parts.items():
                placement = self.placements[pid]
                if placement.page_id != page.id:
                    continue
                paths = copy.deepcopy(part.paths)
                paths.update(LABELS=[], ARTWORK=[])
                parts.append(
                    {
                        "id": pid,
                        "name": part.name,
                        "surface_ids": list(part.surface_ids),
                        "source_revision": self.revision,
                        "placement": {
                            k: getattr(placement, k) for k in ("x_mm", "y_mm", "rotation_deg")
                        },
                        "paths": paths,
                        "labels": copy.deepcopy(part.labels),
                    }
                )
                owner = next(
                    (
                        v
                        for v in self.segmented_variants.values()
                        if v.print_selected
                        and any(r["part_id"] == pid for r in v.triangle_bindings)
                    ),
                    None,
                )
                if owner is not None:
                    record = next(r for r in owner.triangle_bindings if r["part_id"] == pid)
                    parts[-1]["flattening"] = {
                        "mode": "APPROXIMATE",
                        "material_surface_mode": "EXACT_PLANAR_TRIANGLE",
                        "scope": "TRIANGLE_CORE_VS_RETAINED_TARGET; CONNECTORS_CHECKED_SEPARATELY",
                        "variant_id": owner.id,
                        "target_surface_id": owner.target_surface_id,
                        "triangle_id": record["id"],
                        "source_parameter_key": record["source_parameter_key"],
                        "max_surface_deviation_paper_mm_exact": owner.certificate["material_frame"][
                            "max_target_to_material_deviation_paper_mm_exact"
                        ],
                    }
            pages.append(
                {
                    "id": page.id,
                    "width_mm": page.width_mm,
                    "height_mm": page.height_mm,
                    "parts": parts,
                }
            )
        return {
            "project_id": self.project_id,
            "revision": self.revision,
            "construction_checks": {
                "material_profile": copy.deepcopy(self.material_profile),
                "assembly_digest": material._assembly_clearance_key(),
                "connector_bends": {
                    cid: material.connector_bend_clearance(cid) for cid in material.connectors
                },
                "curve_profiles": material._planar_curve_reports("curve_projection_reports"),
                "curve_regions": material._planar_curve_reports("curve_region_reports"),
                "lofts": {
                    sid: self.loft_status(sid)
                    for sid, surface in material.surfaces.items()
                    if surface.kind == "ruled_loft"
                },
                "segmented_variants": {
                    vid: self.segmented_variant_status(vid)
                    for vid, variant in self.segmented_variants.items()
                    if variant.print_selected
                },
                "reference_targets": {
                    variant.target_surface_id: self.loft_status(variant.target_surface_id)
                    for variant in self.segmented_variants.values()
                    if variant.print_selected
                },
                "accepted_layout_overlaps": [
                    list(issue.part_ids)
                    for issue in issues
                    if issue.code == "MATERIAL_OVERLAP" and issue.acknowledged
                ],
                "physical_build": "NOT_VERIFIED",
            },
            "scale_label": f"1:{1 / self.scale:g}",
            "coverage": {
                "expected_part_ids": list(material.parts),
                "expected_surface_ids": list(material.surfaces),
                "expected_segmented_variant_ids": [
                    vid
                    for vid, variant in self.segmented_variants.items()
                    if variant.print_selected
                ],
                "all_construction_surface_ids": list(self.surfaces),
                "reference_surface_ids": [
                    v.target_surface_id
                    for v in self.segmented_variants.values()
                    if v.print_selected
                ],
                "inactive_variant_surface_ids": [
                    r["surface_id"]
                    for v in self.segmented_variants.values()
                    if not v.print_selected
                    for r in v.triangle_bindings
                ],
                "expected_loft_surface_ids": [
                    sid
                    for sid, surface in material.surfaces.items()
                    if surface.kind == "ruled_loft"
                ],
                "source_revisions": {pid: self.revision for pid in material.parts},
            },
            "pages": pages,
        }

    def _planar_curve_reports(self, method):
        view = copy.copy(self)
        view.surfaces = {sid: s for sid, s in self.surfaces.items() if s.kind == "planar"}
        return getattr(ProfileCurveCommands, method)(view)

    def _assembly_clearance_key(self):
        base = BendCommands._assembly_clearance_key(self)
        profiles = {
            pid: asdict(self.profiles[pid])
            for surface in self.surfaces.values()
            if surface.kind == "ruled_loft"
            for pid in surface.source_profile_ids()
        }
        if not profiles:
            return base
        from .paper import digest

        return digest({"assembly": base, "loft_source_profiles": profiles})

    def _state_for_digest(self):
        data = self.to_dict(validate=False)
        data.pop("acknowledgements")
        data.pop("revision")
        return data

    def validate(self):
        uuid(self.project_id)
        self._validate_material_profile()
        if not isinstance(self.name, str):
            raise ValidationError("Název projektu musí být text.")
        number(self.scale, "Měřítko", positive=True)
        _revision(self.revision)
        _revision(self.next_part_number)
        _revision(self.next_joint_number)
        all_ids = [self.project_id]
        for pid, profile in self.profiles.items():
            if profile.id != pid:
                raise ValidationError("Identita profilu nesouhlasí s registrem.")
            profile.validate()
            all_ids.extend(
                [pid, *[v.id for v in profile.vertices], *[s.id for s in profile.segments]]
            )
            if profile.closed and all(s.kind == "line" for s in profile.segments):
                material_polygon(profile.points)
        extra_ids, derived_children = self._validate_segmented_variants()
        all_ids.extend(extra_ids)
        expected_surfaces = []
        if set(self.parts) != set(self.placements):
            raise ValidationError("Každý díl musí mít právě jeden záznam umístění.")
        for sid, surface in self.surfaces.items():
            uuid(sid)
            all_ids.append(sid)
            if (
                surface.id != sid
                or surface.profile_id not in self.profiles
                or not isinstance(surface.name, str)
            ):
                raise ValidationError("Neplatný registr povrchů.")
            if surface.kind == "ruled_loft":
                all_ids.extend(validate_loft_params(self, surface))
                vector(surface.position_mm, 3)
                vector(surface.rotation_deg, 3)
                _revision(surface.revision)
                self._surface_matrix(sid)
                result = loft_analysis(self, surface)
                if any(
                    report["status"] == "INVALID"
                    for report in result.get("source_topology", {}).values()
                ):
                    raise ValidationError("Zdrojový profil loftu se kříží nebo překrývá.")
                self.world_geometry(sid)
                if (
                    surface.part_id not in self.parts
                    or sid not in self.parts[surface.part_id].surface_ids
                ):
                    raise ValidationError("Loft nemá platný vlastní materiálový díl.")
                continue
            if surface.kind != "planar" or (surface.params != {} and sid not in derived_children):
                raise UnsupportedOperationError(
                    "Tento typ konstrukční plochy zatím není implementovaný."
                )
            if len(set(surface.hole_profile_ids)) != len(surface.hole_profile_ids) or any(
                h not in self.profiles for h in surface.hole_profile_ids
            ):
                raise ValidationError("Neplatné reference otvorů.")
            self._source_polygon(surface.profile_id, surface.hole_profile_ids)
            vector(surface.position_mm, 3)
            vector(surface.rotation_deg, 3)
            _revision(surface.revision)
            self._surface_matrix(sid)
            # Validate the rendered material, including hole boundaries and every
            # constrained triangle, before accepting an authoring command.
            self.world_geometry(sid)
            area = (
                self._source_polygon(surface.profile_id, surface.hole_profile_ids).area
                * self.scale
                * self.scale
            )
            if not np.isfinite(area) or area <= 0:
                raise ValidationError("Měřítko dává neplatnou plochu na papíře.")
            if (
                surface.part_id not in self.parts
                or sid not in self.parts[surface.part_id].surface_ids
            ):
                raise ValidationError("Povrch nemá platný papírový díl.")
        pages = set()
        if not self.pages:
            raise ValidationError("Projekt potřebuje alespoň jednu stránku.")
        for page in self.pages:
            uuid(page.id)
            if page.id in pages:
                raise ValidationError("Duplicitní stránka.")
            pages.add(page.id)
            all_ids.append(page.id)
            for value in (page.width_mm, page.height_mm):
                number(value, "Rozměr stránky", positive=True)
            margin = number(page.margin_mm, "Okraj", nonnegative=True)
            if margin * 2 >= min(page.width_mm, page.height_mm):
                raise ValidationError("Tiskový okraj spotřebuje celý list.")
        part_numbers = set()
        for pid, part in self.parts.items():
            uuid(pid)
            all_ids.append(pid)
            if (
                part.id != pid
                or not isinstance(part.name, str)
                or not isinstance(part.stale, bool)
                or part.front_side not in ("inside", "outside")
            ):
                raise ValidationError("Neplatný záznam dílu.")
            _revision(part.number)
            if part.number in part_numbers or part.number >= self.next_part_number:
                raise ValidationError("Čísla dílů musí být jednoznačná a čítač monotónní.")
            part_numbers.add(part.number)
            if (
                not part.surface_ids
                or len(set(part.surface_ids)) != len(part.surface_ids)
                or any(s not in self.surfaces for s in part.surface_ids)
            ):
                raise ValidationError("Neplatné pokrytí dílu.")
            expected_surfaces.extend(part.surface_ids)
            if part.frame.root_surface_id not in part.surface_ids:
                raise ValidationError("Kotva nepatří do dílu.")
            root_profile = self.profiles[self.surfaces[part.frame.root_surface_id].profile_id]
            if not part.stale and (
                root_profile.vertex(part.frame.anchor_vertex_id) is None
                or root_profile.segment(part.frame.axis_segment_id) is None
            ):
                raise ValidationError("Aktuální díl nemá platnou referenci kotvy.")
            if (
                not isinstance(part.lineage, list)
                or len(set(part.lineage)) != len(part.lineage)
                or part.id in part.lineage
            ):
                raise ValidationError("Neplatný původ dílu.")
            for ancestor in part.lineage:
                uuid(ancestor)
            unresolved_new_loft = (
                part.stale
                and not part.polygons
                and len(part.surface_ids) == 1
                and self.surfaces[part.surface_ids[0]].kind == "ruled_loft"
            )
            if not isinstance(part.polygons, dict) or (
                not unresolved_new_loft and set(part.polygons) != set(part.surface_ids)
            ):
                raise ValidationError("Uložený rozvin nepokrývá všechny povrchy.")
            for loops in part.polygons.values():
                if not isinstance(loops, list) or not loops:
                    raise ValidationError("Uložený rozvin nemá obrys.")
                material_polygon(loops[0], loops[1:])
            if not isinstance(part.paths, dict) or set(part.paths) != set(ROLES):
                raise ValidationError("Uložený rozvin nemá úplné role cest.")
            for values in part.paths.values():
                for p in values:
                    if set(p) == {"commands", "closed"}:
                        from .profile_curves import validate_native_path

                        validate_native_path(p)
                        continue
                    if (
                        set(p) != {"points", "closed"}
                        or not isinstance(p["closed"], bool)
                        or len(p["points"]) < 2
                    ):
                        raise ValidationError("Neplatná uložená cesta.")
                    for point in p["points"]:
                        vector(point, 2)
            if (
                type(part.source_revision) is not int
                or not 0 <= part.source_revision <= self.revision
            ):
                raise ValidationError("Neplatná revize rozvinu.")
            if (
                not isinstance(part.input_digest, str)
                or not isinstance(part.labels, list)
                or not isinstance(part.edges, list)
            ):
                raise ValidationError("Neplatná metadata rozvinu.")
            for label in part.labels:
                if (
                    not isinstance(label, dict)
                    or set(label) != {"text", "x", "y", "size_mm"}
                    or not isinstance(label["text"], str)
                ):
                    raise ValidationError("Neplatný štítek dílu.")
                number(label["x"])
                number(label["y"])
                number(label["size_mm"], positive=True)
            for edge in part.edges:
                if (
                    not isinstance(edge, dict)
                    or set(edge)
                    not in (
                        {"surface_id", "edge_id", "start", "end"},
                        {"surface_id", "edge_id", "start", "end", "source"},
                    )
                    or edge["surface_id"] not in part.surface_ids
                ):
                    raise ValidationError("Neplatná uložená hrana rozvinu.")
                uuid(edge["edge_id"])
                if "source" in edge:
                    surface = self.surfaces[edge["surface_id"]]
                    source = edge["source"]
                    if (
                        surface.kind != "ruled_loft"
                        or not isinstance(source, dict)
                        or set(source)
                        != {
                            "feature_id",
                            "patch_id",
                            "profile_id",
                            "segment_id",
                            "role",
                            "parameter_interval",
                        }
                        or source["feature_id"] != surface.id
                        or source["segment_id"] != edge["edge_id"]
                    ):
                        raise ValidationError("Neplatný původ rozvinuté loft hrany.")
                    if source["role"] not in ("FIRST", "SECOND"):
                        raise ValidationError("Neplatná strana zdrojové hranice loftu.")
                    for key in ("patch_id", "profile_id", "segment_id"):
                        uuid(source[key])
                    side = source["role"].lower()
                    interval = source["parameter_interval"]
                    if not isinstance(interval, list) or len(interval) != 2:
                        raise ValidationError("Zdrojová hranice loftu neodpovídá patchi.")
                    for value in interval:
                        number(value, "Zdrojový parametr loft hrany")
                        if not 0 <= value <= 1:
                            raise ValidationError("Zdrojový parametr je mimo původní úsek.")
                    if interval[1] == interval[0]:
                        raise ValidationError("Uložená hrana loftu změnila směr zdroje.")
                    if not part.stale:
                        record = next(
                            (
                                r
                                for r in surface.params["correspondences"]
                                if r["id"] == source["patch_id"]
                            ),
                            None,
                        )
                        expected_profile = surface.source_profile_ids()[0 if side == "first" else 1]
                        if (
                            record is None
                            or source["profile_id"] != expected_profile
                            or source["segment_id"] != record[side + "_segment_id"]
                            or (interval[1] - interval[0])
                            * (record[side + "_interval"][1] - record[side + "_interval"][0])
                            <= 0
                        ):
                            raise ValidationError(
                                "Aktuální hrana loftu nemá platnou zdrojovou vazbu."
                            )
                vector(edge["start"], 2)
                vector(edge["end"], 2)
            placement = self.placements[pid]
            if placement.page_id is not None and placement.page_id not in pages:
                raise ValidationError("Díl odkazuje na chybějící stránku.")
            for value in (placement.x_mm, placement.y_mm, placement.rotation_deg):
                number(value)
            if not isinstance(placement.position_locked, bool) or not isinstance(
                placement.rotation_locked, bool
            ):
                raise ValidationError("Neplatné zámky umístění.")
        if sorted(expected_surfaces) != sorted(self.surfaces):
            raise ValidationError("Materiálové díly nepokrývají právě všechny plochy.")
        occupied_edges, connector_ids, numbers = set(), [], set()
        for jid, joint in self.joints.items():
            uuid(jid)
            all_ids.append(jid)
            if (
                joint.id != jid
                or joint.surface_a == joint.surface_b
                or joint.mode not in ("cut", "fold")
            ):
                raise ValidationError("Neplatný konstrukční spoj.")
            if not isinstance(joint.unresolved, bool):
                raise ValidationError("Neplatný stav reference spoje.")
            for sid, edge_id in ((joint.surface_a, joint.edge_a), (joint.surface_b, joint.edge_b)):
                if (
                    sid not in self.surfaces
                    or (
                        not joint.unresolved
                        and self.profiles[self.surfaces[sid].profile_id].segment(edge_id) is None
                    )
                    or (sid, edge_id) in occupied_edges
                ):
                    raise ValidationError("Neplatná nebo vícekrát připojená hrana.")
                occupied_edges.add((sid, edge_id))
            _revision(joint.revision)
            _revision(joint.number)
            if joint.number in numbers or joint.number >= self.next_joint_number:
                raise ValidationError("Číslo spoje není jednoznačné.")
            numbers.add(joint.number)
            if joint.connector_id:
                if joint.connector_id not in self.connectors:
                    raise ValidationError("Chybějící chlopeň spoje.")
                connector_ids.append(joint.connector_id)
        all_ids.extend(self._validate_interior(connector_ids))
        if sorted(connector_ids) != sorted(self.connectors):
            raise ValidationError("Neplatné pokrytí spojovacích prvků.")
        for cid, connector in self.connectors.items():
            uuid(cid)
            all_ids.append(cid)
            if connector.id != cid:
                raise ValidationError("Neplatná chlopeň.")
            if connector.attachment_id:
                attachment = self.attachments.get(connector.attachment_id)
                if (
                    attachment is None
                    or attachment.connector_id != cid
                    or connector.joint_id
                    or connector.owner_surface_id != attachment.source_surface_id
                    or connector.receiver_side != "unknown"
                ):
                    raise ValidationError("Chlopeň nemá právě jednoho vlastníka a protikus.")
            else:
                joint = self.joints.get(connector.joint_id)
                if (
                    joint is None
                    or joint.connector_id != cid
                    or connector.owner_surface_id
                    not in (
                        joint.surface_a,
                        joint.surface_b,
                    )
                ):
                    raise ValidationError("Chlopeň nemá právě jednoho vlastníka a protikus.")
            number(connector.width_mm, "Šířka chlopně", positive=True)
            if connector.receiver_side not in ("unknown", "inside", "outside"):
                raise ValidationError("Neplatná strana přijímající plochy chlopně.")
            if not 0 < number(connector.taper) <= 1 or connector.shape not in (
                "triangle",
                "trapezoid",
                "custom",
            ):
                raise ValidationError("Neplatný tvar chlopně.")
            _revision(connector.revision)
            if (
                type(connector.count) is not int
                or not 1 <= connector.count <= 4096
                or not isinstance(connector.enabled, bool)
                or not isinstance(connector.tab_ids, list)
                or len(set(connector.tab_ids)) != len(connector.tab_ids)
                or len(connector.tab_ids) != connector.count
                or not isinstance(connector.tab_overrides, dict)
                or set(connector.tab_overrides) - set(connector.tab_ids)
                or any(not isinstance(v, dict) for v in connector.tab_overrides.values())
            ):
                raise ValidationError("Neplatné identity nebo parametry dělených záložek.")
            number(connector.gap_mm, "Mezera záložek", nonnegative=True)
            for tab_id in connector.tab_ids:
                uuid(tab_id)
                all_ids.append(tab_id)
            for outline in [
                connector.outline_mm,
                *[change.get("outline_mm", []) for change in connector.tab_overrides.values()],
            ]:
                if outline:
                    material_polygon(outline)
            for change in connector.tab_overrides.values():
                if not isinstance(change, dict) or set(change) - {
                    "enabled",
                    "width_mm",
                    "taper",
                    "shape",
                    "outline_mm",
                }:
                    raise ValidationError("Neplatná individuální úprava záložky.")
                if "enabled" in change and not isinstance(change["enabled"], bool):
                    raise ValidationError("Vypnutí záložky je explicitní volba.")
                if "width_mm" in change:
                    number(change["width_mm"], positive=True)
                if "taper" in change and not 0 < number(change["taper"]) <= 1:
                    raise ValidationError("Neplatné zkosení záložky.")
                if "shape" in change and change["shape"] not in ("triangle", "trapezoid", "custom"):
                    raise ValidationError("Neplatný individuální tvar záložky.")
        if len(set(all_ids)) != len(all_ids):
            raise ValidationError("Entity sdílejí stejnou identitu.")
        components = {frozenset(c) for c in self._components()}
        if components != {frozenset(p.surface_ids) for p in self.parts.values()}:
            raise ValidationError("Papírové díly neodpovídají grafu skutečných přehybů.")
        if sum(j.mode == "fold" for j in self.joints.values()) != sum(
            len(p.surface_ids) - 1 for p in self.parts.values()
        ):
            raise ValidationError("Přehyby obsahují nepodporovaný cyklus.")
        if not isinstance(self.acknowledgements, dict) or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in self.acknowledgements.items()
        ):
            raise ValidationError("Neplatné potvrzení varování.")

    def to_dict(self, *, validate=True):
        if validate:
            self.validate()
        return {
            "application": APPLICATION,
            "schema_version": SCHEMA_VERSION,
            "status": "experimental",
            "writer_version": WRITER_VERSION,
            "project_id": self.project_id,
            "name": self.name,
            "scale": self.scale,
            "material_profile": copy.deepcopy(self.material_profile),
            "segmented_variants": {vid: asdict(v) for vid, v in self.segmented_variants.items()},
            "revision": self.revision,
            "next_part_number": self.next_part_number,
            "next_joint_number": self.next_joint_number,
            "next_attachment_number": self.next_attachment_number,
            **{
                key: {k: asdict(v) for k, v in getattr(self, key).items()}
                for key in (
                    "profiles",
                    "surfaces",
                    "parts",
                    "joints",
                    "connectors",
                    "placements",
                    "attachments",
                )
            },
            "pages": [asdict(p) for p in self.pages],
            "acknowledgements": copy.deepcopy(self.acknowledgements),
        }

    @classmethod
    def from_dict(cls, data):
        data = copy.deepcopy(data)
        # An explicitly identified006A document has its own complete envelope.
        # Missing B registries in schema2 are corruption, never a legacy fallback.
        upgrading = (
            isinstance(data, dict)
            and type(data.get("schema_version")) is int
            and data["schema_version"] == 1
            and data.get("writer_version") == "0.3.0-experimental"
        )
        upgrading_b = (
            isinstance(data, dict)
            and type(data.get("schema_version")) is int
            and data["schema_version"] == 2
            and data.get("writer_version") == "0.3.0-pc006b-experimental"
        )
        upgrading_c = (
            isinstance(data, dict)
            and type(data.get("schema_version")) is int
            and data["schema_version"] == 3
            and data.get("writer_version") == "0.3.0-pc006b-clearance-experimental"
        )
        upgrading_d = (
            isinstance(data, dict)
            and type(data.get("schema_version")) is int
            and data["schema_version"] == 4
            and data.get("writer_version") == "0.3.0-pc007a-profiles-experimental"
        )
        if upgrading or upgrading_b or upgrading_c or upgrading_d:
            if not isinstance(data.get("surfaces"), dict):
                raise ProjectFormatError("Starší registr povrchů musí být objekt.")
            if "segmented_variants" in data or any(
                isinstance(s, dict)
                and isinstance(s.get("params"), dict)
                and {"segmented_variant_id", "triangle_id"} & set(s["params"])
                for s in data.get("surfaces", {}).values()
            ):
                raise ProjectFormatError("Starší formát nezná odvozené segmentované varianty.")
            data["segmented_variants"] = {}
        if upgrading_d:
            data["schema_version"] = SCHEMA_VERSION
        if upgrading or upgrading_b or upgrading_c:
            # These published experimental envelopes knew only straight
            # sketches and planar features. A version-label change must not
            # smuggle newer capabilities through a permissive copy adapter.
            surfaces, profiles = data.get("surfaces"), data.get("profiles")
            if (
                not isinstance(surfaces, dict)
                or any(
                    not isinstance(record, dict)
                    or record.get("kind") != "planar"
                    or record.get("params") != {}
                    for record in surfaces.values()
                )
                or not isinstance(profiles, dict)
                or any(
                    not isinstance(record, dict)
                    or not isinstance(record.get("segments"), list)
                    or any(
                        not isinstance(segment, dict)
                        or segment.get("kind") != "line"
                        or segment.get("data") != {}
                        for segment in record["segments"]
                    )
                    for record in profiles.values()
                )
            ):
                raise ProjectFormatError(
                    "Starší formát nezná křivkové profily ani nerovinné konstrukční plochy."
                )
        if upgrading_c:
            data["schema_version"] = SCHEMA_VERSION
        if upgrading:
            if any(
                key in data for key in ("attachments", "next_attachment_number", "material_profile")
            ):
                raise ProjectFormatError("Projekt006A obsahuje neočekávaná pole novějšího formátu.")
            data.update(
                attachments={},
                next_attachment_number=1,
                material_profile=copy.deepcopy(DEFAULT_MATERIAL_PROFILE),
            )
            data["schema_version"] = SCHEMA_VERSION
        if upgrading_b:
            if "material_profile" in data:
                raise ProjectFormatError(
                    "Starý B dokument obsahuje pole novější materiálové verze."
                )
            data.update(
                material_profile=copy.deepcopy(DEFAULT_MATERIAL_PROFILE),
                schema_version=SCHEMA_VERSION,
            )
            if isinstance(data.get("connectors"), dict):
                known_fields = set(asdict(Connector("", "", "")))
                for record in data["connectors"].values():
                    if not isinstance(record, dict) or set(record) not in (
                        known_fields,
                        known_fields - {"receiver_side"},
                    ):
                        raise ProjectFormatError("Neznámá struktura původní B chlopně.")
                    record.setdefault("receiver_side", "unknown")
                    if record["tab_ids"] == [] and record["count"] == 1:
                        record["tab_ids"] = [identity()]
        if upgrading and isinstance(data.get("connectors"), dict):
            old_connector_fields = {
                "id",
                "joint_id",
                "owner_surface_id",
                "width_mm",
                "taper",
                "shape",
                "revision",
            }
            for record in data["connectors"].values():
                if not isinstance(record, dict) or set(record) != old_connector_fields:
                    raise ProjectFormatError("Neplatná původní chlopeň projektu006A.")
                defaults = asdict(Connector("", "", ""))
                record.update({k: v for k, v in defaults.items() if k not in record})
                # 006A had one implicit tab, not an independently addressable entity.
                # Allocate its explicit identity once when creating the editable copy.
                record["tab_ids"] = [identity()]
        if (upgrading or upgrading_b or upgrading_c) and isinstance(data.get("parts"), dict):
            for part in data["parts"].values():
                if isinstance(part, dict):
                    part["stale"] = True
        expected = {
            "application",
            "schema_version",
            "status",
            "writer_version",
            "project_id",
            "name",
            "scale",
            "material_profile",
            "segmented_variants",
            "revision",
            "next_part_number",
            "next_joint_number",
            "next_attachment_number",
            "profiles",
            "surfaces",
            "parts",
            "joints",
            "connectors",
            "attachments",
            "placements",
            "pages",
            "acknowledgements",
        }
        if (
            not isinstance(data, dict)
            or set(data) != expected
            or data["application"] != APPLICATION
            or type(data["schema_version"]) is not int
            or data["schema_version"] != SCHEMA_VERSION
            or data["status"] != "experimental"
            or not isinstance(data["writer_version"], str)
        ):
            raise ProjectFormatError("Neznámá verze nebo struktura autorského projektu.")
        try:
            project = cls(data["name"], data["scale"])
            for key in (
                "project_id",
                "revision",
                "next_part_number",
                "next_joint_number",
                "next_attachment_number",
                "acknowledgements",
                "material_profile",
            ):
                setattr(project, key, copy.deepcopy(data[key]))
            for key, cls_type in (
                ("surfaces", SurfaceFeature),
                ("joints", Joint),
                ("connectors", Connector),
                ("attachments", Attachment),
                ("placements", Placement),
                ("segmented_variants", SegmentedVariant),
            ):
                if not isinstance(data[key], dict):
                    raise ProjectFormatError("Registry projektu musí být objekty.")
                setattr(project, key, {k: _record(cls_type, v) for k, v in data[key].items()})
            project.profiles = {}
            for pid, raw in data["profiles"].items():
                raw = copy.deepcopy(raw)
                raw["vertices"] = [_record(Vertex, v) for v in raw["vertices"]]
                raw["segments"] = [_record(CurveSegment, s) for s in raw["segments"]]
                raw["plane"] = _record(SketchPlane, raw["plane"])
                project.profiles[pid] = _record(Profile, raw)
            project.parts = {}
            for pid, raw in data["parts"].items():
                raw = copy.deepcopy(raw)
                raw["frame"] = _record(PaperFrame, raw["frame"])
                project.parts[pid] = _record(MaterialPart, raw)
            project.pages = [_record(Page, p) for p in data["pages"]]
            project.validate()
            return project
        except (
            ValidationError,
            TypeError,
            KeyError,
            AttributeError,
            ValueError,
            IndexError,
            OverflowError,
        ) as exc:
            raise ProjectFormatError(f"Neplatný autorský projekt: {exc}") from exc

    def save(self, path):
        destination = Path(path)
        data = self.to_dict()
        if destination.exists():
            existing = load_project(destination)
            if isinstance(existing, LegacyProject) or existing.requires_save_as:
                raise UnsupportedOperationError(
                    "Starý projekt je pouze ke čtení. Uložte kopii pod novým názvem."
                )
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(
                prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            temporary = None
            self.requires_save_as = False
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    @classmethod
    def load(cls, path):
        return load_project(path)


class LegacyProject:
    read_only = True

    def __init__(self, raw_bytes, path):
        self.raw_bytes, self.path = raw_bytes, Path(path)

    @property
    def raw(self):
        return json.loads(self.raw_bytes.decode("utf-8-sig"))

    def save(self, path=None):
        raise UnsupportedOperationError("Starý projekt je pouze ke čtení.")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProjectFormatError(f"Duplicitní JSON klíč: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ProjectFormatError(f"JSON obsahuje nepovolenou hodnotu {value}.")


def load_project(path):
    source = Path(path)
    raw = source.read_bytes()
    try:
        data = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique, parse_constant=_constant
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectFormatError(f"Projekt není platný UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectFormatError("Kořen projektu musí být objekt.")
    if data.get("application") == "ArchPapercraft.PanelProject" or (
        data.get("version") == "0.2.0"
        and isinstance(data.get("settings"), dict)
        and isinstance(data.get("scene"), list)
    ):
        return LegacyProject(raw, source)
    project = AuthorProject.from_dict(data)
    project.loaded_from_schema = data.get("schema_version")
    project.requires_save_as = project.loaded_from_schema in (1, 2, 3, 4)
    project.loaded_source_path = str(source.resolve())
    return project
