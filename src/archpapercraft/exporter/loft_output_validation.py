"""Bind actual staged native loft cuts to current source certificates.

Source certificates remain authoritative mathematical evidence. This publisher
checks their detached source binding and the ACTUAL serialized geometry against
the SAME intrinsic source, not a newly granted tolerance at each conversion.
"""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from functools import lru_cache
from types import SimpleNamespace

from archpapercraft.authoring.curve_area import native_region_area_bounds

from .curve_output_validation import CurveOutputError, read_pdf_cut_regions
from .svg_curve_validation import read_svg_cut_regions

LOFT_OUTPUT_MAX_NODES = 400000
LOFT_OUTPUT_MAX_COMMANDS = 40000


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _fraction(value):
    if type(value) not in (int, float, Fraction) or not math.isfinite(value):
        raise ValueError("Loft potřebuje konečné skutečné souřadnice.")
    return Fraction(value)


def _positive_bounds(source):
    if source.get("status") != "CERTIFIED":
        raise ValueError("Skutečná plocha zdrojového loftu není doložená.")
    low, high = (Fraction(source[key]) for key in ("area_lower_exact", "area_upper_exact"))
    if low <= 0 or high < low:
        raise ValueError("Zdrojová plocha loftu nemá kladné přesné meze.")
    return low, high


@lru_cache(maxsize=8)
def _bound_source_native(source_json, frame_json):
    """Derive canonical native controls from the bound ACTUAL source records.

    Reuse the approved source analysis/cache; this is binding validation, not
    an independent replacement geometry oracle or a new refinement request.
    No mutable object owned by that source cache is changed or returned.
    """
    from archpapercraft.authoring.circular_shell import transform_native_commands
    from archpapercraft.authoring.loft_surface import (
        _bound_analysis,
        _local_frame,
        _profile_from_record,
    )

    binding = json.loads(source_json)
    surface = binding["surface"]
    intrinsic_json = json.dumps(
        {
            "profiles": binding["profiles"],
            "params": surface["params"],
            "scale": binding["scale"],
        },
        sort_keys=True,
        allow_nan=False,
    )
    result = _bound_analysis(intrinsic_json, json.dumps(surface, sort_keys=True, allow_nan=False))
    if result["status"] != "EXACT":
        raise ValueError("Skutečný vázaný zdroj již nemá doložený přesný rozvin.")
    project = SimpleNamespace(
        profiles={p["id"]: _profile_from_record(p) for p in binding["profiles"]},
        surfaces={surface["id"]: SimpleNamespace(**surface)},
    )
    part = SimpleNamespace(frame=SimpleNamespace(**json.loads(frame_json)))
    rotation, origin = _local_frame(project, part, result)
    commands = [tuple(c) for c in transform_native_commands(
        result["native_commands"], rotation, origin)]
    return (
        tuple(commands),
        _digest(result["representation"]),
        _digest(result["area"]["source_intrinsic"]),
    )


@lru_cache(maxsize=4)
def _bound_curved_material(source_json, frame_json):
    """Fresh source-only reconstruction; persisted material is never approval."""
    from archpapercraft.authoring.curved_connectors import rebuild_curved_material_binding
    from archpapercraft.authoring.loft_surface import build_loft_part

    binding, frame = json.loads(source_json), json.loads(frame_json)
    curved = binding.pop("curved_material_inputs")
    project = rebuild_curved_material_binding(binding, frame, curved)
    sid = binding["surface"]["id"]
    part = build_loft_part(project, project.parts[project.surfaces[sid].part_id])
    report = getattr(part, "_circular_material_report", None)
    return json.dumps({"paths": part.paths, "material": report}, sort_keys=True, allow_nan=False)


