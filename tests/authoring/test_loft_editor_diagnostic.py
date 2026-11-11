"""Exact read-only LX01 diagnostic; no editor/prefs changes or production math."""

import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree


def exact_green(commands):
    """Direct monomial Green integral with original decimal tokens as rationals."""
    total, current, start = Fraction(0), None, None
    for op, *values in commands:
        values = list(map(Fraction, values))
        if op == "M":
            current = start = values
        elif op == "Z":
            total += (current[0]*start[1]-current[1]*start[0])/2
            current = start
        elif op == "L":
            total += (current[0]*values[1]-current[1]*values[0])/2
            current = values
        elif op == "C":
            first, second, end = values[:2], values[2:4], values[4:]
            x, y = [[p, 3*(q-p), 3*(p-2*q+r), -p+3*q-3*r+s]
                    for p, q, r, s in zip(current, first, second, end)]
            total += sum((x[i]*j*y[j]-y[i]*j*x[j])/Fraction(i+j)
                         for i in range(4) for j in range(1, 4))/2
            current = end
        else:
            raise ValueError("LX01 oracle supports native L/C only, never sampled proxies.")
    return total


def compare_files(original, edited):
    # Reuse the independent harness's exact decimal absolute/relative parser;
    # this diagnostic does not call or alter its equality tolerance.
    tool = Path(__file__).resolve().parents[2] / "tools/authoring/editor_probe.py"
    spec = importlib.util.spec_from_file_location("lx01_editor_reader", tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original, edited = Path(original), Path(edited)

    def paths(file):
        return {p.attrib["id"]: p.attrib["d"] for p in ElementTree.parse(file).getroot().iter()
                if p.tag.endswith("path") and p.attrib.get("id", "").startswith("path-")}

    before, after = paths(original), paths(edited)
    assert before.keys() == after.keys(), "Path identities changed in editor"
    report = {"files_sha256": {str(file): hashlib.sha256(file.read_bytes()).hexdigest()
                               for file in (original, edited)}, "paths": []}
    for identity, raw in before.items():
        first, second = module._path_signature(raw), module._path_signature(after[identity])
        assert len(first) == len(second), "Command count changed in editor"
        assert all(a[0] == b[0] and len(a) == len(b) for a, b in zip(first, second))
        worst = max((abs(x-y), i, j, str(x), str(y))
                    for i, (a, b) in enumerate(zip(first, second))
                    for j, (x, y) in enumerate(zip(a[1:], b[1:])))
        a, b = exact_green(first), exact_green(second)
        closed = any(cmd[0] == "Z" for cmd in first)
        report["paths"].append({
            "id": identity, "commands": len(first), "closed_material_boundary": closed,
            "max_coordinate_difference_exact": str(worst[0]),
            "max_coordinate_difference_mm": float(worst[0]), "worst_command_index": worst[1],
            "coordinate_index": worst[2], "original_normalized_value": worst[3],
            "edited_normalized_value": worst[4],
            "green_original_exact": str(a), "green_edited_exact": str(b),
            "green_original_mm2": float(a), "green_edited_mm2": float(b),
            "green_difference_exact": str(abs(a-b)), "green_difference_mm2": float(abs(a-b)),
            "area_scope": ("CLOSED_MATERIAL_AREA" if closed else
                           "OPEN_PATH_INTEGRAL_NOT_MATERIAL_AREA"),
            "serialization_2e5_pass": worst[0] <= Fraction("0.00002"),
            "original_AC_position_001_pass": worst[0] <= Fraction("0.01"),
            "original_AC_area_001_pass": abs(a-b) <= Fraction("0.01") if closed else None,
        })
    return report


def test_exact_green_matches_independent_rectangle_and_polynomial_arch_areas():
    assert exact_green([("M", 0, 0), ("L", 2, 0), ("L", 2, 3), ("L", 0, 3), ("Z",)]) == 6
    # x=3t²−2t³, y=3t−3t²; integral y dx =3/5, clockwise boundary.
    assert exact_green([("M", 0, 0), ("C", 0, 1, 1, 1, 1, 0), ("Z",)]) == Fraction(-3, 5)


def test_diagnostic_retains_decimal_differences_and_relative_cumulative_error(tmp_path):
    original = tmp_path / "before.svg"
    edited = tmp_path / "after.svg"
    original.write_text('<svg><path id="path-model-CUT-0" d="M 0 0 L 1 0 L 1 1 Z"/></svg>')
    edited.write_text('<svg><path id="path-model-CUT-0" d="M 0 0 l 1.00000000000000001 0 '
                      '0 .99999 Z"/></svg>')
    diagnostic = compare_files(original, edited)["paths"][0]
    assert diagnostic["max_coordinate_difference_exact"] == "1/100000"
    assert diagnostic["green_original_exact"] != diagnostic["green_edited_exact"]
    assert diagnostic["serialization_2e5_pass"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True)
    parser.add_argument("--edited", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = compare_files(args.original, args.edited)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
