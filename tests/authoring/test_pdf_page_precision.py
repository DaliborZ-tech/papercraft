"""Actual physical PDF boxes and top-origin coordinates retain tiny reserve."""

import math
import re
from fractions import Fraction as Q

from test_export import snapshot as shared_snapshot  # noqa: F401 - independent fixture

from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions


def test_a4_portrait_and_landscape_actual_page_boxes_do_not_translate_material(
    request, tmp_path,
):
    snapshot = request.getfixturevalue("shared_snapshot")
    export_all(snapshot, tmp_path / "bundle")
    pdf = tmp_path / "bundle" / "model.pdf"
    # Preserve original decimal lexemes, before PDF library float conversion.
    boxes = re.findall(rb"/MediaBox\s*\[([^]]+)\]", pdf.read_bytes())
    assert len(boxes) == 2
    for box, (width, height) in zip(boxes, [(210, 297), (297, 210)]):
        operands = [Q(token.decode("ascii")) for token in box.split()]
        assert operands[:2] == [0, 0]
        physical = [value * Q(127, 360) for value in operands[2:]]
        assert abs(physical[0] - width) < Q(1, 10**10)
        assert abs(physical[1] - height) < Q(1, 10**10)
    parts = read_pdf_cut_regions(pdf)["parts"]
    for pid, angle in [("wall-a", 30), ("wall-b", -30)]:
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        expected = [
            [40 + c * x - s * y, 55 + s * x + c * y]
            for x, y in [(0, 0), (30, 0), (30, 20), (0, 20)]
        ]
        actual = [command[-2:] for command in parts[pid]["loops"][0] if command[0] != "Z"]
        assert len(actual) == len(expected)
        assert (
            max(
                abs(float(a) - b)
                for point, target in zip(actual, expected)
                for a, b in zip(point, target)
            )
            < 1e-10
        )
