"""Independent analytic and adversarial checks for the isolated v1.2 spike."""

import math

import numpy as np
import pytest

from tools.spikes.p2_v12_geometry import (
    Loft,
    Profile,
    approximate_facets,
    base_attachment,
    clipped_area,
    cone_exact,
    cylinder_exact,
    developability_evidence,
    exact_homothetic_flat,
    flat_metric_error,
    roof_attachment,
    segmented_tabs,
    stable_sector_flat,
)

pytestmark = pytest.mark.core


def test_two_coplanar_arcs_are_planar_and_separated_homothetic_arcs_are_conical():
    profile = Profile("circle", 20, 20)
    planar = Loft(profile, profile, 1.5, 0)
    spatial = Loft(profile, profile, 1.5, 30)
    assert developability_evidence(planar)["verdict"] == "EXACT_PLANAR"
    assert developability_evidence(spatial)["verdict"] == "EXACT_CONICAL"
    # Analytic semicircular annulus: outer r30, inner r20.
    assert 0.5 * math.pi * (30**2 - 20**2) == pytest.approx(785.3981633974483)
    assert (
        developability_evidence(spatial)["regularity_proof"]["analytic_jacobian_lower_bound_mm2"]
        > 0
    )


@pytest.mark.parametrize("kind", ["circle", "ellipse", "gothic"])
def test_homothetic_circle_ellipse_gothic_profiles_preserve_the_intrinsic_metric(kind):
    profile = Profile(kind, 20, 30)
    loft = Loft(profile, profile, 1.4, 15)
    evidence = developability_evidence(loft)
    assert evidence["verdict"] == "EXACT_CONICAL"
    assert evidence["max_normalized_triple"] < 1e-12
    assert flat_metric_error(loft)["max_normalized_metric_error"] < 1e-6
    assert flat_metric_error(loft)["max_quad_reported_position_error_mm"] < 1e-6


@pytest.mark.parametrize("kind", ["circle", "ellipse", "gothic"])
def test_rotating_corresponding_profile_points_disproves_exact_development(kind):
    profile = Profile(kind, 20, 30)
    evidence = developability_evidence(Loft(profile, profile, 1.4, 15, 25))
    assert evidence["verdict"] == "NONDEVELOPABLE"
    assert evidence["max_normalized_triple"] > 0.01
    assert evidence["min_K_per_mm2"] < 0


def test_different_nonhomothetic_gothic_profiles_are_not_silently_certified():
    loft = Loft(Profile("gothic", 20, 30), Profile("gothic", 18, 25), 1, 10)
    assert developability_evidence(loft)["verdict"] == "NONDEVELOPABLE"


@pytest.mark.parametrize("u", [0.13, 0.37, 0.88])
def test_twisted_circle_triple_product_matches_closed_form_independent_of_u(u):
    profile = Profile("circle", 20, 20)
    loft = Loft(profile, profile, 1.2, 30, 30)
    # u->theta=pi*(1-u), two differentiated factors contribute pi².
    oracle = -30 * 1.2 * 400 * math.pi**2 * 0.5
    assert loft.differential(u, 0.5)["triple"] == pytest.approx(oracle, rel=1e-12)


def test_gothic_apex_has_two_smooth_spans_and_a_preserved_corner():
    profile = Profile("gothic", 20, 30)
    np.testing.assert_allclose(profile.point(0), [-20, 0, 0], atol=1e-12)
    np.testing.assert_allclose(profile.point(0.5), [0, 30, 0], atol=1e-12)
    np.testing.assert_allclose(profile.point(1), [20, 0, 0], atol=1e-12)
    left, right = profile.derivative(0.5 - 1e-9), profile.derivative(0.5 + 1e-9)
    assert left[1] > 0 and right[1] < 0
    evidence = developability_evidence(Loft(profile, profile, 1.4, 15))
    assert evidence["corner_parameters"] == [0.5]
    assert "crease" in evidence["regularity_proof"]["corner_policy"]


def test_generalized_cylinder_gothic_profile_has_exact_arclength_rectangle_coordinates():
    profile = Profile("gothic", 20, 30)
    flat, error = exact_homothetic_flat(Loft(profile, profile, 1, 15), 1, 1)
    center = (30**2 - 20**2) / (2 * 20)
    oracle_length = 2 * (20 + center) * math.atan2(30, center)
    np.testing.assert_allclose(flat, [oracle_length, 15], atol=1e-8)
    assert error < 1e-8