def validate_loft_snapshot(data):
    """Validate current feature/source UUID/revision/digest and canonical CUT.

    This reuses approved source analysis, recomputing it on a cache miss.
    It never mutates or refines authored profiles or their requested parameters.
    A pure loft has no planar curve_profile entry; that must never skip proof.
    """
    from archpapercraft.authoring.loft_surface import LOFT_PAPER_CONTRACT

    reports = data.get("construction_checks", {}).get("lofts", {})
    if not isinstance(reports, dict):
        raise ValueError("Loft kontroly potřebují úplný registr zdrojů.")
    declared = data.get("coverage", {}).get("expected_loft_surface_ids")
    if declared is not None and (
        not isinstance(declared, list)
        or len(declared) != len(set(declared))
        or set(declared) != set(reports)
    ):
        raise CurveOutputError("Chybí úplné očekávané pokrytí skutečných loft feature.")
    parts = {
        sid: (part, index)
        for index, page in enumerate(data["pages"])
        for part in page["parts"]
        for sid in part.get("surface_ids", [])
    }
    result = {}
    has_curved = any(report.get("source_binding", {}).get("curved_material_inputs")
                     for report in reports.values() if isinstance(report, dict))
    if has_curved:
        from archpapercraft.authoring.errors import ValidationError

        try:
            from archpapercraft.authoring.curved_connectors import validate_curved_snapshot_binding

            validate_curved_snapshot_binding(data)
        except (ValidationError, ValueError, TypeError, KeyError, ImportError) as exc:
            raise CurveOutputError(
                "Nelze ověřit úplné zdroje kruhového materiálu: " + str(exc)) from exc
    for sid, report in reports.items():
        try:
            if not isinstance(report, dict) or report.get("status") != "EXACT":
                raise ValueError("Loft není aktuální doložený EXACT rozvin.")
            part, page_index = parts[sid]
            if part["surface_ids"] != [sid] or report["feature_id"] != sid:
                raise ValueError("Důkaz loftu nepatří skutečnému dílu a feature UUID.")
            if report.get("paper_stale") is not False:
                raise ValueError("Loft má zastaralý nebo neurčený rám rozvinu.")
            if report.get("paper_contract") != LOFT_PAPER_CONTRACT:
                raise ValueError("Loft používá starší nebo neznámý kontrakt výrobního rozvinu.")
            binding = report["source_binding"]
            profiles, surface = binding["profiles"], binding["surface"]
            if (
                len(profiles) != 2
                or surface["id"] != sid
                or surface["kind"] != "ruled_loft"
                or surface["part_id"] != part["id"]
                or report["feature_revision"] != surface["revision"]
                or report["source_profile_ids"] != [p["id"] for p in profiles]
                or report["source_revisions"] != {p["id"]: p["revision"] for p in profiles}
                or surface["profile_id"] != profiles[0]["id"]
                or surface["params"]["second_profile_id"] != profiles[1]["id"]
                or surface["params"]["reference_state"] != "BOUND"
                or report["patches"] != surface["params"]["correspondences"]
            ):
                raise ValueError("Loft source binding má odlišné skutečné zdroje nebo revize.")
            _fraction(binding["scale"])
            if binding["scale"] <= 0:
                raise ValueError("Neplatné zdrojové měřítko loftu.")
            intrinsic = _digest(
                {
                    "profiles": profiles,
                    "params": surface["params"],
                    "scale": binding["scale"],
                }
            )
            if (
                intrinsic != report["intrinsic_source_digest"]
                or _digest({"intrinsic_source_digest": intrinsic, "surface": surface})
                != report["source_digest"]
            ):
                raise ValueError("Loft source digest neodpovídá skutečnému zdroji a feature.")
            coverage = report["area"]["source_intrinsic"]["coverage"]
            flattening = report["flattening"]
            if flattening["status"] != "EXACT":
                raise ValueError("Chybí přesný zdrojový loft důkaz.")
            for index, side in enumerate(("first", "second")):
                profile = profiles[index]
                segments = [s["id"] for s in profile["segments"]]
                matched = [p[side + "_segment_id"] for p in report["patches"]]
                if (
                    coverage[side + "_profile_id"] != profile["id"]
                    or coverage["expected_" + side + "_segment_ids"] != segments
                    or coverage[side + "_closed"] != profile["closed"]
                    or len(matched) != len(set(matched))
                    or set(matched) != set(segments)
                    or flattening["coverage"][side + "_profile_id"] != profile["id"]
                    or flattening["coverage"]["expected_" + side + "_segment_ids"] != segments
                ):
                    raise ValueError("Důkaz nepokrývá všechny skutečné zdrojové úseky loftu.")
            source = report["area"]["source_intrinsic"]
            low, high = _positive_bounds(source)
            budget = max(Fraction(1, 100), low / 1000000)
            material = None
            if binding.get("curved_material_inputs"):
                material = json.loads(_bound_curved_material(
                    json.dumps(binding, sort_keys=True, allow_nan=False),
                    json.dumps(report["paper_frame"], sort_keys=True, allow_nan=False),
                ))
                if report.get("curved_material") != material["material"]:
                    raise ValueError("Materiál chlopní neodpovídá čerstvým skutečným zdrojům.")
            for key in ("area", "paper_frame_area"):
                area = report[key]
                expected_source = (material["material"]["source_material_area"]
                                   if key == "paper_frame_area" and material["material"]
                                   else source) if material is not None else source
                area_low, area_high = _positive_bounds(expected_source)
                if area.get("status") != "CERTIFIED" or area["source_intrinsic"] != expected_source:
                    raise ValueError("Loft nemá plošný důkaz stejného skutečného zdroje.")
                if (expected_source != source and
                        (area.get("relative_area_basis") != "BODY_ONLY" or
                         area.get("relative_area_basis_source") != source)):
                    raise ValueError("Chlopně nesmějí navýšit relativní plošnou toleranci těla.")
                native = area["actual_native"]
                actual = Fraction(native["lower_exact"]), Fraction(native["upper_exact"])
                error = max(abs(actual[0] - area_high), abs(actual[1] - area_low))
                if error > budget or Fraction(area["maximum_error_bound_exact"]) < error:
                    raise ValueError("Plošná mez loftu neodpovídá skutečnému zdroji.")
            if (
                report["native_topology"]["status"] != "VALID"
                or report["paper_frame_topology"]["status"] != "VALID"
                or report["paper_frame"]["root_surface_id"] != sid
            ):
                raise ValueError("Loft nemá aktuální kanonický rám a topologii.")
            paths = part["paths"]["CUT"]
            if len(paths) != 1 or not paths[0].get("closed"):
                raise ValueError("Loft vyžaduje jediný úplný skutečný řezný obrys.")
            commands = paths[0]["commands"]
            has_arcs = any(c[0] == "A" for c in commands)
            if (any(c[0] not in ("M", "L", "C", "A", "Z") for c in commands) or
                    has_arcs and not report["representation"].get("circular_shell")):
                raise ValueError("Loft CUT musí zachovat zdrojově doložené nativní hranice.")
            actual = native_region_area_bounds([commands], max_commands=LOFT_OUTPUT_MAX_COMMANDS)
            declared = report["paper_frame_area"]["actual_native"]
            if actual != (Fraction(declared["lower_exact"]), Fraction(declared["upper_exact"])):
                raise ValueError("Skutečný CUT neodpovídá doloženému kanonickému rámci loftu.")
            representation = report["representation"]
            if representation["status"] != "CERTIFIED_REPRESENTATION_ONLY":
                raise ValueError("Nativní reprezentace loftu není doložená.")
            for key in ("position_error_bound_paper_mm", "boundary_length_error_bound_paper_mm"):
                if not 0 <= _fraction(representation[key]) < Fraction(1, 100):
                    raise ValueError("Zdroj loftu vyčerpal celý publikační geometrický rozpočet.")
            if len(report["closing_rulings"]) != 2:
                raise ValueError("Loft nemá oba skutečné uzavírací rulingy.")
            expected_commands, actual_representation, actual_source = _bound_source_native(
                json.dumps(binding, sort_keys=True, allow_nan=False),
                json.dumps(report["paper_frame"], sort_keys=True, allow_nan=False),
            )
            if material is not None:
                expected_commands = tuple(tuple(c) for c in material["paths"]["CUT"][0]["commands"])
                if any(part["paths"].get(role) != material["paths"].get(role)
                       for role in ("TABS", "GUIDES")):
                    raise ValueError("Chlopně nebo základny ohybů se liší od skutečných zdrojů.")
            if (
                tuple(tuple(c) for c in commands) != expected_commands
                or _digest(representation) != actual_representation
                or _digest(source) != actual_source
            ):
                raise ValueError("Skutečný CUT nebo certifikát neodpovídá vázanému zdroji a rámci.")
            result[sid] = {"part": part, "page_index": page_index, "report": report}
        except (ValueError, KeyError, TypeError, IndexError, ArithmeticError) as exc:
            raise CurveOutputError(
                "Nelze navázat výstup na aktuální zdroj loftu: " + str(exc),
                part_id=parts.get(sid, ({}, None))[0].get("id"),
                report={"status": "UNRESOLVED", "feature_id": sid},
            ) from exc
    return result


