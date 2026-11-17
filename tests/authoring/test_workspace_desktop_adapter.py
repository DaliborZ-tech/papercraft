"""Existing driver inputs on real offscreen widgets, without starting a desktop proof."""

import ast
import copy
import importlib.util
from pathlib import Path

import pytest
import test_workspace as workspace_cases
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QGroupBox, QScrollArea, QTreeWidgetItemIterator

window = workspace_cases.window
ROOT = Path(__file__).resolve().parents[2]


def component_driver(window):
    """Load the actual checked-in input methods; do not execute run_windows."""
    path = ROOT / "tools/authoring/workspace_desktop_steps.py"
    spec = importlib.util.spec_from_file_location("workspace_desktop_steps_component", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = ast.parse((ROOT / "tools/authoring/desktop_b_proof.py").read_text("utf-8"))
    original = next(node for node in ast.walk(source)
                    if isinstance(node, ast.ClassDef) and node.name == "Driver")
    selected = {"visible", "click", "select", "observed_action"}
    original.body = [node for node in original.body if getattr(node, "name", None) in selected]
    original.bases = [ast.Name(id="WorkspaceDesktopSteps", ctx=ast.Load())]

    def check(condition, message):
        assert condition, message

    events = []
    namespace = dict(globals(), WorkspaceDesktopSteps=module.WorkspaceDesktopSteps,
                     QPoint=QPoint, QTest=QTest, QCheckBox=QCheckBox, QGroupBox=QGroupBox,
                     QScrollArea=QScrollArea, QTreeWidgetItemIterator=QTreeWidgetItemIterator,
                     check=check, log=lambda event, **values: events.append((event, values)))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[original], type_ignores=[])),
                 "actual_desktop_driver_input_subset", "exec"), namespace)
    driver = namespace["Driver"]()
    driver.w, driver.check, driver.log = window, check, namespace["log"]
    driver.action_counts = {}
    for name, action in window.actions.items():
        action.triggered.connect(lambda _checked=False, key=name: driver.observed_action(key))
    return driver


def test_input_adapter_changes_contexts_and_sketch_through_actual_buttons(window):
    import archpapercraft.ui.author_window as source

    assert Path(source.__file__).resolve() == ROOT / "src/archpapercraft/ui/author_window.py"
    workspace_cases.arrange_rectangle(window)
    driver = component_driver(window)
    before = copy.deepcopy(window.project.to_dict())
    depth = len(window.controller._undo)
    driver.workspace("Export")
    driver.visible(window.vertex_x)
    assert window.workspace_context == "Modelování"
    driver.visible(window.paper_x)
    assert window.workspace_context == "Stránky"
    driver.visible(window.edge_choice)
    assert window.workspace_context == "Spoje a rozvin"
    driver.visible(window.sketch)
    assert window.workspace_context == "Modelování" and window.sketch.isVisible()
    assert window.project.to_dict() == before and len(window.controller._undo) == depth


def test_input_adapter_types_inline_name_as_a_real_reversible_command(window, qtbot):
    sid = workspace_cases.arrange_rectangle(window)
    driver = component_driver(window)
    before = copy.deepcopy(window.project.to_dict())
    driver.name_house_surface("north", sid)
    assert window.project.surfaces[sid].name == "Severni stena"
    qtbot.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert window.project.to_dict() == before


def test_input_adapter_home_routes_to_visible_active_view_without_geometry_edit(window):
    workspace_cases.arrange_rectangle(window)
    driver = component_driver(window)
    before = copy.deepcopy(window.project.to_dict())
    driver.workspace("Stránky")
    window.paper.scale(2, 2)
    window.viewport.span = 123456
    driver.view_home(window.paper)
    assert window.viewport.span == 123456
    paper_transform = window.paper.transform()
    driver.workspace("Spoje a rozvin")
    driver.view_home(window.viewport)
    assert window.viewport.span != 123456 and window.paper.transform() == paper_transform
    assert window.project.to_dict() == before


def test_input_adapter_stops_at_rejected_pending_context_change(window):
    workspace_cases.arrange_rectangle(window)
    driver = component_driver(window)
    before = copy.deepcopy(window.project.to_dict())
    window.vertex_x.setFocus()
    window.vertex_x.lineEdit().setText("-")
    with pytest.raises(AssertionError, match="Actual workspace button"):
        driver.workspace("Stránky")
    assert window.workspace_context == "Modelování"
    assert window.vertex_x.lineEdit().text() == "-" and window.project.to_dict() == before
    window.vertex_x.lineEdit().setText("0")