def test_zero_samples_alone_do_not_grant_a_certificate_and_coincident_profiles_are_degenerate():
    # b is unused by this spike's circular descriptor, so these descriptors
    # happen to trace the same function, but do not match the proved family key.
    loft = Loft(Profile("circle", 20, 20), Profile("circle", 20, 21), 1.2, 30)
    assert developability_evidence(loft)["verdict"] == "UNPROVEN"
    p = Profile("circle", 20, 20)
    assert developability_evidence(Loft(p, p, 1, 0))["verdict"] == "DEGENERATE_OR_SINGULAR"


def test_exact_cylinder_and_conical_band_arcs_radial_edges_and_area():
    cylinder = cylinder_exact(10, 30)
    assert cylinder["width_mm"] == pytest.approx(20 * math.pi)
    assert cylinder["area_mm2"] == pytest.approx(600 * math.pi)
    cone = cone_exact(10, 20, 30)
    assert (cone["inner_radius_mm"], cone["outer_radius_mm"], cone["radial_edge_mm"]) == (
        30,
        60,
        30,
    )
    assert cone["angle_rad"] == pytest.approx(2 * math.pi / 3)
    assert cone["arc0_mm"] == pytest.approx(20 * math.pi)
    assert cone["arc1_mm"] == pytest.approx(40 * math.pi)
    assert cone["area_mm2"] == pytest.approx(900 * math.pi)


def test_full_cone_declares_apex_singularity_and_exact_cylinder_limit_is_finite():
    cone = cone_exact(0, 20, 30)
    assert cone["singular_boundary"] == ["apex"]
    assert cone["area_mm2"] == pytest.approx(600 * math.pi)
    assert cone_exact(10, 10, 30)["mode"] == "CYLINDER"
    tiny = stable_sector_flat(10, 10 + 1e-14, 30, 1, 1)
    np.testing.assert_allclose(tiny, [20 * math.pi, 30], atol=0.01)
    assert np.isfinite(tiny).all()


@pytest.mark.parametrize(
    "r0,r1,s", [(0, 0, 30), (-1, 20, 30), (10, 20, 10), (10, 20, 5), (10, float("nan"), 30)]
)
def test_degenerate_or_nonfinite_cones_rejected(r0, r1, s):
    with pytest.raises(ValueError):
        cone_exact(r0, r1, s)