def _placed(commands, placement):
    angle = math.radians(float(placement[2]))
    c, s = Fraction(math.cos(angle)), Fraction(math.sin(angle))
    x, y = map(Fraction, placement[:2])
    result = []
    for command in commands:
        if command[0] == "A":
            if command[1] != command[2] or command[3] != 0:
                raise ValueError("Only native circular A can be placed in a loft output.")
            a, b = map(Fraction, command[-2:])
            result.append(["A", *command[1:6], x+c*a-s*b, y+s*a+c*b])
            continue
        coords = []
        for i in range(1, len(command), 2):
            a, b = map(Fraction, command[i : i + 2])
            coords.extend((x + c * a - s * b, y + s * a + c * b))
        result.append([command[0], *coords])
    return result


def _coordinate_errors(source, target, *, details=None, length_budget=Fraction(1, 1000000)):
    """Whole-curve bounds, not samples; exact rational serialized operands.

    Position uses the maximum L1 control difference. Arc-length change is at
    most integral |D'| <= sum |e[j+1]-e[j]| over each Bernstein control polygon.
    The latter is summed over the WHOLE CUT, hence bounds every boundary chain
    or ruling separately without granting a tolerance to each short segment.
    """
    if any(c[0] == "A" for c in source):
        from .circular_output_validation import coordinate_errors

        return coordinate_errors(source, target, details=details, length_budget=length_budget)
    if len(source) != len(target):
        raise ValueError("Skutečný výstup změnil počet původních loft příkazů.")
    position = length = Fraction(0)
    current_source = current_target = start_source = start_target = None
    for a, b in zip(source, target):
        previous_length = length
        if a[0] != b[0] or len(a) != len(b):
            raise ValueError("Skutečný výstup změnil nativní topologii nebo L/C zdroje loftu.")
        op = a[0]
        pa = [tuple(map(Fraction, a[i : i + 2])) for i in range(1, len(a), 2)]
        pb = [tuple(map(Fraction, b[i : i + 2])) for i in range(1, len(b), 2)]
        if op == "Z":
            pa, pb = [start_source], [start_target]
        errors = [(x - u, y - v) for (x, y), (u, v) in zip(pa, pb)]
        local_position = max(abs(x)+abs(y) for x, y in errors)
        if op != "M":
            local_position = max(local_position,
                                 sum(abs(x-y) for x, y in zip(current_source, current_target)))
        position = max(position, local_position)
        if op != "M":
            initial = tuple(x - y for x, y in zip(current_source, current_target))
            chain = [initial, *errors]
            length += sum(abs(x - u) + abs(y - v) for (x, y), (u, v) in zip(chain, chain[1:]))
        else:
            start_source, start_target = pa[0], pb[0]
        current_source, current_target = pa[-1], pb[-1]
        if details is not None:
            details.append({"position": local_position, "length": length-previous_length})
    return position, length


