"""Authored curve commands and bounded display/material projections.

Vertices/segments stay authoritative. Sampling never creates source identities.
"""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import asdict

import numpy as np
from shapely import Polygon

from .commands import atomic
from .curves import Curve, certify_curve, svg_commands
from .errors import ValidationError
from .geometry import number, vector
from .model import SketchPlane


def validate_native_path(path):
    if not isinstance(path["closed"], bool) or not isinstance(path["commands"], list):
        raise ValidationError("Neplatná nativní křivková cesta.")
    commands = path["commands"]
    if (not commands or not isinstance(commands[0], list)
            or not commands[0] or commands[0][0] != "M"):
        raise ValidationError("Křivková cesta potřebuje počáteční bod.")
    if path["closed"] and commands[-1] != ["Z"]:
        raise ValidationError("Uzavřená křivková cesta musí mít uzávěr.")
    sizes = {"M": 2, "L": 2, "C": 6, "A": 7, "Z": 0}
    for command in commands:
        if (not isinstance(command, list) or not command or not isinstance(command[0], str)
                or command[0] not in sizes
                or len(command) != sizes[command[0]] + 1):
            raise ValidationError("Nepodporovaný příkaz nativní křivky.")
        for value in command[1:]:
            number(value)
        if command[0] == "A" and (
            command[1] <= 0 or command[2] <= 0 or command[4] not in (0, 1)
            or command[5] not in (0, 1)
        ):
            raise ValidationError("Neplatné parametry nativního oblouku.")


def _mapped_commands(curve, mapping):
    tokens = re.findall(r"[MLCAZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",
                        svg_commands(curve))
    sizes = {"M": 2, "L": 2, "C": 6, "A": 7, "Z": 0}
    commands, index = [], 0
    matrix, offset = mapping

    def mapped(point):
        return (np.asarray(point) @ matrix.T + offset).tolist()

    while index < len(tokens):
        op = tokens[index]
        values = list(map(float, tokens[index + 1:index + 1 + sizes[op]]))
        index += sizes[op] + 1
        if op == "A":
            scale = np.linalg.norm(matrix[:, 0])
            values[:2] = [values[0] * scale, values[1] * scale]
            if np.linalg.det(matrix) < 0:
                values[5 - 1] = 1 - values[5 - 1]
            values[-2:] = mapped(values[-2:])
        else:
            values = [v for i in range(0, len(values), 2) for v in mapped(values[i:i + 2])]
        commands.append([op, *values])
    return commands


def _reversed_curve(curve):
    data = dict(curve.data)
    if curve.kind == "arc":
        data["sweep_deg"] = -data["sweep_deg"]
    elif curve.kind == "cubic":
        data["control1"], data["control2"] = data["control2"], data["control1"]
    return Curve(curve.end, curve.start, curve.kind, data, curve.segment_id)


def profile_native_path(profile, mapping):
    commands = []
    for segment in profile.segments:
        curve_commands = _mapped_commands(source_curve(profile, segment), mapping)
        commands.extend(curve_commands if not commands else curve_commands[1:])
    if profile.closed:
        commands.append(["Z"])
    return {"commands": commands, "closed": profile.closed}


def has_small_source_detail(project, part):
    """Inspect authored feature sizes, never display tessellation chord sizes."""
    for sid in part.surface_ids:
        surface = project.surfaces[sid]
        for pid in [surface.profile_id, *surface.hole_profile_ids]:
            profile = project.profiles[pid]
            if all(s.kind == "line" for s in profile.segments):
                if any(math.dist(profile.vertex(s.start_vertex_id).point,
                                 profile.vertex(s.end_vertex_id).point) * project.scale < 0.5
                       for s in profile.segments):
                    return True
            else:
                projection = project.profile_projection(pid)
                if any(c["length_lower"] * project.scale < 0.5 for c in projection["curves"]):
                    return True
            box = Polygon(project.profile_outline(pid)).minimum_rotated_rectangle
            points = list(box.exterior.coords)
            if min(math.dist(a, b) for a, b in zip(points, points[1:])) * project.scale < 0.5:
                return True
    return False


