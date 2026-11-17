"""Fresh schema9 D authoring reaches both writers without an archive cache."""

import copy

import pytest
from test_segmented_surface import target
from test_segmented_surface_curves import gothic_target

from archpapercraft.authoring import load_project
from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.segmented_output_validation import validate_segmented_snapshot


@pytest.mark.parametrize("kind", ["line", "curved"])
def test_fresh_current_d_save_reopen_and_both_actual_outputs(kind, tmp_path):
    p, sid, _, _ = target() if kind == "line" else gothic_target()
    assert p.loft_status(sid)["status"] != "EXACT"
    preview = p.preview_segmented_variant(sid)
    assert preview["can_confirm"]
    vid = p.add_segmented_variant(sid, preview_digest=preview["preview_digest"])
    rows = p.segmented_variants[vid].triangle_bindings
    p.add_page()
    per_page = len(rows) // 2
    for index, row in enumerate(rows):
        local = index % per_page
        p.set_placement(
            row["part_id"],
            p.pages[index // per_page].id,
            25 + local % 8 * 18,
            25 + local // 8 * 22,
            position_locked=index == 0,
            rotation_locked=index == 0,
        )
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    snapshot = p.snapshot()
    validate_segmented_snapshot(snapshot)
    state = copy.deepcopy(p.to_dict())
    path = tmp_path / "current9.apcraft"
    p.save(path)
    reopened = load_project(path)
    assert reopened.to_dict() == state
    assert reopened.snapshot() == snapshot
    outputs = export_all(reopened.snapshot(), tmp_path / "bundle")
    assert (tmp_path / "bundle/model.pdf").is_file()
    assert len(list((tmp_path / "bundle").glob("*.svg"))) == 2
    assert outputs
    poisoned = copy.deepcopy(snapshot)
    poisoned["pages"][0]["parts"][0]["paths"]["CUT"][0]["points"][0][0] += 1
    with pytest.raises(CurveOutputError):
        validate_segmented_snapshot(poisoned)
