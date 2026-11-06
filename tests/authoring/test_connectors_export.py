import json

from test_interior import wall_roof

from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter.author_export import export_all


def test_band_and_authored_tabs_share_complete_snapshot_with_both_vector_outputs(tmp_path):
    p, wall, roof, edge = wall_roof()
    aid = p.attach_edge_to_surface(wall, edge, roof, target_side="inside")
    p.set_front_side(p.part_for_surface(roof), "inside")
    band = p.add_glue_band(aid)
    p.recompute()
    ids = [p.part_for_surface(wall), p.part_for_surface(roof), band]
    for pid, y in zip(ids, [20, 90, 170]):
        p.set_placement(pid, p.pages[0].id, 20, y)
    for issue in p.validate_layout():
        assert issue.severity == "warning", issue
        p.acknowledge(issue.id)
    saved = tmp_path / "source.apcraft"
    p.save(saved)
    loaded = AuthorProject.load(saved)
    snapshot = loaded.snapshot()
    assert set(snapshot["coverage"]["expected_part_ids"]) == set(ids)
    assert set(snapshot["coverage"]["expected_surface_ids"]) == set(p.surfaces)
    page = snapshot["pages"][0]
    assert len(page["parts"]) == 3
    target = next(part for part in page["parts"] if part["id"] == p.part_for_surface(roof))
    assert target["paths"]["GUIDES"]
    export_all(snapshot, tmp_path / "vectors")
    assert (tmp_path / "vectors" / "model.pdf").exists()
    assert len(list((tmp_path / "vectors").glob("*.svg"))) == 1
    manifest = json.loads((tmp_path / "vectors" / ".author-export.json").read_text(encoding="utf8"))
    assert manifest
