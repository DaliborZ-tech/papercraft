"""Retained source → selected material → ACTUAL serialized manufacturing cuts.

A canonical author-source replay closes frames, variants, reference exclusions,
ordinary material and connector unions. No naked status string or JSON digest
can substitute for that proof. Serialized geometry is read independently.
"""

from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from fractions import Fraction
from functools import lru_cache

from archpapercraft.authoring.curve_area import native_region_area_bounds

from .curve_output_validation import CurveOutputError, read_pdf_cut_regions
from .loft_output_validation import _coordinate_errors, _placed
from .svg_curve_validation import read_svg_cut_regions

MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_SOURCE_NODES = 500000
MAX_SOURCE_DEPTH = 64
MAX_SOURCE_PARTS = 4096
MAX_SOURCE_VARIANTS = 8
MAX_SOURCE_PAGES = 64
MAX_OUTPUT_COMMANDS = 40000
MAX_OUTPUT_NODES = 400000


def _json(value, *, sort_keys=True):
    pending, count = [(value, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_SOURCE_NODES or depth > MAX_SOURCE_DEPTH:
            raise ValueError("Zdroj segmentace překročil konečný rozpočet struktury.")
        if isinstance(node, dict):
            if any(type(key) is not str for key in node):
                raise ValueError("Zdrojové klíče musí být řetězce.")
            pending.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, (list, tuple)):
            pending.extend((child, depth + 1) for child in node)
        elif not isinstance(node, (str, int, float, bool)) and node is not None:
            raise ValueError("Zdroj potřebuje konečná data JSON.")
        if isinstance(node, float) and not math.isfinite(node):
            raise ValueError("Zdroj má nekonečnou souřadnici.")
    result = json.dumps(
        value, sort_keys=sort_keys, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    if len(result.encode("utf8")) > MAX_SOURCE_BYTES:
        raise ValueError("Zdroj segmentace překročil rozpočet32MiB.")
    return result


@lru_cache(maxsize=2)
def _canonical_snapshot(source_json):
    """Cache only immutable bytes, keyed by actual complete source content."""
    from archpapercraft.authoring import AuthorProject

    source = json.loads(source_json)
    if source.get("application") != "ArchPapercraft.AuthorProject":
        raise ValueError("Chybí skutečný autorský projekt segmentace.")
    for key, limit in (
        ("parts", MAX_SOURCE_PARTS),
        ("surfaces", MAX_SOURCE_PARTS),
        ("profiles", 2 * MAX_SOURCE_PARTS),
        ("segmented_variants", MAX_SOURCE_VARIANTS),
    ):
        if not isinstance(source.get(key), dict) or len(source[key]) > limit:
            raise ValueError("Zdroj má neúplný nebo příliš velký registr " + key + ".")
    if (
        not isinstance(source.get("pages"), list)
        or not 1 <= len(source["pages"]) <= MAX_SOURCE_PAGES
    ):
        raise ValueError("Zdroj nemá konečný podporovaný počet stránek.")
    # No files are opened or written. This validates immutable provenance,
    # selected/reference closure, actual body planes, joins and tab materials.
    project = AuthorProject.from_dict(source)
    canonical = project.snapshot()
    return _json(canonical)


def _commands(path):
    if "commands" in path:
        return path["commands"]
    points = path["points"]
    return [
        ["M", *points[0]],
        *[["L", *point] for point in points[1:]],
        *([["Z"]] if path.get("closed") else []),
    ]


def validate_segmented_snapshot(data):
    """Do not permit D guards to be skipped merely because curve_profiles={} ."""
    checks, coverage = data.get("construction_checks", {}), data.get("coverage", {})
    reports = checks.get("segmented_variants", {})
    declared = coverage.get("expected_segmented_variant_ids", [])
    tagged = any(
        "flattening" in part for page in data.get("pages", []) for part in page.get("parts", [])
    )
    has_reference = bool(
        checks.get("reference_targets")
        or coverage.get("reference_surface_ids")
        or coverage.get("inactive_variant_surface_ids")
    )
    source = checks.get("segmented_source_project")
    if not (reports or declared or tagged or has_reference or source is not None):
        return {}
    try:
        if (
            not isinstance(reports, dict)
            or not isinstance(declared, list)
            or len(declared) != len(set(declared))
            or set(reports) != set(declared)
        ):
            raise ValueError("Odvozené generace nemají úplný očekávaný registr.")
        if not isinstance(source, dict) or not source.get("segmented_variants"):
            raise ValueError("Chybí úplný skutečný zdrojový projekt odvozené varianty.")
        # Registry insertion order also determines the explicit snapshot order.
        # Retain it for replay, while ordinary equality below sorts object keys.
        source_json = _json(source, sort_keys=False)
        canonical = json.loads(_canonical_snapshot(source_json))
        if _json(data) != _json(canonical):
            raise ValueError(
                "Snapshot, jeho materiál/řezy/rám/spoje nebo reference neodpovídají "
                "skutečnému zdrojovému projektu."
            )
        bindings = {}
        for page_index, page in enumerate(data["pages"]):
            for part in page["parts"]:
                flattening = part.get("flattening")
                if flattening is None:
                    continue
                if flattening.get("mode") != "APPROXIMATE":
                    raise ValueError("Odvozený materiál nesmí být vydán za přesný původní cíl.")
                vid = flattening["variant_id"]
                report = reports[vid]
                if report["status"] != "APPROXIMATE" or report["mode"] != "APPROXIMATE":
                    raise ValueError("Odvozená varianta není aktuální potvrzená aproximace.")
                row = next(
                    row for row in report["triangle_bindings"] if row["part_id"] == part["id"]
                )
                bindings[part["id"]] = {
                    "part": part,
                    "page_index": page_index,
                    "flattening": flattening,
                    "report": report,
                    "binding": row,
                    "source_project_digest": hashlib.sha256(source_json.encode()).hexdigest(),
                }
        return bindings
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        StopIteration,
        ArithmeticError,
        RecursionError,
    ) as exc:
        raise CurveOutputError(
            "Nelze doložit odvozený materiál: " + str(exc),
            report={"status": "UNRESOLVED", "scope": "SEGMENTED_SOURCE_AND_MATERIAL_CLOSURE"},
        ) from exc


def _metadata(svg_paths, pdf_path, data):
    from pypdf import PdfReader

    checks = data["construction_checks"]
    expected = {vid: "APPROXIMATE" for vid in checks["segmented_variants"]}
    keywords = json.loads(PdfReader(pdf_path).metadata["/Keywords"])
    if keywords.get("segmented_variant_modes") != expected:
        raise ValueError("Skutečné PDF neobsahuje pravdivý režim APPROXIMATE.")
    if (
        keywords.get("construction_checks_digest")
        != hashlib.sha256(_json(checks).encode()).hexdigest()
    ):
        raise ValueError("Skutečné PDF není svázané se stejným úplným zdrojovým důkazem.")
    for page, path in zip(data["pages"], svg_paths):
        root = ET.parse(path).getroot()
        metadata = root.find("{http://www.w3.org/2000/svg}metadata[@id='construction-checks']")
        if metadata is None or _json(json.loads(metadata.text)) != _json(checks):
            raise ValueError("Skutečné SVG změnilo úplný zdrojový důkaz.")
        groups = {
            node.get("data-part-id"): node for node in root if node.get("data-part-id") is not None
        }
        for part in page["parts"]:
            if "flattening" not in part:
                continue
            record, group = part["flattening"], groups[part["id"]]
            for attr, key in (
                ("data-flattening-mode", "mode"),
                ("data-segmented-variant-id", "variant_id"),
                ("data-target-surface-id", "target_surface_id"),
                ("data-segmented-triangle-id", "triangle_id"),
            ):
                if group.get(attr) != record[key]:
                    raise ValueError("Skutečné SVG ztratilo režim nebo zdrojové UUID dílu.")


def validate_segmented_vector_outputs(data, svg_paths, pdf_path, *, expected_parts):
    """Direct canonical material→each actual file; target deviation added ONCE."""
    bindings = validate_segmented_snapshot(data)
    if not bindings:
        return {}
    try:
        _metadata(svg_paths, pdf_path, data)
        svg = {}
        for index, path in enumerate(svg_paths):
            expected = {
                pid: value for pid, value in expected_parts.items() if value["page_index"] == index
            }
            svg.update(read_svg_cut_regions(path, expected)["parts"])
        pdf = read_pdf_cut_regions(pdf_path)["parts"]
        if set(pdf) != set(expected_parts) or set(svg) != set(expected_parts):
            raise ValueError("Skutečný vektorový výstup nepokrývá právě všechny tiskové díly.")
        records = {}
        for pid, item in bindings.items():
            part, proof = item["part"], item["report"]
            place = part["placement"]
            placement = [place["x_mm"], place["y_mm"], place["rotation_deg"]]
            loops = [_commands(path) for path in part["paths"]["CUT"]]
            # Net material includes the proven body PLUS legitimate tab union.
            source_area = native_region_area_bounds(loops, max_commands=MAX_OUTPUT_COMMANDS)
            area_budget = max(Fraction(1, 100), source_area[0] / 1000000)
            bound = Fraction(item["flattening"]["max_surface_deviation_paper_mm_exact"])
            requested = Fraction(proof["parameters"]["max_deviation_mm"])
            record = {
                "mode": "APPROXIMATE",
                "variant_id": item["flattening"]["variant_id"],
                "target_surface_id": item["flattening"]["target_surface_id"],
                "triangle_id": item["binding"]["id"],
                "source_parameter_key": item["binding"]["source_parameter_key"],
                "source_project_digest": item["source_project_digest"],
                "source_material_area_exact": [str(v) for v in source_area],
                "allowed_material_area_error_exact": str(area_budget),
                "outputs": {},
            }
            for kind, actual in (("svg", svg[pid]), ("pdf", pdf[pid])):
                if actual["page_index"] != item["page_index"] or len(actual["loops"]) != len(loops):
                    raise ValueError(
                        "Skutečný výstup změnil stránku nebo topologii odvozeného dílu."
                    )
                target_loops = (
                    [_placed(loop, actual["placement"]) for loop in actual["loops"]]
                    if kind == "svg"
                    else actual["loops"]
                )
                expected_loops = [_placed(loop, placement) for loop in loops]
                errors = [_coordinate_errors(a, b) for a, b in zip(expected_loops, target_loops)]
                position, length = max(e[0] for e in errors), sum(e[1] for e in errors)
                area = native_region_area_bounds(actual["loops"], max_commands=MAX_OUTPUT_COMMANDS)
                area_error = max(abs(area[0] - source_area[1]), abs(area[1] - source_area[0]))
                # The mesh budget is not re-granted to the vector publisher.
                # Publication has its own0.01mm material metric requirement.
                if position > Fraction(1, 100) or length > Fraction(1, 100):
                    raise ValueError("Skutečný výstup překročil digitální metriku materiálu.")
                if area_error > area_budget or bound + position > requested:
                    raise ValueError("Skutečný výstup překročil plochu nebo původní target budget.")
                record["outputs"][kind] = {
                    "actual_material_area_exact": [str(v) for v in area],
                    "source_material_to_actual_area_error_bound_exact": str(area_error),
                    "source_material_to_actual_position_error_bound_exact": str(position),
                    "source_material_to_actual_whole_cut_length_error_bound_exact": str(length),
                    "original_target_to_actual_position_error_bound_exact": str(bound + position),
                    "original_target_requested_budget_exact": str(requested),
                }
            records[pid] = record
        return {
            "status": "VERIFIED",
            "parts": records,
            "mode": "APPROXIMATE_VS_RETAINED_ORIGINAL_TARGET",
            "area_scope": "DIRECT_CANONICAL_MATERIAL_CORE_PLUS_LEGITIMATE_TABS_TO_EACH_FILE; "
            "NOT_EXACT_SMOOTH_TARGET_AREA",
            "physical_build": "NOT_VERIFIED",
            "new_user_test": "NOT_RUN",
        }
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        ArithmeticError,
        OSError,
        ET.ParseError,
    ) as exc:
        if isinstance(exc, CurveOutputError):
            raise
        raise CurveOutputError(
            "Nelze doložit skutečný odvozený výstup: " + str(exc), report={"status": "UNRESOLVED"}
        ) from exc
