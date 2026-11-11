"""Public D commands/persistence/selection; no native desktop or physical proof."""

import copy
import hashlib
import json
from fractions import Fraction

import numpy as np
import pytest

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import (
    AuthorProject,
    ProjectFormatError,
    ValidationError,
    load_project,
)
from archpapercraft.authoring.editing import rename_author_entities
from archpapercraft.authoring.segmented_surface import (
    SegmentationError,
    _digest,
    _generation_payload,
)


def target():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [40, 0]], closed=False)
    b = p.add_profile(
        [[0, 0], [40, 20]],
        closed=False,
        plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    s = p.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": p.profiles[a].segments[0].id,
                "second_segment_id": p.profiles[b].segments[0].id,
                "first_interval": [0, 1],
                "second_interval": [0, 1],
            }
        ],
    )
    return p, s, a, b


def confirm(p, s, **params):
    preview = p.preview_segmented_variant(s, **params)
    assert preview["can_confirm"], preview
    return p.add_segmented_variant(s, preview_digest=preview["preview_digest"], **params)


@pytest.fixture(scope="module")
def generation_state():
    p, s, a, b = target()
    v = confirm(p, s)
    return p.to_dict(), s, a, b, v


def restored(state):
    data, s, a, b, v = state
    return AuthorProject.from_dict(copy.deepcopy(data)), s, a, b, v


