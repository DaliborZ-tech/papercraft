"""Persistent ruled surfaces; analytic source, bounded development and display stay distinct."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import asdict
from fractions import Fraction
from functools import lru_cache

import numpy as np
from shapely import Polygon

from . import curve_topology as topology
from .commands import atomic
from .curve_area import native_region_area_bounds
from .curves import _control, derivative, evaluate
from .errors import ValidationError
from .geometry import material_polygon, number, path
from .loft_curves import fit_native_loft_boundaries
from .loft_geometry import LoftCorrespondence, LoftProfile, flatten_loft
from .model import (
    MaterialPart,
    PaperFrame,
    Placement,
    Profile,
    SketchPlane,
    SurfaceFeature,
    identity,
    uuid,
)
from .profile_curves import source_curve

_PARAMS = {
    "second_profile_id",
    "correspondences",
    "seam_patch_id",
    "end_ruling_id",
    "tolerance_mm",
    "max_segments",
    "reference_state",
}
_PATCH = {
    "id",
    "ruling_id",
    "first_segment_id",
    "second_segment_id",
    "first_interval",
    "second_interval",
}


def _failure(status, code, message, **details):
    return {"status": status, "code": code, "message": message, "family": "UNPROVEN", **details}


def _topology_profile(profile):
    curves = [source_curve(profile, segment) for segment in profile.segments]
    if profile.closed:
        return asdict(topology.certify_region_topology(curves))
    budget = topology._Budget(
        100000,
        24,
        256
        * math.ulp(
            max(1.0, *(abs(value) for vertex in profile.vertices for value in vertex.point))
        ),
    )
    try:
        if curves[0].start == curves[-1].end:
            raise topology._InvalidError("Otevřený profil se dotýká sám sebe v koncovém bodu.")
        nodes = []
        for curve in curves:
            if curve.kind == "arc":
                center = curve.data["center"]
                angle = math.radians(curve.data["sweep_deg"])
                x, y = np.asarray(curve.start) - center
                predicted = [
                    center[0] + x * math.cos(angle) - y * math.sin(angle),
                    center[1] + x * math.sin(angle) + y * math.cos(angle),
                ]
                if math.dist(predicted, curve.end) > budget.guard:
                    raise topology._UnresolvedError("Konec oblouku překračuje rezervu topologie.")
                nodes.extend(topology._native_arcs(curve))
            else:
                nodes.extend(
                    topology._simple_pieces(topology._Node(curve, controls=_control(curve)), budget)
                )
        for i, j in topology._candidate_pairs(nodes, budget):
            first, second = nodes[i], nodes[j]
            allowed = set(first.ends()) & set(second.ends()) if j == i + 1 else set()
            topology._pair(first, second, allowed, budget)
        return {
            "status": "VALID",
            "reason": "Open source chain proved simple without a closing chord",
            "examined_nodes": budget.used,
        }
    except topology._InvalidError as exc:
        return {"status": "INVALID", "reason": exc.reason, "witness": exc.witness}
    except (topology._UnresolvedError, ValueError, ArithmeticError) as exc:
        return {"status": "UNRESOLVED", "reason": str(exc)}


def _native_topology(commands):
    """Use the same actual-path topology engine as manufacturing exporters."""
    return copy.deepcopy(_native_topology_cached(tuple(tuple(command) for command in commands)))


@lru_cache(maxsize=8)
def _native_topology_cached(commands):
    return asdict(topology.certify_native_region_topology(commands, max_nodes=400000))


def _profile_from_record(record):
    # Only detached dataclass records enter the cached mathematical analysis.
    from .model import CurveSegment, Vertex

    return Profile(
        record["id"],
        record["name"],
        [Vertex(**v) for v in record["vertices"]],
        [CurveSegment(**s) for s in record["segments"]],
        record["closed"],
        SketchPlane(**record["plane"]),
        record["revision"],
    )


def validate_loft_params(project, surface, *, require_bound=False):
    params = surface.params
    if not isinstance(params, dict) or set(params) != _PARAMS or surface.hole_profile_ids:
        raise ValidationError("Neplatná struktura konstrukčního loftu.")
    uuid(surface.profile_id)
    uuid(params["second_profile_id"])
    if (
        surface.profile_id == params["second_profile_id"]
        or params["second_profile_id"] not in project.profiles
    ):
        raise ValidationError("Loft potřebuje dva různé existující profily.")
    tolerance = number(params["tolerance_mm"], "Mez odchylky loftu", positive=True)
    if (
        tolerance > 0.01
        or type(params["max_segments"]) is not int
        or not 2 <= params["max_segments"] <= 65536
    ):
        raise ValidationError("Neplatný rozpočet přesného loftu.")
    if params["reference_state"] not in ("BOUND", "UNRESOLVED"):
        raise ValidationError("Neplatný stav zdrojových referencí loftu.")
    records = params["correspondences"]
    if not isinstance(records, list) or not records:
        raise ValidationError("Zvolte explicitní korespondenci zdrojových úseků.")
    ids = []
    for record in records:
        if not isinstance(record, dict) or set(record) != _PATCH:
            raise ValidationError("Neplatný záznam korespondence loftu.")
        for key in ("id", "ruling_id", "first_segment_id", "second_segment_id"):
            uuid(record[key])
        ids.extend((record["id"], record["ruling_id"]))
        for key in ("first_interval", "second_interval"):
            value = record[key]
            if (
                not isinstance(value, list)
                or any(type(x) not in (int, float) for x in value)
                or value not in ([0, 1], [1, 0])
            ):
                raise ValidationError("Podporovaný loft vyžaduje celé orientované zdrojové úseky.")
    uuid(params["seam_patch_id"])
    uuid(params["end_ruling_id"])
    if len(set(ids)) != len(ids) or params["end_ruling_id"] in ids:
        raise ValidationError("Konstrukční patche a rulingy potřebují odlišné stálé identity.")
    if params["seam_patch_id"] not in [r["id"] for r in records]:
        raise ValidationError("Začátek švu neodkazuje na zvolený patch.")
    if params["seam_patch_id"] != records[0]["id"]:
        raise ValidationError(
            "Šev musí být první korespondencí; otevřený profil začíná na svém konci."
        )
    a, b = project.profiles[surface.profile_id], project.profiles[params["second_profile_id"]]
    for expected, profile in zip(surface.source_profile_ids(), (a, b)):
        uuid(profile.id)
        if profile.id != expected or not isinstance(profile.closed, bool):
            raise ValidationError("Neplatná identita nebo uzavřenost zdrojového profilu loftu.")
        for vertex in profile.vertices:
            uuid(vertex.id)
        for segment in profile.segments:
            uuid(segment.id)
    occupied = {
        project.project_id,
        *project.profiles,
        *project.surfaces,
        *project.parts,
        *project.joints,
        *project.attachments,
        *project.connectors,
        *(page.id for page in project.pages),
    }
    occupied.update(v.id for p in project.profiles.values() for v in p.vertices)
    occupied.update(s.id for p in project.profiles.values() for s in p.segments)
    occupied.update(t for c in project.connectors.values() for t in c.tab_ids)
    for other in project.surfaces.values():
        if other.kind == "ruled_loft" and other.id != surface.id:
            occupied.update(
                r[key] for r in other.params["correspondences"] for key in ("id", "ruling_id")
            )
            occupied.add(other.params["end_ruling_id"])
    if occupied.intersection([*ids, params["end_ruling_id"]]):
        raise ValidationError(
            "Identita loft patche nebo rulingů koliduje s jiným zdrojem projektu."
        )
    if a.closed != b.closed and params["reference_state"] == "BOUND":
        raise ValidationError("Oba profily musí mít stejný otevřený nebo uzavřený stav.")
    bound = params["reference_state"] == "BOUND"
    if require_bound and not bound:
        raise ValidationError("LOFT_REFERENCE_UNRESOLVED: zvolte znovu korespondenci úseků.")
    if bound:
        for side, profile in (("first", a), ("second", b)):
            matched = [r[side + "_segment_id"] for r in records]
            if len(set(matched)) != len(matched) or set(matched) != {
                s.id for s in profile.segments
            }:
                raise ValidationError("Korespondence musí pokrýt právě všechny úseky obou profilů.")
            endpoints = []
            for r in records:
                s = profile.segment(r[side + "_segment_id"])
                ends = (s.start_vertex_id, s.end_vertex_id)
                endpoints.append(ends if r[side + "_interval"] == [0, 1] else ends[::-1])
            if any(x[1] != y[0] for x, y in zip(endpoints, endpoints[1:])):
                raise ValidationError("Korespondence se kříží nebo nenavazuje v pořadí profilu.")
            if profile.closed and endpoints[-1][1] != endpoints[0][0]:
                raise ValidationError("Uzavřený profil nemá úplnou korespondenci kolem švu.")
    return ids + [params["end_ruling_id"]]


def _commands(segments):
    commands = [["M", *segments[0]["start"]]]
    for s in segments:
        if s["kind"] == "line":
            commands.append(["L", *s["end"]])
        else:
            commands.append(["C", *s["data"]["control1"], *s["data"]["control2"], *s["end"]])
    if commands[-1][0] == "L" and commands[-1][1:] == commands[0][1:]:
        commands.pop()
    return [*commands, ["Z"]]


def _reverse(segment):
    result = copy.deepcopy(segment)
    result["start"], result["end"] = result["end"], result["start"]
    if result["kind"] == "cubic":
        d = result["data"]
        d["control1"], d["control2"] = d["control2"], d["control1"]
    return result


def _develop_once(key, effective_tolerance):
    data = json.loads(key)
    a, b = map(_profile_from_record, data["profiles"])
    params, scale = data["params"], data["scale"]
    binding = {
        "source_digest": hashlib.sha256(key.encode()).hexdigest(),
        "source_revisions": {a.id: a.revision, b.id: b.revision},
        "source_profile_ids": [a.id, b.id],
        "patches": copy.deepcopy(params["correspondences"]),
    }
    if params["reference_state"] != "BOUND":
        return {
            **_failure(
                "UNRESOLVED",
                "LOFT_REFERENCE_UNRESOLVED",
                "Zdrojové úseky se změnily. Vyberte znovu korespondenci a kotvu.",
            ),
            **binding,
        }
    topology_reports = {p.id: _topology_profile(p) for p in (a, b)}
    for result in topology_reports.values():
        if result["status"] != "VALID":
            return {
                **_failure("UNRESOLVED", "LOFT_SOURCE_TOPOLOGY_UNRESOLVED", result["reason"]),
                **binding,
                "source_topology": topology_reports,
            }
    correspondence = tuple(
        LoftCorrespondence(
            r["first_segment_id"],
            r["second_segment_id"],
            tuple(r["first_interval"]),
            tuple(r["second_interval"]),
        )
        for r in params["correspondences"]
    )
    solver = flatten_loft(
        LoftProfile.from_profile(a),
        LoftProfile.from_profile(b),
        correspondence,
        scale=scale,
        tolerance_mm=effective_tolerance,
        max_segments=params["max_segments"],
    )
    base = {
        **binding,
        "solver": solver,
        "flattening": {
            key: copy.deepcopy(value) for key, value in solver.items() if key != "patches"
        },
        "source_topology": topology_reports,
        "status": solver["status"],
        "family": solver.get("family", "UNPROVEN"),
        "code": "LOFT_" + solver["status"],
        "message": solver.get("message", "Přesná rodina loftu je doložená s uvedenými mezemi."),
    }
    if "witness" in solver:
        base["witness"] = copy.deepcopy(solver["witness"])
    if solver["status"] != "EXACT":
        return base
    native = fit_native_loft_boundaries(solver)
    base["native"] = native
    if native["status"] != "CERTIFIED_REPRESENTATION_ONLY":
        return {**base, **_failure("UNRESOLVED", "LOFT_NATIVE_BOUND_UNRESOLVED", native["message"])}
    base["representation"] = {
        key: value for key, value in native.items() if key not in ("patches", "source_coverage")
    }
    rulings = []
    for patch, endpoint in ((solver["patches"][0], 0), (solver["patches"][-1], -1)):
        world = (
            math.dist(
                patch["world_first_model_mm"][endpoint], patch["world_second_model_mm"][endpoint]
            )
            * scale
        )
        flat = math.dist(
            patch["flat_first_paper_mm"][endpoint], patch["flat_second_paper_mm"][endpoint]
        )
        error = abs(world - flat) + 2 * solver["numerical_guard_paper_mm"]
        if error > max(0.01, 1e-6 * world):
            return {
                **base,
                **_failure(
                    "UNRESOLVED",
                    "LOFT_RULING_METRIC_UNRESOLVED",
                    "Délka uzavíracího generátoru překročila požadovanou přesnost.",
                ),
            }
        rulings.append(
            {
                "world_length_paper_mm": world,
                "flat_length_paper_mm": flat,
                "length_error_bound_paper_mm": error,
                "scope": "STRAIGHT_RULED_INTERVAL_WITH_ACTUAL_SOURCE_ENDPOINTS",
            }
        )
    base["closing_rulings"] = rulings
    first = [s for p in native["patches"] for s in p["first"]["segments"]]
    second = [s for p in native["patches"] for s in p["second"]["segments"]]
    for chain in (first, second):
        if any(x["end"] != y["start"] for x, y in zip(chain, chain[1:])):
            return {
                **base,
                **_failure(
                    "UNRESOLVED",
                    "LOFT_NATIVE_JOIN_UNRESOLVED",
                    "Číselné konce sousedních rozvinutých úseků se neshodují.",
                ),
            }

    def line(start, end):
        return {"kind": "line", "start": start, "end": end, "data": {}}

    segments = [
        *first,
        line(first[-1]["end"], second[-1]["end"]),
        *[_reverse(s) for s in reversed(second)],
        line(second[0]["start"], first[0]["start"]),
    ]
    commands = _commands(segments)
    proof = _native_topology(commands)
    base.update(native_commands=commands, native_topology=proof)
    if proof["status"] != "VALID":
        return {
            **base,
            **_failure(
                "UNRESOLVED",
                "LOFT_NATIVE_TOPOLOGY_UNRESOLVED",
                "Nepřekrývání skutečného rozvinutého obrysu nebylo doložené: "
                + proof.get("reason", ""),
            ),
        }
    loop = [point for patch in solver["patches"] for point in patch["flat_first_paper_mm"][:-1]]
    loop += [solver["patches"][-1]["flat_first_paper_mm"][-1]]
    loop += [
        point
        for patch in reversed(solver["patches"])
        for point in reversed(patch["flat_second_paper_mm"][1:])
    ]
    loop += [solver["patches"][0]["flat_second_paper_mm"][0]]
    try:
        material_polygon(loop)
    except ValidationError as exc:
        return {
            **base,
            **_failure(
                "UNRESOLVED",
                "LOFT_PROXY_TOPOLOGY_UNRESOLVED",
                "Zobrazený obrys potřebuje jemnější rozpočet: " + str(exc),
            ),
        }
    base["flat_loop"] = loop
    return base


def _area_interval_record(low, high):
    return {
        "lower_exact": str(low),
        "upper_exact": str(high),
        "lower_paper_mm2": math.nextafter(float(low), -math.inf),
        "upper_paper_mm2": math.nextafter(float(high), math.inf),
    }


@lru_cache(maxsize=12)
def _native_area_cached(commands, max_commands):
    return native_region_area_bounds([commands], max_commands=max_commands)


def _area_check(source, commands, max_commands):
    """Independent source vs actual binary native material, in paper square mm."""
    low, high = Fraction(source["area_lower_exact"]), Fraction(source["area_upper_exact"])
    if low <= 0 or high < low:
        raise ValueError("Intrinsic surface area is not proved finite and positive")
    actual_low, actual_high = _native_area_cached(
        tuple(tuple(command) for command in commands), max_commands
    )
    error = max(abs(actual_low - high), abs(actual_high - low))
    allowed = max(Fraction(1, 100), low / 1000000)
    return {
        "status": "CERTIFIED" if error <= allowed else "UNRESOLVED",
        "source_intrinsic": copy.deepcopy(source),
        "actual_native": _area_interval_record(actual_low, actual_high),
        "maximum_error_bound_exact": str(error),
        "maximum_error_bound_paper_mm2": math.nextafter(float(error), math.inf),
        "allowed_error_exact": str(allowed),
        "allowed_error_paper_mm2": float(allowed),
        "proof": "INDEPENDENT_INTRINSIC_AREA_VS_ACTUAL_NATIVE_GREEN_INTEGRAL_INTERVALS",
        "tolerance_scope": "MAX_0.01_PAPER_MM2_OR_1E-6_INTRINSIC_AREA_LOWER_BOUND",
        "max_commands": max_commands,
        "serialized_output": "NOT_VERIFIED",
    }


def _source_intrinsic_area(data):
    try:
        from .loft_area import certify_loft_intrinsic_area
    except ImportError:
        return {"status": "UNRESOLVED", "message": "Důkaz skutečné plochy není dostupný."}
    first, second = map(_profile_from_record, data["profiles"])
    references = tuple(
        LoftCorrespondence(
            r["first_segment_id"],
            r["second_segment_id"],
            tuple(r["first_interval"]),
            tuple(r["second_interval"]),
        )
        for r in data["params"]["correspondences"]
    )
    report = certify_loft_intrinsic_area(
        LoftProfile.from_profile(first),
        LoftProfile.from_profile(second),
        references,
        scale=data["scale"],
        absolute_budget_mm2=1e-4,
        max_nodes=65536,
        max_depth=24,
    )
    if report["status"] == "CERTIFIED":
        expected = {
            "first_profile_id": first.id,
            "second_profile_id": second.id,
            "first_closed": first.closed,
            "second_closed": second.closed,
            "expected_first_segment_ids": [s.id for s in first.segments],
            "expected_second_segment_ids": [s.id for s in second.segments],
            "correspondences": [
                {
                    "first_segment_id": r.first_segment_id,
                    "second_segment_id": r.second_segment_id,
                    "first_parameter_interval": list(r.first_interval),
                    "second_parameter_interval": list(r.second_interval),
                }
                for r in references
            ],
        }
        if any(report.get("coverage", {}).get(key) != value for key, value in expected.items()):
            return {"status": "UNRESOLVED", "message": "Důkaz plochy neodpovídá zdrojovým vazbám."}
    return report


@lru_cache(maxsize=4)
def _analyze(key):
    data = json.loads(key)
    requested = data["params"]["tolerance_mm"]
    result = _develop_once(key, requested)
    if result["status"] != "EXACT":
        return result  # Preserve the original B3 witness/topology/budget diagnosis.
    source = _source_intrinsic_area(data)
    if source["status"] != "CERTIFIED":
        return {
            **result,
            **_failure(
                "UNRESOLVED",
                "LOFT_INTRINSIC_AREA_UNRESOLVED",
                "Skutečná plocha konstrukce není doložená: " + source.get("message", ""),
                family=result["family"],
                area={"status": "UNRESOLVED", "source_intrinsic": source},
            ),
        }
    attempts = []
    max_commands = (
        2 * data["params"]["max_segments"] + 2 * len(data["params"]["correspondences"]) + 8
    )
    for attempt in range(5):
        effective = requested / 10**attempt
        if attempt:
            candidate = _develop_once(key, effective)
            if candidate["status"] != "EXACT":
                attempts.append(
                    {
                        "attempt": attempt,
                        "effective_tolerance_mm": effective,
                        "status": candidate["status"],
                        "code": candidate["code"],
                        "message": candidate["message"],
                    }
                )
                break
            result = candidate
        try:
            area = _area_check(source, result["native_commands"], max_commands)
        except (ValueError, ArithmeticError, TypeError, KeyError) as exc:
            area = {
                "status": "UNRESOLVED",
                "source_intrinsic": copy.deepcopy(source),
                "message": str(exc),
            }
        attempts.append(
            {
                "attempt": attempt,
                "effective_tolerance_mm": effective,
                **{
                    k: v
                    for k, v in area.items()
                    if k
                    in (
                        "status",
                        "message",
                        "maximum_error_bound_exact",
                        "maximum_error_bound_paper_mm2",
                        "allowed_error_exact",
                    )
                },
            }
        )
        result.update(
            area={**area, "refinement_attempts": copy.deepcopy(attempts)},
            requested_tolerance_mm=requested,
            effective_tolerance_mm=effective,
        )
        if area["status"] == "CERTIFIED":
            return result
    return {
        **result,
        **_failure(
            "UNRESOLVED",
            "LOFT_AREA_UNRESOLVED",
            "Plocha rozvinu není v požadované toleranci; konečný rozpočet zjemnění nestačil.",
            family=result["family"],
            area={**result["area"], "refinement_attempts": attempts},
        ),
    }


@lru_cache(maxsize=8)
def _bound_analysis(intrinsic_key, surface_record):
    # The geometry cache has no UI feature UUID. Detach before binding only
    # fields whose contract explicitly denotes the owning surface feature.
    result = copy.deepcopy(_analyze(intrinsic_key))
    surface = json.loads(surface_record)
    feature_id = surface["id"]
    result["feature_id"] = feature_id
    solver = result.get("solver")
    if solver is not None:
        solver["feature_id"] = feature_id
        for patch, reference in zip(
            solver.get("patches", []), surface["params"]["correspondences"]
        ):
            patch["feature_id"] = feature_id
            patch["patch_id"] = reference["id"]
    native = result.get("native")
    if native is not None:
        native["feature_id"] = feature_id
        references = surface["params"]["correspondences"]
        for index, (patch, reference) in enumerate(zip(native.get("patches", []), references)):
            patch["patch_id"] = reference["id"]
            for side in ("first", "second"):
                for segment in patch[side]["segments"]:
                    segment["source"]["feature_id"] = feature_id
                    segment["source"]["patch_id"] = reference["id"]
            for segment in patch["closed_boundary_segments"]:
                segment["source"]["feature_id"] = feature_id
                segment["source"]["patch_id"] = reference["id"]
                if segment["source"].get("kind") == "EXPLICIT_MATCHED_RULING":
                    segment["source"]["ruling_id"] = (
                        reference["ruling_id"]
                        if segment["source"]["u"] == 0
                        else references[index + 1]["ruling_id"]
                        if index + 1 < len(references)
                        else surface["params"]["end_ruling_id"]
                    )
    binding = json.dumps(
        {"intrinsic_source_digest": result["source_digest"], "surface": surface},
        sort_keys=True,
        allow_nan=False,
    )
    result.update(
        intrinsic_source_digest=result["source_digest"],
        source_digest=hashlib.sha256(binding.encode()).hexdigest(),
        feature_revision=surface["revision"],
    )
    return result


def analysis(project, surface):
    validate_loft_params(project, surface)
    key = json.dumps(
        {
            "profiles": [asdict(project.profiles[pid]) for pid in surface.source_profile_ids()],
            "params": surface.params,
            "scale": project.scale,
        },
        sort_keys=True,
        allow_nan=False,
    )
    surface_record = json.dumps(asdict(surface), sort_keys=True, allow_nan=False)
    # Callers never receive either cached mutable dictionary. Preview workers
    # and the main document may safely consume/mutate their detached result.
    return copy.deepcopy(_bound_analysis(key, surface_record))


def world_loft_geometry(project, surface):
    result = analysis(project, surface)
    if surface.params["reference_state"] != "BOUND":
        return {
            "vertices": [],
            "triangles": [],
            "boundary": [],
            "vertex_normals": [],
            "triangle_sources": [],
            "vertex_sources": [],
            "status": "UNRESOLVED",
            "message": result["message"],
            "mesh_role": "NO_SOURCE_CORRESPONDENCE_NO_MESH",
        }
    a, b = (project.profiles[pid] for pid in surface.source_profile_ids())
    matrix = project._surface_matrix(surface.id)
    vertices, raw, normals, sources, triangles, triangle_sources, boundary = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    solver_patches = result.get("solver", {}).get("patches", [])
    patch_normals = []
    for index, reference in enumerate(surface.params["correspondences"]):
        ca, cb = (
            source_curve(a, a.segment(reference["first_segment_id"])),
            source_curve(b, b.segment(reference["second_segment_id"])),
        )
        ts = (
            solver_patches[index]["parameters"]
            if solver_patches
            else np.linspace(0, 1, 33).tolist()
        )
        first, second = [], []
        offset = len(vertices)
        for t in ts:
            ta = reference["first_interval"][0] + t * (
                reference["first_interval"][1] - reference["first_interval"][0]
            )
            tb = reference["second_interval"][0] + t * (
                reference["second_interval"][1] - reference["second_interval"][0]
            )
            pa, pb = a.plane.world([evaluate(ca, ta)])[0], b.plane.world([evaluate(cb, tb)])[0]
            da, db = np.asarray(derivative(ca, ta)), np.asarray(derivative(cb, tb))
            da = (da[0] * np.asarray(a.plane.u) + da[1] * np.asarray(a.plane.v)) * (
                reference["first_interval"][1] - reference["first_interval"][0]
            )
            db = (db[0] * np.asarray(b.plane.u) + db[1] * np.asarray(b.plane.v)) * (
                reference["second_interval"][1] - reference["second_interval"][0]
            )
            for v in (0.0, 1.0):
                point = (1 - v) * pa + v * pb
                normal = np.cross((1 - v) * da + v * db, pb - pa)
                length = np.linalg.norm(normal)
                normal = normal / length if length > 0 else np.zeros(3)
                transformed = matrix[:3, :3] @ point + matrix[:3, 3]
                raw.append(point)
                vertices.append(transformed.tolist())
                normals.append((matrix[:3, :3] @ normal).tolist())
                sources.append(
                    {
                        "feature_id": surface.id,
                        "patch_id": reference["id"],
                        "u": t,
                        "v": v,
                        "first_profile_id": a.id,
                        "second_profile_id": b.id,
                        "first_segment_id": ca.segment_id,
                        "second_segment_id": cb.segment_id,
                        "first_parameter": ta,
                        "second_parameter": tb,
                    }
                )
                (first if v == 0 else second).append(transformed.tolist())
        for i in range(len(ts) - 1):
            for face in (
                [offset + 2 * i, offset + 2 * i + 2, offset + 2 * i + 1],
                [offset + 2 * i + 1, offset + 2 * i + 2, offset + 2 * i + 3],
            ):
                triangles.append(face)
                triangle_sources.append(
                    {
                        "feature_id": surface.id,
                        "patch_id": reference["id"],
                        "uv": [[sources[j]["u"], sources[j]["v"]] for j in face],
                    }
                )
        planar_patch = result["status"] == "EXACT" and ca.kind == cb.kind == "line"
        patch_normals.append(
            {
                "patch_id": reference["id"],
                "vertex_range": [offset, len(vertices)],
                "normal_scope": "TRUE_SOURCE_DERIVATIVE_AT_EACH_VERTEX",
                "planar_patch": planar_patch,
                "constant_normal": normals[offset] if planar_patch else None,
            }
        )
        for side, chain in (("first", first), ("second", second)):
            for i, (p, q) in enumerate(zip(chain, chain[1:])):
                boundary.append(
                    {
                        "id": reference[side + "_segment_id"],
                        "start": p,
                        "end": q,
                        "source": {
                            "feature_id": surface.id,
                            "patch_id": reference["id"],
                            "profile_id": a.id if side == "first" else b.id,
                            "role": side.upper(),
                            "u_interval": [ts[i], ts[i + 1]],
                        },
                    }
                )
        boundary.append(
            {
                "id": reference["ruling_id"],
                "start": first[0],
                "end": second[0],
                "source": {
                    "feature_id": surface.id,
                    "patch_id": reference["id"],
                    "role": "SEAM_START" if index == 0 else "CONSTRUCTION_RULING",
                    "paired_ruling_id": surface.params["end_ruling_id"]
                    if index == 0 and a.closed
                    else None,
                },
            }
        )
        if index == len(surface.params["correspondences"]) - 1:
            boundary.append(
                {
                    "id": surface.params["end_ruling_id"],
                    "start": first[-1],
                    "end": second[-1],
                    "source": {
                        "feature_id": surface.id,
                        "patch_id": reference["id"],
                        "role": "SEAM_END",
                        "paired_ruling_id": surface.params["correspondences"][0]["ruling_id"]
                        if a.closed
                        else None,
                    },
                }
            )
    actual = np.asarray(vertices)
    raw = np.asarray(raw)
    if not np.isfinite(actual).all():
        raise ValidationError("Umístění loftu dává nekonečnou geometrii.")
    source_areas, actual_areas = [], []
    for face in triangles:
        p, q, r = raw[face]
        x, y, z = actual[face]
        source_areas.append(math.hypot(*np.cross(q - p, r - p)) / 2 * project.scale**2)
        actual_areas.append(math.hypot(*np.cross(y - x, z - x)) / 2 * project.scale**2)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            expected = math.dist(raw[face[i]], raw[face[j]]) * project.scale
            value = math.dist(actual[face[i]], actual[face[j]]) * project.scale
            if abs(value - expected) > max(0.01, 1e-6 * expected):
                raise ValidationError("Umístění loftu ztrácí délkovou přesnost modelu.")
    area = math.fsum(source_areas)
    if abs(math.fsum(actual_areas) - area) > max(0.01, 1e-6 * area):
        raise ValidationError("Umístění loftu ztrácí plošnou přesnost zobrazeného materiálu.")
    return {
        "vertices": vertices,
        "triangles": triangles,
        "boundary": boundary,
        "vertex_normals": normals,
        "patch_normals": patch_normals,
        "vertex_sources": sources,
        "triangle_sources": triangle_sources,
        "status": result["status"],
        "mesh_role": "DISPLAY_ONLY_NOT_FOLD",
        "source_evaluation": "DIRECT_RULED_SURFACE_S(u,v); MESH_PICKING_IS_NOT_ANALYTIC_INVERSE",
        "interpolation_bound_paper_mm": result.get("solver", {}).get(
            "representation_error_bound_paper_mm"
        ),
    }


def material_envelopes(project, part, *, output_error_mm=0):
    from .curve_material import _result

    surface = project.surfaces[part.surface_ids[0]]
    result = analysis(project, surface)
    if part.stale or result["status"] != "EXACT":
        raise ValidationError("Rozvin loftu nemá aktuální doložený materiál.")
    loop = part.polygons[surface.id][0]
    guard = 128 * math.ulp(max(1.0, *(abs(x) for point in loop for x in point)))
    error = result["native"]["position_error_bound_paper_mm"] + output_error_mm + guard
    chords = [(tuple(a), tuple(b), error) for a, b in zip(loop, loop[1:] + loop[:1])]
    source_ids = tuple(
        r[side + "_segment_id"]
        for r in surface.params["correspondences"]
        for side in ("first", "second")
    )
    return _result(Polygon(loop), chords, result["source_digest"], source_ids)


def has_small_loft_detail(project, part):
    result = analysis(project, project.surfaces[part.surface_ids[0]])
    for patch in result["solver"]["patches"]:
        for side in ("first", "second"):
            chain = patch["flat_" + side + "_paper_mm"]
            length = math.fsum(math.dist(a, b) for a, b in zip(chain, chain[1:]))
            if length + result["solver"]["boundary_length_error_bound_paper_mm"] < 0.5:
                return True
    if any(r["world_length_paper_mm"] < 0.5 for r in result["closing_rulings"]):
        return True
    rectangle = Polygon(part.polygons[part.surface_ids[0]][0]).minimum_rotated_rectangle
    points = list(rectangle.exterior.coords)
    return min(math.dist(a, b) for a, b in zip(points, points[1:])) < 0.5


def _local_frame(project, part, result):
    surface = project.surfaces[part.frame.root_surface_id]
    profile = project.profiles[surface.profile_id]
    anchor, axis = (
        profile.vertex(part.frame.anchor_vertex_id),
        profile.segment(part.frame.axis_segment_id),
    )
    if anchor is None or axis is None:
        raise ValidationError("ANCHOR_UNRESOLVED: zvolte znovu zdrojovou kotvu loftu.")
    patch = next((p for p in result["solver"]["patches"] if p["first_segment_id"] == axis.id), None)
    if patch is None:
        raise ValidationError("ANCHOR_UNRESOLVED: úsek kotvy není v korespondenci.")
    points = patch["flat_first_paper_mm"]
    start, end = (
        (points[0], points[-1])
        if patch["first_parameter_interval"] == [0, 1]
        else (points[-1], points[0])
    )
    if anchor.id == axis.start_vertex_id:
        origin = start
    elif anchor.id == axis.end_vertex_id:
        origin = end
    else:
        candidates = []
        for p in result["solver"]["patches"]:
            segment = profile.segment(p["first_segment_id"])
            ids = [segment.start_vertex_id, segment.end_vertex_id]
            if p["first_parameter_interval"] == [1, 0]:
                ids.reverse()
            for vertex_id, point in zip(
                ids, [p["flat_first_paper_mm"][0], p["flat_first_paper_mm"][-1]]
            ):
                if vertex_id == anchor.id and point not in candidates:
                    candidates.append(point)
        if len(candidates) != 1:
            raise ValidationError("ANCHOR_UNRESOLVED: kotva má na otevřeném švu více výskytů.")
        origin = candidates[0]
    dx, dy = np.asarray(end) - start
    angle = -math.atan2(dy, dx)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    return rotation, np.asarray(origin)


def crease_geometry(project, surface, result, front_side):
    """One-sided analytic tangent-plane turns about the source C0-to-C1 ruling.

    Supported EXACT families have a constant tangent plane along each ruling.
    We evaluate its midpoint using BOTH live profile derivatives, never mesh
    triangles, source chords or a uniform mountain label for all source corners.
    Common proper rigid placement preserves this signed triple product.
    """
    from .paper import fold_direction

    a, b = (project.profiles[pid] for pid in surface.source_profile_ids())

    def endpoint(reference, endpoint):
        values, tangents = [], []
        for side, profile in (("first", a), ("second", b)):
            curve = source_curve(profile, profile.segment(reference[side + "_segment_id"]))
            interval = reference[side + "_interval"]
            parameter = interval[endpoint]
            values.append(profile.plane.world([evaluate(curve, parameter)])[0])
            derivative_uv = derivative(curve, parameter)
            tangents.append(
                (
                    np.asarray(profile.plane.u) * derivative_uv[0]
                    + np.asarray(profile.plane.v) * derivative_uv[1]
                )
                * (interval[1] - interval[0])
            )
        ruling = values[1] - values[0]
        return ruling, np.cross((tangents[0] + tangents[1]) / 2, ruling)

    def unit(value):
        length = math.hypot(*value)
        if not math.isfinite(length) or length <= 0:
            raise ValidationError("LOFT_CREASE_UNRESOLVED: ohyb nemá doloženou orientaci.")
        return value / length

    records = surface.params["correspondences"]
    creases = []
    if result["status"] != "EXACT":
        return creases
    for index, patch in enumerate(result["solver"]["patches"]):
        if patch["join_before_kind"] != "FOLD_CREASE":
            continue
        _, previous = endpoint(records[index - 1], 1)
        ruling, following = endpoint(records[index], 0)
        before, after, axis = unit(previous), unit(following), unit(ruling)
        sine = float(np.dot(axis, np.cross(before, after)))
        cosine = float(np.dot(before, after))
        if abs(sine) < 128 * math.ulp(1.0) and cosine < 0:
            raise ValidationError("LOFT_CREASE_UNRESOLVED: směr obratu o 180° není jednoznačný.")
        angle = math.atan2(sine, cosine)
        creases.append(
            {
                "patch_id": records[index]["id"],
                "ruling_id": records[index]["ruling_id"],
                "signed_angle_deg": math.degrees(angle),
                "role": fold_direction(angle, front_side),
                "normal_scope": "ANALYTIC_ONE_SIDED_RULED_DERIVATIVES_AT_COMMON_RULING",
                "axis_orientation": "FIRST_PROFILE_TO_SECOND_PROFILE",
            }
        )
    return creases


def build_loft_part(project, old_part):
    if len(old_part.surface_ids) != 1:
        raise ValidationError(
            "Loft zatím potřebuje vlastní papírový díl; složené kontakty nejsou doložené."
        )
    surface = project.surfaces[old_part.surface_ids[0]]
    result = analysis(project, surface)
    if result["status"] != "EXACT":
        raise ValidationError(result["code"] + ": " + result["message"])
    rotation, origin = _local_frame(project, old_part, result)

    def mapped(points):
        return ((np.asarray(points) - origin) @ rotation.T).tolist()

    part = copy.deepcopy(old_part)
    part.polygons = {surface.id: [mapped(result["flat_loop"])]}
    commands = []
    for command in result["native_commands"]:
        commands.append(
            [
                command[0],
                *[
                    x
                    for point in mapped([command[i : i + 2] for i in range(1, len(command), 2)])
                    for x in point
                ],
            ]
            if command[0] != "Z"
            else ["Z"]
        )
    proof = _native_topology(commands)
    if proof["status"] != "VALID":
        raise ValidationError("LOFT_FRAME_TOPOLOGY_UNRESOLVED: " + proof.get("reason", ""))
    try:
        area = _area_check(
            result["area"]["source_intrinsic"], commands, result["area"]["max_commands"]
        )
    except (ValueError, ArithmeticError, TypeError, KeyError) as exc:
        raise ValidationError("LOFT_FRAME_AREA_UNRESOLVED: plocha rámu není doložená.") from exc
    if area["status"] != "CERTIFIED":
        raise ValidationError(
            "LOFT_FRAME_AREA_UNRESOLVED: rám rozvinu překročil plošnou toleranci."
        )
    part.paths = {key: [] for key in ("CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "GUIDES")}
    part.paths["CUT"] = [{"commands": commands, "closed": True}]
    part.edges = []
    creases = {c["patch_id"]: c for c in crease_geometry(project, surface, result, part.front_side)}
    for patch, reference in zip(result["solver"]["patches"], surface.params["correspondences"]):
        for side in ("first", "second"):
            points = mapped(patch["flat_" + side + "_paper_mm"])
            for i, (a, b) in enumerate(zip(points, points[1:])):
                part.edges.append(
                    {
                        "surface_id": surface.id,
                        "edge_id": reference[side + "_segment_id"],
                        "start": a,
                        "end": b,
                        "source": {
                            "feature_id": surface.id,
                            "patch_id": reference["id"],
                            "profile_id": patch[side + "_profile_id"],
                            "segment_id": reference[side + "_segment_id"],
                            "role": side.upper(),
                            "parameter_interval": [
                                patch["source_parameters"][i][0 if side == "first" else 1],
                                patch["source_parameters"][i + 1][0 if side == "first" else 1],
                            ],
                        },
                    }
                )
        if patch["join_before_kind"] == "FOLD_CREASE":
            part.paths[creases[reference["id"]]["role"]].append(
                path(mapped([patch["flat_first_paper_mm"][0], patch["flat_second_paper_mm"][0]]))
            )
    center = Polygon(part.polygons[surface.id][0]).representative_point()
    part.labels = [{"text": part.name, "x": center.x, "y": center.y, "size_mm": 2.5}]
    from .paper import part_input

    part.input_digest = part_input(project, part)
    part.stale = False
    if old_part.stale or part.input_digest != old_part.input_digest:
        part.source_revision = project.revision
    return part


class LoftCommands:
    def _loft_preview_result(self, surface_id):
        return {
            **self.loft_status(surface_id),
            "surface_id": surface_id,
            "part_id": self.part_for_surface(surface_id),
            "params": copy.deepcopy(self.surfaces[surface_id].params),
            "world_geometry": self.world_geometry(surface_id),
            "project_state": self.to_dict(),
        }

    def loft_status(self, surface_id):
        surface = self.surfaces[surface_id]
        if surface.kind == "planar":
            self._source_polygon(surface.profile_id, surface.hole_profile_ids)
            return {
                "status": "EXACT",
                "family": "PLANAR_REGION",
                "code": "PLANAR_REGION_EXACT",
                "message": "Rovinný materiál s původním vnějším obrysem a otvory.",
                "source_profile_ids": surface.source_profile_ids(),
            }
        result = analysis(self, surface)
        from .paper import part_input

        part = self.parts[surface.part_id]
        stale = part.stale or part.input_digest != part_input(self, part)
        frame_area, frame_topology, frame_failure = None, None, {}
        if result["status"] == "EXACT" and not stale:
            try:
                frame_topology = _native_topology(part.paths["CUT"][0]["commands"])
                if frame_topology["status"] != "VALID":
                    raise ValueError("Uložený skutečný obrys nemá doloženou topologii.")
                frame_area = _area_check(
                    result["area"]["source_intrinsic"],
                    part.paths["CUT"][0]["commands"],
                    result["area"]["max_commands"],
                )
            except (ValueError, ArithmeticError, TypeError, KeyError, IndexError) as exc:
                frame_area = {"status": "UNRESOLVED", "message": str(exc)}
            if frame_area["status"] != "CERTIFIED":
                frame_failure = {
                    "status": "UNRESOLVED",
                    "code": "LOFT_FRAME_AREA_UNRESOLVED",
                    "message": "Uložený rozvin nemá doloženou plošnou přesnost.",
                }
        return copy.deepcopy(
            {
                "crease_geometry": crease_geometry(
                    self, surface, result, self.parts[surface.part_id].front_side
                ),
                "paper_frame": asdict(part.frame),
                "paper_input_digest": part.input_digest,
                "paper_stale": stale,
                "paper_contract": "ANALYTIC_SIGNED_CREASES_AND_INTRINSIC_AREA_V1",
                "paper_frame_area": frame_area,
                "paper_frame_topology": frame_topology,
                **{
                    key: value
                    for key, value in result.items()
                    if key not in ("solver", "native", "flat_loop", "native_commands")
                },
                **frame_failure,
            }
        )

    def preview_loft(
        self,
        first_profile_id,
        second_profile_id,
        *,
        correspondences,
        seam_patch_id=None,
        end_ruling_id=None,
        tolerance_mm=0.005,
        max_segments=16384,
        name="Ostění",
    ):
        clone = copy.deepcopy(self)
        sid = clone.add_loft(
            first_profile_id,
            second_profile_id,
            correspondences=correspondences,
            seam_patch_id=seam_patch_id,
            end_ruling_id=end_ruling_id,
            tolerance_mm=tolerance_mm,
            max_segments=max_segments,
            name=name,
        )
        return clone._loft_preview_result(sid)

    def preview_loft_update(
        self,
        surface_id,
        *,
        second_profile_id=None,
        correspondences=None,
        seam_patch_id=None,
        tolerance_mm=None,
        max_segments=None,
    ):
        clone = copy.deepcopy(self)
        clone.update_loft(
            surface_id,
            second_profile_id=second_profile_id,
            correspondences=correspondences,
            seam_patch_id=seam_patch_id,
            tolerance_mm=tolerance_mm,
            max_segments=max_segments,
        )
        # Source edits truthfully keep the previous paper cache stale until
        # the author's recompute command; the actual source mesh is live.
        return clone._loft_preview_result(surface_id)

    @atomic
    def add_loft(
        self,
        first_profile_id,
        second_profile_id,
        *,
        correspondences,
        seam_patch_id=None,
        end_ruling_id=None,
        tolerance_mm=0.005,
        max_segments=16384,
        name="Ostění",
    ):
        for profile_id in (first_profile_id, second_profile_id):
            uuid(profile_id)
            if profile_id not in self.profiles:
                raise ValidationError("Vyberte existující zdrojový profil loftu.")
        a, b = self.profiles[first_profile_id], self.profiles[second_profile_id]
        records = copy.deepcopy(correspondences)
        if not isinstance(records, list) or not records:
            raise ValidationError("Vyberte explicitní korespondenci profilových úseků.")
        for record in records:
            if not isinstance(record, dict):
                raise ValidationError("Korespondence potřebuje záznamy zdrojových úseků.")
            record.setdefault("id", identity())
            record.setdefault("ruling_id", identity())
            record.setdefault("first_interval", [0, 1])
            record.setdefault("second_interval", [0, 1])
        seam = records[0]["id"] if seam_patch_id is None else seam_patch_id
        if a.closed and seam in [r["id"] for r in records]:
            index = next(i for i, r in enumerate(records) if r["id"] == seam)
            records = records[index:] + records[:index]
        elif seam != records[0]["id"]:
            raise ValidationError("Otevřený profil začíná švem na prvním spárovaném úseku.")
        sid, pid = identity(), identity()
        surface = SurfaceFeature(
            sid,
            name,
            a.id,
            kind="ruled_loft",
            part_id=pid,
            params={
                "second_profile_id": b.id,
                "correspondences": records,
                "seam_patch_id": seam,
                "end_ruling_id": identity() if end_ruling_id is None else end_ruling_id,
                "tolerance_mm": tolerance_mm,
                "max_segments": max_segments,
                "reference_state": "BOUND",
            },
        )
        validate_loft_params(self, surface, require_bound=True)
        for profile in (a, b):
            topology_result = _topology_profile(profile)
            if topology_result["status"] == "INVALID":
                raise ValidationError(
                    "Profil loftu se kříží nebo překrývá: " + topology_result["reason"]
                )
        if asdict(a.plane) == asdict(b.plane):
            from .loft_geometry import _homothety, _pair

            family = _homothety(
                _pair(
                    LoftProfile.from_profile(a),
                    LoftProfile.from_profile(b),
                    [
                        LoftCorrespondence(
                            r["first_segment_id"],
                            r["second_segment_id"],
                            tuple(r["first_interval"]),
                            tuple(r["second_interval"]),
                        )
                        for r in records
                    ],
                )
            )
            if family is not None and family[0] == 1 and all(x == 0 for x in family[1]):
                raise ValidationError("Shodné profily ve stejné rovině mají nulovou plochu loftu.")
        # Coplanar closed inputs construct a real planar region, not a closed
        # volume or an approximate space loft with an invented normal.
        if a.closed and b.closed and asdict(a.plane) == asdict(b.plane):
            for outer, hole in ((a, b), (b, a)):
                try:
                    self._source_polygon(outer.id, [hole.id])
                except ValidationError:
                    continue
                return self.add_surface(outer.id, [hole.id], name=name)
            raise ValidationError(
                "Rovinný pás potřebuje oddělený vnější obrys a skutečný vnitřní otvor."
            )
        frame = PaperFrame(sid, a.vertices[0].id, a.segments[0].id)
        part = MaterialPart(
            pid,
            f"P{self.next_part_number} · {name}",
            [sid],
            frame,
            polygons={},
            paths={key: [] for key in ("CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "GUIDES")},
            number=self.next_part_number,
        )
        self.surfaces[sid], self.parts[pid] = surface, part
        index = self.next_part_number - 1
        self.next_part_number += 1
        self.placements[pid] = Placement(x_mm=(index % 3) * 120.0, y_mm=(index // 3) * 120.0)
        self._touch([sid])
        result = analysis(self, surface)
        if result.get("family") == "SINGULAR_HOMOTHETY":
            raise ValidationError("Korespondence obsahuje zhroucení nebo křížení generátorů.")
        if result["status"] == "EXACT":
            self.parts[pid] = build_loft_part(self, part)
        return sid

    @atomic
    def update_loft(
        self,
        surface_id,
        *,
        second_profile_id=None,
        correspondences=None,
        seam_patch_id=None,
        tolerance_mm=None,
        max_segments=None,
    ):
        surface = self.surfaces[surface_id]
        if surface.kind != "ruled_loft":
            raise ValidationError("Rovinný pás upravujte jako vlastní obrys a otvor.")
        params = surface.params
        if second_profile_id is not None:
            params["second_profile_id"] = second_profile_id
        if correspondences is not None:
            records = copy.deepcopy(correspondences)
            if (
                not isinstance(records, list)
                or not records
                or any(not isinstance(record, dict) for record in records)
            ):
                raise ValidationError(
                    "Korespondence potřebuje neprázdný seznam zdrojových záznamů."
                )
            previous = {
                (r["first_segment_id"], r["second_segment_id"]): r
                for r in params["correspondences"]
            }
            for record in records:
                old = previous.get((record["first_segment_id"], record["second_segment_id"]), {})
                record.setdefault("id", old.get("id", identity()))
                record.setdefault("ruling_id", old.get("ruling_id", identity()))
            params["correspondences"] = records
            params["reference_state"] = "BOUND"
        if seam_patch_id is not None:
            params["seam_patch_id"] = seam_patch_id
        if tolerance_mm is not None:
            params["tolerance_mm"] = tolerance_mm
        if max_segments is not None:
            params["max_segments"] = max_segments
        records = params["correspondences"]
        if self.profiles[surface.profile_id].closed and params["seam_patch_id"] in [
            r["id"] for r in records
        ]:
            index = next(i for i, r in enumerate(records) if r["id"] == params["seam_patch_id"])
            params["correspondences"] = records[index:] + records[:index]
        validate_loft_params(self, surface)
        self._touch([surface_id])