def test_facet_approximation_declares_error_and_cuts_instead_of_claiming_exact_smooth_development():
    profile = Profile("circle", 20, 20)
    loft = Loft(profile, profile, 1.2, 30, 30)
    rows = [approximate_facets(loft, n, n // 4) for n in (8, 16, 32)]
    assert all(row["mode"] == "EXPLICIT_FACET_APPROXIMATION" for row in rows)
    assert (
        rows[2]["max_sampled_surface_distance_mm"]
        < rows[1]["max_sampled_surface_distance_mm"]
        < rows[0]["max_sampled_surface_distance_mm"]
    )
    for row in rows:
        assert (
            row["max_sampled_surface_distance_mm"]
            <= row["analytic_global_same_parameter_distance_upper_bound_mm"]
        )
        n = row["n_u"]
        chord_oracle = 2 * 20 * n * math.sin(math.pi / (2 * n))
        assert row["boundary_chord_length_mm"] == pytest.approx(chord_oracle, abs=1e-10)
        assert row["triangle_islands"] == 2 * row["n_u"] * row["n_v"]
        assert "NOT a certified" in row["sampling"]


def test_surface_distance_screening_below_tolerance_is_not_mistaken_for_a_bound():
    profile = Profile("circle", 20, 20)
    row = approximate_facets(Loft(profile, profile, 1.2, 30, 30), 64, 16)
    assert row["max_sampled_surface_distance_mm"] < 0.01
    assert row["analytic_global_same_parameter_distance_upper_bound_mm"] > 0.01


def test_roof_wall_attaches_to_true_interior_uv_line_without_changing_the_trim_boundary():
    result = roof_attachment()
    assert result["line_strictly_inside_surface"]
    np.testing.assert_allclose(
        result["attachment_uv_mm"], [[3, 5 * math.sqrt(2)], [103, 5 * math.sqrt(2)]], atol=1e-10
    )
    np.testing.assert_allclose(
        result["mapped_wall_line_world_mm"], [[0, 0, 40], [100, 0, 40]], atol=1e-10
    )
    assert result["maximum_contact_gap_mm"] < 1e-10
    assert result["fake_boundary_distance_mm"] == pytest.approx(5 * math.sqrt(2))
    assert result["available_material_contact_mm2"] == 500
    assert result["outside_boundary_unchanged"]


def test_overhang_change_recomputes_uv_from_semantic_world_contact_and_gap_is_not_glue():
    before, after = roof_attachment(), roof_attachment(8)
    assert before["attachment_uv_mm"] != after["attachment_uv_mm"]
    np.testing.assert_allclose(
        before["mapped_wall_line_world_mm"], after["mapped_wall_line_world_mm"], atol=1e-10
    )
    floating = roof_attachment(normal_gap=1)
    assert floating["maximum_contact_gap_mm"] == pytest.approx(1)
    assert not floating["contact_valid_0_01mm"]
    assert floating["available_material_contact_mm2"] == 0


def test_tab_footprint_is_clipped_by_real_material_and_base_holes_are_subtracted():
    oversize = roof_attachment(tab_width=50)
    assert oversize["nominal_tab_footprint_mm2"] == 5000
    assert oversize["available_material_contact_mm2"] == pytest.approx(100 * 30 * math.sqrt(2))
    assert not oversize["complete_footprint_supported"]
    base = base_attachment()
    assert not base["building_floor_inserted"] and not base["attachment_is_cut_path"]
    assert base["nominal_glue_region_mm2"] == 1600
    assert base["actual_material_glue_region_mm2"] == 1500


@pytest.mark.parametrize("count", [12, 24, 48])
def test_segmented_triangular_tabs_have_explicit_arc_chord_bend_and_adhesion_metrics(count):
    row = segmented_tabs(count=count)
    arc = 40 * math.pi / count - 0.8
    assert row["base_arc_mm"] == pytest.approx(arc)
    assert row["base_chord_mm"] == pytest.approx(40 * math.sin(arc / 40))
    assert row["hinge_sagitta_mm"] == pytest.approx(20 * (1 - math.cos(arc / 40)))
    assert row["maximum_side_length_change_mm"] > 0
    assert row["collision_pairs_over_1e_8_mm2"] == 0
    assert "NOT proof" in row["certificate"]


def test_tabs_balance_curvature_and_contact_and_wrong_bend_or_wide_tabs_fail():
    coarse, middle, fine = (segmented_tabs(count=n) for n in (12, 24, 48))
    assert coarse["hinge_sagitta_mm"] > 0.2 > middle["hinge_sagitta_mm"] > fine["hinge_sagitta_mm"]
    assert (
        fine["nominal_adhesion_excluding_bend_zone_mm2_per_tab"]
        < 8
        < middle["nominal_adhesion_excluding_bend_zone_mm2_per_tab"]
    )
    wide = segmented_tabs(width=25)
    assert wide["collision_pairs_over_1e_8_mm2"] > 0
    wrong = segmented_tabs(bend_deg=80)
    assert wrong["tip_plane_gap_if_rigid_misbent_mm"] == pytest.approx(
        5 * math.sin(math.radians(10))
    )
    assert wrong["fraction_within_0_1mm_contact_band_before_bend_relief"] < 0.25


def test_a_tab_extending_beyond_cap_is_clipped_to_actual_receiver_material():
    row = segmented_tabs(width=45)
    assert row["footprints_extending_outside_cap"] == 24
    assert (
        row["material_limited_adhesion_mm2_per_tab"]
        < row["nominal_adhesion_excluding_bend_zone_mm2_per_tab"]
    )
    assert 0 < row["cap_clip_area_error_upper_bound_mm2_per_tab"] < 0.01


@pytest.mark.parametrize(
    "kwargs",
    [
        {"gap": -0.1},
        {"gap": 100},
        {"width": 0},
        {"count": True},
        {"count": 2},
        {"radius": float("nan")},
        {"bend_zone": 5},
    ],
)
def test_invalid_tab_gap_width_count_and_bend_zone_are_rejected(kwargs):
    with pytest.raises(ValueError):
        segmented_tabs(**kwargs)


def test_convex_contact_intersection_handles_touch_and_true_overlap():
    square = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    assert clipped_area(square, square + [1, 0]) == 0
    assert clipped_area(square, square + [0.25, 0]) == pytest.approx(0.75)


def test_trim_domains_and_unproved_exact_requests_are_rejected():
    p = Profile("circle", 20, 20)
    with pytest.raises(ValueError):
        Loft(p, p, 1, 30).point(0.5, 1.01)
    with pytest.raises(ValueError):
        p.point(-0.1)
    with pytest.raises(ValueError):
        exact_homothetic_flat(Loft(p, p, 1, 30, 25), 0.5, 0.5)
    with pytest.raises(ValueError):
        stable_sector_flat(10, 20, 30, 1.1, 0.5)
