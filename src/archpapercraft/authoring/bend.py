"""Connect authored straight-hinge material to the continuous clearance checker."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict

import numpy as np
from scipy.spatial.transform import Rotation
from shapely import Polygon, constrained_delaunay_triangles
from shapely.ops import unary_union

from .attachments import edge_source, source_outward, surface_basis
from .commands import atomic
from .curve_material import surface_envelopes
from .errors import ValidationError
from .geometry import number, triangulate

DEFAULT_MATERIAL_PROFILE = {
    "thickness_mm": None,
    "clearance_mm": 0.0,
    "bend_radius_mm": 0.0,
    "crease_zone_mm": 0.5,
}
_MISSING = object()


def _guaranteed_triangles(material):
    """A guaranteed lower set may omit ill-conditioned derived slivers."""
    triangles, omitted_area = [], 0.0
    for face in constrained_delaunay_triangles(material).geoms:
        if not material.covers(face):
            raise ValidationError(
                "Garantovaná triangulace zasahuje mimo skutečně doložený materiál."
            )
        points = np.asarray(face.exterior.coords[:-1])
        singular = np.linalg.svd(points-points.mean(axis=0), compute_uv=False)
        if len(singular) < 2 or singular[1] <= 0 or singular[0]/singular[1] > 4096:
            omitted_area += face.area
        else:
            triangles.append(points)
    return triangles, omitted_area


def _upper_chord_rectangle(a, b, radius):
    a, b = np.asarray(a), np.asarray(b)
    tangent = (b-a)/math.dist(a, b)
    normal = np.array([-tangent[1], tangent[0]])
    points = np.array([a-radius*tangent-radius*normal, b+radius*tangent-radius*normal,
                       b+radius*tangent+radius*normal, a-radius*tangent+radius*normal])
    return Polygon(points), points[[[0, 1, 2], [0, 2, 3]]]


class BendCommands:
    def _bend_surface_bounds(self):
        """Complete lower/upper material registries, including holes and components."""
        key = self._assembly_clearance_key()
        cached = getattr(self, "_bend_surface_bound_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        records, proof = [], {}
        for sid, surface in self.surfaces.items():
            world = self.world_geometry(sid)
            proxy = np.asarray(world["vertices"])[np.asarray(world["triangles"])]*self.scale
            bounds = surface_envelopes(self, sid, paper=True)
            if bounds.is_exact:
                records.append((sid, proxy, proxy))
                continue
            lower_uv, omitted_area = _guaranteed_triangles(bounds.guaranteed)

            def mapped(triangles):
                if not len(triangles):
                    return np.empty((0, 3, 3))
                points = np.asarray(triangles).reshape(-1, 2)
                world = self._surface_world_points(sid, points/self.scale)*self.scale
                return world.reshape(-1, 3, 3)

            lower = mapped(lower_uv)
            # Decompose the possible material into the full proxy plus outward
            # chord tubes, avoiding tiny Boolean-union slivers. Tube overlap is
            # harmless: triangles represent the UNION of supplied material.
            upper_uv, covers = [], [bounds.proxy]
            tube_radius = 0.0
            for pid in [surface.profile_id, *surface.hole_profile_ids]:
                profile = self.profiles[pid]
                ids = {s.id for s in profile.segments if s.kind != "line"}
                if not ids:
                    continue
                for certificate in self.profile_projection(pid)["curves"]:
                    if certificate["segment_id"] not in ids:
                        continue
                    points = np.asarray(certificate["points"])*self.scale
                    for a, b in zip(points, points[1:]):
                        magnitude = max(1., *(abs(float(v)) for p in (a, b) for v in p))
                        radius = math.nextafter(bounds.max_error+512*math.ulp(magnitude), math.inf)
                        rectangle, triangles = _upper_chord_rectangle(a, b, radius)
                        covers.append(rectangle)
                        upper_uv.extend(triangles)
                        tube_radius = max(tube_radius, radius)
            if not unary_union(covers).covers(bounds.possible):
                raise ValidationError(
                    "Možný křivkový materiál není úplně pokrytý obalem ohybu. "
                    "Přepočítejte díl nebo upravte křivkový profil."
                )
            upper = np.concatenate([proxy, mapped(upper_uv)])
            records.append((sid, lower, upper))
            proof[sid] = {
                "method": "GUARANTEED_LOWER_MATERIAL_AND_COMPLETE_PROXY_PLUS_OUTWARD_TUBES_UPPER",
                "guaranteed_empty": not len(lower), "omitted_lower_sliver_area_mm2": omitted_area,
                "source_bound_mm": bounds.max_error, "upper_tube_radius_mm": tube_radius,
                "lower_triangle_count": len(lower), "upper_triangle_count": len(upper),
                "possible_material_fully_covered": True,
            }
        value = records, proof
        self._bend_surface_bound_cache = key, value
        return value

    def _bend_tab_obstacles(self):
        """Actual active tab material in its final pose, never a convex outline hull."""
        records = []
        for cid, connector in self.connectors.items():
            if not connector.enabled:
                continue
            geometry = self._connector_geometry(cid)
            for contact in geometry["tabs"]:
                receiver = contact["receiver_surface_id"]
                footprint = np.asarray(contact["footprint_uv_mm"])
                points, faces = triangulate(footprint)
                world = self._surface_world_points(receiver, points / self.scale) * self.scale
                records.append({
                    "id": "tab:" + contact["tab_id"],
                    "tab_id": contact["tab_id"],
                    "connector_id": cid,
                    "receiver_id": receiver,
                    "receiver_side": geometry["receiver_side"],
                    "triangles": world[faces],
                })
        if len({r["id"] for r in records}) != len(records):
            raise ValidationError("Aktivní chlopně nemají jednoznačné stabilní identity.")
        return records

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
        before = copy.deepcopy(self.material_profile)
        if thickness_mm is not _MISSING:
            self.material_profile["thickness_mm"] = thickness_mm
        for key, value in (
            ("clearance_mm", clearance_mm), ("bend_radius_mm", bend_radius_mm),
            ("crease_zone_mm", crease_zone_mm),
        ):
            if value is not None:
                self.material_profile[key] = value
        self._validate_material_profile()
        if self.material_profile == before:
            self.material_profile = before
            return
        self._touch(list(self.surfaces))

    def _assembly_clearance_key(self):
        used = {pid for surface in self.surfaces.values() for pid in surface.source_profile_ids()}
        state = {
            "scale": self.scale,
            "material_profile": self.material_profile,
            "profiles": {pid: asdict(self.profiles[pid]) for pid in sorted(used)},
            "profile_subdivisions": {
                key: value for key, value in self.profile_subdivisions.items()
                if value["history"]["profile_id"] in used
            },
            **{name: {key: asdict(value) for key, value in getattr(self, name).items()}
               for name in ("surfaces", "joints", "attachments", "connectors")},
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
        # A source edge remains the same full semantic hinge after subdivision.
        # Active display-boundary IDs are not its persistent material identity.
        _, _, source_edge = edge_source(self, source, edge_id)
        a, b = self._surface_world_points(source, source_edge) * self.scale
        axis = (b - a) / math.dist(a, b)
        _, outward = source_outward(self, source, edge_id)
        _, u, v = surface_basis(self, source)
        flat_outward = outward[0] * u + outward[1] * v
        initial_normal = np.asarray(self.world_geometry(source)["normal"])
        profile = self.material_profile
        thickness = profile["thickness_mm"]
        material = MaterialProfile(thickness, profile["clearance_mm"], profile["bend_radius_mm"])
        bounded_surfaces, bound_proof = self._bend_surface_bounds()
        contact_by_id = {tab["tab_id"]: tab for tab in geometry["tabs"]}
        assembled_tabs = self._bend_tab_obstacles()
        reports = []
        precedence = {"CLEAR": 0, "UNVERIFIED": 1, "UNRESOLVED": 2, "COLLISION": 3}
        for tab in geometry["all_tabs"]:
            if not tab["enabled"]:
                continue
            contact = contact_by_id[tab["id"]]
            receiver = contact["receiver_surface_id"]
            lo, hi = tab["source_interval"]
            hinge_start, hinge_end = a + lo * (b - a), a + hi * (b - a)
            outline = np.asarray(tab["outline_mm"])
            crease = profile["crease_zone_mm"]
            if 2 * crease > min(tab["base_length_mm"], float(np.max(outline[:, 1]))):
                raise ValidationError(
                    "Místní pás ohybu je příliš široký vůči záložce. "
                    "Zmenšete jej nejvýše na polovinu délky základny i výšky chlopně; "
                    "nesmí zakrýt celou kontrolovanou záložku."
                )
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
            radius = crease
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
            lower_obstacles, upper_obstacles = [], []
            for sid, lower, upper in bounded_surfaces:
                role = "source" if sid == source else "receiver" if sid == receiver else "other"
                lower_obstacles.append(MaterialObstacle(sid, lower, thickness, role))
                upper_obstacles.append(MaterialObstacle(sid, upper, thickness, role))
            # One tab moves while all other active tabs are already folded.
            # Opposite receiver sides have no authored physical layer offset.
            # Their zero-offset solids must not fabricate a certain collision.
            # Keep them explicit in the unresolved inventory, never grant a
            # blanket contact permission or erase another certain collision.
            unresolved_layers = []
            expected_ids = [o.id for o in upper_obstacles]
            for record in assembled_tabs:
                if record["tab_id"] == tab["id"]:
                    continue
                expected_ids.append(record["id"])
                side = geometry["receiver_side"]
                other_side = record["receiver_side"]
                uncertain = record["receiver_id"] == receiver and (
                    side == "unknown" or other_side == "unknown" or side != other_side
                )
                if uncertain:
                    unresolved_layers.append(record["id"])
                else:
                    obstacle = MaterialObstacle(record["id"], record["triangles"], thickness)
                    lower_obstacles.append(obstacle)
                    upper_obstacles.append(obstacle)
            options = {"expected_obstacle_ids": [o.id for o in upper_obstacles],
                       "allowances": allowances,
                       **({"max_depth": 8, "max_intervals": 128} if thickness is None else {})}
            upper_result = check_fold_clearance(sweep, material, upper_obstacles, **options)
            if not bound_proof:
                detail = asdict(upper_result)
            else:
                lower_result = check_fold_clearance(
                    sweep, material, lower_obstacles, lower_bound_only=True, **options,
                )
                if lower_result.status == "COLLISION":
                    detail = asdict(lower_result)
                elif upper_result.status == "CLEAR":
                    detail = asdict(upper_result)
                else:
                    detail = asdict(upper_result)
                    if upper_result.status == "COLLISION":
                        detail.update(status="UNRESOLVED", witness_angle_deg=None,
                                      witness_point_mm=None,
                                      message="Možný křivkový obal zasahuje do ohybu, ale "
                                      "střet se zaručeným materiálem nebyl doložen.")
                    detail["status"] = max(
                        (detail["status"], "UNRESOLVED" if lower_result.status == "UNRESOLVED"
                         else "UNVERIFIED" if thickness is None else "UNRESOLVED"),
                        key=precedence.__getitem__,
                    )
                detail["material_envelopes"] = {
                    "guaranteed_check": asdict(lower_result),
                    "possible_check": asdict(upper_result),
                    "bounds": copy.deepcopy(bound_proof),
                    "verdict_rule": (
                        "COLLISION_REQUIRES_GUARANTEED; CLEAR_REQUIRES_COMPLETE_POSSIBLE"
                    ),
                }
            detail["expected_obstacle_ids"] = expected_ids
            detail["unresolved_layer_obstacle_ids"] = unresolved_layers
            accounted = set(detail["checked_obstacle_ids"]) | set(unresolved_layers)
            detail["not_evaluated_obstacle_ids"] = [
                oid for oid in expected_ids if oid not in accounted
            ]
            detail["layer_geometry"] = (
                "Opposite or unknown receiver sides require explicit physical layer offsets; "
                "these obstacles are inventoried but their clearance is not established."
                if unresolved_layers else "NO_UNRESOLVED_RECEIVER_LAYER_PAIRS"
            )
            if unresolved_layers and detail["status"] != "COLLISION":
                layer_status = "UNVERIFIED" if thickness is None else "UNRESOLVED"
                detail["status"] = max(
                    (detail["status"], layer_status), key=precedence.__getitem__,
                )
                detail["message"] += " " + (
                    "Vzájemnou polohu vrstev chlopní na protilehlých nebo neurčených "
                    "stranách příjemce nelze ověřit. Nejde o prokázanou kolizi ani "
                    "volný prostor; určete skutečnou konstrukci vrstev."
                )
            detail["search_scope"] = (
                "BOUNDED_ZERO_THICKNESS_COLLISION_WITNESS_SEARCH; ABSENCE_NOT_PROVEN"
                if thickness is None else "CONTINUOUS_DECLARED_MATERIAL_ENVELOPE"
            )
            detail["search_limits"] = (
                {"max_depth": 8, "max_intervals": 128} if thickness is None
                else {"max_depth": 12, "max_intervals": 4096}
            )
            reports.append(detail)
        status = max((r["status"] for r in reports), key=precedence.__getitem__)
        return {
            "status": status, "tabs": reports,
            "material_profile": copy.deepcopy(profile),
            "assembly_digest": self._assembly_clearance_key(),
            "motion": "shorter_signed_rigid_fold; finite_crease_and_contact_reservations",
            "assembly_scenario": "ONE_TAB_MOVES_ALL_OTHER_ACTIVE_TABS_ALREADY_FOLDED",
            "physical_build": "NOT_VERIFIED",
            **({"message": "U křivkového materiálu nelze doložit volný prostor pro ohyb. "
                "Posuňte spoj dále od křivkové hrany nebo upravte profil a ověřte jej znovu."}
               if bound_proof and status == "UNRESOLVED" else {}),
        }