def manual_layout(p, v):
    p.add_page()
    for index, row in enumerate(p.segmented_variants[v].triangle_bindings):
        p.set_placement(
            row["part_id"],
            p.pages[index // 32].id,
            25 + (index % 8) * 18,
            25 + ((index // 8) % 4) * 22,
            (index % 3) * 15,
            position_locked=index == 0,
            rotation_locked=index == 0,
        )


@pytest.fixture(scope="module")
def laid_out_state(generation_state):
    p, s, a, b, v = restored(generation_state)
    manual_layout(p, v)
    assert not p.validate_layout()
    return p.to_dict(), s, a, b, v


def test_required_d_preview_is_detached_and_original_nonexact_target_survives():
    p, s, a, b = target()
    before = p.to_dict()
    preview = p.preview_segmented_variant(s)
    assert p.to_dict() == before
    assert p.loft_status(s)["status"] != "EXACT"
    assert preview["status"] == preview["mode"] == "APPROXIMATE"
    report = preview["certificate"]["math"]
    assert report["max_surface_deviation_paper_mm"] == 0.15625
    assert report["counts"]["triangles"] == 64
    assert report["counts"]["paired_cut_seams"] == 84
    assert report["patches"][0]["developability_determinant_exact"] == "-24000"
    assert preview["certificate"]["embedding"]["status"] == "CERTIFIED"
    material = preview["certificate"]["material_frame"]
    assert Fraction(material["max_target_to_material_deviation_paper_mm_exact"]) <= Fraction(1, 4)
    assert (
        float(Fraction(material["max_material_normal_angle_deg_exact"]))
        >= report["max_normal_angle_bound_deg"]
    )
    preview["source_binding"]["profiles"][0]["vertices"][0]["point"][0] = 999
    assert p.profiles[a].points[0] == [0.0, 0.0]
    assert p.profiles[b].points[1] == [40.0, 20.0]


def test_generated_parts_have_short_unique_print_names_and_reopen_preserves_author_names(
    generation_state,
):
    p, _, _, _, vid = restored(generation_state)
    records = p.segmented_variants[vid].triangle_bindings
    names = [p.parts[r["part_id"]].name for r in records]
    assert len(names) == len(set(names)) == 64
    assert all(name == f"P{p.parts[r['part_id']].number}" for name, r in zip(names, records))
    assert all(p.parts[r["part_id"]].labels[0]["text"] == name for r, name in zip(records, names))
    # Existing/custom authored names are not silently shortened on load.
    pid = records[0]["part_id"]
    rename_author_entities(p, part_id=pid, part_name="Owner custom name")
    p.recompute([pid])
    reopened = AuthorProject.from_dict(p.to_dict())
    assert reopened.parts[pid].name == "Owner custom name"
    assert reopened.parts[pid].labels[0]["text"] == "Owner custom name"


def test_generation_has_unique_planar_material_and_immutable_uv_edge_mapping(generation_state):
    p, s, _, _, v = restored(generation_state)
    variant = p.segmented_variants[v]
    assert len(p.parts) == len(p.surfaces) == 65  # 64 material islands + original reference.
    assert len(variant.triangle_bindings) == 64 and len(variant.paired_seams) == 84
    assert len({r["id"] for r in variant.triangle_bindings}) == 64
    assert len({r["source_parameter_key"] for r in variant.triangle_bindings}) == 64
    assert p.material_part_ids() == {r["part_id"] for r in variant.triangle_bindings}
    assert p.part_for_surface(s) not in p.material_part_ids()
    for record in variant.triangle_bindings:
        assert p.surfaces[record["surface_id"]].kind == "planar"
        assert p.parts[record["part_id"]].frame.root_surface_id == record["surface_id"]
        assert len(record["edge_ids"]) == 3 and len(record["parameter_vertices_exact"]) == 3
        assert p.placements[record["part_id"]].page_id is None
        for point in record["parameter_vertices_exact"]:
            assert all(0 <= Fraction(x) <= 1 for x in point)


def test_actual_generated_material_vertices_follow_independent_bilinear_target(generation_state):
    p, _, _, _, v = restored(generation_state)
    variant = p.segmented_variants[v]
    total = float(
        Fraction(
            variant.certificate["material_frame"]["max_target_to_material_deviation_paper_mm_exact"]
        )
    )
    # Every source parameter vertex lies on S=(40u,20uv,30v). Actual generated
    # profile-plane coordinates add a bounded finite reconstruction reserve.
    for record in variant.triangle_bindings:
        profile = p.profiles[record["profile_id"]]
        actual = profile.plane.world(profile.points)
        uv = [[float(Fraction(x)) for x in point] for point in record["parameter_vertices_exact"]]
        expected = np.array([[40 * u, 20 * u * w, 30 * w] for u, w in uv])
        assert np.max(np.linalg.norm(actual - expected, axis=1)) < 1e-12
        centre = actual.mean(axis=0)
        u, w = np.mean(uv, axis=0)
        assert np.linalg.norm(centre - [40 * u, 20 * u * w, 30 * w]) <= total


def test_manual_two_page_layout_save_open_and_explicit_material_reference_snapshot(
    laid_out_state, tmp_path
):
    p, s, a, b, v = restored(laid_out_state)
    path = tmp_path / "derived.apcraft"
    p.save(path)
    reopened = load_project(path)
    assert reopened.to_dict() == p.to_dict()
    snapshot = reopened.snapshot()
    coverage = snapshot["coverage"]
    assert coverage["reference_surface_ids"] == [s]
    assert len(coverage["expected_surface_ids"]) == 64
    assert len(coverage["all_construction_surface_ids"]) == 65
    assert s not in coverage["expected_surface_ids"]
    assert coverage["expected_segmented_variant_ids"] == [v]
    assert snapshot["construction_checks"]["reference_targets"][s]["status"] != "EXACT"
    assert not snapshot["construction_checks"]["lofts"]
    proof = snapshot["construction_checks"]["segmented_variants"][v]
    assert proof["mode"] == proof["status"] == "APPROXIMATE"
    assert proof["source_binding"]["profiles"][0]["id"] == a
    assert proof["source_binding"]["profiles"][1]["id"] == b
    assert [len(page["parts"]) for page in snapshot["pages"]] == [32, 32]
    assert all(
        part["flattening"]["mode"] == "APPROXIMATE"
        for page in snapshot["pages"]
        for part in page["parts"]
    )


@pytest.mark.parametrize(
    "params",
    [
        {"max_deviation_mm": 0.25, "max_cells": 1},
        {"max_deviation_mm": 0.001, "max_cells": 16},
        {"max_deviation_mm": 0},
        {"max_deviation_mm": True},
        {"max_depth": -1},
    ],
)
def test_infeasible_budget_is_typed_unresolved_without_any_partial_mutation(params):
    p, s, _, _ = target()
    before = p.to_dict()
    preview = p.preview_segmented_variant(s, **params)
    assert preview["status"] == "UNRESOLVED" and not preview["can_confirm"]
    with pytest.raises(SegmentationError) as caught:
        p.add_segmented_variant(s, preview_digest="not-a-confirmation", **params)
    assert caught.value.report["status"] == "UNRESOLVED"
    assert p.to_dict() == before


def test_curved_source_is_retained_by_generic_segmentation_without_implicit_conversion():
    p = AuthorProject.new(scale=1)
    a = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [0, 0],
                "end": [20, 0],
                "data": {"control1": [4, 5], "control2": [16, 5]},
            }
        ],
        closed=False,
    )
    b = p.copy_profile(a, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    s = p.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": p.profiles[a].segments[0].id,
                "second_segment_id": p.profiles[b].segments[0].id,
                "first_interval": [0, 1],
                "second_interval": [0, 1],
            }
        ],
    )
    before = p.to_dict()
    result = p.preview_segmented_variant(s)
    assert result["status"] == "APPROXIMATE" and result["can_confirm"]
    assert result["certificate"]["math"]["family"] == "INTERVAL_CURVED_RULED_TRIANGLE_ISLANDS"
    assert p.to_dict() == before
    variant = p.add_segmented_variant(s, preview_digest=result["preview_digest"])
    assert p.profiles[a].segments[0].kind == "cubic"
    assert p.segmented_variants[variant].source_binding["profiles"] == [
        before["profiles"][a],
        before["profiles"][b],
    ]


