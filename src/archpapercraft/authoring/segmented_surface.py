"""Confirmed, immutable generations of a retained live ruled target.

The original target is never overwritten or promoted to EXACT. A closed registry
selects either its material or one explicitly confirmed derived generation for
printing. Inactive generations retain their independent author layout.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict
from fractions import Fraction
from functools import lru_cache
from itertools import combinations

import numpy as np

from .commands import atomic
from .curve_area import _atan, _pi, _sqrt
from .errors import ValidationError
from .geometry import rigid_matrix, validate_rigid
from .loft_geometry import LoftCorrespondence, LoftProfile
from .loft_surface import _profile_from_record
from .model import (
    CurveSegment,
    MaterialPart,
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
from .segmented_loft import segment_ruled_loft

MAX_DOMAIN_TRIANGLES = 512
MAX_EMBEDDING_PAIRS = 200000


class SegmentationError(ValidationError):
    def __init__(self, message, report=None):
        self.code = "SEGMENTATION_UNRESOLVED"
        self.report = copy.deepcopy(report or {"status": "UNRESOLVED", "message": message})
        super().__init__(self.code + ": " + message)


def _json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _fingerprint(binding):
    data = copy.deepcopy(binding)
    for record in [data["surface"], *data["profiles"]]:
        record.pop("name", None)
        record.pop("revision", None)
    return _digest(data)


def _source_binding(project, target_id):
    surface = project.surfaces[target_id]
    if surface.kind != "ruled_loft":
        raise SegmentationError("Vyberte původní prostorový cíl mezi dvěma živými profily.")
    return {
        "surface": asdict(surface),
        "profiles": [asdict(project.profiles[pid]) for pid in surface.source_profile_ids()],
        "scale": project.scale,
    }


def _source_matrix(surface):
    result = np.eye(4)
    for matrix in surface["parent_transforms"]:
        result = result @ validate_rigid(matrix)
    return result @ rigid_matrix(surface["position_mm"], surface["rotation_deg"])


def _orient(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _triangle_contact_allowed(a, b, shared):
    """Exact projected convex separation, including only intended shared nodes."""
    for first, second in ((a, b), (b, a)):
        winding = 1 if _orient(*first) > 0 else -1
        for p, q in zip(first, [*first[1:], first[0]]):
            values = [winding * _orient(p, q, point) for point in second]
            if max(values) > 0:
                continue
            zero = [point for point, value in zip(second, values) if value == 0]
            if not zero:
                return True
            component = 0 if p[0] != q[0] else 1
            low = max(min(p[component], q[component]), min(v[component] for v in zero))
            high = min(max(p[component], q[component]), max(v[component] for v in zero))
            if low > high:
                return True
            permitted = [v[component] for v in shared if _orient(p, q, v) == 0]
            return bool(permitted and min(permitted) <= low <= high <= max(permitted))
    return False


def _embedding(report):
    """A supported graph projection proof, not a generic intersection heuristic."""
    triangles = report["triangles"]
    patches = len(report["patches"])
    closed = report["source"]["first_closed"]
    examined = 0
    units = [tuple(Fraction(i == j) for j in range(3)) for i in range(3)]
    projections = [(units[a], units[b]) for a, b in ((0, 1), (0, 2), (1, 2))]
    for a, b, c in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        for factor in (
            Fraction(1, 8),
            Fraction(-1, 8),
            Fraction(1, 4),
            Fraction(-1, 4),
            Fraction(1, 2),
            Fraction(-1, 2),
            Fraction(1),
            Fraction(-1),
        ):
            projections.append(
                (units[a], tuple(units[b][i] + factor * units[c][i] for i in range(3)))
            )
    for projection in projections:
        records = []
        for triangle in triangles:
            points = [
                tuple(sum(Fraction(p[i]) * row[i] for i in range(3)) for row in projection)
                for p in triangle["world_vertices_model_mm"]
            ]
            if _orient(*points) == 0:
                break
            nodes = []
            for u, v in triangle["parameter_vertices_exact"]:
                x = triangle["patch_index"] + Fraction(u)
                nodes.append((0 if closed and x == patches else x, Fraction(v)))
            records.append((points, nodes))
        else:
            for (a, ka), (b, kb) in combinations(records, 2):
                examined += 1
                if examined > MAX_EMBEDDING_PAIRS:
                    raise SegmentationError(
                        "Konečný rozpočet ověření nekřížení dílů byl vyčerpán.",
                        {
                            "status": "UNRESOLVED",
                            "embedding_pairs_examined": examined - 1,
                            "embedding_pair_limit": MAX_EMBEDDING_PAIRS,
                        },
                    )
                common = set(ka) & set(kb)
                shared = []
                valid = True
                for node in common:
                    x, y = a[ka.index(node)], b[kb.index(node)]
                    if x != y:
                        valid = False
                        break
                    shared.append(x)
                if not valid or not _triangle_contact_allowed(a, b, shared):
                    break
            else:
                return {
                    "status": "CERTIFIED",
                    "projection_matrix_exact": [[str(v) for v in row] for row in projection],
                    "triangle_pairs": len(triangles) * (len(triangles) - 1) // 2,
                    "examined_pairs_all_projections": examined,
                    "pair_budget": MAX_EMBEDDING_PAIRS,
                    "proof": "EXACT_RATIONAL_PROJECTED_TRIANGLE_INTERIORS_AND_DECLARED_UV_CONTACTS",
                    "scope": "DELIVERED_RAW_TRIANGLE_GRAPH_BEFORE_COMMON_RIGID_POSE; "
                    "MATERIAL_FRAME_PERTURBATION_BOUNDED_SEPARATELY",
                }
    raise SegmentationError(
        "Pro tuto variantu nelze doložit globální nekřížení dílů. "
        "Podporovaný řez potřebuje jednoznačnou rovinnou projekci."
    )


def _profile_spec(vertices):
    a, b, c = np.asarray(vertices, dtype=float)
    u = b - a
    length = float(np.linalg.norm(u))
    u /= length
    normal = np.cross(b - a, c - a)
    normal /= np.linalg.norm(normal)
    v = np.cross(normal, u)
    points = [[0.0, 0.0], [length, 0.0], [float(np.dot(c - a, u)), float(np.dot(c - a, v))]]
    plane = {"origin": a.tolist(), "u": u.tolist(), "v": v.tolist()}
    SketchPlane(**copy.deepcopy(plane)).validate()
    # Exact rational coordinates of the actual finite-input construction plane.
    reconstructed = [
        tuple(
            Fraction(plane["origin"][i])
            + Fraction(plane["u"][i]) * Fraction(p[0])
            + Fraction(plane["v"][i]) * Fraction(p[1])
            for i in range(3)
        )
        for p in points
    ]
    return {"points": points, "plane": plane}, reconstructed


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _plane_normal(points, linear):
    edges = [[Fraction(p[i]) - Fraction(points[0][i]) for i in range(3)] for p in points[1:]]
    edges = [[sum(row[i] * edge[i] for i in range(3)) for row in linear] for edge in edges]
    return _cross(*edges)


def _normal_offset(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    if dot <= 0:
        raise SegmentationError("Skutečný rovinný frame změnil orientaci normály dílu.")
    cross = _cross(a, b)
    ratio = _sqrt(sum(v * v for v in cross))[1] / dot
    angle = _atan(ratio)[1] if ratio <= 1 else _pi()[1] / 2 - _atan(1 / ratio)[0]
    return angle * 180 / _pi()[0]


@lru_cache(maxsize=8)
def _candidate(source_json, parameter_json):
    binding, params = json.loads(source_json), json.loads(parameter_json)
    if set(binding) != {"surface", "profiles", "scale"} or len(binding["profiles"]) != 2:
        raise SegmentationError("Neplatná původní zdrojová vazba varianty.")
    surface = binding["surface"]
    profiles = [_profile_from_record(p) for p in binding["profiles"]]
    references = surface["params"]["correspondences"]
    if (
        surface["kind"] != "ruled_loft"
        or surface["params"]["reference_state"] != "BOUND"
        or [p.id for p in profiles]
        != [surface["profile_id"], surface["params"]["second_profile_id"]]
    ):
        raise SegmentationError("Původní profilové reference nejsou jednoznačně navázané.")
    report = segment_ruled_loft(
        *(LoftProfile.from_profile(p) for p in profiles),
        tuple(
            LoftCorrespondence(
                r["first_segment_id"],
                r["second_segment_id"],
                tuple(r["first_interval"]),
                tuple(r["second_interval"]),
            )
            for r in references
        ),
        scale=binding["scale"],
        **params,
    )
    if report["status"] != "CERTIFIED":
        raise SegmentationError(report["message"], report)
    if len(report["triangles"]) > MAX_DOMAIN_TRIANGLES:
        raise SegmentationError(
            "Varianta překročila konečný doménový rozpočet "
            f"{MAX_DOMAIN_TRIANGLES} samostatných dílů."
        )
    embedding = _embedding(report)
    matrix = _source_matrix(surface)
    linear = [[Fraction(v) for v in row[:3]] for row in matrix[:3]]
    gram = [
        [sum(linear[k][i] * linear[k][j] for k in range(3)) for j in range(3)] for i in range(3)
    ]
    upper = max(sum(abs(v) for v in row) for row in gram)
    lower = min(gram[i][i] - sum(abs(v) for j, v in enumerate(gram[i]) if j != i) for i in range(3))
    if lower <= 0:
        raise SegmentationError("Umístění nemá doloženou nenulovou prostorovou metriku.")
    operator, condition = _sqrt(upper)[1], _sqrt(upper / lower)[1]
    rho = (condition - 1) / (condition + 1)
    # Polar decomposition: each direction rotates at most asin(rho), hence
    # the angle of two normals changes by at most 2*asin(rho).
    pose_angle = 2 * rho / _sqrt(1 - rho * rho)[0] * 180 / _pi()[0]
    specs, reconstruction, normal_offset, flat_metric = [], Fraction(0), Fraction(0), Fraction(0)
    for triangle in report["triangles"]:
        spec, actual = _profile_spec(triangle["world_vertices_model_mm"])
        specs.append(spec)
        normal_offset = max(
            normal_offset,
            _normal_offset(
                _plane_normal(triangle["world_vertices_model_mm"], linear),
                _plane_normal(actual, linear),
            ),
        )
        raw_points = triangle["world_vertices_model_mm"]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            raw_length = _sqrt(
                sum((Fraction(x) - Fraction(y)) ** 2 for x, y in zip(raw_points[a], raw_points[b]))
            )
            flat_length = _sqrt(
                sum(
                    (Fraction(x) - Fraction(y)) ** 2
                    for x, y in zip(spec["points"][a], spec["points"][b])
                )
            )
            flat_metric = max(
                flat_metric,
                abs(raw_length[0] - flat_length[1]),
                abs(raw_length[1] - flat_length[0]),
            )
        for raw, point in zip(triangle["world_vertices_model_mm"], actual):
            delta = [point[i] - Fraction(raw[i]) for i in range(3)]
            transformed = [sum(row[i] * delta[i] for i in range(3)) for row in linear]
            reconstruction = max(reconstruction, _sqrt(sum(v * v for v in transformed))[1])
    total = Fraction(
        report["max_surface_deviation_paper_mm_exact"]
    ) * operator + reconstruction * Fraction(binding["scale"])
    if total > Fraction(params["max_deviation_mm"]):
        raise SegmentationError("Skutečný rovinný frame a umístění vyčerpaly odchylkový rozpočet.")
    source_length = max(Fraction(e["source_length_upper_paper_mm_exact"]) for e in report["edges"])
    pose_strain = max(operator - 1, 1 - _sqrt(lower)[0])
    length_error = (
        max(Fraction(e["absolute_length_difference_bound_paper_mm_exact"]) for e in report["edges"])
        + flat_metric * Fraction(binding["scale"])
        + pose_strain * source_length
    )
    certificate = {
        "math": report,
        "embedding": embedding,
        "material_frame": {
            "status": "CERTIFIED",
            "pose_operator_upper_exact": str(operator),
            "max_reconstruction_error_paper_mm_exact": str(
                reconstruction * Fraction(binding["scale"])
            ),
            "max_target_to_material_deviation_paper_mm_exact": str(total),
            "max_source_edge_to_flat_length_difference_bound_paper_mm_exact": str(length_error),
            "flat_metric_rounding_reserve_paper_mm_exact": str(
                flat_metric * Fraction(binding["scale"])
            ),
            "max_material_normal_angle_deg_exact": str(
                Fraction(report["max_normal_angle_bound_deg_exact"]) + pose_angle + normal_offset
            ),
            "pose_normal_angle_reserve_deg_exact": str(pose_angle),
            "plane_normal_offset_bound_deg_exact": str(normal_offset),
            "normal_scope": "SOURCE_NORMAL_FIELD_TO_ACTUAL_MATERIAL_PLANE; "
            "CONDITION_AND_EXACT_RECONSTRUCTION_RESERVES",
            "proof": "EXACT_RATIONAL_PLANE_RECONSTRUCTION_AND_POSE_OPERATOR_BOUND",
        },
    }
    return certificate, specs


def _generation_payload(variant):
    data = asdict(variant)
    for key in ("generation_digest", "print_selected", "name"):
        data.pop(key)
    return data


def _triangle_key(report, triangle, references):
    reference = references[triangle["patch_index"]]
    return _digest(
        {
            "source": report["patches"][triangle["patch_index"]]["source"],
            "patch_id": reference["id"],
            "parameter_vertices_exact": triangle["parameter_vertices_exact"],
        }
    )


def _seam_use(report, records, use):
    index = use["triangle_index"]
    parameters = report["triangles"][index]["parameter_vertices_exact"]
    edge = next(
        i
        for i in range(3)
        if [parameters[i], parameters[(i + 1) % 3]] == use["parameter_endpoints_exact"]
    )
    return {
        "triangle_id": records[index]["id"],
        "edge_id": records[index]["edge_ids"][edge],
        "parameter_endpoints_exact": copy.deepcopy(use["parameter_endpoints_exact"]),
    }


def _geometry_binding(profile, surface):
    data = {"profile": asdict(profile), "surface": asdict(surface)}
    for value in data.values():
        value.pop("revision", None)
        value.pop("name", None)
    return _digest(data)


def _preview_geometry(binding, certificate, specs):
    """Detached display of the ACTUAL generated material-frame triangles.

    No application identity is allocated and no mesh can be injected at confirm.
    The authoritative confirmation re-derives everything from source + token.
    """
    matrix = _source_matrix(binding["surface"])
    vertices, faces, normals, sources = [], [], [], []
    scale = binding["scale"]
    refs = binding["surface"]["params"]["correspondences"]
    for triangle, spec in zip(certificate["math"]["triangles"], specs):
        points = np.asarray(spec["points"])
        plane = SketchPlane(**spec["plane"])
        world = plane.world(points) @ matrix[:3, :3].T + matrix[:3, 3]
        if not np.isfinite(world).all():
            raise SegmentationError("Umístění převyšuje konečnou přesnost materiálového náhledu.")
        normal = np.cross(world[1] - world[0], world[2] - world[0])
        norm = float(np.linalg.norm(normal))
        if norm <= 0 or not np.isfinite(norm):
            raise SegmentationError("Umístění ztratilo nenulovou plochu odvozeného dílu.")
        for a, b in ((0, 1), (1, 2), (2, 0)):
            expected = float(np.linalg.norm(points[a] - points[b])) * scale
            actual = float(np.linalg.norm(world[a] - world[b])) * scale
            if abs(expected - actual) > max(0.01, expected * 1e-6):
                raise SegmentationError("Umístění ztratilo metrickou přesnost odvozeného dílu.")
        offset = len(vertices)
        vertices.extend(world.tolist())
        faces.append([offset, offset + 1, offset + 2])
        normals.extend([(normal / norm).tolist() for _ in range(3)])
        sources.append(
            {
                "target_surface_id": binding["surface"]["id"],
                "patch_id": refs[triangle["patch_index"]]["id"],
                "parameter_vertices_exact": copy.deepcopy(triangle["parameter_vertices_exact"]),
                "source": copy.deepcopy(
                    certificate["math"]["patches"][triangle["patch_index"]]["source"]
                ),
            }
        )
    return {
        "mode": "APPROXIMATE",
        "vertices": vertices,
        "triangles": faces,
        "vertex_normals": normals,
        "triangle_sources": sources,
        "mesh_role": "DETACHED_ACTUAL_MATERIAL_FRAME_PREVIEW; NOT_PERSISTENT_IDENTITIES",
    }


class SegmentedCommands:
    def preview_segmented_variant(
        self, target_surface_id, *, max_deviation_mm=0.25, max_cells=4096, max_depth=16
    ):
        try:
            binding = _source_binding(self, target_surface_id)
            target = self.surfaces[target_surface_id]
            previous_children = {
                r["surface_id"]
                for v in self.segmented_variants.values()
                if v.target_surface_id == target_surface_id
                for r in v.triangle_bindings
            }
            relations = [
                *({j.surface_a, j.surface_b} for j in self.joints.values()),
                *({a.source_surface_id, a.target_surface_id} for a in self.attachments.values()),
            ]
            if any(
                pair & previous_children and not pair <= previous_children for pair in relations
            ):
                raise SegmentationError(
                    "Odvozené díly mají spoje s jinými částmi. Nejdříve je "
                    "výslovně odpojte; přemapování na novou generaci není doložené."
                )
            if (
                len(self.parts[target.part_id].surface_ids) != 1
                or any(
                    target_surface_id in {j.surface_a, j.surface_b} for j in self.joints.values()
                )
                or any(
                    target_surface_id in {a.source_surface_id, a.target_surface_id}
                    for a in self.attachments.values()
                )
            ):
                raise SegmentationError(
                    "Nejprve odpojte původní spoje cíle; jejich přemapování "
                    "na odvozené díly zatím není doložené."
                )
            params = {
                "max_deviation_mm": max_deviation_mm,
                "max_cells": max_cells,
                "max_depth": max_depth,
            }
            certificate, specs = _candidate(_json(binding), _json(params))
            geometry = _preview_geometry(binding, certificate, specs)
            fingerprint = _fingerprint(binding)
            return {
                "status": "APPROXIMATE",
                "mode": "APPROXIMATE",
                "can_confirm": True,
                "target_surface_id": target_surface_id,
                "parameters": params,
                "source_binding": copy.deepcopy(binding),
                "source_fingerprint": fingerprint,
                "certificate": copy.deepcopy(certificate),
                "preview_geometry": geometry,
                "preview_digest": _digest(
                    {"source": fingerprint, "parameters": params, "certificate": certificate}
                ),
                "physical_build": "NOT_VERIFIED",
                "new_user_test": "NOT_RUN",
            }
        except (ValidationError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
            return {
                "status": "UNRESOLVED",
                "mode": "UNRESOLVED",
                "can_confirm": False,
                "code": "SEGMENTATION_UNRESOLVED",
                "message": str(exc),
                "math_report": copy.deepcopy(getattr(exc, "report", {})),
                "target_surface_id": target_surface_id,
                "physical_build": "NOT_VERIFIED",
            }

    @atomic
    def add_segmented_variant(
        self,
        target_surface_id,
        *,
        preview_digest,
        max_deviation_mm=0.25,
        max_cells=4096,
        max_depth=16,
        name="Segmentovaná varianta",
    ):
        return self._add_segmented_generation(
            target_surface_id, preview_digest, name, None, max_deviation_mm, max_cells, max_depth
        )

    @atomic
    def update_segmented_variant(
        self,
        variant_id,
        *,
        preview_digest,
        max_deviation_mm=0.25,
        max_cells=4096,
        max_depth=16,
        name=None,
    ):
        previous = self.segmented_variants[variant_id]
        return self._add_segmented_generation(
            previous.target_surface_id,
            preview_digest,
            name or previous.name,
            variant_id,
            max_deviation_mm,
            max_cells,
            max_depth,
        )

    def _add_segmented_generation(self, target, token, name, previous, deviation, cells, depth):
        preview = self.preview_segmented_variant(
            target, max_deviation_mm=deviation, max_cells=cells, max_depth=depth
        )
        if not preview["can_confirm"]:
            raise SegmentationError(preview["message"], preview)
        if token != preview["preview_digest"]:
            raise SegmentationError("Náhled již neodpovídá živému cíli. Vytvořte nový náhled.")
        if not isinstance(name, str):
            raise SegmentationError("Název varianty musí být text.")
        binding, params = preview["source_binding"], preview["parameters"]
        certificate, specs = _candidate(_json(binding), _json(params))
        report, variant_id = certificate["math"], identity()
        surface = binding["surface"]
        references = surface["params"]["correspondences"]
        records = []
        for index, (triangle, spec) in enumerate(zip(report["triangles"], specs)):
            profile_id, sid, pid, triangle_id = (identity() for _ in range(4))
            vertices = [Vertex(identity(), list(p)) for p in spec["points"]]
            segments = [
                CurveSegment(identity(), "line", a.id, b.id)
                for a, b in zip(vertices, [*vertices[1:], vertices[0]])
            ]
            profile = Profile(
                profile_id,
                f"Obrys {name} {index + 1}",
                vertices,
                segments,
                True,
                SketchPlane(**copy.deepcopy(spec["plane"])),
            )
            child = SurfaceFeature(
                sid,
                f"{name} {index + 1}",
                profile_id,
                params={"segmented_variant_id": variant_id, "triangle_id": triangle_id},
                position_mm=list(surface["position_mm"]),
                rotation_deg=list(surface["rotation_deg"]),
                parent_transforms=copy.deepcopy(surface["parent_transforms"]),
                part_id=pid,
            )
            number = self.next_part_number
            self.next_part_number += 1
            part = MaterialPart(
                pid,
                f"P{number} · {child.name}",
                [sid],
                PaperFrame(sid, vertices[0].id, segments[0].id),
                number=number,
            )
            self.profiles[profile_id], self.surfaces[sid], self.parts[pid] = profile, child, part
            self.placements[pid] = Placement(x_mm=(index % 8) * 15.0, y_mm=(index // 8) * 15.0)
            records.append(
                {
                    "id": triangle_id,
                    "surface_id": sid,
                    "profile_id": profile_id,
                    "part_id": pid,
                    "triangle_index": index,
                    "source_parameter_key": _triangle_key(report, triangle, references),
                    "source": copy.deepcopy(report["patches"][triangle["patch_index"]]["source"]),
                    "patch_id": references[triangle["patch_index"]]["id"],
                    "parameter_vertices_exact": copy.deepcopy(triangle["parameter_vertices_exact"]),
                    "material_input_digest": _geometry_binding(profile, child),
                    "vertex_ids": [v.id for v in vertices],
                    "edge_ids": [s.id for s in segments],
                }
            )
        seams = []
        for edge in report["edges"]:
            if edge["role"] == "PAIRED_ISLAND_CUT":
                seams.append(
                    {
                        "id": identity(),
                        "uses": [
                            {
                                **_seam_use(report, records, u),
                            }
                            for u in edge["uses"]
                        ],
                        "source_edge": copy.deepcopy(edge),
                    }
                )
        variant = SegmentedVariant(
            variant_id,
            name,
            target,
            binding,
            preview["source_fingerprint"],
            params,
            copy.deepcopy(certificate),
            records,
            seams,
            "",
            previous,
        )
        variant.generation_digest = _digest(_generation_payload(variant))
        for old in self.segmented_variants.values():
            if old.target_surface_id == target:
                old.print_selected = False
        self.segmented_variants[variant_id] = variant
        self._touch()
        from .paper import build_part

        for record in records:
            pid = record["part_id"]
            self.parts[pid] = build_part(self, self.parts[pid])
        return variant_id

    @atomic
    def select_segmented_variant(self, variant_id):
        variant = self.segmented_variants[variant_id]
        if self.segmented_variant_status(variant_id)["status"] != "APPROXIMATE":
            raise SegmentationError(
                "Nejdříve obnovte nebo znovu potvrďte aktuální náhled varianty."
            )
        for other in self.segmented_variants.values():
            if other.target_surface_id == variant.target_surface_id:
                other.print_selected = other.id == variant_id
        self._touch()

    @atomic
    def restore_segmented_target(self, target_surface_id):
        if target_surface_id not in self.surfaces:
            raise SegmentationError("Původní konstrukční cíl chybí.")
        for variant in self.segmented_variants.values():
            if variant.target_surface_id == target_surface_id:
                variant.print_selected = False
        self._touch()

    def segmented_variant_status(self, variant_id):
        variant = self.segmented_variants[variant_id]
        current = _source_binding(self, variant.target_surface_id)
        status, message = "APPROXIMATE", "Potvrzená odvozená varianta odpovídá živému cíli."
        if _fingerprint(current) != variant.source_fingerprint:
            status, message = (
                "STALE",
                "Původní cíl se změnil. Potvrďte nový náhled; starý layout zůstává.",
            )
        elif any(
            _geometry_binding(self.profiles[r["profile_id"]], self.surfaces[r["surface_id"]])
            != r["material_input_digest"]
            for r in variant.triangle_bindings
        ):
            status, message = (
                "UNRESOLVED",
                "Odvozený materiál byl změněn; původní mez jej již nepotvrzuje.",
            )
        return {
            "status": status,
            "mode": "APPROXIMATE",
            "message": message,
            "variant_id": variant_id,
            "target_surface_id": variant.target_surface_id,
            "source_binding": copy.deepcopy(variant.source_binding),
            "source_fingerprint": variant.source_fingerprint,
            "current_source_fingerprint": _fingerprint(current),
            "generation_digest": variant.generation_digest,
            "parameters": copy.deepcopy(variant.parameters),
            "certificate": copy.deepcopy(variant.certificate),
            "triangle_bindings": copy.deepcopy(variant.triangle_bindings),
            "paired_seams": copy.deepcopy(variant.paired_seams),
            "material_surface_ids": [r["surface_id"] for r in variant.triangle_bindings],
            "material_part_ids": [r["part_id"] for r in variant.triangle_bindings],
            "physical_build": "NOT_VERIFIED",
            "new_user_test": "NOT_RUN",
        }

    def material_part_ids(self):
        excluded = set()
        for variant in self.segmented_variants.values():
            if variant.print_selected:
                excluded.add(self.surfaces[variant.target_surface_id].part_id)
            else:
                excluded.update(r["part_id"] for r in variant.triangle_bindings)
        return set(self.parts) - excluded

    def print_material_view(self):
        view = copy.copy(self)
        material = self.material_part_ids()
        surfaces = {sid for pid in material for sid in self.parts[pid].surface_ids}
        view.parts = {pid: p for pid, p in self.parts.items() if pid in material}
        view.surfaces = {sid: s for sid, s in self.surfaces.items() if sid in surfaces}
        view.placements = {pid: p for pid, p in self.placements.items() if pid in material}
        view.joints = {
            k: j for k, j in self.joints.items() if {j.surface_a, j.surface_b} <= surfaces
        }
        view.attachments = {
            k: a
            for k, a in self.attachments.items()
            if {a.source_surface_id, a.target_surface_id} <= surfaces
        }
        connectors = {j.connector_id for j in [*view.joints.values(), *view.attachments.values()]}
        view.connectors = {k: c for k, c in self.connectors.items() if k in connectors}
        view.validate = (
            self.validate
        )  # Validate the FULL closed registry before material-only checks.
        view._is_print_material_view = True
        return view

    def _validate_segmented_variants(self):
        extra_ids, children, selected_targets = [], {}, set()
        if not isinstance(self.segmented_variants, dict):
            raise ValidationError("Registr odvozených variant musí být objekt.")
        for variant_id, variant in self.segmented_variants.items():
            uuid(variant_id)
            if not isinstance(variant, SegmentedVariant) or variant.id != variant_id:
                raise ValidationError("Neplatná identita generace segmentované varianty.")
            if not isinstance(variant.name, str) or type(variant.print_selected) is not bool:
                raise ValidationError("Neplatný název nebo tiskový výběr varianty.")
            if (
                variant.target_surface_id not in self.surfaces
                or self.surfaces[variant.target_surface_id].kind != "ruled_loft"
            ):
                raise ValidationError("Původní živý konstrukční cíl varianty chybí.")
            if variant.source_binding["surface"]["id"] != variant.target_surface_id:
                raise ValidationError("Neměnná generace odkazuje na jiný původní target UUID.")
            if variant.print_selected:
                if variant.target_surface_id in selected_targets:
                    raise ValidationError(
                        "Pro jeden cíl může tisknout jen jedna potvrzená generace."
                    )
                selected_targets.add(variant.target_surface_id)
            if variant.previous_variant_id is not None and (
                variant.previous_variant_id not in self.segmented_variants
                or self.segmented_variants[variant.previous_variant_id].target_surface_id
                != variant.target_surface_id
                or variant.previous_variant_id == variant_id
            ):
                raise ValidationError("Neplatná návaznost uchované generace varianty.")
            if (
                _fingerprint(variant.source_binding) != variant.source_fingerprint
                or _digest(_generation_payload(variant)) != variant.generation_digest
            ):
                raise ValidationError("Neměnná provenance varianty byla změněna.")
            certificate, specs = _candidate(
                _json(variant.source_binding), _json(variant.parameters)
            )
            if variant.certificate != certificate:
                raise ValidationError("Uložený segmentační důkaz nepatří skutečnému zdroji.")
            report = certificate["math"]
            if len(variant.triangle_bindings) != len(report["triangles"]):
                raise ValidationError("Varianta nepokrývá všechny ověřené trojúhelníky.")
            refs = variant.source_binding["surface"]["params"]["correspondences"]
            extra_ids.append(variant_id)
            triangle_ids = set()
            for i, (record, triangle) in enumerate(
                zip(variant.triangle_bindings, report["triangles"])
            ):
                if set(record) != {
                    "id",
                    "surface_id",
                    "profile_id",
                    "part_id",
                    "triangle_index",
                    "source_parameter_key",
                    "source",
                    "patch_id",
                    "parameter_vertices_exact",
                    "material_input_digest",
                    "edge_ids",
                    "vertex_ids",
                }:
                    raise ValidationError("Neplatná struktura provenance odvozeného dílu.")
                uuid(record["id"])
                extra_ids.append(record["id"])
                triangle_ids.add(record["id"])
                if (
                    record["triangle_index"] != i
                    or record["source_parameter_key"] != _triangle_key(report, triangle, refs)
                    or record["parameter_vertices_exact"] != triangle["parameter_vertices_exact"]
                    or record["source"] != report["patches"][triangle["patch_index"]]["source"]
                    or record["patch_id"] != refs[triangle["patch_index"]]["id"]
                ):
                    raise ValidationError(
                        "Trojúhelník nemá původní jednoznačné source/UV mapování."
                    )
                sid, pid, profile_id = (record[k] for k in ("surface_id", "part_id", "profile_id"))
                if sid in children or sid not in self.surfaces or pid not in self.parts:
                    raise ValidationError("Odvozené identity byly ztraceny nebo nahrazeny.")
                surface = self.surfaces[sid]
                if (
                    surface.profile_id != profile_id
                    or surface.part_id != pid
                    or surface.kind != "planar"
                    or self.parts[pid].surface_ids != [sid]
                    or surface.params
                    != {"segmented_variant_id": variant_id, "triangle_id": record["id"]}
                    or [v.id for v in self.profiles[profile_id].vertices] != record["vertex_ids"]
                    or [s.id for s in self.profiles[profile_id].segments] != record["edge_ids"]
                ):
                    raise ValidationError("Skutečný odvozený díl neodpovídá své neměnné identitě.")
                spec = specs[i]
                expected_profile = Profile(
                    profile_id,
                    "",
                    [
                        Vertex(vid, point)
                        for vid, point in zip(record["vertex_ids"], spec["points"])
                    ],
                    [
                        CurveSegment(eid, "line", a, b)
                        for eid, a, b in zip(
                            record["edge_ids"],
                            record["vertex_ids"],
                            record["vertex_ids"][1:] + record["vertex_ids"][:1],
                        )
                    ],
                    True,
                    SketchPlane(**copy.deepcopy(spec["plane"])),
                )
                original = variant.source_binding["surface"]
                expected_surface = SurfaceFeature(
                    sid,
                    "",
                    profile_id,
                    params=copy.deepcopy(surface.params),
                    position_mm=list(original["position_mm"]),
                    rotation_deg=list(original["rotation_deg"]),
                    parent_transforms=copy.deepcopy(original["parent_transforms"]),
                    part_id=pid,
                )
                if record["material_input_digest"] != _geometry_binding(
                    expected_profile, expected_surface
                ):
                    raise ValidationError("Materiálová vazba trojúhelníku byla zfalšována.")
                children[sid] = variant_id
            expected = [e for e in report["edges"] if e["role"] == "PAIRED_ISLAND_CUT"]
            if len(variant.paired_seams) != len(expected):
                raise ValidationError("Chybí skutečné párované řezy varianty.")
            for seam, source in zip(variant.paired_seams, expected):
                uuid(seam["id"])
                extra_ids.append(seam["id"])
                uses = [
                    {
                        **_seam_use(report, variant.triangle_bindings, u),
                    }
                    for u in source["uses"]
                ]
                if (
                    set(seam) != {"id", "uses", "source_edge"}
                    or seam["uses"] != uses
                    or seam["source_edge"] != source
                ):
                    raise ValidationError("Provenance párovaného řezu byla nahrazena.")
        for variant_id in self.segmented_variants:
            seen, current = set(), variant_id
            while current is not None:
                if current in seen:
                    raise ValidationError("Historie generací obsahuje cyklus.")
                seen.add(current)
                current = self.segmented_variants[current].previous_variant_id
        selected = self.material_part_ids()
        material = {sid for pid in selected for sid in self.parts[pid].surface_ids}
        for pair in [
            *({j.surface_a, j.surface_b} for j in self.joints.values()),
            *({a.source_surface_id, a.target_surface_id} for a in self.attachments.values()),
        ]:
            if pair & material and not pair <= material:
                raise ValidationError(
                    "Spoj propojuje tiskový materiál s netisknoucí referencí; "
                    "nejdříve zvolte a připojte skutečnou variantu."
                )
        return extra_ids, children
