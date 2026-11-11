"""Explicit author choices, one domain transaction, no packing or lock bypass."""

import copy

import pytest

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ValidationError


def three_parts():
    p = AuthorProject.new(scale=1)
    ids = [
        p.part_for_surface(p.add_surface(p.add_profile([[0, 0], [10, 0], [10, 10], [0, 10]])))
        for _ in range(3)
    ]
    return p, ids


def test_batch_matches_explicit_single_choices_and_validates_once(monkeypatch):
    p, ids = three_parts()
    reference = AuthorProject.from_dict(p.to_dict())
    updates = {
        ids[0]: {"page_id": p.pages[0].id, "x_mm": 32.125, "y_mm": 45, "rotation_deg": 17},
        ids[1]: {
            "page_id": None,
            "x_mm": -14,
            "y_mm": 9,
            "rotation_deg": -30,
            "position_locked": True,
            "rotation_locked": True,
        },
    }
    for pid, values in updates.items():
        reference.set_placement(pid, **values)
    calls, original, revision = [], p.validate, p.revision
    monkeypatch.setattr(p, "validate", lambda: (calls.append(True), original())[1])
    p.set_placements(updates)
    assert len(calls) == 1
    assert p.revision == revision + 1
    assert p.placements == reference.placements
    # The omitted part remains untouched; no inferred page/grid/rotation.
    assert p.placements[ids[2]].page_id is None


@pytest.mark.parametrize(
    "bad",
    [
        {"page_id": "missing-page"},
        {"x_mm": True},
        {"x_mm": float("nan")},
        {"y_mm": float("inf")},
        {"rotation_deg": float("-inf")},
        {"position_locked": 1},
        {"rotation_locked": "false"},
        {"unexpected": 1},
        None,
    ],
)
def test_invalid_late_update_rolls_back_every_earlier_change(bad):
    p, ids = three_parts()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_placements({ids[0]: {"x_mm": 100}, ids[1]: bad})
    assert p.to_dict() == before


@pytest.mark.parametrize("updates", [[], [("same", {}), ("same", {})], None])
def test_non_mapping_or_duplicate_input_sequence_is_typed_failure(updates):
    p, _ = three_parts()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_placements(updates)
    assert p.to_dict() == before


def test_duplicate_producing_mapping_cannot_override_dict_iteration():
    p, ids = three_parts()

    class Repeated(dict):
        def items(self):
            return [(ids[0], {"x_mm": 10}), (ids[0], {"x_mm": 20})]

    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_placements(Repeated())
    assert p.to_dict() == before


def test_unknown_part_is_not_created_and_no_prior_change_survives():
    p, ids = three_parts()
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.set_placements({ids[0]: {"x_mm": 100}, "unknown": {"y_mm": 5}})
    assert p.to_dict() == before


@pytest.mark.parametrize(
    "bad",
    [
        {"x_mm": 40},
        {"rotation_deg": 20},
        {"position_locked": False, "x_mm": 40},
        {"rotation_locked": False, "rotation_deg": 20},
    ],
)
def test_batch_obeys_existing_locks_without_unlock_and_move_shortcut(bad):
    p, ids = three_parts()
    p.set_placement(ids[1], position_locked=True, rotation_locked=True)
    before = p.to_dict()
    with pytest.raises(ValidationError, match="zamčen"):
        p.set_placements({ids[0]: {"x_mm": 100}, ids[1]: bad})
    assert p.to_dict() == before


def test_empty_and_noop_batch_do_not_create_phantom_revision_or_history():
    p, ids = three_parts()
    before = p.to_dict()
    p.set_placements({})
    p.set_placements({ids[0]: {"x_mm": p.placements[ids[0]].x_mm}})
    assert p.to_dict() == before


def test_one_controller_undo_restores_all_author_choices():
    p, ids = three_parts()
    c = AuthorController()
    c.project = p
    before = copy.deepcopy(p.to_dict())
    c.execute(
        "Manual page placement",
        lambda project: project.set_placements(
            {
                ids[0]: {"page_id": p.pages[0].id, "x_mm": 40, "y_mm": 50, "rotation_deg": 30},
                ids[1]: {"page_id": p.pages[0].id, "x_mm": 90, "y_mm": 80, "rotation_deg": -30},
            }
        ),
    )
    after = c.project.to_dict()
    c.undo()
    assert c.project.to_dict() == before and not c.can_undo
    c.redo()
    assert c.project.to_dict() == after


def test_outside_sheet_keeps_original_authoring_semantics_with_actionable_issue():
    p, ids = three_parts()
    p.set_placements({ids[0]: {"page_id": p.pages[0].id, "x_mm": -20, "y_mm": 30}})
    assert p.placements[ids[0]].x_mm == -20
    assert any(i.code == "PHYSICAL_OVERFLOW" and ids[0] in i.part_ids for i in p.validate_layout())


def test_sixty_four_derived_parts_are_one_explicit_atomic_batch(monkeypatch):
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
    v = p.add_segmented_variant(s, preview_digest=p.preview_segmented_variant(s)["preview_digest"])
    second_page = p.add_page()
    rows = p.segmented_variants[v].triangle_bindings
    updates = {
        r["part_id"]: {
            "page_id": p.pages[0].id if i < 32 else second_page,
            "x_mm": 25 + (i % 8) * 18,
            "y_mm": 25 + ((i // 8) % 4) * 22,
            "rotation_deg": 0,
        }
        for i, r in enumerate(rows)
    }
    calls, original = [], p.validate
    monkeypatch.setattr(p, "validate", lambda: (calls.append(True), original())[1])
    p.set_placements(updates)
    assert len(calls) == 1
    assert all(p.placements[pid].x_mm == values["x_mm"] for pid, values in updates.items())
    snapshot = p.snapshot()
    assert [len(page["parts"]) for page in snapshot["pages"]] == [32, 32]