def test_source_edit_invalidates_confirmation_and_old_layout_survives_recompute(laid_out_state):
    p, s, _, b, v = restored(laid_out_state)
    original = copy.deepcopy(p.segmented_variants[v])
    layout = copy.deepcopy(p.placements)
    p.move_vertex(b, p.profiles[b].vertices[1].id, [40, 21])
    assert p.segmented_variant_status(v)["status"] == "STALE"
    assert any(i.code == "SEGMENTED_VARIANT_STALE" for i in p.validate_layout())
    with pytest.raises(ValidationError):
        p.snapshot()
    p.recompute()
    assert p.segmented_variant_status(v)["status"] == "STALE"
    assert p.segmented_variants[v] == original and p.placements == layout
    assert AuthorProject.from_dict(p.to_dict()).segmented_variants[v] == original
    assert p.loft_status(s)["status"] != "EXACT"


def test_stale_preview_token_cannot_confirm_changed_source():
    p, s, _, b = target()
    preview = p.preview_segmented_variant(s)
    p.move_vertex(b, p.profiles[b].vertices[1].id, [40, 21])
    before = p.to_dict()
    with pytest.raises(SegmentationError, match="Náhled"):
        p.add_segmented_variant(s, preview_digest=preview["preview_digest"])
    assert p.to_dict() == before


def test_immutable_update_retains_inactive_generation_and_author_locks(laid_out_state):
    p, s, _, _, v = restored(laid_out_state)
    old = copy.deepcopy(p.segmented_variants[v])
    placements = copy.deepcopy(p.placements)
    preview = p.preview_segmented_variant(s, max_deviation_mm=0.1)
    new = p.update_segmented_variant(
        v, preview_digest=preview["preview_digest"], max_deviation_mm=0.1
    )
    assert new != v and p.segmented_variants[new].previous_variant_id == v
    assert p.segmented_variants[new].print_selected and not p.segmented_variants[v].print_selected
    old.print_selected = False
    assert p.segmented_variants[v] == old
    assert all(p.placements[k] == placement for k, placement in placements.items())
    p.select_segmented_variant(v)
    assert p.snapshot()["coverage"]["expected_segmented_variant_ids"] == [v]
    assert p.snapshot()["coverage"]["inactive_variant_surface_ids"]


def test_restore_target_is_not_a_false_exact_or_global_error_suppression(laid_out_state):
    p, s, _, _, v = restored(laid_out_state)
    before = copy.deepcopy(p.placements)
    p.restore_segmented_target(s)
    assert p.part_for_surface(s) in p.material_part_ids()
    assert not p.segmented_variants[v].print_selected
    assert p.loft_status(s)["status"] != "EXACT"
    with pytest.raises(ValidationError):
        p.snapshot()
    p.select_segmented_variant(v)
    assert p.placements == before and p.snapshot()
    other = p.add_surface(p.add_profile([[0, 0], [10, 0], [0, 10]]))
    assert any(
        i.code == "UNPLACED" and p.part_for_surface(other) in i.part_ids
        for i in p.validate_layout()
    )
    with pytest.raises(ValidationError):
        p.snapshot()


@pytest.mark.parametrize("mutation", ["report", "coverage", "uv", "triangle", "source", "seams"])
def test_forged_generation_or_mapping_is_rejected_on_open_even_with_recomputed_hash(
    generation_state, mutation
):
    p, _, _, _, v = restored(generation_state)
    variant = p.segmented_variants[v]
    if mutation == "report":
        variant.certificate["math"]["max_surface_deviation_paper_mm"] = 0
    elif mutation == "coverage":
        variant.triangle_bindings.pop()
    elif mutation == "uv":
        variant.triangle_bindings[0]["parameter_vertices_exact"][1][0] = "1/100"
    elif mutation == "triangle":
        variant.triangle_bindings[0]["surface_id"] = variant.triangle_bindings[1]["surface_id"]
    elif mutation == "source":
        variant.source_binding["surface"]["id"] = p.project_id
    else:
        variant.paired_seams[0]["uses"][0]["triangle_id"] = p.project_id
    variant.generation_digest = _digest(_generation_payload(variant))
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(p.to_dict(validate=False))


