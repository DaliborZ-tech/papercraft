"""Independent native-curve/persistence/UI oracles, never a novice study."""

import copy
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QDialog
from shapely import Polygon

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ValidationError
from archpapercraft.authoring.curves import Curve
from archpapercraft.authoring.profile_curves import _mapped_commands
from archpapercraft.ui.author_curves import CurveEditorDialog
from archpapercraft.ui.author_profile_placement import ProfilePlacementDialog


def quarter(project):
    return project.add_profile(
        segments=[
            {"kind": "arc", "start": [20, 0], "end": [0, 20], "center": [0, 0], "sweep_deg": 90},
            {"kind": "line", "start": [0, 20], "end": [0, 0]},
            {"kind": "line", "start": [0, 0], "end": [20, 0]},
        ]
    )


def circle(project, radius, center=(0, 0)):
    x, y = center
    return project.add_profile(
        segments=[
            {
                "kind": "arc",
                "start": [x + radius, y],
                "end": [x - radius, y],
                "center": [x, y],
                "sweep_deg": 180,
            },
            {
                "kind": "arc",
                "start": [x - radius, y],
                "end": [x + radius, y],
                "center": [x, y],
                "sweep_deg": 180,
            },
        ]
    )


def test_actual_review_import_is_bound_to_the_profiles_worktree():
    import archpapercraft.authoring.profile_curves as actual

    root = Path(__file__).resolve().parents[4]
    assert (
        Path(actual.__file__).resolve() == root / "src/archpapercraft/authoring/profile_curves.py"
    )


def test_p01_actual_cubic_self_crossing_cannot_be_certified_from_its_chord_rectangle():
    p = AuthorProject.new(scale=1)
    pid = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [0, 0.0005],
                "end": [10, 0.0005],
                "control1": [3, -0.001],
                "control2": [7, -0.001],
            },
            {"kind": "line", "start": [10, 0.0005], "end": [10, 0]},
            {"kind": "line", "start": [10, 0], "end": [0, 0]},
            {"kind": "line", "start": [0, 0], "end": [0, 0.0005]},
        ]
    )
    before = p.to_dict()
    with pytest.raises(ValidationError):
        p.add_surface(pid)
    assert p.to_dict() == before


def test_p02_layout_cannot_certify_gap_smaller_than_known_native_outward_bulge():
    p = AuthorProject.new(scale=1)
    profile = p.add_profile(
        segments=[
            {"kind": "line", "start": [0, 0], "end": [10, 0]},
            {
                "kind": "cubic",
                "start": [10, 0],
                "end": [10, 10],
                "control1": [10.0015, 3],
                "control2": [10.0015, 7],
            },
            {"kind": "line", "start": [10, 10], "end": [0, 10]},
            {"kind": "line", "start": [0, 10], "end": [0, 0]},
        ]
    )
    a = p.add_surface(profile)
    b = p.add_surface(p.add_profile([[0, 0], [2, 0], [2, 10], [0, 10]]))
    p.set_placement(p.part_for_surface(a), p.pages[0].id, 40, 40)
    p.set_placement(p.part_for_surface(b), p.pages[0].id, 50.0005, 40)
    # Actual cubic at .5 is x=10+.75*.0015=10.001125; overlap width .000625.
    with pytest.raises(ValidationError):
        p.snapshot()


def test_native_concave_material_hole_is_not_filled_by_tessellation_or_native_restore():
    p = AuthorProject.new(scale=1)
    outer = p.add_profile([[0, 0], [20, 0], [20, 6], [12, 6], [12, 20], [0, 20]])
    hole = circle(p, 2, (5, 5))
    surface = p.add_surface(outer, [hole])
    pid = p.part_for_surface(surface)
    world = p.world_geometry(surface)
    triangles = np.asarray(world["vertices"])[np.asarray(world["triangles"])]
    assert all(not Polygon(t[:, :2]).contains(__import__("shapely").Point(5, 5)) for t in triangles)
    assert all(
        not Polygon(t[:, :2]).contains(__import__("shapely").Point(15, 15)) for t in triangles
    )
    paths = p.parts[pid].paths["CUT"]
    assert len(paths) == 2
    assert sum(c[0] == "A" for path in paths for c in path.get("commands", [])) >= 2
    assert p.curve_projection_reports()[hole]["source_segment_ids"] == [
        s.id for s in p.profiles[hole].segments
    ]


@pytest.mark.parametrize("det", [1, -1])
def test_native_arc_mapping_handles_true_orthogonal_rotation_and_reflection(det):
    curve = Curve((3, 0), (0, 3), "arc", {"center": (0, 0), "sweep_deg": 90}, "own")
    matrix = np.array([[0, -2 * det], [2, 0]])
    commands = _mapped_commands(curve, (matrix, np.array([7, 11])))
    assert commands[0] == ["M", 7, 17]
    arc = commands[1]
    assert arc[0] == "A" and arc[1:3] == [6, 6]
    assert arc[5] == (1 if det == 1 else 0)
    assert arc[-2:] == [7 - 6 * det, 11]


