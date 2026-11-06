"""Real Qt input tests against a hand-authored read-only projection fixture.

These verify view behavior and signal boundaries, not a new-user study.
"""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from archpapercraft.ui.author_paper import AuthorPaperView

pytestmark = pytest.mark.ui


class ProjectionFixture:
    def __init__(self):
        self.pages = [
            SimpleNamespace(id="page-one", width_mm=210.0, height_mm=297.0, margin_mm=10.0),
            SimpleNamespace(id="page-two", width_mm=210.0, height_mm=297.0, margin_mm=10.0),
        ]
        self.parts = {
            name: SimpleNamespace(id=name, name="Vlastní díl " + name, stale=False)
            for name in ("below", "piece")
        }
        self.placements = {
            name: SimpleNamespace(
                page_id="page-one",
                x_mm=50.0,
                y_mm=60.0,
                rotation_deg=0.0,
                position_locked=False,
                rotation_locked=False,
            )
            for name in self.parts
        }
        outer = [[0.0, 0.0], [60.0, 0.0], [60.0, 50.0], [0.0, 50.0]]
        hole = [[15.0, 15.0], [45.0, 15.0], [45.0, 35.0], [15.0, 35.0]]
        tab = [[60.0, 10.0], [65.0, 12.0], [65.0, 28.0], [60.0, 30.0]]
        self.geometries = {
            "below": {
                "polygons": {"surface-below": [outer]},
                "paths": {"CUT": [{"points": outer, "closed": True}]},
                "edges": [],
                "labels": [],
            },
            "piece": {
                "polygons": {"surface-piece": [outer, hole]},
                "paths": {
                    "CUT": [{"points": outer, "closed": True}, {"points": hole, "closed": True}],
                    "TABS": [{"points": tab, "closed": True}],
                },
                "labels": [],
                "edges": [
                    {
                        "surface_id": "surface-piece",
                        "edge_id": "stable-top-edge",
                        "start": [0.0, 0.0],
                        "end": [60.0, 0.0],
                    },
                    {
                        "surface_id": "surface-piece",
                        "edge_id": "stable-left-edge",
                        "start": [0.0, 50.0],
                        "end": [0.0, 0.0],
                    },
                ],
            },
        }

    def part_geometry(self, identity):
        return deepcopy(self.geometries[identity])


@pytest.fixture
def paper(qtbot):
    project = ProjectionFixture()
    view = AuthorPaperView()
    view.resize(1000, 650)
    qtbot.addWidget(view)
    view.set_project(project)
    view.show()
    qtbot.waitExposed(view)
    qtbot.wait(30)
    view.resetTransform()
    view.scale(2.0, 2.0)
    view.centerOn(245.0, 130.0)
    return view, project


def click_point(view, local, identity="piece"):
    return view.mapFromScene(view.part_items[identity].mapToScene(QPointF(*local)))


def drag(qtbot, view, start, end, release_modifier=Qt.KeyboardModifier.NoModifier, cancel=False):
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    middle = start + (end - start) / 2
    qtbot.mouseMove(view.viewport(), middle, delay=15)
    qtbot.mouseMove(view.viewport(), end, delay=15)
    if cancel:
        qtbot.keyClick(view, Qt.Key.Key_Escape)
    qtbot.mouseRelease(
        view.viewport(), Qt.MouseButton.LeftButton, release_modifier, end
    )
    qtbot.wait(25)


