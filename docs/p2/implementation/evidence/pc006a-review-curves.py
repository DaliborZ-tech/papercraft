"""Read actual serialized PDF curves against circular analytic oracles."""

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from pypdf.generic import ContentStream

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from archpapercraft.exporter.author_export import export_all

root = Path(tempfile.mkdtemp(prefix="pc006a-review-curves-"))
results = []
for radius in (0.0001, 0.001, 0.01, 0.1, 1, 10):
    x, y, degrees = 53.123456789, 71.987654321, 37.0
    commands = [["M", radius, 0.0], ["A", radius, radius, 0.0, 0, 1, -radius, 0.0], ["A", radius, radius, 0.0, 0, 1, radius, 0.0], ["Z"]]
    snap = {"project_id": "arc-review", "revision": 1, "scale_label": "1:1", "pages": [{"id": "one", "width_mm": 210, "height_mm": 297, "parts": [{"id": "arc", "name": "Arc", "placement": {"x_mm": x, "y_mm": y, "rotation_deg": degrees}, "paths": {"CUT": [{"commands": commands, "closed": True}]}, "labels": []}]}]}
    folder = root / str(radius)
    files = export_all(snap, folder)
    doc = PdfReader(files[-1])
    page = doc.pages[0]
    matrix, stack, curves, current = np.eye(3), [], [], None

    def point(values):
        p = matrix @ [float(values[0]), float(values[1]), 1.0]
        return np.array([p[0] * 25.4 / 72, (float(page.mediabox.height) - p[1]) * 25.4 / 72])

    for operands, op in ContentStream(page.get_contents(), doc).operations:
        if op == b"q":
            stack.append(matrix.copy())
        elif op == b"Q":
            matrix = stack.pop()
        elif op == b"cm":
            a, b, c, d, e, f = map(float, operands)
            matrix = matrix @ np.array([[a, c, e], [b, d, f], [0, 0, 1]])
        elif op == b"m":
            current = point(operands)
        elif op == b"l":
            current = point(operands)
        elif op == b"c":
            curve = np.array([current, *[point(operands[i:i+2]) for i in (0, 2, 4)]])
            curves.append(curve)
            current = curve[-1]
    max_error = 0.0
    for index, curve in enumerate(curves):
        for t in np.linspace(0, 1, 1001):
            actual = sum((1-t)**(3-i) * t**i * (1, 3, 3, 1)[i] * p for i, p in enumerate(curve))
            angle = (index + t) * 2 * math.pi / len(curves) + math.radians(degrees)
            ideal = np.array([x + radius * math.cos(angle), y + radius * math.sin(angle)])
            max_error = max(max_error, float(np.linalg.norm(actual - ideal)))
    manifest = json.loads((folder / ".author-export.json").read_text())
    bound = manifest["pdf_arc_approximation"]["max_position_error_mm"]
    results.append({"radius_mm": radius, "pdf_cubic_count": len(curves), "sampled_actual_serialized_position_error_mm": max_error, "declared_arc_bound_mm": bound, "sample_above_declared_bound": max_error > bound, "within_required_digital_0_01mm": max_error < .01})
result = {"source_root": str(args.source), "scratch": str(root), "meaning": "Sampling can falsify an asserted bound, not certify it. Includes serialized PDF transform/coordinate rounding.", "results": results}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
