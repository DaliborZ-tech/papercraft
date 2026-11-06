"""Connect authored straight-hinge material to the continuous clearance checker."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict

import numpy as np
from scipy.spatial.transform import Rotation
from shapely import Polygon

from .attachments import source_outward, surface_basis
from .commands import atomic
from .errors import ValidationError
from .geometry import number, triangulate

DEFAULT_MATERIAL_PROFILE = {
    "thickness_mm": None,
    "clearance_mm": 0.0,
    "bend_radius_mm": 0.0,
    "crease_zone_mm": 0.5,
}
_MISSING = object()


class BendCommands:
    def _validate_material_profile(self):
        profile = self.material_profile
        if not isinstance(profile, dict) or set(profile) != set(DEFAULT_MATERIAL_PROFILE):
            raise ValidationError("Materiálový profil nemá úplné známé parametry.")
        if profile["thickness_mm"] is not None:
            number(profile["thickness_mm"], "Tloušťka papíru", positive=True)
        for field in ("clearance_mm", "bend_radius_mm", "crease_zone_mm"):
            number(profile[field], field, nonnegative=True)

    @atomic
    def set_material_profile(
        self, *, thickness_mm=_MISSING, clearance_mm=None,
        bend_radius_mm=None, crease_zone_mm=None,
    ):
        if thickness_mm is not _MISSING:
            self.material_profile["thickness_mm"] = thickness_mm
        for key, value in (
            ("clearance_mm", clearance_mm), ("bend_radius_mm", bend_radius_mm),
            ("crease_zone_mm", crease_zone_mm),
        ):
            if value is not None:
                self.material_profile[key] = value
        self._validate_material_profile()
        self._touch(list(self.surfaces))

    def _assembly_clearance_key(self):
        state = {
            "scale": self.scale,
            "material_profile": self.material_profile,
            **{name: {key: asdict(value) for key, value in getattr(self, name).items()}
               for name in ("profiles", "surfaces", "joints", "attachments", "connectors")},
        }
        return hashlib.sha256(json.dumps(
            state, sort_keys=True, ensure_ascii=False, allow_nan=False
        ).encode("utf8")).hexdigest()

    def connector_bend_clearance(self, connector_id):
        key = self._assembly_clearance_key()
        cache = getattr(self, "_bend_cache", None)
        if cache is None or cache[0] != key:
            self._bend_cache = (key, {})
        results = self._bend_cache[1]
        if connector_id not in results:
            try:
                results[connector_id] = self._check_connector_bend(connector_id)
            except (ValidationError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                results[connector_id] = {
                    "status": "UNRESOLVED", "message": str(exc), "tabs": [],
                    "material_profile": copy.deepcopy(self.material_profile),
                    "assembly_digest": key,
                }
        return copy.deepcopy(results[connector_id])

    def _check_connector_bend(self, connector_id):
        from .clearance import (
            ContactAllowance,
            FoldSweep,
            MaterialObstacle,
            MaterialProfile,
            check_fold_clearance,
        )

        connector = self.connectors[connector_id]
        geometry = self._connector_geometry(connector_id)
        if not connector.enabled or not geometry["tabs"]:
            return {"status": "NOT_APPLICABLE", "message": "Žádná aktivní záložka.", "tabs": []}
        source = connector.owner_surface_id
        if connector.attachment_id:
            relation = self.attachments[connector.attachment_id]
            edge_id = relation.source_edge_id
        else:
            relation = self.joints[connector.joint_id]
            edge_id = relation.edge_a if source == relation.surface_a else relation.edge_b
        edge = next(e for e in self.world_geometry(source)["boundary"] if e["id"] == edge_id)
        a, b = np.asarray([edge["start"], edge["end"]], dtype=float) * self.scale
        axis = (b - a) / math.dist(a, b)
        _, outward = source_outward(self, source, edge_id)
        _, u, v = surface_basis(self, source)
        flat_outward = outward[0] * u + outward[1] * v
        initial_normal = np.asarray(self.world_geometry(source)["normal"])
        profile = self.material_profile
        thickness = profile["thickness_mm"]
        material = MaterialProfile(thickness, profile["clearance_mm"], profile["bend_radius_mm"])
        obstacles = []
        for sid in self.surfaces:
            world = self.world_geometry(sid)
            triangles = np.asarray(world["vertices"])[np.asarray(world["triangles"])] * self.scale
            obstacles.append(MaterialObstacle(sid, triangles, thickness))
        contact_by_id = {tab["tab_id"]: tab for tab in geometry["tabs"]}
        reports = []
        for tab in geometry["all_tabs"]:
            if not tab["enabled"]:
                continue
            contact = contact_by_id[tab["id"]]
            receiver = contact["receiver_surface_id"]
            lo, hi = tab["source_interval"]
            hinge_start, hinge_end = a + lo * (b - a), a + hi * (b - a)
            outline = np.asarray(tab["outline_mm"])
            initial = (hinge_start + outline[:, :1] * axis
                       + outline[:, 1:] * flat_outward)
            final = contact.get("folded_world")
            if final is None:
                final = self._surface_world_points(
                    receiver, np.asarray(contact["footprint_uv_mm"]) / self.scale
                )
            final = np.asarray(final) * self.scale
            j = next(index for index, point in enumerate(outline) if point[1] > 0)
            desired = (final[j] - hinge_start - outline[j, 0] * axis) / outline[j, 1]
            angle = math.atan2(np.dot(axis, np.cross(flat_outward, desired)),
                               np.dot(flat_outward, desired))
            rotation = Rotation.from_rotvec(axis * angle)
            mapped = rotation.apply(initial - hinge_start) + hinge_start
            if not np.allclose(mapped, final, rtol=0, atol=1e-7):
                raise ValidationError("Konečný otisk není tuhým ohybem zdrojové záložky.")
            local, faces = triangulate(outline)
            points = hinge_start + local[:, :1] * axis + local[:, 1:] * flat_outward
            sweep = FoldSweep(
                patches_world_mm=points[faces], hinge_start_mm=hinge_start,
                hinge_end_mm=hinge_end, angle_deg=math.degrees(angle),
                source_id=source, receiver_id=receiver, initial_normal=initial_normal,
                final_normal=rotation.apply(initial_normal), tab_id=tab["id"],
            )
            radius = profile["crease_zone_mm"]
            padding = (thickness or 0) / 2 + profile["clearance_mm"] + profile["bend_radius_mm"]
            numerical_contact_band = 0.001  # Finite model-contact tolerance, paper mm.
            band = padding + (thickness or 0) / 2 + numerical_contact_band
            allowances = []
            if radius > 0:
                crease_box = [
                    hinge_start + axis * x + flat_outward * y + initial_normal * z
                    for x in (-radius, math.dist(hinge_start, hinge_end) + radius)
                    for y in (-radius, radius) for z in (-radius, radius)
                ]
                for sid in (source, receiver):
                    allowances.append(ContactAllowance(
                        sid, "hinge", crease_box, (0, math.degrees(angle)),
                        "Declared finite local crease zone; deforming paper is not a cutout "
                        "or a mechanically certified rigid solid inside this zone.",
                    ))
            # The crease box includes a complete radius-r tube. Outside it, radial
            # distance is at least r; contact phase uses this MINIMUM radius.
            delta = math.pi / 2 if radius <= band else math.asin(band / radius)
            delta = min(abs(angle), delta)
            phase_start = math.degrees(angle - math.copysign(delta, angle))
            target_outline = np.asarray(contact["footprint_uv_mm"])
            target_points, target_faces = triangulate(target_outline)
            _, tu, tv = surface_basis(self, receiver)
            target_normal = np.cross(tu, tv)
            for face in target_faces:
                patch = Polygon(target_points[face]).buffer(
                    padding + numerical_contact_band, join_style="mitre"
                )
                local_ring = np.asarray(patch.exterior.coords[:-1])
                ring = self._surface_world_points(receiver, local_ring / self.scale) * self.scale
                depth = (thickness or 0) / 2 + numerical_contact_band
                volume = [point + sign * depth * target_normal
                          for point in ring for sign in (-1, 1)]
                allowances.append(ContactAllowance(
                    receiver, "final_contact", volume, (phase_start, math.degrees(angle)),
                    "Finite approach/contact layer around the actual receiving footprint; "
                    "does not certify glue strength or remove other model parts.",
                ))
            obstacles_for_tab = [
                MaterialObstacle(o.id, o.triangles_world_mm, o.thickness_mm,
                                 "source" if o.id == source else
                                 "receiver" if o.id == receiver else "other")
                for o in obstacles
            ]
            result = check_fold_clearance(
                sweep, material, obstacles_for_tab,
                expected_obstacle_ids=list(self.surfaces), allowances=allowances,
            )
            reports.append(asdict(result))
        precedence = {"CLEAR": 0, "UNVERIFIED": 1, "UNRESOLVED": 2, "COLLISION": 3}
        status = max((r["status"] for r in reports), key=precedence.__getitem__)
        return {
            "status": status, "tabs": reports,
            "material_profile": copy.deepcopy(profile),
            "assembly_digest": self._assembly_clearance_key(),
            "motion": "shorter_signed_rigid_fold; finite_crease_and_contact_reservations",
            "physical_build": "NOT_VERIFIED",
        }