def test_derived_profile_edit_is_unverified_until_repaired_and_recomputed(laid_out_state):
    p, _, _, _, v = restored(laid_out_state)
    row = p.segmented_variants[v].triangle_bindings[0]
    profile = p.profiles[row["profile_id"]]
    vertex, original = profile.vertices[1].id, list(profile.vertices[1].point)
    p.move_vertex(profile.id, vertex, [original[0] + 1, original[1]])
    assert p.segmented_variant_status(v)["status"] == "UNRESOLVED"
    assert AuthorProject.from_dict(p.to_dict())
    with pytest.raises(ValidationError):
        p.snapshot()
    p.move_vertex(profile.id, vertex, original)
    p.recompute([row["part_id"]])
    assert p.snapshot()


def test_public_controller_undo_redo_and_failed_confirm_keep_both_models_and_history(
    generation_state,
):
    data, s, _, _, _ = generation_state
    controller = AuthorController()
    controller.project = AuthorProject.from_dict(copy.deepcopy(data))
    controller.execute("Restore original target", lambda p: p.restore_segmented_target(s))
    before = controller.project.to_dict()
    controller.execute(
        "Confirm new generation",
        lambda p: p.add_segmented_variant(
            s, preview_digest=p.preview_segmented_variant(s)["preview_digest"]
        ),
    )
    after = controller.project.to_dict()
    controller.undo()
    assert controller.project.to_dict() == before
    with pytest.raises(SegmentationError):
        controller.execute(
            "Bad limit", lambda p: p.add_segmented_variant(s, preview_digest="bad", max_cells=1)
        )
    assert controller.can_redo and controller.project.to_dict() == before
    controller.redo()
    assert controller.project.to_dict() == after


def test_schema4_copy_preserves_source_and_layout_but_refuses_variant_capability(tmp_path):
    p, _, _, _ = target()
    data = p.to_dict()
    data.pop("segmented_variants")
    data.update(schema_version=4, writer_version="0.3.0-pc007a-profiles-experimental")
    path = tmp_path / "old-v4.apcraft"
    path.write_text(json.dumps(data), encoding="utf8")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    loaded = load_project(path)
    assert loaded.requires_save_as and loaded.loaded_from_schema == 4
    assert loaded.profiles == p.profiles and loaded.placements == p.placements
    with pytest.raises(ValidationError):
        loaded.save(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    loaded.save(tmp_path / "safe-copy.apcraft")
    data["segmented_variants"] = {}
    with pytest.raises(ProjectFormatError, match="Starší"):
        AuthorProject.from_dict(data)


@pytest.mark.parametrize("change", ["geometry_without_revision", "plane", "pose", "scale"])
def test_source_fingerprint_uses_actual_data_not_only_revision(generation_state, change):
    p, s, _, b, v = restored(generation_state)
    revisions = (p.profiles[b].revision, p.surfaces[s].revision)
    if change == "geometry_without_revision":
        p.profiles[b].vertices[1].point[1] += 1
    elif change == "plane":
        p.profiles[b].plane.origin[2] += 1
    elif change == "pose":
        p.surfaces[s].position_mm[0] += 1
    else:
        p.scale = 0.5
    assert revisions == (p.profiles[b].revision, p.surfaces[s].revision)
    assert p.segmented_variant_status(v)["status"] == "STALE"


def test_forged_material_substitution_cannot_rebind_itself_by_updating_both_hashes(
    generation_state,
):
    from archpapercraft.authoring.segmented_surface import _geometry_binding

    p, _, _, _, v = restored(generation_state)
    variant = p.segmented_variants[v]
    record = variant.triangle_bindings[0]
    profile, surface = p.profiles[record["profile_id"]], p.surfaces[record["surface_id"]]
    profile.vertices[1].point[0] += 1
    record["material_input_digest"] = _geometry_binding(profile, surface)
    variant.generation_digest = _digest(_generation_payload(variant))
    with pytest.raises(ProjectFormatError, match="zfalšována"):
        AuthorProject.from_dict(p.to_dict(validate=False))


def test_global_triangle_embedding_not_proved_is_not_silently_promoted():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [40, 0], [0, 10]], closed=False)
    b = p.add_profile(
        [[0, 0], [40, 20], [0, 10]],
        closed=False,
        plane={"origin": [0, 0, 30], "u": [1, 0, 0], "v": [0, 1, 0]},
    )
    s = p.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": x.id,
                "second_segment_id": y.id,
                "first_interval": [0, 1],
                "second_interval": [0, 1],
            }
            for x, y in zip(p.profiles[a].segments, p.profiles[b].segments)
        ],
    )
    before = p.to_dict()
    result = p.preview_segmented_variant(s)
    assert result["status"] == "UNRESOLVED" and not result["can_confirm"]
    assert "globální" in result["message"]
    assert p.to_dict() == before


