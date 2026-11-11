"""Curved B3 source retained beside bounded planar material; backend evidence."""

import copy
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, load_project
from archpapercraft.authoring.segmented_surface import SegmentationError


def gothic_target():
    project = AuthorProject.new(scale=1)
    profiles = []
    for width, height, depth in ((20, 30, 0), (18, 25, 10)):
        centre = (height * height - width * width) / (2 * width)
        sweep = math.degrees(math.atan2(height, -centre)) - 180
        profiles.append(
            project.add_profile(
                segments=[
                    {
                        "kind": "arc",
                        "start": [-width, 0],
                        "end": [0, height],
                        "data": {"center": [centre, 0], "sweep_deg": sweep},
                    },
                    {
                        "kind": "arc",
                        "start": [0, height],
                        "end": [width, 0],
                        "data": {"center": [-centre, 0], "sweep_deg": sweep},
                    },
                    {"kind": "line", "start": [width, 0], "end": [-width, 0]},
                ],
                plane={"origin": [0, 0, depth], "u": [1, 0, 0], "v": [0, 1, 0]},
            )
        )
    a, b = profiles
    target = project.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": x.id,
                "second_segment_id": y.id,
                "first_interval": [0, 1],
                "second_interval": [0, 1],
            }
            for x, y in zip(project.profiles[a].segments, project.profiles[b].segments)
        ],
    )
    return project, target, a, b


def _analytic_gothic(width, height, patch, parameter):
    """Test-side circle rotation; no production curve evaluator/certifier."""
    if patch == 2:
        return np.array([width * (1 - 2 * parameter), 0])
    centre = (height * height - width * width) / (2 * width)
    omega = math.atan2(height, -centre) - math.pi
    origin = np.array([centre if patch == 0 else -centre, 0])
    start = np.array([-width, 0] if patch == 0 else [0, height])
    x, y = start - origin
    sine, cosine = math.sin(omega * parameter), math.cos(omega * parameter)
    return origin + [x * cosine - y * sine, x * sine + y * cosine]


@pytest.fixture(scope="module")
def curved_state():
    p, target, a, b = gothic_target()
    preview = p.preview_segmented_variant(target)
    assert preview["can_confirm"], preview
    variant = p.add_segmented_variant(target, preview_digest=preview["preview_digest"])
    return p.to_dict(), target, a, b, variant, preview


def test_nonhomothetic_gothic_source_remains_rejected_while_material_is_approximate(curved_state):
    data, target, a, b, variant, preview = curved_state
    p = AuthorProject.from_dict(copy.deepcopy(data))
    assert p.loft_status(target)["status"] == "REJECTED"
    proof = p.segmented_variant_status(variant)
    assert proof["mode"] == proof["status"] == "APPROXIMATE"
    math_report = proof["certificate"]["math"]
    assert math_report["family"] == "INTERVAL_CURVED_RULED_TRIANGLE_ISLANDS"
    assert math_report["counts"]["triangles"] == 96
    assert len(proof["paired_seams"]) == 96
    assert len(p.parts) == 97 and p.part_for_surface(target) not in p.material_part_ids()
    assert [r["id"] for r in proof["source_binding"]["profiles"]] == [a, b]
    assert [s.kind for s in p.profiles[a].segments] == ["arc", "arc", "line"]
    assert all(
        "bilinear_coefficients_model_mm_exact" not in patch for patch in math_report["patches"]
    )
    material = proof["certificate"]["material_frame"]
    bound = float(Fraction(material["max_target_to_material_deviation_paper_mm_exact"]))
    assert 0.18 < bound < 0.25
    assert proof["certificate"]["embedding"]["status"] == "CERTIFIED"
    assert preview["preview_geometry"]["mesh_role"].startswith("DETACHED_ACTUAL_MATERIAL_FRAME")


