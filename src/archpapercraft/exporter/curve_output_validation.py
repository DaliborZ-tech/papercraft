"""Read and certify the actually serialized staged PDF manufacturing regions.

The own-writer contract uses marked parts/roles and absolute m/l/c/h paths.
Coordinates are exact Fractions of supported PDF decimal operands after the
actual serialized CTM, converted to physical top-left page millimetres. Source
curves, expected geometry helpers and pre-serialization controls are not used.
"""

from __future__ import annotations

import copy
import hashlib
import math
from dataclasses import asdict, is_dataclass
from fractions import Fraction
from itertools import combinations
from pathlib import Path

_MM_PER_PT = Fraction(127, 360)
_IDENTITY = (Fraction(1), Fraction(0), Fraction(0), Fraction(1), Fraction(0), Fraction(0))
_ROLES = {"CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "LABELS", "ARTWORK", "GUIDES"}
_STYLE_OPS = {b"w", b"J", b"j", b"M", b"d", b"RG", b"rg", b"G", b"g", b"K", b"k"}
_PATH_OPS = {b"m", b"l", b"c", b"h", b"re", b"v", b"y"}
_PAINT_OPS = {b"S", b"s", b"n", b"f", b"f*", b"F", b"B", b"B*", b"b", b"b*"}


class CurveOutputError(ValueError):
    """Actual output could not be proved safe; publication must stay atomic."""

    def __init__(self, reason, *, part_id=None, page_index=None, part_name=None, report=None):
        self.reason, self.part_id, self.page_index = reason, part_id, page_index
        self.part_name, self.report = part_name, report
        label = part_name or ("Díl " + str(part_id) if part_id else "Vektorový výstup")
        page = f", stránka {page_index + 1}" if page_index is not None else ""
        super().__init__(f"{label}{page}: {reason}")


def _number(value):
    try:
        result = Fraction(str(value))
        if isinstance(value, float) and (
            not math.isfinite(value) or float(str(value)) != float(value)
        ):
            raise ValueError("PDF number lost precision during operand decoding")
        return result
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise CurveOutputError("Číselnou přesnost skutečného PDF nelze bezpečně přečíst.") from exc


def _matrix_product(current, supplied):
    a, b, c, d, e, f = current
    u, v, w, x, y, z = supplied
    return (a*u+c*v, b*u+d*v, a*w+c*x, b*w+d*x, a*y+c*z+e, b*y+d*z+f)


def _context(marked):
    part = next((value for kind, value in reversed(marked) if kind == "part"), None)
    role = next((value for kind, value in reversed(marked) if kind == "role"), None)
    return part, role


def _page_geometry(page, page_index):
    if _number(page.get("/Rotate", 0)) % 360 or _number(page.get("/UserUnit", 1)) != 1:
        raise CurveOutputError("PDF používá nepodporované otočení nebo jednotku stránky.",
                               page_index=page_index)
    media = tuple(_number(value) for value in page.mediabox)
    left, bottom, right, top = media
    if right <= left or top <= bottom:
        raise CurveOutputError("PDF nemá platný fyzický rozměr stránky.", page_index=page_index)
    if "/CropBox" in page and tuple(_number(v) for v in page["/CropBox"]) != media:
        raise CurveOutputError("PDF obsahuje neočekávané oříznutí stránky.", page_index=page_index)
    resources = page.get("/Resources", {})
    if hasattr(resources, "get_object"):
        resources = resources.get_object()
    if resources and resources.get("/XObject"):
        raise CurveOutputError("PDF obsahuje neočekávaný obrazový nebo formulářový objekt.",
                               page_index=page_index)
    return left, bottom, right, top


def read_pdf_cut_regions(path):
    """Return actual marked CUT loops, with exact rational page-mm coordinates.

    This parser intentionally supports the own-writer format, not arbitrary PDF
    drawing programs. Unsupported CUT operators, clipping and unclosed paths
    block validation instead of disappearing from manufacturing coverage.
    """
    try:
        from pypdf import PdfReader
        from pypdf.generic import ContentStream
    except ImportError as exc:
        raise CurveOutputError("Není dostupné čtení a ověření skutečného PDF.") from exc
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise CurveOutputError("Zašifrované PDF nelze ověřit jako výrobní výstup.")
        result = {"pages": [], "parts": {},
                  "coordinate_system": "PHYSICAL_PAGE_TOP_LEFT_MM",
                  "arithmetic": "EXACT_FRACTIONS_OF_SUPPORTED_SERIALIZED_PDF_DECIMALS"}
        for page_index, page in enumerate(reader.pages):
            left, bottom, right, top = _page_geometry(page, page_index)
            result["pages"].append({"page_index": page_index,
                                    "width_mm": (right-left)*_MM_PER_PT,
                                    "height_mm": (top-bottom)*_MM_PER_PT})
            matrix, graphics, marked = _IDENTITY, [], []
            loops, owner = [], None
            outside_path = False

            def fail(message):
                identity = _context(marked)[0] or (owner[0] if owner else None)
                raise CurveOutputError(message, part_id=identity, page_index=page_index)

            def point(values):
                if len(values) != 2:
                    fail("PDF souřadnice nemá úplnou dvojici čísel.")
                x, y = (_number(v) for v in values)
                a, b, c, d, e, f = matrix
                return [(a*x+c*y+e-left)*_MM_PER_PT, (top-b*x-d*y-f)*_MM_PER_PT]

            content = page.get_contents()
            operations = [] if content is None else ContentStream(content, reader).operations
            for operands, op in operations:
                part_id, role = _context(marked)
                cut = part_id is not None and role == "CUT"
                if op in (b"W", b"W*", b"Do", b"BI", b"ID", b"EI", b"INLINE IMAGE"):
                    fail("PDF obsahuje neočekávaný ořez nebo rastrový/formulářový výstup.")
                if op in (b"BDC", b"gs") or (op == b"Tr" and operands and operands[0] != 0):
                    fail("PDF obsahuje nepodporované značení nebo grafický stav.")
                if op == b"q":
                    if operands:
                        fail("Neplatný zásobník transformačních stavů PDF.")
                    graphics.append(matrix)
                    continue
                if op == b"Q":
                    if operands or not graphics:
                        fail("Transformační zásobník PDF není vyvážený.")
                    matrix = graphics.pop()
                    continue
                if op == b"cm":
                    if len(operands) != 6:
                        fail("PDF transformace nemá šest souřadnic.")
                    supplied = tuple(_number(value) for value in operands)
                    if supplied[0]*supplied[3] - supplied[1]*supplied[2] == 0:
                        fail("PDF transformace zplošťuje nebo ruší výrobní plochu.")
                    matrix = _matrix_product(matrix, supplied)
                    continue
                if op == b"BMC":
                    if len(operands) != 1:
                        fail("PDF značení dílu nebo role je neúplné.")
                    tag = str(operands[0])
                    if not tag.startswith("/"):
                        fail("PDF značení dílu nebo role není pojmenovaný identifikátor.")
                    if tag.startswith("/APPart_"):
                        identity = tag[len("/APPart_"):]
                        if not identity or part_id is not None or identity in result["parts"]:
                            fail("PDF opakuje nebo vnořuje značení papírového dílu.")
                        result["parts"][identity] = {"page_index": page_index, "loops": []}
                        entry = ("part", identity)
                    elif tag.startswith("/APRole_"):
                        value = tag[len("/APRole_"):]
                        if value not in _ROLES or part_id is None or role is not None:
                            fail("PDF má neplatnou nebo vnořenou výrobní roli.")
                        entry = ("role", value)
                    else:
                        entry = ("other", tag)
                    marked.append(entry)
                    if loops and _context(marked) != owner:
                        fail("PDF změnilo díl nebo roli před dokončením řezu.")
                    continue
                if op == b"EMC":
                    if operands or not marked:
                        fail("PDF značení dílů a rolí není vyvážené.")
                    marked.pop()
                    if loops and _context(marked) != owner:
                        fail("PDF ukončilo značení před vykreslením úplného řezu.")
                    continue
                if not cut:
                    if op in _PATH_OPS:
                        outside_path = True
                    elif op in _PAINT_OPS:
                        outside_path = False
                    continue
                if op in _STYLE_OPS:
                    if op == b"d" and operands and operands[0]:
                        fail("Výrobní řez PDF je nečekaně přerušovaný.")
                    continue
                if op == b"n":
                    if loops:
                        fail("PDF zahodilo rozpracovaný výrobní obrys bez vykreslení.")
                    outside_path = False
                    continue
                if op == b"m":
                    if outside_path:
                        fail("PDF směšuje neoznačenou cestu s výrobním řezem.")
                    owner = (part_id, role)
                    loops.append([["M", *point(operands)]])
                elif op in (b"l", b"c", b"h"):
                    if not loops or loops[-1][-1][0] == "Z":
                        fail("PDF řez nemá odpovídající otevřený počáteční bod.")
                    if op == b"l":
                        loops[-1].append(["L", *point(operands)])
                    elif op == b"c":
                        if len(operands) != 6:
                            fail("PDF kubická křivka nemá úplné řídicí body.")
                        loops[-1].append(["C", *(v for i in (0, 2, 4)
                                                  for v in point(operands[i:i+2]))])
                    else:
                        if operands:
                            fail("PDF uzávěr křivky má nečekané parametry.")
                        loops[-1].append(["Z"])
                elif op in (b"S", b"s"):
                    if operands or not loops:
                        fail("PDF výrobní řez nemá žádný úplný obrys.")
                    if op == b"s" and loops[-1][-1][0] != "Z":
                        loops[-1].append(["Z"])
                    if any(loop[-1][0] != "Z" for loop in loops):
                        fail("PDF výrobní řez obsahuje neuzavřený obrys.")
                    if any(len(loop) < 3 for loop in loops):
                        fail("PDF výrobní obrys nemá úplnou nenulovou hranici.")
                    result["parts"][part_id]["loops"].extend(loops)
                    loops, owner = [], None
                else:
                    fail("PDF výrobní řez používá nepodporovaný příkaz "
                         + op.decode("ascii", errors="replace") + ".")
            if graphics or marked or loops:
                fail("PDF neukončilo transformační stav, značení nebo úplný výrobní řez.")
        return result
    except CurveOutputError:
        raise
    except Exception as exc:
        raise CurveOutputError(
            "Skutečný výrobní obsah PDF nelze úplně přečíst: " + str(exc)
        ) from exc


def _json_value(value):
    if isinstance(value, Fraction):
        return str(value)
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


def _certificate(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict) and "status" in value:
        return value
    raise CurveOutputError("Ověření skutečného PDF nevrátilo rozpoznaný geometrický důkaz.")


def _command_points(loop):
    points = []
    for command in loop:
        if not isinstance(command, (list, tuple)) or not command:
            continue
        if command[0] in ("M", "L") and len(command) == 3:
            points.append(tuple(command[1:]))
        elif command[0] == "C" and len(command) == 7:
            points.extend(tuple(command[i:i+2]) for i in (1, 3, 5))
        elif command[0] == "A" and len(command) == 8:
            points.append(tuple(command[-2:]))
    return points


def _extent_order(loop):
    points = _command_points(loop)
    if not points:
        return Fraction(-1)
    return ((max(p[0] for p in points)-min(p[0] for p in points))
            * (max(p[1] for p in points)-min(p[1] for p in points)))


def _split_cubic(points):
    levels = [tuple(points)]
    while len(levels[-1]) > 1:
        levels.append(tuple(tuple((x+y)/2 for x, y in zip(a, b))
                            for a, b in zip(levels[-1], levels[-1][1:])))
    return tuple(level[0] for level in levels), tuple(level[-1] for level in reversed(levels))


def _inside_page(loops, width, height, max_depth=24, max_nodes=20000):
    """Exact control-hull proof, refining only hulls crossing a physical edge."""
    used = 0

    def inside(point):
        return 0 <= point[0] <= width and 0 <= point[1] <= height

    for loop in loops:
        current = start = None
        for command in loop:
            op = command[0]
            if op == "M":
                current = start = tuple(command[1:3])
                if not inside(current):
                    return {"status": "OUTSIDE", "point": current, "examined_nodes": used}
            elif op == "L" or op == "Z":
                current = start if op == "Z" else tuple(command[1:3])
                if not inside(current):
                    return {"status": "OUTSIDE", "point": current, "examined_nodes": used}
            else:
                if op != "C":
                    return {"status": "UNRESOLVED", "reason": "UNSUPPORTED_PAGE_BOUND_COMMAND",
                            "examined_nodes": used}
                controls = (current, *(tuple(command[i:i+2]) for i in (1, 3, 5)))
                pending = [(controls, 0)]
                while pending:
                    points, depth = pending.pop()
                    used += 1
                    if used > max_nodes:
                        return {"status": "UNRESOLVED", "examined_nodes": used}
                    if not inside(points[0]) or not inside(points[-1]):
                        return {"status": "OUTSIDE", "point": points[0]
                                if not inside(points[0]) else points[-1], "examined_nodes": used}
                    if all(inside(p) for p in points):
                        continue
                    if depth >= max_depth:
                        return {"status": "UNRESOLVED", "examined_nodes": used}
                    left, right = _split_cubic(points)
                    pending.extend(((right, depth+1), (left, depth+1)))
                current = tuple(command[-2:])
    return {"status": "INSIDE", "proof": "EXACT_RATIONAL_CUBIC_CONTROL_HULL_SUBDIVISION",
            "examined_nodes": used}


def validate_native_output_regions(actual, expected_parts, allowed_overlap_pairs=(), *, report,
                                   check_separation=True, check_page_bounds=True):
    """Prove exactly supplied serialized manufacturing regions in a named scope.

    PDF supplies actual physical page coordinates and requests all checks. An SVG
    reader may supply exact part-local paths with both optional checks disabled;
    the report then explicitly makes no physical-page or part-separation claim.
    Empty manufacturing coverage is not a successful geometric proof.
    """
    if not isinstance(report, dict):
        raise CurveOutputError("Výstupní geometrické ověření potřebuje jednoznačný záznam rozsahu.")
    report = copy.deepcopy(report)
    report.update(status="UNRESOLVED", parts={}, separations=[], new_user_test="NOT_RUN",
                  physical_build="NOT_VERIFIED")
    report["proof_scope"] = {
        "within_part_topology": "EXACT_SUPPLIED_NATIVE_COMMANDS",
        "physical_page_bounds": ("REQUESTED" if check_page_bounds
                                 else "NOT_CHECKED_LOCAL_COORDINATES"),
        "same_page_part_separation": ("REQUESTED" if check_separation
                                      else "NOT_CHECKED_LOCAL_COORDINATES"),
    }

    def fail(reason, pid=None, page_index=None):
        record = expected_parts.get(pid, {}) if isinstance(expected_parts, dict) else {}
        name = record.get("name") if isinstance(record, dict) else None
        raise CurveOutputError(reason, part_id=pid, page_index=page_index,
                               part_name=name, report=_json_value(report))

    if not isinstance(expected_parts, dict) or not expected_parts or any(
        not isinstance(pid, str) or not pid or not isinstance(value, dict)
        or type(value.get("page_index")) is not int or value["page_index"] < 0
        or type(value.get("loop_count")) is not int or value["loop_count"] < 1
        for pid, value in expected_parts.items()
    ):
        fail("Očekávané výrobní pokrytí nemá úplné díly, stránky a počty obrysů.")
    if (not isinstance(actual, dict) or not isinstance(actual.get("parts"), dict)
            or not isinstance(actual.get("pages"), list)):
        fail("Skutečný vektorový výstup nemá úplný přehled dílů a stránek.")
    if set(actual["parts"]) != set(expected_parts):
        missing = set(expected_parts) - set(actual["parts"])
        identity = next(iter(sorted(missing or (set(actual["parts"]) - set(expected_parts)))))
        fail("Vektorový výstup nepokrývá přesně všechny očekávané papírové díly.", identity)
    pages = {page.get("page_index"): page for page in actual["pages"] if isinstance(page, dict)}
    if len(pages) != len(actual["pages"]):
        fail("Vektorový výstup opakuje nebo neidentifikuje všechny stránky.")
    report["pages"] = actual["pages"]
    report["arithmetic"] = actual.get("arithmetic", "EXACT_SUPPLIED_NATIVE_COMMANDS")
    for pid, expected in expected_parts.items():
        part = actual["parts"][pid]
        if (not isinstance(part, dict) or type(part.get("page_index")) is not int
                or not isinstance(part.get("loops"), (list, tuple))
                or part["page_index"] not in pages):
            fail("Vektorový výstup nemá úplnou identitu stránky a obrysů dílu.", pid)
        if (part["page_index"] != expected["page_index"]
                or len(part["loops"]) != expected["loop_count"]):
            fail("Vektorový výstup změnil stránku nebo počet řezných obrysů včetně otvorů.",
                 pid, part["page_index"])
    try:
        from archpapercraft.authoring.curve_topology import (
            certify_native_region_separation,
            certify_native_region_topology,
        )
    except ImportError as exc:
        raise CurveOutputError(
            "Není dostupný úplný geometrický důkaz skutečných výstupních křivek.",
            report=_json_value(report),
        ) from exc
    regions = {}
    for pid, expected in expected_parts.items():
        part = actual["parts"][pid]
        page_index, loops = part["page_index"], part["loops"]
        if page_index != expected["page_index"] or len(loops) != expected["loop_count"]:
            fail("Vektorový výstup změnil stránku nebo počet řezných obrysů včetně otvorů.",
                 pid, page_index)
        candidates, chosen = [], None
        for index in sorted(range(len(loops)), key=lambda i: _extent_order(loops[i]), reverse=True):
            holes = [loop for i, loop in enumerate(loops) if i != index]
            certificate = _certificate(certify_native_region_topology(loops[index], holes))
            candidates.append({"outer_index": index, "certificate": certificate})
            if certificate["status"] == "VALID":
                chosen = (loops[index], holes)
                break
        report["parts"][pid] = {"name": expected.get("name"), "page_index": page_index,
                                 "loop_count": len(loops), "topology_candidates": candidates}
        if chosen is None:
            fail("Topologii skutečných výstupních řezů a otvorů nelze doložit. "
                 "Upravte dotýkající se nebo křížící se obrysy.", pid, page_index)
        page = pages[page_index]
        page_proof = (_inside_page(loops, page["width_mm"], page["height_mm"])
                      if check_page_bounds else
                      {"status": "NOT_CHECKED", "scope": "LOCAL_COORDINATES_ONLY"})
        report["parts"][pid]["page_bounds"] = page_proof
        if check_page_bounds and page_proof["status"] != "INSIDE":
            fail("Skutečný výstupní díl přesahuje fyzickou stránku nebo jeho umístění "
                 "nelze bezpečně doložit.", pid, page_index)
        regions[pid] = chosen
    allowed = set()
    for pair in allowed_overlap_pairs:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2 or pair[0] == pair[1]
                or any(not isinstance(pid, str) or pid not in expected_parts for pid in pair)):
            fail("Přijatý překryv neodkazuje na konkrétní dva existující díly.")
        allowed.add(tuple(sorted(pair)))
    for first, second in combinations(sorted(regions), 2):
        if not check_separation:
            continue
        page_index = expected_parts[first]["page_index"]
        if page_index != expected_parts[second]["page_index"]:
            continue
        record = {"first_part_id": first, "second_part_id": second, "page_index": page_index}
        if (first, second) in allowed:
            record["status"] = "EXPLICIT_SOURCE_LAYOUT_OVERLAP_ACCEPTED"
        else:
            a, b = regions[first], regions[second]
            certificate = _certificate(certify_native_region_separation(a[0], a[1], b[0], b[1]))
            record.update(status=certificate["status"], certificate=certificate)
        report["separations"].append(record)
        if record["status"] not in ("DISJOINT", "EXPLICIT_SOURCE_LAYOUT_OVERLAP_ACCEPTED"):
            other = expected_parts[second].get("name") or "druhého dílu"
            fail("Skutečné výstupní řezy se překrývají, dotýkají nebo jejich oddělení od "
                 + other + " nelze doložit. Zvětšete mezeru nebo upravte obrys.", first, page_index)
    report["status"] = "VALID"
    if check_page_bounds:
        report["proof_scope"]["physical_page_bounds"] = "CERTIFIED_ACTUAL_COMMANDS"
    if check_separation:
        report["proof_scope"]["same_page_part_separation"] = "CERTIFIED_OR_EXPLICIT_SOURCE_ACK"
    return _json_value(report)


def validate_pdf_curve_geometry(path, expected_parts, allowed_overlap_pairs=()):
    """Certify the actual staged PDF; unsupported/inconclusive output blocks."""
    try:
        pdf_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise CurveOutputError("Připravené PDF nelze přečíst pro výrobní kontrolu.") from exc
    report = {"status": "UNRESOLVED", "kind": "ACTUAL_STAGED_PDF_CURVE_GEOMETRY",
              "pdf_sha256": pdf_hash}
    try:
        actual = read_pdf_cut_regions(path)
    except CurveOutputError as exc:
        record = expected_parts.get(exc.part_id, {}) if isinstance(expected_parts, dict) else {}
        name = record.get("name") if isinstance(record, dict) else None
        raise CurveOutputError(exc.reason, part_id=exc.part_id, page_index=exc.page_index,
                               part_name=name, report=report) from exc
    return validate_native_output_regions(actual, expected_parts, allowed_overlap_pairs,
                                          report=report)