def restore_native_cut_curves(project, part, mappings):
    """Replace intact certified chord chains by their authored native curves.

    Exact chain matching supplies provenance. A Boolean-fragmented source curve
    is refused rather than silently printed as an unrelated polygonal curve.
    """
    records = []
    for sid in part.surface_ids:
        surface = project.surfaces[sid]
        for pid in [surface.profile_id, *surface.hole_profile_ids]:
            profile = project.profiles[pid]
            curved = [s for s in profile.segments if s.kind != "line"]
            if not curved:
                continue
            projections = {c["segment_id"]: c for c in project.profile_projection(pid)["curves"]}
            matrix, offset = mappings[sid]
            for segment in curved:
                samples = np.asarray(projections[segment.id]["points"]) @ matrix.T + offset
                curve = source_curve(profile, segment)
                for reversed_ in (False, True):
                    records.append({
                        "key": (sid, segment.id),
                        "samples": samples[::-1] if reversed_ else samples,
                        "commands": _mapped_commands(
                            _reversed_curve(curve) if reversed_ else curve, mappings[sid]
                        ),
                    })
    if not records:
        return
    used, paths = set(), []
    for old_path in part.paths["CUT"]:
        ring = np.asarray(old_path["points"])
        count = len(ring)
        start = next((i for i, p in enumerate(ring)
                      if any(np.array_equal(p, r["samples"][0]) for r in records)), None)
        if start is None:
            paths.append(old_path)
            continue
        ring = np.roll(ring, -start, axis=0)
        commands, index = [["M", *ring[0].tolist()]], 0
        while index < count:
            matched = None
            for record in records:
                chain = record["samples"]
                if record["key"] in used or index + len(chain) - 1 > count:
                    continue
                actual = ring[np.arange(index, index + len(chain)) % count]
                if np.array_equal(actual, chain):
                    matched = record
                    break
            if matched:
                commands.extend(matched["commands"][1:])
                used.add(matched["key"])
                index += len(matched["samples"]) - 1
            else:
                index += 1
                commands.append(["L", *ring[index % count].tolist()])
        commands.append(["Z"])
        paths.append({"commands": commands, "closed": True})
    if used != {r["key"] for r in records}:
        raise ValidationError(
            "Materiálový spoj rozdělil zdrojovou křivku. Oddělte dotýkající se materiál "
            "nebo upravte spoj; nelze potichu nahradit původní křivku polygonem."
        )
    part.paths["CUT"] = paths


def source_curve(profile, segment):
    return Curve(
        tuple(profile.vertex(segment.start_vertex_id).point),
        tuple(profile.vertex(segment.end_vertex_id).point),
        segment.kind, segment.data, segment.id,
    )


def arc_from_bulge(start, end, sweep_deg):
    """A circular segment with fixed authored endpoints and signed turn."""
    a, b = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    angle = math.radians(number(sweep_deg, "Úhel oblouku"))
    if not 0 < abs(angle) < 2 * math.pi:
        raise ValidationError("Úhel oblouku musí být nenulový a menší než celý obvod.")
    chord = b - a
    if np.linalg.norm(chord) <= 1e-9:
        raise ValidationError("Oblouk potřebuje dva různé koncové body.")
    center = (a + b) / 2 + np.array([-chord[1], chord[0]]) / (2 * math.tan(angle / 2))
    return {"center": center.tolist(), "sweep_deg": float(sweep_deg)}


def move_curve_endpoint(profile, vertex_id, value):
    """Keep arc bulge and cubic endpoint handles while moving a shared vertex."""
    vertex = profile.vertex(vertex_id)
    old = np.asarray(vertex.point)
    delta = np.asarray(value) - old
    vertex.point = list(value)
    for segment in profile.segments:
        if vertex_id not in (segment.start_vertex_id, segment.end_vertex_id):
            continue
        if segment.kind == "arc":
            segment.data = arc_from_bulge(
                profile.vertex(segment.start_vertex_id).point,
                profile.vertex(segment.end_vertex_id).point,
                segment.data["sweep_deg"],
            )
        elif segment.kind == "cubic":
            handle = "control1" if segment.start_vertex_id == vertex_id else "control2"
            segment.data[handle] = (np.asarray(segment.data[handle]) + delta).tolist()