def test_actual_curved_material_vertices_and_interiors_follow_independent_circles(curved_state):
    data, _, _, _, variant, preview = curved_state
    p = AuthorProject.from_dict(copy.deepcopy(data))
    v = p.segmented_variants[variant]
    bound = float(
        Fraction(v.certificate["material_frame"]["max_target_to_material_deviation_paper_mm_exact"])
    )
    for row, raw in zip(v.triangle_bindings, v.certificate["math"]["triangles"]):
        actual = p.profiles[row["profile_id"]].plane.world(p.profiles[row["profile_id"]].points)
        uv = np.array(
            [[float(Fraction(x)) for x in point] for point in row["parameter_vertices_exact"]]
        )
        patch = raw["patch_index"]
        for weights in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0.2, 0.3, 0.5), (0.6, 0.2, 0.2)):
            u, w = np.array(weights) @ uv
            first = _analytic_gothic(20, 30, patch, u)
            second = _analytic_gothic(18, 25, patch, u)
            source = np.r_[(1 - w) * first + w * second, 10 * w]
            assert np.linalg.norm(np.array(weights) @ actual - source) <= bound
    mesh = preview["preview_geometry"]
    for triangle, row in zip(mesh["triangles"], v.triangle_bindings):
        assert {tuple(mesh["vertices"][i]) for i in triangle} == {
            tuple(point) for point in p.world_geometry(row["surface_id"])["vertices"]
        }


def test_curved_generation_manual_batch_two_pages_save_open_and_source_staleness(
    curved_state, tmp_path
):
    data, target, a, _, variant, _ = curved_state
    p = AuthorProject.from_dict(copy.deepcopy(data))
    p.add_page()
    p.set_placements(
        {
            row["part_id"]: {
                "page_id": p.pages[i // 48].id,
                "x_mm": 25 + i % 8 * 20,
                "y_mm": 25 + (i // 8) % 6 * 24,
                "rotation_deg": 0,
                "position_locked": i == 0,
                "rotation_locked": i == 0,
            }
            for i, row in enumerate(p.segmented_variants[variant].triangle_bindings)
        }
    )
    assert not p.validate_layout()
    path = tmp_path / "own-gothic-approximate.apcraft"
    p.save(path)
    reopened = load_project(path)
    assert reopened.to_dict() == p.to_dict()
    snapshot = reopened.snapshot()
    assert [len(page["parts"]) for page in snapshot["pages"]] == [48, 48]
    assert snapshot["coverage"]["reference_surface_ids"] == [target]
    assert snapshot["construction_checks"]["reference_targets"][target]["status"] == "REJECTED"
    assert all(
        part["flattening"]["mode"] == "APPROXIMATE"
        for page in snapshot["pages"]
        for part in page["parts"]
    )
    layouts = copy.deepcopy(reopened.placements)
    arc = reopened.profiles[a].segments[0]
    new_data = copy.deepcopy(arc.data)
    # A legal source profile plane change needs no internal curve reconstruction.
    reopened.profiles[a].plane.origin[0] += 0.1
    assert reopened.segmented_variant_status(variant)["status"] == "STALE"
    with pytest.raises(ValidationError):
        reopened.snapshot()
    reopened.recompute()
    assert reopened.placements == layouts
    assert reopened.segmented_variant_status(variant)["status"] == "STALE"
    assert reopened.profiles[a].segments[0].data == new_data


def test_strict_curved_budget_blocks_confirmation_without_partial_material():
    p, target, _, _ = gothic_target()
    before = p.to_dict()
    preview = p.preview_segmented_variant(target, max_deviation_mm=0.000001, max_cells=8)
    assert preview["status"] == "UNRESOLVED" and not preview["can_confirm"]
    with pytest.raises(SegmentationError):
        p.add_segmented_variant(target, preview_digest="no", max_deviation_mm=0.000001, max_cells=8)
    assert p.to_dict() == before


def test_historical_line_generation_opens_unchanged_with_curved_backend():
    path = (
        Path(__file__).parents[2]
        / "docs/p2/implementation/evidence/pc008-domain-95fa2c7/backend-fixture.apcraft"
    )
    p = load_project(path)
    assert len(p.segmented_variants) == 1 and len(p.material_part_ids()) == 64
    variant = next(iter(p.segmented_variants))
    assert p.segmented_variant_status(variant)["status"] == "APPROXIMATE"
    assert [len(page["parts"]) for page in p.snapshot()["pages"]] == [32, 32]