def test_paired_cut_edges_have_actual_stable_profile_edge_uuids(generation_state):
    p, _, _, _, v = restored(generation_state)
    variant = p.segmented_variants[v]
    by_triangle = {r["id"]: r for r in variant.triangle_bindings}
    for seam in variant.paired_seams:
        assert len(seam["uses"]) == 2
        for use in seam["uses"]:
            row = by_triangle[use["triangle_id"]]
            assert use["edge_id"] in row["edge_ids"]
            assert p.profiles[row["profile_id"]].segment(use["edge_id"]) is not None


@pytest.mark.parametrize("move", [{"x_mm": 26}, {"rotation_deg": 10}])
def test_derived_manual_layout_locks_are_effective_and_rollback(laid_out_state, move):
    p, _, _, _, v = restored(laid_out_state)
    pid = p.segmented_variants[v].triangle_bindings[0]["part_id"]
    before = p.to_dict()
    with pytest.raises(ValidationError, match="zamčen"):
        p.set_placement(pid, **move)
    assert p.to_dict() == before


def test_direct_clearance_queries_use_the_complete_selected_material_not_reference(
    generation_state, monkeypatch
):
    from archpapercraft.authoring.bend import BendCommands

    p, s, _, _, v = restored(generation_state)
    seen = []

    def inspect_registry(material, _):
        seen.append(set(material.surfaces))
        return {"status": "UNVERIFIED", "scope": "ROUTING_TEST_NOT_GEOMETRIC_PROOF"}

    monkeypatch.setattr(BendCommands, "connector_bend_clearance", inspect_registry)
    assert p.connector_bend_clearance("routing-probe")["status"] == "UNVERIFIED"
    assert seen == [{r["surface_id"] for r in p.segmented_variants[v].triangle_bindings}]
    assert s not in seen[0]


def test_embedding_pair_budget_is_finite_and_unresolved_without_partial_state(monkeypatch):
    from archpapercraft.authoring import segmented_surface

    p, s, _, _ = target()
    before = p.to_dict()
    monkeypatch.setattr(segmented_surface, "MAX_EMBEDDING_PAIRS", 0)
    preview = p.preview_segmented_variant(s)
    assert preview["status"] == "UNRESOLVED"
    assert preview["math_report"]["embedding_pair_limit"] == 0
    assert p.to_dict() == before


def test_connected_external_material_requires_explicit_remap_before_new_generation(
    generation_state,
):
    p, s, _, _, v = restored(generation_state)
    row = p.segmented_variants[v].triangle_bindings[0]
    source = p.profiles[row["profile_id"]]
    copy_profile = p.add_profile(
        source.points,
        plane={
            "origin": list(source.plane.origin),
            "u": list(source.plane.u),
            "v": list(source.plane.v),
        },
    )
    other = p.add_surface(copy_profile)
    p.connect_edges(
        row["surface_id"], row["edge_ids"][0], other, p.profiles[copy_profile].segments[0].id
    )
    before = p.to_dict()
    preview = p.preview_segmented_variant(s)
    assert preview["status"] == "UNRESOLVED" and "odpojte" in preview["message"]
    assert p.to_dict() == before


def test_preview_shows_actual_material_frame_and_cannot_inject_changed_mesh():
    p, s, _, _ = target()
    preview = p.preview_segmented_variant(s)
    mesh = copy.deepcopy(preview["preview_geometry"])
    assert len(mesh["triangles"]) == len(mesh["triangle_sources"]) == 64
    assert len(mesh["vertices"]) == len(mesh["vertex_normals"]) == 192
    preview["preview_geometry"]["vertices"][0][0] = 999
    variant = p.add_segmented_variant(s, preview_digest=preview["preview_digest"])
    for triangle, record in zip(mesh["triangles"], p.segmented_variants[variant].triangle_bindings):
        shown = {tuple(mesh["vertices"][i]) for i in triangle}
        actual = {tuple(point) for point in p.world_geometry(record["surface_id"])["vertices"]}
        assert shown == actual