class ProfileCurveCommands:
    def profile_projection(self, profile_id, *, tolerance_mm=0.002):
        """Bound each chord in paper mm; this is not a topology/loft proof."""
        profile = self.profiles[profile_id]
        tolerance_mm = number(tolerance_mm, "Přesnost zobrazení", positive=True)
        key = json.dumps([asdict(profile), self.scale, tolerance_mm], sort_keys=True)
        cache = getattr(self, "_profile_curve_cache", None)
        if cache is None:
            cache = self._profile_curve_cache = {}
        if key in cache:
            return copy.deepcopy(cache[key])
        curves = []
        points = []
        for segment in profile.segments:
            curve = source_curve(profile, segment)
            certificate = certify_curve(
                curve, chord_tolerance=tolerance_mm / self.scale,
                length_tolerance=tolerance_mm / (self.scale * len(profile.segments)),
            )
            if certificate.status != "CERTIFIED":
                raise ValidationError(
                    "Přesnost křivky nelze doložit v dostupném rozpočtu. "
                    "Zkontrolujte rozměry, řídicí body nebo rozdělte křivku. "
                    + certificate.message
                )
            curves.append(asdict(certificate))
            points.extend(list(point) for point in certificate.points[:-1])
        if not profile.closed:
            points.append(list(profile.vertices[-1].point))
        result = {
            "points": points, "curves": curves,
            "chord_deviation_bound_paper_mm": max(
                c["max_chord_deviation_bound"] * self.scale for c in curves
            ),
            "length_lower_paper_mm": math.fsum(c["length_lower"] for c in curves) * self.scale,
            "length_upper_paper_mm": math.fsum(c["length_upper"] for c in curves) * self.scale,
            "source_profile_id": profile.id, "source_revision": profile.revision,
        }
        if len(cache) > 128:
            cache.clear()
        cache[key] = copy.deepcopy(result)
        return result

    def profile_outline(self, profile_id):
        profile = self.profiles[profile_id]
        if all(segment.kind == "line" for segment in profile.segments):
            return profile.points
        return self.profile_projection(profile_id)["points"]

    @atomic
    def set_profile_segment(self, profile_id, segment_id, *, kind, data=None):
        profile = self.profiles[profile_id]
        segment = profile.segment(segment_id)
        if segment is None:
            raise ValidationError("Vybraný úsek už v profilu není.")
        candidate = copy.deepcopy(data or {})
        if segment.kind == kind and segment.data == candidate:
            return
        segment.kind, segment.data = kind, candidate
        profile.validate()
        self.profile_projection(profile_id)
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))

    @atomic
    def set_profile_plane(self, profile_id, *, origin, u, v):
        profile = self.profiles[profile_id]
        plane = SketchPlane(vector(origin, 3), vector(u, 3), vector(v, 3))
        plane.validate()
        if asdict(plane) == asdict(profile.plane):
            return
        profile.plane = plane
        profile.revision += 1
        self._touch(self._profile_surfaces(profile_id))

    @atomic
    def copy_profile(self, profile_id, *, factor=1, center=(0, 0), plane=None, name=None):
        source = self.profiles[profile_id]
        factor = number(factor, "Poměr kopie", positive=True)
        center = np.asarray(vector(center, 2))

        def mapped(point):
            return (center + factor * (np.asarray(point) - center)).tolist()

        segments = []
        for segment in source.segments:
            data = copy.deepcopy(segment.data)
            for key in ("center", "control1", "control2"):
                if key in data:
                    data[key] = mapped(data[key])
            segments.append({
                "kind": segment.kind,
                "start": mapped(source.vertex(segment.start_vertex_id).point),
                "end": mapped(source.vertex(segment.end_vertex_id).point), "data": data,
            })
        return self.add_profile(
            segments=segments, closed=source.closed, name=name or source.name + " · kopie",
            plane=plane or source.plane,
        )