def test_existing_straight_seam_tab_on_curved_material_keeps_actual_arc_cut():
    p = AuthorProject.new(scale=1)
    profile = quarter(p)
    a = p.add_surface(profile)
    rectangle = p.add_profile([[20, 0], [0, 0], [0, -10], [20, -10]])
    b = p.add_surface(rectangle)
    relation = p.connect_edges(
        a, p.profiles[profile].segments[2].id, b, p.profiles[rectangle].segments[0].id
    )
    p.set_tab(relation, owner=a, width_mm=2, taper=1)
    p.recompute()
    assert any(
        c[0] == "A"
        for path in p.parts[p.part_for_surface(a)].paths["CUT"]
        for c in path.get("commands", [])
    )
    assert p.connector_geometry(p.joints[relation].connector_id)["valid"]
    assert len(p.connectors[p.joints[relation].connector_id].tab_ids) == 1


@pytest.mark.parametrize("radius,expected", [(0.1, True), (2, False), (20, False)])
def test_small_detail_uses_native_size_not_chord_density(radius, expected):
    p = AuthorProject.new(scale=1)
    s = p.add_surface(circle(p, radius))
    p.set_placement(p.part_for_surface(s), p.pages[0].id, 60, 60)
    assert any(i.code == "SMALL_DETAIL" for i in p.validate_layout()) == expected


def test_actual_schema3_copy_preservation_survives_new_curve_commands_and_history(tmp_path):
    root = Path(__file__).resolve().parents[4]
    origin = (
        root
        / "docs/p2/implementation/evidence/pc006b-desktop-eb08f97-run06/model-A/model-A.apcraft"
    )
    path = tmp_path / "old.apcraft"
    path.write_bytes(origin.read_bytes())
    before = path.read_bytes()
    c = AuthorController()
    c.open(path)
    source = next(iter(c.project.profiles))
    c.execute("independent copy", lambda p: p.copy_profile(source, factor=1.2))
    c.undo()
    c.redo()
    with pytest.raises(ValidationError):
        c.execute("invalid material", lambda p: p.set_material_profile(thickness_mm=-1))
    with pytest.raises(ValueError):
        c.save(path)
    c.save(tmp_path / "new.apcraft")
    assert path.read_bytes() == before
    assert AuthorProject.load(tmp_path / "new.apcraft").to_dict() == c.project.to_dict()


@pytest.mark.ui
def test_curve_editor_noop_preserves_raw_control_precision_and_cancel_is_staged(qtbot):
    p = AuthorProject.new(scale=1)
    pid = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [0, 0],
                "end": [10, 10],
                "control1": [2.123456789, 3.123456789],
                "control2": [7.123456789, 8.123456789],
            }
        ],
        closed=False,
    )
    segment = p.profiles[pid].segments[0]
    before = copy.deepcopy(p.to_dict())
    dialog = CurveEditorDialog(p, pid, segment.id)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_spec == {"kind": "cubic", "data": segment.data}
    assert p.to_dict() == before
    cancelled = CurveEditorDialog(p, pid, segment.id)
    qtbot.addWidget(cancelled)
    cancelled.kind.setCurrentIndex(cancelled.kind.findData("line"))
    cancelled.reject()
    assert cancelled.result_spec is None and p.to_dict() == before


@pytest.mark.ui
def test_profile_copy_dialog_commits_visible_depth_using_model_units(qtbot):
    p = AuthorProject.new()
    pid = p.add_profile(
        [[0, 0], [20, 0]],
        closed=False,
        plane={"origin": [10, 20, 30], "u": [0.8, 0.6, 0], "v": [0, 0, 1]},
    )
    before = p.to_dict()
    dialog = ProfilePlacementDialog(p, pid, copying=True, unit_factor=1000, unit_label="m")
    qtbot.addWidget(dialog)
    dialog.show()
    field = dialog.fields["depth"]
    field.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClicks(field, "1.25")
    dialog.accept()  # Deliberately no Enter before accepting staged specification.
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert np.allclose(dialog.result_spec["plane"]["origin"], [760, -980, 30])
    assert dialog.result_spec["factor"] == 1.2
    assert p.to_dict() == before


@pytest.mark.ui
def test_curve_editor_invalid_pending_number_stops_without_touching_source(qtbot):
    p = AuthorProject.new()
    pid = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [0, 0],
                "end": [10, 0],
                "control1": [3, 2],
                "control2": [7, 2],
            }
        ],
        closed=False,
    )
    before = p.to_dict()
    dialog = CurveEditorDialog(p, pid, p.profiles[pid].segments[0].id)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.details.setChecked(True)
    field = dialog.fields["control1_x"]
    field.setFocus()
    qtbot.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(field, Qt.Key.Key_Backspace)
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert dialog.result_spec is None and dialog.feedback.text()
    assert p.to_dict() == before