def validate_loft_vector_outputs(data, svg_paths, pdf_path, *, expected_parts):
    """Direct source intrinsic → ACTUAL SVG and ACTUAL PDF, same final budget."""
    lofts = validate_loft_snapshot(data)
    if not lofts:
        return {}
    svg = {}
    for index, path in enumerate(svg_paths):
        expected = {
            pid: value for pid, value in expected_parts.items() if value["page_index"] == index
        }
        svg.update(read_svg_cut_regions(path, expected)["parts"])
    pdf = read_pdf_cut_regions(pdf_path)["parts"]
    auxiliary = {}
    if any(item["report"].get("curved_material") for item in lofts.values()):
        from .circular_output_validation import read_svg_role_regions

        for role in ("GUIDES", "TABS"):
            svg_role = {}
            for index, path in enumerate(svg_paths):
                expected = {pid: value for pid, value in expected_parts.items()
                            if value["page_index"] == index}
                svg_role.update(read_svg_role_regions(
                    path, expected, role=role, require_closed=role == "TABS")["parts"])
            auxiliary[role] = {"svg": svg_role, "pdf": read_pdf_cut_regions(
                pdf_path, role=role, require_closed=role == "TABS")["parts"]}
    records = {}
    for sid, item in lofts.items():
        part, report = item["part"], item["report"]
        pid = part["id"]
        body_source = report["area"]["source_intrinsic"]
        material = report.get("curved_material")
        source = material["source_material_area"] if material is not None else body_source
        low, high = _positive_bounds(source)
        area_budget = max(Fraction(1, 100), _positive_bounds(body_source)[0] / 1000000)
        placement = part["placement"]
        requested = [placement["x_mm"], placement["y_mm"], placement["rotation_deg"]]
        commands = part["paths"]["CUT"][0]["commands"]
        expected = _placed(commands, requested)
        record = {
            "feature_id": sid,
            "part_id": pid,
            "source_profile_ids": report["source_profile_ids"],
            "source_digest": report["source_digest"],
            "intrinsic_source_digest": report["intrinsic_source_digest"],
            "source_area_exact": [str(low), str(high)],
            "allowed_area_error_exact": str(area_budget),
            "outputs": {},
            **({"source_native_strain_scope": "SOURCE_NATIVE_A_CHART_DOMAIN_CERTIFICATE",
                "actual_vector_scope": "CUT_GUIDE_FILL_POSITION_GLOBAL_LENGTH_AND_AREA_ONLY",
                "actual_pdf_derivative_strain": "NOT_CLAIMED",
                "physical_fold": "NOT_VERIFIED"} if material is not None else {}),
        }
        for kind, actual in (("svg", svg[pid]), ("pdf", pdf[pid])):
            try:
                loops = actual["loops"]
                if len(loops) != 1 or actual["page_index"] != item["page_index"]:
                    raise ValueError("Výstup změnil úplné pokrytí loft dílu nebo stránky.")
                actual_area = native_region_area_bounds(
                    loops, max_commands=LOFT_OUTPUT_MAX_COMMANDS
                )
                area_error = max(abs(actual_area[0] - high), abs(actual_area[1] - low))
                actual_commands = (
                    _placed(loops[0], actual["placement"]) if kind == "svg" else loops[0]
                )
                details = []
                numeric_position, numeric_length = _coordinate_errors(
                    expected, actual_commands, details=details)
                material_metrics = {}
                if material is not None:
                    owners = material["cut_command_ownership"]
                    if len(owners) != len(details):
                        raise ValueError("Chybí zdrojové pokrytí příkazů chlopní.")
                    tab_position, tab_length = Fraction(0), Fraction(0)
                    for owner, measured in zip(owners, details):
                        if owner["kind"] == "TAB_CUT":
                            tab_position = max(tab_position, measured["position"])
                            tab_length += measured["length"]
                    reserve = Fraction(material["publication_error_budget_exact"])
                    if tab_position > reserve or tab_length > reserve:
                        raise ValueError(
                            "Skutečné řezy chlopní vyčerpaly vlastní publikační rezervu.")
                    material_metrics = {
                        "tab_cut_position_error_exact": str(tab_position),
                        "tab_cut_global_length_error_exact": str(tab_length),
                        "tab_publication_error_budget_exact": str(reserve),
                    }
                    for role, index_key in (("GUIDES", "guide_path_index"),
                                            ("TABS", "fill_path_index")):
                        actual_role = auxiliary[role][kind][pid]
                        source_paths = part["paths"].get(role, [])
                        if (actual_role["page_index"] != item["page_index"] or
                                len(actual_role["loops"]) != len(source_paths)):
                            raise ValueError(
                                "Tištěný ohyb nebo záložka ztratil úplné pokrytí cest.")
                        role_position, role_length = Fraction(0), Fraction(0)
                        for packet in material["slots"]:
                            i = packet[index_key]
                            reference = _placed(source_paths[i]["commands"], requested)
                            actual_path = actual_role["loops"][i]
                            if kind == "svg":
                                actual_path = _placed(actual_path, actual_role["placement"])
                            error, deficit = _coordinate_errors(
                                reference, actual_path,
                                length_budget=reserve/(64*max(1, len(material["slots"]))))
                            role_position = max(role_position, error)
                            role_length += deficit
                        if role_position > reserve or role_length > reserve:
                            raise ValueError(
                                "Skutečný tištěný " + role + " vyčerpal vlastní rezervu chlopní.")
                        material_metrics[role.lower()+"_position_error_exact"] = str(role_position)
                        material_metrics[role.lower()+"_global_length_error_exact"] = str(
                            role_length)
                representation = report["representation"]
                # position_error_bound already includes source F→line delta.
                # Add ONLY the actual binary-native→serialized difference.
                total_position = (
                    _fraction(representation["position_error_bound_paper_mm"]) + numeric_position
                    + (Fraction(material["body_trim_position_error_exact"])
                       if material is not None else 0)
                )
                total_length = (
                    _fraction(representation["boundary_length_error_bound_paper_mm"])
                    + numeric_length
                    + (Fraction(material["body_trim_global_length_error_exact"])
                       if material is not None else 0)
                )
                rulings = []
                for ruling in report["closing_rulings"]:
                    bound = _fraction(ruling["length_error_bound_paper_mm"]) + numeric_length
                    budget = max(
                        Fraction(1, 100), _fraction(ruling["world_length_paper_mm"]) / 1000000
                    )
                    rulings.append(
                        {"total_error_bound_exact": str(bound), "allowed_error_exact": str(budget)}
                    )
                    if bound > budget:
                        raise ValueError(
                            "Skutečný výstup překročil délkový rozpočet uzavíracího rulingu."
                        )
                record["outputs"][kind] = {
                    **material_metrics,
                    "area_exact": [str(v) for v in actual_area],
                    "source_to_actual_area_error_bound_exact": str(area_error),
                    "source_to_actual_position_error_bound_exact": str(total_position),
                    "source_to_actual_profile_length_error_bound_exact": str(total_length),
                    "native_to_actual_position_error_bound_exact": str(numeric_position),
                    "native_to_actual_whole_cut_length_error_bound_exact": str(numeric_length),
                    "closing_rulings": rulings,
                }
                if area_error > area_budget:
                    raise ValueError(
                        "Skutečná plocha zdroj→výstup překročila normativní rozpočet loftu."
                    )
                if total_position > Fraction(1, 100) or total_length > Fraction(1, 100):
                    raise ValueError(
                        "Skutečný zdroj→výstup překročil polohový nebo délkový rozpočet loftu."
                    )
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                raise CurveOutputError(
                    "Nelze doložit skutečný loft " + kind.upper() + ": " + str(exc),
                    part_id=pid,
                    part_name=part.get("name"),
                    page_index=item["page_index"],
                    report={"status": "UNRESOLVED", "lofts": {sid: record}},
                ) from exc
        records[sid] = record
    return {
        "status": "VERIFIED",
        "lofts": records,
        "area_scope": "DIRECT_SAME_INTRINSIC_SOURCE_TO_EACH_ACTUAL_OUTPUT_NOT_FRESH_STAGE_BUDGETS",
        "metric_scope": (
            "SOURCE_NATIVE_ARC_INTERVALS_AND_ACTUAL_PDF_HERMITE_LENGTH; SOURCE_BOUND_ONCE"
            if any(item["report"]["representation"].get("circular_shell")
                   for item in lofts.values()) else
            "WHOLE_BERNSTEIN_CONTROL_DIFFERENCES; SOURCE_F_TO_NATIVE_BOUND_ONCE"),
        "physical_build": "NOT_VERIFIED",
        "new_user_test": "NOT_RUN",
        "actual_pdf_vector_metrics": "VERIFIED_NOT_A_PDF_DERIVATIVE_OR_PHYSICAL_FOLD_PROOF",
    }