def wheel(view, modifier):
    position = QPointF(view.viewport().rect().center())
    event = QWheelEvent(
        position,
        QPointF(view.viewport().mapToGlobal(position.toPoint())),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        modifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(view.viewport(), event)


def test_hole_picking_reaches_underlying_material_and_tabs_remain_selectable(paper, qtbot):
    view, project = paper
    chosen = []
    view.part_selected.connect(chosen.append)
    assert not view.part_items["piece"].shape().contains(QPointF(30.0, 25.0))
    assert view.part_items["piece"].shape().contains(QPointF(63.0, 20.0))
    qtbot.mouseClick(
        view.viewport(), Qt.MouseButton.LeftButton, pos=click_point(view, (30.0, 25.0))
    )
    assert chosen[-1] == "below"
    qtbot.mouseClick(
        view.viewport(), Qt.MouseButton.LeftButton, pos=click_point(view, (63.0, 20.0))
    )
    assert chosen[-1] == "piece"


def test_drag_emits_one_snapped_anchor_command_without_mutating_project(paper, qtbot):
    view, project = paper
    before = deepcopy(project.__dict__)
    requests = []
    view.placement_changed.connect(lambda *args: requests.append(args))
    start = click_point(view, (5.0, 5.0))
    end = start + QPoint(25, -15)
    a, b = view.mapToScene(start), view.mapToScene(end)
    drag(qtbot, view, start, end)
    assert len(requests) == 1
    identity, payload = requests[0]
    assert identity == "piece" and payload == {
        "page_id": "page-one",
        "x_mm": round(50 + b.x() - a.x()),
        "y_mm": round(60 + b.y() - a.y()),
        "rotation_deg": 0.0,
    }
    assert project.__dict__ == before


def test_alt_on_release_preserves_submillimetre_drag_position(paper, qtbot):
    view, project = paper
    requests = []
    view.placement_changed.connect(lambda *args: requests.append(args))
    start = click_point(view, (5.0, 5.0))
    end = start + QPoint(25, -15)
    a, b = view.mapToScene(start), view.mapToScene(end)
    drag(qtbot, view, start, end, Qt.KeyboardModifier.AltModifier)
    assert len(requests) == 1
    payload = requests[0][1]
    assert payload["x_mm"] == pytest.approx(50 + b.x() - a.x())
    assert payload["y_mm"] == pytest.approx(60 + b.y() - a.y())
    assert payload["x_mm"] != round(payload["x_mm"])


def test_drag_to_second_page_uses_page_under_drop_and_anchor_relative_coordinates(paper, qtbot):
    view, project = paper
    requests = []
    view.placement_changed.connect(lambda *args: requests.append(args))
    start = click_point(view, (5.0, 5.0))
    origin = view.page_origins["page-two"]
    end = view.mapFromScene(origin + QPointF(35.0, 45.0))
    a, b = view.mapToScene(start), view.mapToScene(end)
    drag(qtbot, view, start, end)
    payload = requests[0][1]
    assert payload["page_id"] == "page-two"
    assert payload["x_mm"] == round(50 + b.x() - a.x() - origin.x())
    assert payload["y_mm"] == round(60 + b.y() - a.y() - origin.y())
    assert project.placements["piece"].page_id == "page-one"


def test_escape_restores_preview_and_release_emits_no_command(paper, qtbot):
    view, project = paper
    requests = []
    view.placement_changed.connect(lambda *args: requests.append(args))
    origin = QPointF(view.part_items["piece"].pos())
    start = click_point(view, (5.0, 5.0))
    drag(qtbot, view, start, start + QPoint(50, 20), cancel=True)
    assert view.part_items["piece"].pos() == origin and requests == []
    assert project.placements["piece"].x_mm == 50.0


def test_independent_locks_allow_rotation_of_position_locked_part(paper, qtbot):
    view, project = paper
    placement = project.placements["piece"]
    placement.position_locked = True
    view.set_project(project)
    view.select("piece")
    requests = []
    view.placement_changed.connect(lambda *args: requests.append(args))
    start = click_point(view, (5.0, 5.0))
    drag(qtbot, view, start, start + QPoint(30, 20))
    assert requests == []
    wheel(view, Qt.KeyboardModifier.AltModifier)
    assert len(requests) == 1 and requests[0][1] == {
        "page_id": "page-one",
        "x_mm": 50.0,
        "y_mm": 60.0,
        "rotation_deg": 5.0,
    }
    assert placement.rotation_deg == 0.0
    placement.rotation_locked = True
    view.set_project(project)
    view.select("piece")
    wheel(view, Qt.KeyboardModifier.AltModifier)
    assert len(requests) == 1


def test_rotation_lock_does_not_lock_drag_or_lose_precise_stored_position(paper, qtbot):
    view, project = paper
    placement = project.placements["piece"]
    placement.rotation_locked = True
    placement.x_mm = 50.123456789
    view.set_project(project)
    view.select("piece")
    requests = []
    view.placement_changed.connect(lambda *args: requests.append(args))
    wheel(view, Qt.KeyboardModifier.AltModifier)
    assert requests == []
    start = click_point(view, (5.0, 5.0))
    drag(qtbot, view, start, start + QPoint(20, 0), Qt.KeyboardModifier.AltModifier)
    assert len(requests) == 1 and requests[0][1]["rotation_deg"] == 0.0
    assert project.placements["piece"].x_mm == 50.123456789


def test_tray_placement_survives_redraw_without_repacking(paper):
    view, project = paper
    placement = project.placements["piece"]
    placement.page_id = None
    placement.x_mm = 37.123456789
    placement.y_mm = 59.875
    view.set_project(project)
    expected = view.tray_origin + QPointF(placement.x_mm, placement.y_mm)
    assert view.part_items["piece"].pos() == expected
    view.set_project(project)
    assert view.part_items["piece"].pos() == expected


def test_edge_picking_uses_stable_ids_and_screen_pixel_tolerance(paper, qtbot):
    view, project = paper
    picked = []
    view.edge_selected.connect(lambda *args: picked.append(args))
    part = view.part_items["piece"]
    near = part.mapToScene(QPointF(30.0, -2.5))
    far = part.mapToScene(QPointF(30.0, -5.0))
    assert view.nearest_edge(near) == ("piece", "surface-piece", "stable-top-edge")
    assert view.nearest_edge(far) is None
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(near))
    assert picked[-1] == ("surface-piece", "stable-top-edge")
    view.scale(4, 4)
    assert view.nearest_edge(part.mapToScene(QPointF(30.0, -0.625))) == (
        "piece",
        "surface-piece",
        "stable-top-edge",
    )
    assert view.nearest_edge(part.mapToScene(QPointF(30.0, -1.25))) is None


def test_collision_highlight_respects_holes_and_zoom_does_not_change_document(paper):
    view, project = paper
    before = deepcopy(project.__dict__)
    view.show_issue(SimpleNamespace(part_ids=("below", "piece"), code="MATERIAL_OVERLAP"))
    assert len(view.issue_overlays) == 1
    highlight = view.issue_overlays[0].path()
    assert not highlight.contains(QPointF(80.0, 85.0))
    assert highlight.contains(QPointF(55.0, 65.0))
    wheel(view, Qt.KeyboardModifier.ControlModifier)
    view.select("piece", ("surface-piece", "stable-top-edge"))
    view.focus_part("piece")
    assert project.__dict__ == before


def test_stale_geometry_remains_visible_and_cannot_be_mistaken_for_current(paper):
    view, project = paper
    before = view.part_items["piece"].shape()
    project.parts["piece"].stale = True
    view.set_project(project)
    assert view.part_items["piece"].shape() == before
    assert "neaktuální" in view.part_items["piece"].toolTip()
