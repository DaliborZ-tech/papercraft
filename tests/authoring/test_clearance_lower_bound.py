"""An explicit empty guaranteed set keeps identity without inventing material."""

import numpy as np
import pytest

from archpapercraft.authoring.clearance import (
    ContactAllowance,
    FoldSweep,
    MaterialObstacle,
    MaterialProfile,
    check_fold_clearance,
)


def scene(known=True, obstacle=False):
    sweep = FoldSweep(
        patches_world_mm=[[[20, 5, 0], [60, 5, 0], [60, 5, -5], [20, 5, -5]]],
        hinge_start_mm=[20, 5, 0], hinge_end_mm=[60, 5, 0], angle_deg=-90,
        source_id="source", receiver_id="receiver", initial_normal=[0, 1, 0],
        final_normal=[0, 0, -1],
    )
    thickness = 0.2 if known else None
    obstacles = [MaterialObstacle(key, np.empty((0, 3, 3)), thickness)
                 for key in ("source", "receiver")]
    if obstacle:
        obstacles.append(MaterialObstacle("certain-mid-fold", [
            [[25, 3, -2.5], [55, 3, -2.5], [55, 3, -1.5]],
            [[25, 3, -2.5], [55, 3, -1.5], [25, 3, -1.5]],
        ], thickness))
    return sweep, MaterialProfile(thickness), obstacles


def check(*, known=True, obstacle=False, lower=False, missing=False):
    sweep, material, obstacles = scene(known, obstacle)
    return check_fold_clearance(
        sweep, material, obstacles, expected_obstacle_ids=[o.id for o in obstacles][missing:],
        lower_bound_only=lower,
    )


def test_complete_default_contract_still_rejects_empty_source_and_receiver():
    result = check()
    assert result.status == "UNRESOLVED"
    assert result.material_domain == "COMPLETE_DECLARED_MATERIAL"


def test_lower_empty_material_remains_explicit_and_cannot_mean_full_scene_clear():
    result = check(lower=True)
    assert result.status == "CLEAR"
    assert result.material_domain == "GUARANTEED_LOWER_BOUND_ONLY"
    assert set(result.checked_obstacle_ids) == {"source", "receiver"}
    assert set(result.empty_obstacle_ids) == {"source", "receiver"}


@pytest.mark.parametrize("known", [False, True])
def test_empty_required_lower_sets_cannot_erase_an_independent_certain_collision(known):
    result = check(known=known, obstacle=True, lower=True)
    assert result.status == "COLLISION", result
    assert result.obstacle_id == "certain-mid-fold"
    assert result.material_domain == "GUARANTEED_LOWER_BOUND_ONLY"
    assert set(result.empty_obstacle_ids) == {"source", "receiver"}


def test_unknown_thickness_stays_unverified_and_complete_registry_is_still_required():
    assert check(known=False, lower=True).status == "UNVERIFIED"
    result = check(lower=True, missing=True)
    assert result.status == "UNRESOLVED" and "registry" in result.message


def test_whole_sweep_pruning_cannot_apply_a_permission_that_is_only_valid_late_in_the_fold():
    sweep, material, obstacles = scene()
    obstacles[0] = MaterialObstacle("source", [
        [[20, 5, 0], [60, 5, 0], [60, 5, 10]],
        [[20, 5, 0], [60, 5, 10], [20, 5, 10]],
    ], 0.2, "source")
    box = [[x, y, z] for x in (19, 61) for y in (4.5, 5.5) for z in (-0.5, 0.5)]

    def run(interval):
        return check_fold_clearance(
            sweep, material, obstacles, expected_obstacle_ids=["source", "receiver"],
            lower_bound_only=True,
            allowances=[ContactAllowance("source", "hinge", box, interval,
                                          "Explicit local source crease reservation")],
        )

    late = run((-90, -60))
    assert late.status == "COLLISION", late
    assert late.obstacle_id == "source" and late.witness_angle_deg > -60
    assert not any(row["obstacle_id"] == "source"
                   and row["interaction_inside_whole_fold_permission_triangles"]
                   for row in late.broad_phase_pruning)
    whole = run((-90, 0))
    assert whole.status == "CLEAR", whole
    assert "source" in whole.checked_obstacle_ids
    assert any(row["obstacle_id"] == "source"
               and row["interaction_inside_whole_fold_permission_triangles"] == 2
               for row in whole.broad_phase_pruning)
