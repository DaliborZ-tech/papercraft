"""Certify local CUT topology of the actually written own-format native SVG.

Group rotation/translation are invertible isometries. This check proves the
serialized local manufacturing topology, not exact inter-part page distances.
Page separation uses source material envelopes with the full output reservation;
the PDF validator separately certifies its actually serialized page coordinates.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from .curve_output_validation import CurveOutputError, validate_native_output_regions

_NS = "{http://www.w3.org/2000/svg}"
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_TOKEN = re.compile(r"[\s,]*(" + _NUMBER + r"|[MLCAZ])")
_PLACEMENT = re.compile(
    rf"translate\(({_NUMBER})\s+({_NUMBER})\)\s+rotate\(({_NUMBER})\)"
)


def _loops(text):
    tokens, offset = [], 0
    while offset < len(text):
        match = _TOKEN.match(text, offset)
        if match is None:
            if text[offset:].strip():
                raise CurveOutputError("SVG řez obsahuje nepodporovaný nebo neúplný příkaz.")
            break
        tokens.append(match[1])
        offset = match.end()
    loops, current, index = [], None, 0
    arities = {"M": 2, "L": 2, "C": 6, "A": 7, "Z": 0}
    while index < len(tokens):
        op = tokens[index]
        if op not in arities:
            raise CurveOutputError("SVG řez nemá úplné absolutní příkazy M/L/C/A/Z.")
        size = arities[op]
        try:
            values = [Fraction(value) for value in tokens[index + 1:index + 1 + size]]
        except (ValueError, ZeroDivisionError) as exc:
            raise CurveOutputError("Čísla skutečného SVG řezu nelze přesně přečíst.") from exc
        if len(values) != size:
            raise CurveOutputError("SVG řez má neúplné souřadnice.")
        if op == "M":
            if current is not None:
                raise CurveOutputError("SVG řez obsahuje neukončený obrys.")
            current = [[op, *values]]
        elif current is None:
            raise CurveOutputError("SVG řez nezačíná úplným obrysem.")
        else:
            current.append([op, *values])
            if op == "Z":
                loops.append(current)
                current = None
        index += size + 1
    if current is not None or not loops:
        raise CurveOutputError("SVG řez není uzavřený nebo chybí.")
    return loops


def validate_svg_curve_geometry(path, expected_parts):
    """Validate actual local CUT subpaths, preserving decimal operands exactly."""
    try:
        raw = Path(path).read_bytes()
        root = ET.fromstring(raw)
        if root.tag != _NS + "svg" or root.get("viewBox", "").split()[:2] != ["0", "0"]:
            raise CurveOutputError("SVG nemá očekávané papírové souřadnice.")
        width, height = (Fraction(root.attrib[key].removesuffix("mm"))
                         for key in ("width", "height"))
        if width <= 0 or height <= 0 or any(
            not root.attrib[key].endswith("mm") for key in ("width", "height")
        ):
            raise CurveOutputError("SVG nemá doložené fyzické jednotky stránky.")
        if [Fraction(v) for v in root.attrib["viewBox"].split()] != [0, 0, width, height]:
            raise CurveOutputError("SVG mění měřítko fyzické stránky.")
        allowed_tags = {_NS + tag for tag in ("svg", "g", "path", "text", "title", "metadata")}
        for node in root.iter():
            if node.tag not in allowed_tags or any(
                key in node.attrib for key in
                ("style", "clip-path", "mask", "filter", "display", "visibility")
            ) or (node.get("transform") and node.get("data-part-id") is None):
                raise CurveOutputError(
                    "Výrobní SVG obsahuje nepodporovanou kresbu nebo změnu stavu."
                )
        for child in root:
            if child.tag in (_NS + "title", _NS + "metadata"):
                continue
            if child.tag != _NS + "g" or (
                child.get("data-part-id") is None and child.get("id") != "page-GUIDES"
            ):
                raise CurveOutputError(
                    "Výrobní SVG obsahuje neoznačenou kresbu mimo díly a kalibraci."
                )
        page_index = next((record["page_index"] for record in expected_parts.values()), 0)
        actual = {"parts": {}, "pages": [{"page_index": page_index,
                                          "width_mm": str(width), "height_mm": str(height)}],
                  "arithmetic": "EXACT_FRACTIONS_OF_SERIALIZED_SVG_DECIMALS"}
        for group in root.iter(_NS + "g"):
            pid = group.get("data-part-id")
            if pid is None:
                continue
            expected = expected_parts.get(pid)
            if expected is None or pid in actual["parts"] or group not in list(root):
                raise CurveOutputError("SVG změnilo úplné pokrytí papírových dílů.")
            if not _PLACEMENT.fullmatch(group.get("transform", "")):
                raise CurveOutputError("SVG díl nemá podporované pevné umístění.",
                                       part_id=pid, part_name=expected.get("name"))
            roles = [node.get("data-role") for node in group if node.tag != _NS + "title"]
            if len(roles) != 7 or set(roles) != {
                "CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "LABELS", "ARTWORK", "GUIDES"
            }:
                raise CurveOutputError(
                    "SVG díl nemá úplné jednoznačné výrobní vrstvy.", part_id=pid,
                )
            cut = [node for node in group if node.get("data-role") == "CUT"]
            if len(cut) != 1 or cut[0].get("transform"):
                raise CurveOutputError("SVG dílu chybí jednoznačná vrstva řezů.", part_id=pid)
            loops = []
            for node in cut[0]:
                if node.tag != _NS + "path" or node.get("transform"):
                    raise CurveOutputError("SVG řez používá nepodporovanou strukturu.", part_id=pid)
                loops.extend(_loops(node.get("d", "")))
            actual["parts"][pid] = {"page_index": expected["page_index"], "loops": loops}
        report = {"status": "UNRESOLVED", "kind": "ACTUAL_STAGED_SVG_LOCAL_CUT_TOPOLOGY",
                  "svg_sha256": hashlib.sha256(raw).hexdigest(), "parts": {}, "separations": [],
                  "placement_scope": "SOURCE_CONSERVATIVE_OUTPUT_BUDGET_ENVELOPES; "
                                     "NO_EXACT_SERIALIZED_SVG_PAGE_SEPARATION_CLAIM",
                  "physical_build": "NOT_VERIFIED", "new_user_test": "NOT_RUN"}
        if not expected_parts and not actual["parts"]:
            report["status"] = "NO_MATERIAL"
            return report
        return validate_native_output_regions(
            actual, expected_parts, report=report,
            check_separation=False, check_page_bounds=False,
        )
    except CurveOutputError:
        raise
    except (OSError, ET.ParseError, ValueError, KeyError, TypeError) as exc:
        raise CurveOutputError("Skutečné výrobní SVG nelze úplně ověřit: " + str(exc)) from exc
