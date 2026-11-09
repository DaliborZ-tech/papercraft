"""Deterministic SVG/PDF publication for a validated authoring snapshot.

All input geometry and placements are paper millimetres in a top-left, Y-down
coordinate system. The caller owns surface coverage and author acknowledgements;
this writer also refuses stale/error metadata, duplicate part placements, invalid
numbers and clipping outside the physical page in a complete export.

``export_all(snapshot, directory, font_path=None)`` returns one SVG per page and
``model.pdf``. ``.author-export.json`` records this bundle's digest and owned files.
The input mapping is copied before use. Files are staged before publication, old
owned outputs are backed up, and a failed publication rolls back the whole set.
If the filesystem also refuses rollback, ExportWriteError.recovery_directory
points to the retained byte-for-byte backups; success is never reported.

CUT owns manufacturing strokes. TABS paths are fill-only, so tab bases/cuts must
be represented exactly once in CUT/FOLD by the snapshot builder. This module
imports no Qt or application/UI state and never changes placements or packing.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import threading
import xml.etree.ElementTree as ET
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from reportlab.pdfbase import pdfdoc, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.pdfgen.canvas import Canvas

from archpapercraft.precision import (
    AREA_ABSOLUTE_BUDGET_MM2,
    AREA_RELATIVE_BUDGET,
    PDF_ARC_TOLERANCE_MM,
    PDF_DIGITAL_BUDGET_MM,
)

from .curve_output_validation import CurveOutputError

ROLES = ("CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "LABELS", "ARTWORK", "GUIDES")
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_LOCK = threading.RLock()
_MANIFEST = ".author-export.json"
_INSTRUCTION = "Tisk 100 % / skutečná velikost. Kalibrace 100 mm na papíře."


class SnapshotError(ValueError):
    """The export input is invalid or cannot represent a complete printable bundle."""


class FontError(RuntimeError):
    """No embeddable font with every required character is available."""


class ExportWriteError(OSError):
    """Staging/publication failed; recovery_directory is set if rollback also failed."""

    def __init__(self, message: str, recovery_directory: Path | None = None):
        super().__init__(message)
        self.recovery_directory = recovery_directory


def _number(value: Any, context: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotError(f"{context}: expected a finite number")
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        raise SnapshotError(f"{context}: expected {'positive ' if positive else ''}finite number")
    return value


def _identity(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value) or value in (".", ".."):
        raise SnapshotError(f"{context}: invalid stable identifier")
    return value


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or any(
        not (
            char in "\t\n\r"
            or 0x20 <= ord(char) <= 0xD7FF
            or 0xE000 <= ord(char) <= 0xFFFD
            or 0x10000 <= ord(char) <= 0x10FFFF
        )
        for char in value
    ):
        raise SnapshotError(f"{context}: expected XML-compatible text")
    return value


def _source_identity(value: Any, context: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
        raise SnapshotError(f"{context}: invalid source identifier")
    return value


def _detached(snapshot: dict) -> dict:
    try:
        return json.loads(json.dumps(snapshot, allow_nan=False, ensure_ascii=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise SnapshotError(f"Snapshot must contain finite JSON data: {exc}") from exc


def canonical_digest(snapshot: dict) -> str:
    """Hash semantic snapshot content; only explicit top-level metadata is excluded."""
    data = _detached(snapshot)
    if not isinstance(data, dict):
        raise SnapshotError("Snapshot must be an object")
    data.pop("metadata", None)
    encoded = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    try:
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    except UnicodeError as exc:
        raise SnapshotError("Snapshot contains invalid Unicode") from exc


def _rotation(placement: dict) -> float:
    return math.remainder(placement.get("rotation_deg", 0), 360.0)


def _world(point: list, placement: dict) -> tuple[float, float]:
    angle = math.radians(_rotation(placement))
    c, s = math.cos(angle), math.sin(angle)
    return (
        placement["x_mm"] + c * point[0] - s * point[1],
        placement["y_mm"] + s * point[0] + c * point[1],
    )


def _commands(path: dict) -> list[list]:
    """Normalize native paths without sampling their construction curves."""
    if not isinstance(path, dict) or not isinstance(path.get("closed"), bool):
        raise SnapshotError("Path requires an explicit boolean closed flag")
    if path.get("fill_rule", "evenodd") not in ("evenodd", "nonzero"):
        raise SnapshotError("Unsupported path fill rule")
    if ("points" in path) == ("commands" in path):
        raise SnapshotError("Path requires exactly one of points or commands")
    if "points" in path:
        points = path["points"]
        if not isinstance(points, list) or len(points) < (3 if path["closed"] else 2):
            raise SnapshotError("Path has insufficient points")
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise SnapshotError("A point must contain x and y")
            for value in point:
                _number(value, "path coordinate")
        commands = [["M", *points[0]], *[["L", *point] for point in points[1:]]]
        if path["closed"]:
            commands.append(["Z"])
    else:
        commands = path["commands"]
        if not isinstance(commands, list) or not commands:
            raise SnapshotError("Native path commands must be a nonempty array")
    counts = {"M": 3, "L": 3, "C": 7, "A": 8, "Z": 1}
    current, start, drawn = None, None, False
    for command in commands:
        if (
            not isinstance(command, list)
            or not command
            or not isinstance(command[0], str)
            or command[0] not in counts
        ):
            raise SnapshotError("Native paths support absolute M/L/C/A/Z commands only")
        op = command[0]
        if len(command) != counts[op]:
            raise SnapshotError(f"Invalid {op} command arity")
        for number in command[1:]:
            _number(number, f"{op} coordinate")
        if op == "M":
            current, start = command[1:3], command[1:3]
        elif current is None:
            raise SnapshotError("A drawing command requires an initial M")
        elif op == "Z":
            drawn |= current != start
            current = start
        else:
            if op == "A":
                if command[1] <= 0 or command[2] <= 0:
                    raise SnapshotError("Native arc radii must be positive")
                if command[4] not in (0, 1) or command[5] not in (0, 1):
                    raise SnapshotError("Arc flags must be zero or one")
                if current == command[-2:]:
                    raise SnapshotError("A full circle needs two explicit arc segments")
            drawn |= (
                any(command[i : i + 2] != current for i in (1, 3, 5))
                if op == "C"
                else current != command[-2:]
            )
            current = command[-2:]
    if commands[0][0] != "M" or not drawn:
        raise SnapshotError("Degenerate path without drawing geometry")
    if path["closed"] and commands[-1][0] != "Z":
        commands = [*commands, ["Z"]]
    return commands


def _arc(start: list, command: list) -> tuple:
    """SVG endpoint to center conversion, W3C SVG implementation notes B.2.4."""
    rx, ry, degrees, large, sweep, x2, y2 = command[1:]
    phi = math.radians(degrees % 360)
    c, s = math.cos(phi), math.sin(phi)
    x1, y1 = start
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x, y = c * dx + s * dy, -s * dx + c * dy
    norm = math.hypot(x / rx, y / ry)
    if norm > 1:
        rx, ry = rx * norm, ry * norm
    nx, ny = x / rx, y / ry
    denominator = nx * nx + ny * ny
    if denominator == 0:
        raise SnapshotError("Arc endpoints cannot be resolved at this precision")
    factor = math.sqrt(max(0, (1 - denominator) / denominator))
    if large == sweep:
        factor = -factor
    cxp, cyp = factor * rx * ny, -factor * ry * nx
    cx, cy = c * cxp - s * cyp + (x1 + x2) / 2, s * cxp + c * cyp + (y1 + y2) / 2
    theta = math.atan2((y - cyp) / ry, (x - cxp) / rx)
    end = math.atan2((-y - cyp) / ry, (-x - cxp) / rx)
    delta = (end - theta) % math.tau if sweep else -((theta - end) % math.tau)
    if not all(math.isfinite(v) for v in (rx, ry, cx, cy, theta, delta)):
        raise SnapshotError("Arc geometry overflowed")
    return cx, cy, rx, ry, phi, theta, delta


def _arc_point(arc: tuple, theta: float) -> tuple[float, float]:
    cx, cy, rx, ry, phi, _, _ = arc
    c, s = math.cos(phi), math.sin(phi)
    return cx + rx * math.cos(theta) * c - ry * math.sin(theta) * s, cy + rx * math.cos(
        theta
    ) * s + ry * math.sin(theta) * c


def _arc_tangent(arc: tuple, theta: float) -> tuple[float, float]:
    _, _, rx, ry, phi, _, _ = arc
    c, s = math.cos(phi), math.sin(phi)
    return -rx * math.sin(theta) * c - ry * math.cos(theta) * s, -rx * math.sin(
        theta
    ) * s + ry * math.cos(theta) * c


def _arc_cubics(arc: tuple, *, tolerance_mm=None) -> tuple[list[tuple], float]:
    """Cubic Hermite interpolation with a global, nonsampled position bound.

    Each coordinate's Hermite remainder is M4*h**4/384. The norm of the two
    coordinate bounds is <= hypot(rx,ry)*h**4/384, invariant under rotation.
    This is conservative compared with the usual circle-specific cubic fit.
    """
    _, _, rx, ry, _, theta, delta = arc
    radius = math.hypot(rx, ry)
    tolerance_mm = PDF_ARC_TOLERANCE_MM if tolerance_mm is None else tolerance_mm
    tolerance_mm = _number(tolerance_mm, "Arc representation budget", positive=True)
    max_step = min(math.pi / 2, (384 * tolerance_mm / radius) ** 0.25)
    count = max(1, math.ceil(abs(delta) / max_step))
    if count > 100000:
        raise SnapshotError("Arc needs more cubic segments than the supported export limit")
    step = delta / count
    curves = []
    for index in range(count):
        a, b = theta + index * step, theta + (index + 1) * step
        p, q = _arc_point(arc, a), _arc_point(arc, b)
        t, u = _arc_tangent(arc, a), _arc_tangent(arc, b)
        curves.append(
            (
                p[0] + step * t[0] / 3,
                p[1] + step * t[1] / 3,
                q[0] - step * u[0] / 3,
                q[1] - step * u[1] / 3,
                *q,
            )
        )
    return curves, radius * abs(step) ** 4 / 384


def _cubic_point(points: list, t: float) -> tuple:
    return tuple(
        sum((1 - t) ** (3 - i) * t**i * (1, 3, 3, 1)[i] * p[axis] for i, p in enumerate(points))
        for axis in (0, 1)
    )


def _quadratic_roots(a: float, b: float, c: float) -> list[float]:
    scale = max(abs(a), abs(b), abs(c))
    if scale == 0:
        return []
    a, b, c = a / scale, b / scale, c / scale
    if a == 0:
        return [-c / b] if b else []
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return []
    q = -0.5 * (b + math.copysign(math.sqrt(discriminant), b))
    return [q / a, c / q] if q else [-b / (2 * a)]


def _bounds(path: dict, place: dict) -> tuple:
    """Analytic extrema after placement; endpoints alone do not bound a curve."""
    points, current, start = [], None, None
    for command in _commands(path):
        op = command[0]
        if op == "M":
            current = start = command[1:3]
            points.append(_world(current, place))
        elif op in ("L", "Z"):
            current = start if op == "Z" else command[1:3]
            points.append(_world(current, place))
        elif op == "C":
            controls = [
                _world(p, place) for p in (current, command[1:3], command[3:5], command[5:7])
            ]
            candidates = [0.0, 1.0]
            for axis in (0, 1):
                p, q, r, s = [v[axis] for v in controls]
                candidates += [
                    t
                    for t in _quadratic_roots(
                        3 * (-p + 3 * q - 3 * r + s), 6 * (p - 2 * q + r), 3 * (q - p)
                    )
                    if 0 < t < 1
                ]
            points.extend(_cubic_point(controls, t) for t in candidates)
            current = command[5:7]
        elif op == "A":
            arc = _arc(current, command)
            _, _, rx, ry, phi, theta, delta = arc
            angle = phi + math.radians(_rotation(place))
            candidates = [theta, theta + delta]
            for a, b in (
                (rx * math.cos(angle), -ry * math.sin(angle)),
                (rx * math.sin(angle), ry * math.cos(angle)),
            ):
                peak = math.atan2(b, a)
                for value in (peak, peak + math.pi):
                    distance = (
                        (value - theta) % math.tau if delta >= 0 else (theta - value) % math.tau
                    )
                    if distance <= abs(delta) + 1e-12:
                        candidates.append(value)
            points.extend(_world(_arc_point(arc, t), place) for t in candidates)
            current = command[-2:]
    if not all(math.isfinite(value) for point in points for value in point):
        raise SnapshotError("Path world coordinates overflowed")
    return (
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    )


def _validate(data: dict) -> None:
    if not isinstance(data, dict):
        raise SnapshotError("Snapshot must be an object")
    _identity(data.get("project_id"), "project_id")
    _number(data.get("revision"), "revision")
    if not isinstance(data["revision"], int) or data["revision"] < 0:
        raise SnapshotError("revision must be a non-negative integer")
    if "construction_checks" in data:
        checks = data["construction_checks"]
        if not isinstance(checks, dict) or not isinstance(checks.get("connector_bends"), dict):
            raise SnapshotError("Construction checks must contain an explicit connector registry")
        for report in checks["connector_bends"].values():
            if not isinstance(report, dict) or report.get("status") not in (
                "CLEAR", "UNVERIFIED", "NOT_APPLICABLE"
            ):
                raise SnapshotError("Snapshot contains blocked or unresolved construction checks")
            tabs = report.get("tabs", [])
            if not isinstance(tabs, list) or any(
                not isinstance(tab, dict) or tab.get("status") not in ("CLEAR", "UNVERIFIED")
                for tab in tabs
            ):
                raise SnapshotError("Snapshot contains a blocked tab motion")
        curves = checks.get("curve_profiles", {})
        regions = checks.get("curve_regions", {})
        if not isinstance(regions, dict) or any(
            not isinstance(report, dict) or report.get("status") != "VALID"
            for report in regions.values()
        ):
            raise SnapshotError("Snapshot has unresolved native-curve material topology")
        if not isinstance(curves, dict):
            raise SnapshotError("Source curve checks must be an explicit registry")
        for report in curves.values():
            if not isinstance(report, dict) or report.get("status") != "CERTIFIED":
                raise SnapshotError("Snapshot contains an uncertified source curve")
            budget = _number(report.get("representation_budget_paper_mm"),
                             "Curve representation budget", positive=True)
            if budget > PDF_DIGITAL_BUDGET_MM:
                raise SnapshotError("Curve representation budget exceeds the digital limit")
            for key in ("chord_deviation_bound_paper_mm", "svg_deviation_bound_paper_mm",
                        "svg_length_error_bound_paper_mm"):
                bound = _number(report.get(key), key)
                if not 0 <= bound <= budget:
                    raise SnapshotError("A source curve bound exceeds its declared budget")
            lower = _number(report.get("length_lower_paper_mm"), "Curve length lower bound")
            upper = _number(report.get("length_upper_paper_mm"), "Curve length upper bound")
            if lower < 0 or not lower <= upper <= lower + budget:
                raise SnapshotError("Source curve length bounds exceed their budget")
    if "partial" in data and not isinstance(data["partial"], bool):
        raise SnapshotError("partial must be an explicit boolean")
    if (
        data.get("valid") is False
        or data.get("stale")
        or data.get("integrity_errors")
        or data.get("source_revisions_valid") is False
    ):
        raise SnapshotError("Snapshot has stale geometry or integrity errors")
    if str(data.get("status", "current")).lower() in {"stale", "invalid", "error"}:
        raise SnapshotError("Snapshot is not current")
    if str(data.get("geometry_status", "current")).lower() in {
        "stale",
        "invalid",
        "error",
        "pending",
    }:
        raise SnapshotError("Snapshot geometry is not current")
    for issue in data.get("issues", []):
        if not isinstance(issue, dict):
            raise SnapshotError("issues must contain objects")
        if str(issue.get("severity", "")).upper() in {"ERROR", "BLOCKER", "INTEGRITY"}:
            raise SnapshotError("Integrity errors cannot be acknowledged away")
    _text(data.get("scale_label"), "scale_label")
    if "name" in data:
        _text(data["name"], "name")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise SnapshotError("At least one page is required")
    page_ids, part_ids = set(), set()
    for page in pages:
        if not isinstance(page, dict):
            raise SnapshotError("Page must be an object")
        pid = _identity(page.get("id"), "page.id")
        if pid.casefold() in page_ids:
            raise SnapshotError(f"Duplicate page ID {pid}")
        page_ids.add(pid.casefold())
        width = _number(page.get("width_mm"), "page.width_mm", positive=True)
        height = _number(page.get("height_mm"), "page.height_mm", positive=True)
        if width < 120 or height < 35:
            raise SnapshotError(
                "Page is too small for the required 100 mm calibration and print instruction"
            )
        if not isinstance(page.get("parts"), list):
            raise SnapshotError("page.parts must be an array")
        for part in page["parts"]:
            if not isinstance(part, dict):
                raise SnapshotError("Part must be an object")
            part_id = _identity(part.get("id"), "part.id")
            if part_id in part_ids:
                raise SnapshotError(f"Part {part_id} appears more than once")
            part_ids.add(part_id)
            if "name" in part:
                _text(part["name"], "part.name")
            if "source_revision" in part:
                value = part["source_revision"]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise SnapshotError("part.source_revision must be a nonnegative integer")
            if part.get("stale") or str(part.get("status", "current")).lower() in {
                "stale",
                "invalid",
                "error",
            }:
                raise SnapshotError(f"Part {part_id} is not current")
            place = part.get("placement")
            if not isinstance(place, dict):
                raise SnapshotError(f"Part {part_id} has no placement")
            for key in ("x_mm", "y_mm"):
                _number(place.get(key), f"placement.{key}")
            _number(place.get("rotation_deg", 0), "placement.rotation_deg")
            paths = part.get("paths")
            if not isinstance(paths, dict) or any(role not in ROLES for role in paths):
                raise SnapshotError(f"Part {part_id}: invalid path roles")
            if not paths.get("CUT"):
                raise SnapshotError(f"Part {part_id} has no manufacturing cut geometry")
            for role, items in paths.items():
                if not isinstance(items, list):
                    raise SnapshotError(f"{role} must contain an array of paths")
                for path in items:
                    try:
                        left, top, right, bottom = _bounds(path, place)
                    except (ArithmeticError, ValueError) as exc:
                        if isinstance(exc, SnapshotError):
                            raise
                        raise SnapshotError(f"Invalid path geometry: {exc}") from exc
                    if not data.get("partial") and (
                        left < -1e-7
                        or top < -1e-7
                        or right > width + 1e-7
                        or bottom > height + 1e-7
                    ):
                        raise SnapshotError(
                            f"Part {part_id} exceeds the physical page; complete export refused"
                        )
            if not isinstance(part.get("labels", []), list):
                raise SnapshotError("labels must be an array")
            for label in part.get("labels", []):
                if not isinstance(label, dict) or not isinstance(label.get("text"), str):
                    raise SnapshotError("Label must contain editable text")
                _text(label["text"], "label.text")
                for key in ("x", "y"):
                    _number(label.get(key), f"label.{key}")
                _number(label.get("size_mm", 2.5), "label.size_mm", positive=True)
    if not part_ids:
        raise SnapshotError("At least one placed part is required")
    if "coverage" in data:
        coverage = data["coverage"]
        if not isinstance(coverage, dict):
            raise SnapshotError("coverage must be an object")
        expected = coverage.get("expected_part_ids")
        surfaces = coverage.get("expected_surface_ids")
        for name, values in (("expected_part_ids", expected), ("expected_surface_ids", surfaces)):
            if not isinstance(values, list) or not values:
                raise SnapshotError(f"coverage.{name} must be a nonempty array")
            for value in values:
                (_identity if name == "expected_part_ids" else _source_identity)(
                    value, f"coverage.{name}"
                )
            if len(set(values)) != len(values):
                raise SnapshotError(f"coverage.{name} contains duplicate identities")
        if set(expected) != part_ids:
            raise SnapshotError("Placed parts do not exactly cover the authoritative part registry")
        projected = []
        for page in pages:
            for part in page["parts"]:
                ids = part.get("surface_ids")
                if not isinstance(ids, list) or not ids:
                    raise SnapshotError("Covered parts need their source surface identities")
                if "source_revision" not in part:
                    raise SnapshotError("Covered parts need their source revision")
                for value in ids:
                    _source_identity(value, "part.surface_ids")
                projected.extend(ids)
                if "source_revisions" in coverage:
                    revisions = coverage["source_revisions"]
                    if not isinstance(revisions, dict) or set(revisions) != part_ids:
                        raise SnapshotError("Authoritative source revision registry is incomplete")
                    if revisions[part["id"]] != part.get("source_revision"):
                        raise SnapshotError(
                            "Part source revision differs from its authoritative source"
                        )
        if set(projected) != set(surfaces) or len(projected) != len(surfaces):
            raise SnapshotError(
                "Snapshot does not exactly cover the authoritative material surfaces"
            )
    if (data.get("construction_checks", {}).get("lofts")
            or data.get("coverage", {}).get("expected_loft_surface_ids")):
        from .loft_output_validation import validate_loft_snapshot

        validate_loft_snapshot(data)


def _font(font_path: str | Path | None, texts: list[str]) -> tuple[str, str, str]:
    candidates = (
        [Path(font_path)]
        if font_path is not None
        else [
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arial.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        ]
    )
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FontError("An embeddable Unicode font is required; no available font was found")
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        name = "PanelFont_" + digest[:16]
        font = TTFont(name, str(path))
        os2 = font.face.table.get("OS/2")
        if os2 is None:
            raise FontError("Font embedding permissions cannot be verified (missing OS/2 table)")
        with path.open("rb") as stream:
            stream.seek(os2["offset"] + 8)
            fs_type = int.from_bytes(stream.read(2), "big")
        if fs_type & (0x0002 | 0x0100 | 0x0200):
            raise FontError(
                f"Font license flags prohibit subset embedding (fsType=0x{fs_type:04x})"
            )
        missing = sorted(
            {
                ord(char)
                for text in texts
                for char in text
                if not char.isspace() and ord(char) not in font.face.charWidths
            }
        )
        if missing:
            raise FontError(
                "Font lacks required glyphs: " + ", ".join(f"U+{value:04X}" for value in missing)
            )
        pdfmetrics.registerFont(font)
        family = font.face.familyName
        family = (
            family.decode("utf-8", errors="replace") if isinstance(family, bytes) else str(family)
        )
        return name, family, digest
    except FontError:
        raise
    except (OSError, ValueError, KeyError, RuntimeError, TTFError) as exc:
        raise FontError(f"Cannot load/embed the required font: {exc}") from exc


def _fmt(value: float) -> str:
    return format(0.0 if value == 0 else float(value), ".15g")


def _svg_path(path: dict) -> str:
    return " ".join(
        command[0]
        + (" " + " ".join(_fmt(value) for value in command[1:]) if len(command) > 1 else "")
        for command in _commands(path)
    )


def _curve_bound(data: dict, *, arc_tolerance_mm=None) -> float:
    bound = 0.0
    for page in data["pages"]:
        for part in page["parts"]:
            for paths in part["paths"].values():
                for path in paths:
                    current, start = None, None
                    for command in _commands(path):
                        op = command[0]
                        if op == "M":
                            current = start = command[1:3]
                        elif op == "Z":
                            current = start
                        else:
                            if op == "A":
                                _, error = _arc_cubics(_arc(current, command),
                                                       tolerance_mm=arc_tolerance_mm)
                                bound = max(bound, error)
                            current = command[-2:]
    return bound


def _source_svg_bound(data):
    checks = data.get("construction_checks", {})
    bounds = [report["svg_deviation_bound_paper_mm"]
              for report in checks.get("curve_profiles", {}).values()]
    bounds.extend(report["representation"]["position_error_bound_paper_mm"]
                  for report in checks.get("lofts", {}).values())
    return max(bounds, default=0)


def _curve_output_expectations(data):
    """Expected coverage, not expected coordinates for the serialized proof."""
    return {
        part["id"]: {
            "page_index": page_index, "name": part.get("name", part["id"]),
            "loop_count": sum(command[0] == "M" for path in part["paths"]["CUT"]
                              for command in _commands(path)),
        }
        for page_index, page in enumerate(data["pages"]) for part in page["parts"]
    }


def _validate_vector_area_agreement(checks, expected):
    """Apply the independent normative area tolerance, never a positional tube."""
    sources = {pid: record for page in checks["svg"] for pid, record in page["parts"].items()}
    comparisons = {}
    for pid, target in checks["pdf"]["parts"].items():
        source = sources[pid]
        s = source["material_area_bounds_mm2"]
        p = target["material_area_bounds_mm2"]
        source_low, source_high = Fraction(s["lower"]), Fraction(s["upper"])
        pdf_low, pdf_high = Fraction(p["lower"]), Fraction(p["upper"])
        difference = max(abs(pdf_low-source_high), abs(pdf_high-source_low))
        base_lower = Fraction(source["base_area_lower_bound_mm2"])
        budget = max(Fraction(str(AREA_ABSOLUTE_BUDGET_MM2)),
                     base_lower * Fraction(str(AREA_RELATIVE_BUDGET)))
        comparisons[pid] = {
            "svg_area_bounds_mm2": [str(source_low), str(source_high)],
            "pdf_area_bounds_mm2": [str(pdf_low), str(pdf_high)],
            "absolute_difference_bound_mm2": str(difference),
            "allowed_area_error_mm2": str(budget),
            "base_area_lower_bound_mm2": str(base_lower),
        }
        if difference > budget:
            raise CurveOutputError(
                f"Nelze doložit plošnou shodu SVG a PDF: odchylka má mez "
                f"{float(difference):.6g} mm², povolená mez je {float(budget):.6g} mm². "
                "Přesnost polohy nenahrazuje přesnost plochy. Předchozí výstupy zůstaly zachované.",
                part_id=pid, part_name=expected[pid]["name"],
                page_index=expected[pid]["page_index"],
                report={"status": "REJECTED", "area_comparisons": comparisons},
            )
    return {"status": "VERIFIED", "comparisons": comparisons,
            "acceptance": "04_AREA_max(0.01_mm2,1e-6_BASE_AREA); AC-X04",
            "scope": "ACTUAL_NET_CUT_AREA_AGREEMENT; source flattening verified separately"}


def _serialized_matrix(canvas) -> list[Decimal]:
    """Read the actual CTM token just emitted by this installed ReportLab.

    ReportLab rounds numbers and may combine consecutive transformations. Its
    unrounded _currentMatrix is therefore not an oracle for the written file.
    Fail explicitly if a future backend changes the emitted representation.
    """
    tokens = canvas._code[-1].split()
    if len(tokens) != 7 or tokens[-1] != "cm":
        raise SnapshotError("Cannot verify the PDF backend's serialized transformation")
    return [Decimal(value) for value in tokens[:-1]]


def _precise_transform(canvas, matrix):
    """Emit a local CTM without ReportLab's six-digit rounding/combination.

    The backend still tracks the real matrix. Replacing its just-emitted token
    is safe only immediately after our own q; a changed backend contract fails
    explicitly. Fixed decimal notation is required by PDF (no exponent tokens).
    The independent raw reader and numeric bound inspect these actual lexemes.
    """
    if not canvas._code or canvas._code[-1] != "q":
        raise SnapshotError("A precise local PDF transform needs a fresh saved graphics state")
    canvas.transform(*matrix)
    _serialized_matrix(canvas)  # Verify the installed backend emitted one local cm.
    canvas._code[-1] = " ".join(
        format(float(value), ".17f").rstrip("0").rstrip(".") or "0" for value in matrix
    ) + " cm"


def _serialized_controls(code: str) -> list[tuple[Decimal, Decimal]]:
    points, values = [], []
    for token in code.split():
        if token in ("m", "l", "c"):
            expected = 6 if token == "c" else 2
            if len(values) != expected:
                raise SnapshotError("Cannot verify the PDF backend's path coordinates")
            points.extend((values[index], values[index + 1]) for index in range(0, expected, 2))
            values = []
        elif token in ("n", "h", "S"):
            if values:
                raise SnapshotError("Unexpected PDF path coordinate representation")
        else:
            values.append(Decimal(token))
    if values:
        raise SnapshotError("Incomplete PDF path coordinate representation")
    return points


def _precise_path(path, controls):
    """Preserve native controls beyond ReportLab fp_str's six-digit tokens.

    The installed backend's original code is checked before replacing numeric
    operands only. Commands/order/closure stay unchanged; subsequent numeric
    proof and the independent raw reader inspect these actual serialized bytes.
    """
    code = path.getCode()
    if len(_serialized_controls(code)) != len(controls):
        raise SnapshotError("Cannot bind precise PDF coordinates to the actual backend path")
    operands = iter(value for point in controls for value in point)
    result = []
    for token in code.split():
        if token in ("n", "m", "l", "c", "h", "S"):
            result.append(token)
        else:
            result.append(format(float(next(operands)), ".17f").rstrip("0").rstrip(".") or "0")
    if next(operands, None) is not None or not isinstance(path._code, list):
        raise SnapshotError("Cannot verify the precise PDF path backend contract")
    path._code[:] = [" ".join(result)]


def _numeric_error(serialized, reference, matrices, media_height, placement=None) -> float:
    """Conservative serialized position difference at vertices/control points.

    A line/cubic's difference is a Bernstein polynomial of the differences at
    its controls. Its norm cannot exceed their maximum: this checks the whole
    segment, not samples. Arcs have a separate analytic interpolation bound.
    Decimal arithmetic avoids cancelling the very rounding error under test.
    """
    if len(serialized) != len(reference):
        raise SnapshotError("PDF serialized controls do not cover the requested geometry")
    with localcontext() as context:
        context.prec = 768  # Enough for cancellation across the finite-double input range.
        ratio = Decimal(127) / Decimal(360)  # Exact definition: paper mm per PDF point.
        if placement is not None:
            angle = math.radians(_rotation(placement))
            cosine, sine = Decimal.from_float(math.cos(angle)), Decimal.from_float(math.sin(angle))
            tx = Decimal.from_float(float(placement["x_mm"]))
            ty = Decimal.from_float(float(placement["y_mm"]))
        maximum = Decimal(0)
        for actual, ideal in zip(serialized, reference):
            x, y = actual
            for a, b, c, d, e, f in reversed(matrices):
                x, y = a * x + c * y + e, b * x + d * y + f
            x, y = x * ratio, (media_height - y) * ratio
            px, py = (Decimal.from_float(float(value)) for value in ideal)
            if placement is not None:
                px, py = tx + cosine * px - sine * py, ty + sine * px + cosine * py
            error = ((x - px) ** 2 + (y - py) ** 2).sqrt()
            maximum = max(maximum, error)
        return math.nextafter(float(maximum), math.inf) if maximum else 0.0


def _page_footer(data: dict, page_index: int) -> str:
    return f"Měřítko modelu {data['scale_label']} · Strana {page_index + 1} / {len(data['pages'])}"


def _svg(
    page: dict,
    data: dict,
    family: str,
    digest: str,
    target: Path,
    page_index: int,
    curve_bound: float = 0.0,
    numeric_bound: float = 0.0,
) -> None:
    width, height = page["width_mm"], page["height_mm"]
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": f"{_fmt(width)}mm",
            "height": f"{_fmt(height)}mm",
            "viewBox": f"0 0 {_fmt(width)} {_fmt(height)}",
            "data-project-id": data["project_id"],
            "data-snapshot-digest": digest,
            "data-page-id": page["id"],
            "data-pdf-arc-interpolation-error-bound-mm": _fmt(curve_bound),
            "data-pdf-numeric-serialization-error-bound-mm": _fmt(numeric_bound),
            "data-pdf-combined-position-error-bound-mm": _fmt(
                _source_svg_bound(data) + curve_bound + numeric_bound
            ),
        },
    )
    ET.SubElement(root, "title").text = str(data.get("name", data["project_id"]))
    if "construction_checks" in data:
        full, summary = _construction_metadata(data)
        root.set("data-construction-checks-digest", summary["construction_checks_digest"])
        ET.SubElement(root, "metadata", {"id": "construction-checks"}).text = full
    for part in page["parts"]:
        place = part["placement"]
        group = ET.SubElement(
            root,
            "g",
            {
                "id": "part-" + part["id"],
                "data-part-id": part["id"],
                "transform": (
                    f"translate({_fmt(place['x_mm'])} {_fmt(place['y_mm'])}) "
                    f"rotate({_fmt(_rotation(place))})"
                ),
            },
        )
        ET.SubElement(group, "title").text = str(part.get("name", part["id"]))
        for role in ROLES:
            attrs = {
                "id": f"role-{part['id']}-{role}",
                "data-role": role,
                "class": role,
                "fill": "none",
                "stroke": "#202b2b",
                "stroke-width": "0.25",
            }
            if role == "TABS":
                attrs.update(fill="#eee6d5", stroke="none")
            elif role == "GUIDES":
                attrs.update(stroke="#8c9894", **{"stroke-width": "0.15"})
            elif role == "FOLD_MOUNTAIN":
                attrs["stroke-dasharray"] = "2,1"
            elif role == "FOLD_VALLEY":
                attrs["stroke-dasharray"] = "2,0.5,0.5,0.5"
            subgroup = ET.SubElement(group, "g", attrs)
            for index, path in enumerate(part["paths"].get(role, [])):
                ET.SubElement(
                    subgroup,
                    "path",
                    {
                        "id": f"path-{part['id']}-{role}-{index}",
                        "d": _svg_path(path),
                        "fill-rule": path.get("fill_rule", "evenodd"),
                    },
                )
            if role == "LABELS":
                for index, label in enumerate(part.get("labels", [])):
                    node = ET.SubElement(
                        subgroup,
                        "text",
                        {
                            "id": f"label-{part['id']}-{index}",
                            "x": _fmt(label["x"]),
                            "y": _fmt(label["y"]),
                            "font-size": _fmt(label.get("size_mm", 2.5)),
                            "font-family": family,
                            # Native editor typing must preserve a trailing space
                            # while the author is entering the next word (C06).
                            "{http://www.w3.org/XML/1998/namespace}space": "preserve",
                            "fill": "#202b2b",
                            "stroke": "none",
                        },
                    )
                    node.text = label["text"]
    guide = ET.SubElement(root, "g", {"id": "page-GUIDES", "data-role": "GUIDES"})
    ET.SubElement(
        guide,
        "path",
        {
            "d": _svg_path({"points": [[10, height - 15], [110, height - 15]], "closed": False}),
            "stroke": "#202b2b",
            "stroke-width": "0.25",
            "fill": "none",
            "data-calibration-mm": "100",
        },
    )
    for index, (text, y) in enumerate(
        [
            (_INSTRUCTION, height - 10),
            (_page_footer(data, page_index), height - 5),
        ]
    ):
        node = ET.SubElement(
            guide,
            "text",
            {
                "id": f"page-label-{index}",
                "x": "10",
                "y": _fmt(y),
                "font-family": family,
                "{http://www.w3.org/XML/1998/namespace}space": "preserve",
                "font-size": "2.5",
                "fill": "#202b2b",
            },
        )
        node.text = ("ČÁSTEČNÝ VÝSTUP — " if data.get("partial") else "") + text
    ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)


def _pdf(data: dict, font_name: str, digest: str, target: Path, curve_bound: float = 0.0,
         *, arc_tolerance_mm=None) -> float:
    mm = 72 / 25.4
    canvas = Canvas(str(target), invariant=1, pageCompression=1)
    canvas.setTitle(str(data.get("name", data["project_id"])))
    numeric_bound = 0.0
    page_matrix, part_matrix, media_height = None, None, None

    def text(value, x, y, size):
        nonlocal numeric_bound
        canvas.saveState()
        _precise_transform(canvas, (1, 0, 0, -1, x, y))
        matrices = [
            page_matrix,
            *([part_matrix] if part_matrix is not None else []),
            _serialized_matrix(canvas),
        ]
        numeric_bound = max(
            numeric_bound,
            _numeric_error(
                [(Decimal(0), Decimal(0))],
                [(x, y)],
                matrices,
                media_height,
                place if part_matrix is not None else None,
            ),
        )
        canvas.setFont(font_name, size)
        canvas.drawString(0, 0, value)
        canvas.restoreState()

    for page_index, page in enumerate(data["pages"]):
        canvas.setPageSize((page["width_mm"] * mm, page["height_mm"] * mm))
        canvas.saveState()
        _precise_transform(canvas, (mm, 0, 0, -mm, 0, page["height_mm"] * mm))
        page_matrix = _serialized_matrix(canvas)
        media_height = Decimal(pdfdoc.format(page["height_mm"] * mm, canvas._doc).decode("ascii"))
        for part in page["parts"]:
            place = part["placement"]
            canvas.saveState()
            theta = math.radians(_rotation(place))
            c, s = math.cos(theta), math.sin(theta)
            _precise_transform(canvas, (c, s, -s, c, place["x_mm"], place["y_mm"]))
            part_matrix = _serialized_matrix(canvas)
            canvas._code.append(f"/APPart_{part['id']} BMC")
            # Fill tabs before manufacturing lines; no duplicate tab strokes.
            for role in (
                "TABS",
                "ARTWORK",
                "CUT",
                "FOLD_MOUNTAIN",
                "FOLD_VALLEY",
                "GUIDES",
                "LABELS",
            ):
                canvas._code.append(f"/APRole_{role} BMC")
                canvas.setLineWidth(0.15 if role == "GUIDES" else 0.25)
                canvas.setStrokeColorRGB(
                    *((0.55, 0.6, 0.58) if role == "GUIDES" else (0.125, 0.17, 0.17))
                )
                canvas.setFillColorRGB(0.933, 0.902, 0.835)
                canvas.setDash(
                    [2, 1]
                    if role == "FOLD_MOUNTAIN"
                    else [2, 0.5, 0.5, 0.5]
                    if role == "FOLD_VALLEY"
                    else []
                )
                for item in part["paths"].get(role, []):
                    path = canvas.beginPath()
                    controls = []
                    current, start = None, None
                    for command in _commands(item):
                        op = command[0]
                        if op == "M":
                            current = start = command[1:3]
                            path.moveTo(*current)
                            controls.append(current)
                        elif op == "L":
                            current = command[1:3]
                            path.lineTo(*current)
                            controls.append(current)
                        elif op == "C":
                            path.curveTo(*command[1:])
                            controls.extend(command[index : index + 2] for index in (1, 3, 5))
                            current = command[-2:]
                        elif op == "A":
                            curves, _ = _arc_cubics(_arc(current, command),
                                                     tolerance_mm=arc_tolerance_mm)
                            for curve in curves:
                                path.curveTo(*curve)
                                controls.extend(curve[index : index + 2] for index in (0, 2, 4))
                            current = command[-2:]
                        else:
                            path.close()
                            current = start
                    if any(sid in data.get("construction_checks", {}).get("lofts", {})
                           for sid in part.get("surface_ids", [])):
                        _precise_path(path, controls)
                    numeric_bound = max(
                        numeric_bound,
                        _numeric_error(
                            _serialized_controls(path.getCode()),
                            controls,
                            [page_matrix, part_matrix],
                            media_height,
                            place,
                        ),
                    )
                    canvas.drawPath(
                        path,
                        stroke=int(role != "TABS"),
                        fill=int(role == "TABS"),
                        fillMode=0 if item.get("fill_rule", "evenodd") == "evenodd" else 1,
                    )
                canvas._code.append("EMC")
            canvas.setFillColorRGB(0.125, 0.17, 0.17)
            for label in part.get("labels", []):
                text(label["text"], label["x"], label["y"], label.get("size_mm", 2.5))
            canvas._code.append("EMC")
            canvas.restoreState()
            part_matrix = None
        canvas.setDash([])
        canvas.setStrokeColorRGB(0.125, 0.17, 0.17)
        canvas.setFillColorRGB(0.125, 0.17, 0.17)
        canvas.setLineWidth(0.25)
        canvas.line(10, page["height_mm"] - 15, 110, page["height_mm"] - 15)
        numeric_bound = max(
            numeric_bound,
            _numeric_error(
                _serialized_controls(canvas._code[-1]),
                [(10, page["height_mm"] - 15), (110, page["height_mm"] - 15)],
                [page_matrix],
                media_height,
            ),
        )
        prefix = "ČÁSTEČNÝ VÝSTUP — " if data.get("partial") else ""
        text(prefix + _INSTRUCTION, 10, page["height_mm"] - 10, 2.5)
        text(
            prefix + _page_footer(data, page_index),
            10,
            page["height_mm"] - 5,
            2.5,
        )
        canvas.restoreState()
        canvas.showPage()
    source_bound = _source_svg_bound(data)
    if source_bound + curve_bound + numeric_bound > PDF_DIGITAL_BUDGET_MM:
        raise SnapshotError(
            "PDF numeric serialization cannot preserve the required 0.01 mm precision; "
            "choose a paper frame near the material instead of compensating extreme coordinates. "
            f"Source/SVG bound={source_bound:.8g} mm, interpolation bound={curve_bound:.8g} mm, "
            f"serialization bound={numeric_bound:.8g} mm."
        )
    if "construction_checks" in data:
        _, summary = _construction_metadata(data)
        canvas.setKeywords(json.dumps(summary, sort_keys=True, ensure_ascii=False, allow_nan=False))
    canvas.setSubject(
        "Author export snapshot "
        + digest
        + "; arc_interpolation_error_bound_mm="
        + _fmt(curve_bound)
        + "; numeric_serialization_error_bound_mm="
        + _fmt(numeric_bound)
        + "; combined_position_error_bound_mm="
        + _fmt(source_bound + curve_bound + numeric_bound)
    )
    canvas.save()
    return numeric_bound


def _construction_metadata(data):
    checks = data["construction_checks"]
    full = json.dumps(checks, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    summary = {
        "construction_checks_digest": hashlib.sha256(full.encode("utf8")).hexdigest(),
        "material_profile": checks.get("material_profile"),
        "connector_statuses": {
            cid: report["status"] for cid, report in checks["connector_bends"].items()
        },
        "physical_build": "NOT_VERIFIED",
        "unknown_search_scope": "BOUNDED_COLLISION_WITNESS_SEARCH; ABSENCE_NOT_PROVEN",
    }
    return full, summary


def _remove_stage(stage: Path, parent: Path) -> None:
    if stage.resolve().parent != parent.resolve() or not stage.name.startswith(".author-export-"):
        raise ExportWriteError(
            "Refusing to remove a directory not owned by this export transaction"
        )
    shutil.rmtree(stage)


def _write_validated_vectors(data, stage, names, font_name, family, digest, curve_bound):
    """Tighten arc representation inside the transaction, without relaxing AC.

    A positional bound alone cannot guarantee the independent area budget. Try
    at most four progressively finer representations. Other errors never retry;
    no existing user file is touched until all checks have succeeded.
    """
    tolerance, attempts = PDF_ARC_TOLERANCE_MM, []
    for attempt in range(4):
        if attempt:
            curve_bound = _curve_bound(data, arc_tolerance_mm=tolerance)
        numeric_bound = _pdf(data, font_name, digest, stage / "new/model.pdf", curve_bound,
                             arc_tolerance_mm=tolerance)
        for page_index, (page, name) in enumerate(zip(data["pages"], names)):
            _svg(page, data, family, digest, stage / "new" / name, page_index,
                 curve_bound, numeric_bound)
        checks = {}
        record = {"requested_interpolation_bound_mm": tolerance,
                  "actual_interpolation_bound_mm": curve_bound}
        construction = data.get("construction_checks", {})
        if construction.get("curve_profiles") or construction.get("lofts"):
            from .curve_output_validation import validate_pdf_curve_geometry
            from .loft_output_validation import (
                LOFT_OUTPUT_MAX_COMMANDS,
                LOFT_OUTPUT_MAX_NODES,
                validate_loft_vector_outputs,
            )
            from .svg_curve_validation import validate_svg_curve_geometry

            expected = _curve_output_expectations(data)
            allowed = data["construction_checks"].get("accepted_layout_overlaps", [])
            budgets = (
                {"max_nodes": LOFT_OUTPUT_MAX_NODES, "max_commands": LOFT_OUTPUT_MAX_COMMANDS}
                if construction.get("lofts") else {}
            )
            checks["pdf"] = validate_pdf_curve_geometry(
                stage / "new/model.pdf", expected, allowed, **budgets,
            )
            checks["svg"] = [
                validate_svg_curve_geometry(
                    stage / "new" / name,
                    {pid: value for pid, value in expected.items() if value["page_index"] == index},
                    **budgets,
                )
                for index, name in enumerate(names[:-1])
            ]
            try:
                checks["area_agreement"] = _validate_vector_area_agreement(checks, expected)
            except CurveOutputError as exc:
                if attempt == 3:
                    raise
                record.update(status="AREA_BUDGET_NOT_MET", evidence=exc.report)
                attempts.append(record)
                tolerance /= 10
                continue
            if construction.get("lofts"):
                checks["lofts"] = validate_loft_vector_outputs(
                    data, [stage / "new" / name for name in names[:-1]],
                    stage / "new/model.pdf", expected_parts=expected,
                )
            record["status"] = "ACTUAL_GEOMETRY_AND_AREA_VERIFIED"
        else:
            record["status"] = "POSITION_CHECKED_ONLY; NO_AUTHORED_MATERIAL_CERTIFICATE"
        attempts.append(record)
        return curve_bound, numeric_bound, checks, tolerance, attempts
    raise AssertionError("Bounded vector validation loop must return or raise")


def export_all(
    snapshot: dict, output_directory: str | Path, *, font_path: str | Path | None = None
) -> list[Path]:
    """Write a complete vector bundle transactionally without mutating the snapshot.

    A missing/unsupported/glyph-incomplete font fails before any output changes.
    Old files owned by a previous manifest are replaced/removed as one rollback
    transaction; unrelated files in the chosen directory remain untouched.
    """
    with _LOCK:
        data = _detached(snapshot)
        _validate(data)
        try:
            curve_bound = _curve_bound(data)
        except (ArithmeticError, ValueError) as exc:
            if isinstance(exc, SnapshotError):
                raise
            raise SnapshotError(f"Cannot represent arc at the required precision: {exc}") from exc
        texts = [_INSTRUCTION, data["scale_label"], "ČÁSTEČNÝ VÝSTUP —"]
        texts.extend(_page_footer(data, index) for index in range(len(data["pages"])))
        texts.extend(
            label["text"]
            for page in data["pages"]
            for part in page["parts"]
            for label in part.get("labels", [])
        )
        font_name, family, font_digest = _font(font_path, texts)
        digest = canonical_digest(data)
        directory = Path(output_directory).absolute()
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ExportWriteError("Output directory must be a real directory")
        names = [f"page-{page['id']}.svg" for page in data["pages"]] + ["model.pdf"]
        previous = []
        old_manifest = directory / _MANIFEST
        if old_manifest.exists():
            try:
                prior_manifest = json.loads(old_manifest.read_text(encoding="utf-8"))
                if prior_manifest.get("schema_version") != 1:
                    raise ValueError("Unknown export manifest schema")
                if prior_manifest.get("project_id", data["project_id"]) != data["project_id"]:
                    raise ValueError("The directory contains another project's export bundle")
                previous = prior_manifest["files"]
                if not isinstance(previous, list) or any(
                    name not in ["model.pdf"]
                    and not re.fullmatch(r"page-[A-Za-z0-9][A-Za-z0-9_.-]*\.svg", name)
                    for name in previous
                ):
                    raise ValueError("Invalid owned file list")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise ExportWriteError(
                    f"Previous export manifest is invalid; existing outputs preserved: {exc}"
                ) from exc
        stage = None
        committed = []
        backups = {}
        retained = False
        try:
            directory.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".author-export-", dir=directory.parent))
            (stage / "new").mkdir()
            (stage / "old").mkdir()
            curve_bound, numeric_bound, actual_curve_checks, used_tolerance, attempts = (
                _write_validated_vectors(data, stage, names, font_name, family, digest, curve_bound)
            )
            (stage / "new" / _MANIFEST).write_text(
                json.dumps(
                    dict(
                        schema_version=1,
                        project_id=data["project_id"],
                        snapshot_digest=digest,
                        font_sha256=font_digest,
                        pdf_arc_approximation={
                            "method": "cubic_hermite",
                            "max_interpolation_error_mm": curve_bound,
                            "requested_interpolation_bound_mm": used_tolerance,
                            "precision_attempts": attempts,
                            "bound_scope": "arc_to_cubic_before_numeric_serialization",
                        },
                        pdf_geometry_precision={
                            "numeric_serialization_bound_mm": numeric_bound,
                            "source_to_native_svg_bound_mm": _source_svg_bound(data),
                            "combined_position_error_bound_mm": (
                                _source_svg_bound(data) + curve_bound + numeric_bound
                            ),
                            "required_digital_budget_mm": PDF_DIGITAL_BUDGET_MM,
                            "method": "serialized_CTM_and_Bernstein_control_difference",
                            "scope": (
                                "finite_input_paths_calibration_text_anchors; "
                                "font_outlines_excluded"
                            ),
                        },
                        files=names,
                        **({"actual_curve_output_checks": actual_curve_checks}
                           if actual_curve_checks else {}),
                        **({"construction_checks": data["construction_checks"],
                            "construction_summary": _construction_metadata(data)[1]}
                           if "construction_checks" in data else {}),
                    ),
                    sort_keys=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            for staged_file in (stage / "new").iterdir():
                with staged_file.open("rb+") as stream:
                    stream.flush()
                    os.fsync(stream.fileno())
            affected = list(dict.fromkeys([*names, *previous, _MANIFEST]))
            for name in affected:
                current = directory / name
                if current.is_symlink() or (current.exists() and not current.is_file()):
                    raise ExportWriteError(f"Refusing to replace non-file output {name}")
                if current.exists():
                    if name != _MANIFEST and name not in previous:
                        raise ExportWriteError(
                            f"Refusing to replace an unrelated existing file {name}"
                        )
                    backup = stage / "old" / name
                    shutil.copy2(current, backup)
                    backups[name] = backup
            directory.mkdir(exist_ok=True)
            for name in affected:
                new = stage / "new" / name
                target = directory / name
                if new.exists():
                    os.replace(new, target)
                elif target.exists():
                    target.unlink()
                committed.append(name)
        except Exception as exc:
            rollback_errors = []
            for name in reversed(committed):
                try:
                    if name in backups:
                        os.replace(backups[name], directory / name)
                    elif (directory / name).exists():
                        (directory / name).unlink()
                except OSError as rollback_error:
                    rollback_errors.append(str(rollback_error))
            if rollback_errors:
                retained = True
                raise ExportWriteError(
                    f"Export failed ({exc}); rollback also failed: {'; '.join(rollback_errors)}",
                    stage,
                ) from exc
            if isinstance(exc, (SnapshotError, FontError, ExportWriteError, CurveOutputError)):
                raise
            raise ExportWriteError(f"Export failed; previous outputs restored: {exc}") from exc
        finally:
            if stage is not None and not retained:
                _remove_stage(stage, directory.parent)
        return [directory / name for name in names]
