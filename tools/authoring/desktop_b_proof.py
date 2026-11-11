"""Opt-in full A and mixed-part Windows proof through real authoring widgets.

First compile/review this driver. Run only on the coordinated desktop:
python tools/authoring/desktop_b_proof.py --output <fresh-dir> --expected-sha <pin>
--oracle-only checks the independently specified dimensions without launching Qt.
This is technical automation, never novice-user or physical-build evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCALE = 0.01
LENGTH_TOL = 0.01  # Paper mm; distinct from area tolerance in paper mm².
AREA_TOL = 0.01


def oracle():
    """Hand-specified construction; no production geometry helper is imported."""
    slope = math.hypot(3500, 3500)
    return {
        "scale": SCALE,
        "building_model_mm": {"length": 10000, "width": 6000, "wall": 4000, "ridge": 7000},
        "initial_roof_paper_mm": {"length": 108, "half_slope": slope * SCALE},
        "roof_wall_trace_paper_mm": math.hypot(500, 500) * SCALE,
        "changed_south_eave_model_mm": 800,
        "changed_south_slope_paper_mm": math.hypot(3800, 3800) * SCALE,
        "changed_trace_from_eave_paper_mm": math.hypot(800, 800) * SCALE,
        "areas_paper_mm2": {
            "long_wall": 100 * 40,
            "gable_wall": 60 * 40 + 60 * 30 / 2,
            "base": 130 * 100,
            "brace_outer": 60 * 30 + 60 * 30 / 2,
            "brace_hole": 20 * 15,
            "brace_net": 60 * 30 + 60 * 30 / 2 - 20 * 15,
            "soffit": 80 * 10,
            "initial_half_roof": 108 * slope * SCALE,
            "changed_south_roof": 108 * math.hypot(3800, 3800) * SCALE,
        },
        "authored_top_tabs": {
            "hinge_length_mm": 100,
            "count": 4,
            "gap_mm": 1,
            "base_length_mm": 100 / 4 - 1,
            "triangle_width_mm": 5,
            "triangle_area_mm2": 24 * 5 / 2,
            "custom_outline_mm": [
                [0, 0],
                [24, 0],
                [24, 2],
                [14, 2],
                [14, 4],
                [10, 4],
                [10, 2],
                [0, 2],
            ],
            "custom_area_mm2": 24 * 2 + (14 - 10) * 2,
            "active_count": 3,
            "active_area_mm2": 2 * (24 * 5 / 2) + 24 * 2 + (14 - 10) * 2,
            "existing_bottom_area_mm2": 90 * 2 * (1 + 0.6) / 2,
            "wall_cut_area_mm2": 100 * 40 + 176 + 144,
        },
        "mixed": {
            "initial_rise_model_mm": 3000,
            "changed_rise_model_mm": 3500,
            "initial_slope_model_mm": math.hypot(3000, 3000),
            "changed_slope_model_mm": math.hypot(3000, 3500),
            "changed_angle_deg": math.degrees(math.atan2(3500, 3000)),
            "page_number": 2,
            "anchor_paper_mm": [60, 60],
            "rotation_deg": 30,
            "wall_page_points_paper_mm": [
                [
                    60 + x * math.cos(math.pi / 6) - y * math.sin(math.pi / 6),
                    60 + x * math.sin(math.pi / 6) + y * math.cos(math.pi / 6),
                ]
                for x, y in [(0, 0), (100, 0), (100, 40), (0, 40)]
            ],
        },
    }


def area(points):
    """Translation-relative shoelace, independent of production material geometry."""
    origin = points[0]
    shifted = [[x - origin[0], y - origin[1]] for x, y in points]
    return (
        abs(
            math.fsum(a[0] * b[1] - a[1] * b[0] for a, b in zip(shifted, shifted[1:] + shifted[:1]))
        )
        / 2
    )


def svg_line_loops(path):
    """Independent reader for this strictly planar proof's native M/L/Z cuts."""
    tokens = re.findall(r"[MLZ]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", path)
    loops, current, index = [], [], 0
    while index < len(tokens):
        op = tokens[index]
        index += 1
        if op in ("M", "L"):
            if op == "M":
                current = []
            current.append([float(tokens[index]), float(tokens[index + 1])])
            index += 2
        elif op == "Z":
            loops.append(current)
            current = []
        else:
            raise AssertionError(f"Unexpected nonplanar SVG path token {op}")
    return loops


def pdf_stroked_loops(reader):
    """Read actual PDF CTM/path operators; return stroked closed loops in page mm."""
    from pypdf.generic import ContentStream

    result = []
    for page_index, page in enumerate(reader.pages):
        matrix, stack, current, closed = [1, 0, 0, 1, 0, 0], [], [], []
        height = float(page.mediabox.height) * 25.4 / 72
        for operands, operation in ContentStream(page.get_contents(), reader).operations:
            if operation == b"q":
                stack.append(matrix[:])
            elif operation == b"Q":
                matrix = stack.pop()
            elif operation == b"cm":
                a, b, c, d, e, f = matrix
                u, v, w, x, y, z = map(float, operands)
                matrix = [
                    a * u + c * v,
                    b * u + d * v,
                    a * w + c * x,
                    b * w + d * x,
                    a * y + c * z + e,
                    b * y + d * z + f,
                ]
            elif operation in (b"m", b"l"):
                if operation == b"m":
                    current = []
                x, y = map(float, operands)
                a, b, c, d, e, f = matrix
                current.append(
                    [(a * x + c * y + e) * 25.4 / 72, height - (b * x + d * y + f) * 25.4 / 72]
                )
            elif operation == b"h":
                closed.append(current)
                current = []
            elif operation in (b"S", b"s", b"f", b"f*", b"B", b"B*", b"b", b"b*", b"n"):
                if operation in (b"S", b"s"):
                    result.extend((page_index, loop) for loop in closed)
                current, closed = [], []
    return result


def source_files():
    paths = [
        *ROOT.joinpath("src").rglob("*.py"),
        *ROOT.joinpath("tools/authoring").glob("*.py"),
        ROOT / "pyproject.toml",
    ]
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_windows(output, expected_sha, fixture="all"):
    # Imported only after explicit CLI entry and fresh-directory/source guards.
    # The shared virtualenv may have an editable install pointing at another
    # worktree. Bind actual imports, not just Git/hash metadata, to this source.
    sys.path.insert(0, str(ROOT / "src"))
    import native_dialogs
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    from PySide6.QtCore import QPoint, QPointF, QRectF, QSettings, Qt, QTimer
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QGroupBox,
        QMenu,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QToolBar,
    )

    from archpapercraft import __version__ as application_version
    from archpapercraft import app as entry
    from archpapercraft.ui import author_window
    from archpapercraft.ui.author_export_job import ExportProgressDialog

    if Path(author_window.__file__).resolve() != (
        ROOT / "src/archpapercraft/ui/author_window.py"
    ).resolve():
        raise ValueError("Actual application module is outside the pinned worktree")

    sha = git("rev-parse", "HEAD")
    if sha != expected_sha:
        raise ValueError(f"Expected reviewed source {expected_sha}, actual HEAD {sha}")
    hashes = source_files()
    changed = git(
        "diff", "--name-only", "HEAD", "--", "src", "pyproject.toml",
        "tools/authoring",
    )
    tracked = set(git("ls-files").splitlines())
    if changed or set(hashes) - tracked:
        raise ValueError("Native proof requires committed application and harness sources")
    output.mkdir(parents=True)  # Must not already exist.
    report = {
        "status": "RUNNING",
        "source_sha": sha,
        "requested_fixture": fixture,
        "fixture_status": {"model-A": "NOT_RUN", "mixed-part": "NOT_RUN",
                           "curves-planar": "NOT_RUN", "loft-B1": "NOT_RUN",
                           "loft-B2": "NOT_RUN", "loft-Bezier": "NOT_RUN"},
        "source_status_at_start": git("status", "--porcelain=v1"),
        "source_files_sha256": hashes,
        "actual_application_module": str(Path(author_window.__file__).resolve()),
        "platform": platform.platform(),
        "python": sys.version,
        "application_version": application_version,
        "pid": os.getpid(),
        "oracle": oracle(),
        "versions": {
            package: importlib.metadata.version(package)
            for package in ["PySide6", "numpy", "shapely", "pypdf", "reportlab", "PyOpenGL"]
        },
        "evidence_kind": "actual_app_main_QTest_widgets_own_PID_native_dialogs",
        "new_user": "NOT_RUN",
        "new_user_reason": "Owner confirmed no actual new participant is currently available",
        "physical_build": "NOT_RUN",
        "AU19": "NOT_RUN_PC010",
        "started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "steps": [],
        "inputs": [],
        "dialogs": [],
        "negative_cases": [],
    }
    settings = QSettings(str(output / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("tips_enabled", True)
    started, windows, failures, expected_messages = time.monotonic(), [], [], []
    exit_code = [1]

    def write_report():
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["files_sha256"] = {
            p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "results.json"
        }
        (output / "results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )

    def check(condition, message):
        if not condition or failures:
            raise AssertionError(
                f"{message}; unexpected dialogs={failures}" if failures else message
            )

    def log(name, **details):
        report["inputs"].append({"event": name, **details})

    def step(name, **details):
        check(True, name)
        report["steps"].append({"name": name, "status": "PASS", **details})
        write_report()

    def close_messages():
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, ExportProgressDialog):
            now = time.monotonic()
            records = report.setdefault("export_progress", [])
            if not records or records[-1]["dialog_identity"] != id(dialog):
                records.append({"dialog_identity": id(dialog), "samples": 0,
                                "max_observed_gap_seconds": 0, "phases": [], "last_at": now})
            record = records[-1]
            record["max_observed_gap_seconds"] = max(
                record["max_observed_gap_seconds"], now - record["last_at"])
            record["last_at"], record["samples"] = now, record["samples"] + 1
            text = dialog.description.text()
            if not record["phases"] or record["phases"][-1]["text"] != text:
                record["phases"].append({"text": text, "elapsed_seconds": now-started})
                dialog.screen().grabWindow(int(dialog.winId())).save(str(
                    output / f"export-progress-{len(records)}-{len(record['phases'])}.png"))
        if isinstance(dialog, QMessageBox):
            data = {
                "kind": "real_QMessageBox",
                "title": dialog.windowTitle(),
                "text": dialog.text(),
            }
            report["dialogs"].append(data)
            if expected_messages and expected_messages[0] == dialog.windowTitle():
                expected_messages.pop(0)
                button = dialog.button(QMessageBox.StandardButton.Ok)
                check(button is not None, "Expected real message lacks OK")
                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            else:
                failures.append(data)
                dialog.reject()
        if time.monotonic() - started > 900:
            report.update(status="FAIL", error="900-second driver deadline", failures=failures)
            write_report()
            QApplication.instance().exit(1)

    from loft_desktop_steps import LoftDesktopSteps

    class Driver(LoftDesktopSteps):
        def __init__(self, window):
            self.w = window
            self.check, self.step, self.log = check, step, log
            self.roles = {}
            self.authored_top = None
            self.action_counts = {}
            for name, action in window.actions.items():
                action.triggered.connect(
                    lambda _checked=False, key=name: self.observed_action(key)
                )

        def observed_action(self, name):
            self.action_counts[name] = self.action_counts.get(name, 0) + 1
            log("observed_QAction_triggered", action=name, count=self.action_counts[name])

        def visible(self, widget):
            for header, box in self.w.sections.values():
                if box.isAncestorOf(widget) and not header.isChecked():
                    self.click(header)
            ancestor = widget.parentWidget()
            while ancestor:
                if isinstance(ancestor, QGroupBox) and ancestor.isCheckable():
                    if not ancestor.isChecked():
                        QTest.mouseClick(ancestor, Qt.MouseButton.LeftButton, pos=QPoint(9, 12))
                ancestor = ancestor.parentWidget()
            ancestor = widget.parentWidget()
            while ancestor and not isinstance(ancestor, QScrollArea):
                ancestor = ancestor.parentWidget()
            if ancestor:
                ancestor.ensureWidgetVisible(widget)
            QTest.qWait(35)
            check(
                widget.isVisible() and widget.isEnabled(),
                f"Required widget hidden/disabled: {widget.objectName() or type(widget).__name__}",
            )
            return widget

        def click(self, widget):
            self.visible(widget)
            point = QPoint(8, widget.height() // 2) if isinstance(widget, QCheckBox) else None
            if point is None:
                QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
            else:
                QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=point)
            QTest.qWait(55)

        def number(self, widget, value):
            self.visible(widget)
            target = widget.window()
            target.raise_()
            target.activateWindow()
            QTest.qWait(80)
            widget.setFocus()
            QTest.qWait(20)
            focus = QApplication.focusWidget()
            log("numeric_focus_context", window_active=target.isActiveWindow(),
                focused_class=type(focus).__name__ if focus else None,
                owns_focus=focus is widget or (focus is not None and widget.isAncestorOf(focus)))
            check(target.isActiveWindow() and
                  (focus is widget or (focus is not None and widget.isAncestorOf(focus))),
                  "Numeric input target did not receive actual active-window focus")
            QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
            text = f"{value:.6f}" if isinstance(value, float) else str(value)
            text = text.replace(".", widget.locale().decimalPoint())
            QTest.keyClicks(widget, text)
            # Tab commits numeric text without activating a dialog's default OK.
            QTest.keyClick(widget, Qt.Key.Key_Tab)
            QTest.qWait(65)
            log("numeric_after_tab", expected=value, interpreted_value=widget.value(),
                visible_text=widget.text(), still_focused=widget.hasFocus())
            check(
                math.isclose(widget.value(), value, abs_tol=max(0.000001, 1e-10 * abs(value))),
                f"Numeric input lost: {value} != {widget.value()}",
            )
            log(
                "numeric_widget",
                object=widget.objectName(),
                value=value,
                typed_text=text,
                locale=widget.locale().name(),
            )

        def combo(self, widget, index):
            check(index >= 0 and index < widget.count(), "Combo option absent")
            self.visible(widget).setFocus()
            QTest.keyClick(widget, Qt.Key.Key_F4)
            QTest.qWait(35)
            view = widget.view()
            check(view.isVisible(), "Actual combo popup did not open")
            QTest.keyClick(view, Qt.Key.Key_Home)
            for _ in range(index):
                QTest.keyClick(view, Qt.Key.Key_Down)
            QTest.keyClick(view, Qt.Key.Key_Return)
            QTest.qWait(60)
            check(widget.currentIndex() == index, "Popup selection failed")

        def data(self, widget, value):
            index = next((i for i in range(widget.count()) if widget.itemData(i) == value), -1)
            self.combo(widget, index)

        def shortcut(self, key, shift=False):
            # A native Windows dialog may release activation. Sending a key to
            # an inactive QWidget does not prove its window QAction fired.
            self.w.raise_()
            self.w.activateWindow()
            QTest.qWait(80)
            self.w.setFocus()
            modifiers = Qt.KeyboardModifier.ControlModifier
            if shift:
                modifiers |= Qt.KeyboardModifier.ShiftModifier
            sequence = QKeySequence(modifiers.value | key.value)
            expected = [
                name for name, action in self.w.actions.items()
                if action.shortcut().matches(sequence) == QKeySequence.SequenceMatch.ExactMatch
            ]
            before = {name: self.action_counts.get(name, 0) for name in expected}
            active = QApplication.activeWindow()
            focus = QApplication.focusWidget()
            log("shortcut_context", sequence=sequence.toString(), expected_actions=expected,
                window_active=self.w.isActiveWindow(),
                active_window_title=active.windowTitle() if active else None,
                focus_class=type(focus).__name__ if focus else None)
            check(active is self.w and self.w.isActiveWindow(),
                  "Shortcut target was not active after explicit native window activation")
            QTest.keyClick(self.w, key, modifiers)
            QTest.qWait(85)
            observed = {name: [before[name], self.action_counts.get(name, 0)] for name in expected}
            check(all(after == previous+1 for previous, after in observed.values()),
                  "Actual shortcut did not trigger its expected window QAction: " + repr(observed))

        def action(self, name):
            action = self.w.actions[name]
            for toolbar in self.w.findChildren(QToolBar):
                button = toolbar.widgetForAction(action)
                if button:
                    self.click(button)
                    return
            menu = next(obj for obj in action.associatedObjects() if isinstance(obj, QMenu))
            top = self.w.menuBar().actionGeometry(menu.menuAction()).center()
            QTest.mouseClick(self.w.menuBar(), Qt.MouseButton.LeftButton, pos=top)
            QTest.qWait(40)
            QTest.mouseClick(
                menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center()
            )
            QTest.qWait(70)

        def modal(self, launch, edit):
            errors = []

            def drive():
                dialog = QApplication.activeModalWidget()
                try:
                    check(isinstance(dialog, QDialog), "Expected actual application dialog absent")
                    edit(dialog)
                    check(not dialog.isVisible(), "Driver did not accept/cancel actual dialog")
                except Exception:
                    errors.append(traceback.format_exc())
                    if dialog:
                        details = {"kind": "failed_authoring_dialog", "title": dialog.windowTitle()}
                        if hasattr(dialog, "specification"):
                            details["actual_specification"] = dialog.specification()
                        report["dialogs"].append(details)
                        self.capture("FAIL-authoring-dialog", dialog)
                        dialog.reject()

            QTimer.singleShot(220, drive)
            launch()
            check(not errors, "Dialog proof failed: " + "\n".join(errors))
            check(True, "Modal command")

        def ok(self, dialog):
            buttons = dialog.findChild(QDialogButtonBox)
            self.click(buttons.button(QDialogButtonBox.StandardButton.Ok))

        def capture(self, name, dialog=None):
            QTest.qWait(150)
            window = dialog or self.w
            check(
                window.screen()
                .grabWindow(int(window.winId()))
                .save(str(output / f"{name}-desktop.png")),
                "Desktop capture failed",
            )
            check(
                self.w.viewport.grabFramebuffer().save(str(output / f"{name}-opengl.png")),
                "OpenGL capture failed",
            )

        def select(self, sid):
            item = next(
                self.w.tree.topLevelItem(i)
                for i in range(self.w.tree.topLevelItemCount())
                if self.w.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == sid
            )
            self.w.tree.scrollToItem(item)
            QTest.mouseClick(
                self.w.tree.viewport(),
                Qt.MouseButton.LeftButton,
                pos=self.w.tree.visualItemRect(item).center(),
            )
            QTest.qWait(55)
            check(self.w.selected_surface == sid, "Tree selection failed")

        def rectangle(self, role, width, height, plane="XY", position=None, rotation=None):
            self.data(self.w.plane, plane)
            before = set(self.w.project.surfaces)

            def edit(dialog):
                fields = dialog.findChildren(QDoubleSpinBox)
                check(len(fields) == 2, "Rectangle dialog fields changed")
                self.number(fields[0], width)
                self.number(fields[1], height)
                self.ok(dialog)

            self.modal(lambda: self.action("rectangle"), edit)
            sid = next(iter(set(self.w.project.surfaces) - before))
            self.roles[role] = sid
            if position or rotation:
                self.transform(sid, position or [0, 0, 0], rotation or [0, 0, 0])
            log("own_rectangle", role=role, surface_id=sid, model_mm=[width, height], plane=plane)
            return sid

        def sketch_points(self, sketch, points, *, finish=True):
            # View-only framing is explicit; no model, input or signal is injected.
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            margin = max(max(xs) - min(xs), max(ys) - min(ys), 100) * 0.15
            sketch.fitInView(
                QRectF(
                    min(xs) - margin,
                    -max(ys) - margin,
                    max(xs) - min(xs) + 2 * margin,
                    max(ys) - min(ys) + 2 * margin,
                ),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            log("view_only_camera_frame", points=points)
            QTest.qWait(45)
            for x, y in points:
                pixel = sketch.mapFromScene(QPointF(x, -y))
                check(sketch.viewport().rect().contains(pixel), "Sketch pixel outside view")
                QTest.mouseClick(sketch.viewport(), Qt.MouseButton.LeftButton, pos=pixel)
                QTest.qWait(25)
            if finish:
                QTest.keyClick(sketch, Qt.Key.Key_Return)
                QTest.qWait(75)

        def polygon(self, role, points, plane="YZ", hole=False):
            self.data(self.w.plane, plane)
            before = set(self.w.project.surfaces)
            self.shortcut(Qt.Key.Key_H if hole else Qt.Key.Key_L)
            check(self.w.sketch.drawing, "UI sketch did not start")
            self.sketch_points(self.w.sketch, points)
            check(not self.w.sketch.drawing, "Sketch did not become actual surface/hole")
            sid = (
                self.w.selected_surface
                if hole
                else next(iter(set(self.w.project.surfaces) - before))
            )
            if not hole:
                self.roles[role] = sid
            log(
                "own_clicked_hole" if hole else "own_clicked_polygon",
                role=role,
                surface_id=sid,
                requested_model_mm=points,
            )
            return sid

        def transform(self, sid, position, rotation):
            self.select(sid)
            for field, value in zip(self.w.transform_fields, [*position, *rotation]):
                self.number(field, value)

        def vertex(self, sid, index, x=None, y=None):
            self.select(sid)
            self.combo(self.w.vertex_choice, index)
            if x is not None:
                self.number(self.w.vertex_x, x)
            if y is not None:
                self.number(self.w.vertex_y, y)

        def edge(self, sid, index):
            self.select(sid)
            self.combo(self.w.edge_choice, index)
            return self.w.selected_edge

        def fold(self, sid_a, index_a, sid_b, index_b, angle):
            before = set(self.w.project.joints)
            self.edge(sid_a, index_a)
            self.click(self.w.connect_button)
            self.select(sid_b)

            def edit(dialog):
                self.number(dialog.findChild(QDoubleSpinBox), angle)
                self.ok(dialog)

            self.modal(lambda: self.combo(self.w.edge_choice, index_b), edit)
            jid = next(iter(set(self.w.project.joints) - before))
            # Receiving part is the visible selection: retain A as the material frame.
            self.select(sid_a)
            self.data(self.w.connectors_panel.relationship, ("joint", jid))
            self.data(self.w.joint_mode, "fold")
            self.shortcut(Qt.Key.Key_R)
            check(
                self.w.project.surfaces[sid_a].part_id == self.w.project.surfaces[sid_b].part_id,
                "Actual fold UI did not create one shared material part",
            )
            log("actual_edgepair_fold", joint_id=jid, angle_deg=angle)
            return jid

        def attach(self, source, edge_index, target, *, direction=1, interval=None, region=None):
            before = set(self.w.project.attachments)
            self.edge(source, edge_index)

            def edit(dialog):
                self.data(dialog.receiver, target)
                self.data(dialog.mode, "contact")
                self.data(dialog.direction, direction)
                if interval:
                    self.number(dialog.start_fraction, interval[0] * 100)
                    self.number(dialog.end_fraction, interval[1] * 100)
                if region:
                    self.click(dialog.draw_region)
                    self.sketch_points(dialog.sketch, region)
                log("actual_attachment_specification", specification=dialog.specification())
                check(
                    dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(),
                    "Actual contact dialog rejected existing physical contact: "
                    + dialog.feedback.text(),
                )
                log(
                    "actual_attachment_preview",
                    source=source,
                    target=target,
                    interval=interval,
                    region=region,
                    feedback=dialog.feedback.text(),
                )
                self.ok(dialog)

            self.modal(lambda: self.shortcut(Qt.Key.Key_J), edit)
            return next(iter(set(self.w.project.attachments) - before))

        def relation(self, source, kind, rid):
            self.select(source)
            self.data(self.w.connectors_panel.relationship, (kind, rid))

        def tab(self, source, aid, width=2, *, band=False):
            self.relation(source, "attachment", aid)
            before = set(self.w.project.parts)

            def edit(dialog):
                self.number(dialog.width, width)
                self.ok(dialog)

            self.modal(
                lambda: self.click(
                    self.w.connectors_panel.band if band else self.w.connectors_panel.edit
                ),
                edit,
            )
            if band:
                new = set(self.w.project.parts) - before
                check(len(new) == 1, "Pásek must create a real material part")
                return next(iter(new))
            return self.w.project.attachments[aid].connector_id

        def author_top_tabs(self, south, aid):
            expected = report["oracle"]["authored_top_tabs"]
            self.relation(south, "attachment", aid)

            def split(dialog):
                self.number(dialog.width, 5)
                self.data(dialog.shape, "triangle")
                self.number(dialog.count, 4)
                self.number(dialog.gap, 1)
                self.ok(dialog)

            self.modal(lambda: self.click(self.w.connectors_panel.edit), split)
            cid = self.w.project.attachments[aid].connector_id
            geometry = self.w.project.connector_geometry(cid)
            ids = list(self.w.project.connectors[cid].tab_ids)
            check(
                len(ids) == 4 and len(set(ids)) == 4, "Split tabs need four semantic stable UUIDs"
            )
            self.near(
                geometry["hinge_length_mm"],
                expected["hinge_length_mm"],
                "full selected source hinge",
            )
            for tab in geometry["all_tabs"]:
                self.near(tab["base_length_mm"], expected["base_length_mm"], "split base length")
            for tab in geometry["tabs"]:
                self.near(tab["nominal_area_mm2"], 60, "initial triangle area", tolerance=AREA_TOL)
            self.data(self.w.connectors_panel.tabs, ids[1])

            def disable(dialog):
                check(dialog.enabled.isChecked(), "Newly split tab unexpectedly off")
                self.click(dialog.enabled)
                self.ok(dialog)

            self.modal(lambda: self.click(self.w.connectors_panel.edit_tab), disable)
            self.data(self.w.connectors_panel.tabs, ids[2])

            def custom(dialog):
                self.data(dialog.shape, "custom")
                self.click(dialog.draw)
                check(dialog.canvas.points == [[0, 0], [24, 0]], "Drawing lost fixed 24mm hinge")
                for x, y in expected["custom_outline_mm"][2:]:
                    point = dialog.canvas.mapFromScene(QPointF(x, -y))
                    check(
                        dialog.canvas.viewport().rect().contains(point), "Tab sketch point clipped"
                    )
                    QTest.mouseClick(dialog.canvas.viewport(), Qt.MouseButton.LeftButton, pos=point)
                    QTest.qWait(35)
                QTest.keyClick(dialog.canvas, Qt.Key.Key_Return)
                check(
                    len(dialog.canvas.points) == 8,
                    "Mouse drawing did not create eight tab vertices",
                )
                log(
                    "actual_drawn_tab_before_numeric_refinement",
                    tab_id=ids[2],
                    paper_mm=copy.deepcopy(dialog.canvas.points),
                )
                # The sketch is real mouse input, followed by the author's exact
                # numeric refinement. Pixel approximation is not the expected oracle.
                for index, (x, y) in enumerate(expected["custom_outline_mm"][2:], 2):
                    self.data(dialog.vertex, index)
                    self.number(dialog.vertex_x, x)
                    self.number(dialog.vertex_y, y)
                check(
                    dialog.outline == expected["custom_outline_mm"], "Precise stepped outline lost"
                )
                self.capture("A-positive-stepped-tab-drawn-and-refined", dialog)
                self.ok(dialog)

            self.modal(lambda: self.click(self.w.connectors_panel.edit_tab), custom)
            self.authored_top = {"connector_id": cid, "ids": ids, "attachment_id": aid}
            self.audit_authored_tabs()
            step(
                "A_positive_split_triangles_individual_off_and_drawn_custom_tab",
                connector_id=cid,
                tab_ids=ids,
                disabled_id=ids[1],
                custom_id=ids[2],
                active_area_mm2=176,
                existing_bottom_area_mm2=144,
                wall_material_mm2=4000,
                wall_cut_mm2=4320,
            )

        def audit_authored_tabs(self):
            expected, record = report["oracle"]["authored_top_tabs"], self.authored_top
            cid, ids = record["connector_id"], record["ids"]
            connector = self.w.project.connectors[cid]
            check(connector.tab_ids == ids, "Authored tab IDs changed across command/save/reopen")
            check(connector.tab_overrides[ids[1]]["enabled"] is False, "Individual off state lost")
            custom = connector.tab_overrides[ids[2]]
            check(
                custom["shape"] == "custom"
                and custom["outline_mm"] == expected["custom_outline_mm"],
                "Drawn custom tab did not remain editable after persistence",
            )
            geometry = self.w.project.connector_geometry(cid)
            check(
                [t["tab_id"] for t in geometry["tabs"]] == [ids[0], ids[2], ids[3]],
                "Active split tab coverage differs from stable author selection",
            )
            for tab, nominal in zip(geometry["tabs"], [60, 56, 60]):
                self.near(tab["nominal_area_mm2"], nominal, "individual authored area", AREA_TOL)
                self.near(
                    tab["available_area_mm2"], nominal, "actual receiver contact area", AREA_TOL
                )
            self.near(
                sum(tab["nominal_area_mm2"] for tab in geometry["tabs"]),
                176,
                "all active upper tabs",
                AREA_TOL,
            )
            self.near(
                self.net_area(self.roles["south"]), 4000, "unchanged wall material area", AREA_TOL
            )
            part_id = self.w.project.surfaces[self.roles["south"]].part_id
            cut = self.w.project.part_geometry(part_id)["paths"]["CUT"]
            self.near(
                sum(area(path["points"]) for path in cut if path["closed"]),
                4320,
                "wall CUT including unchanged144mm2 bottom connector",
                AREA_TOL,
            )

        def place(self, sid, page_index, x, y, angle=0):
            self.select(sid)
            self.combo(self.w.page_choice, page_index + 1)
            for field, value in zip(
                (self.w.paper_x, self.w.paper_y, self.w.paper_angle), [x, y, angle]
            ):
                self.number(field, value)
            placement = self.w.project.placements[self.w.selected_part]
            check(
                [placement.page_id, placement.x_mm, placement.y_mm, placement.rotation_deg]
                == [self.w.project.pages[page_index].id, x, y, angle],
                "Manual placement lost",
            )

        def add_page(self):
            self.click(next(b for b in self.w.findChildren(QPushButton) if b.text() == "Přidat A4"))

        def net_area(self, sid):
            loops = self.w.project.part_geometry(self.w.project.surfaces[sid].part_id)["polygons"][
                sid
            ]
            return area(loops[0]) - sum(area(loop) for loop in loops[1:])

        def near(self, actual, expected, label, tolerance=LENGTH_TOL):
            check(
                abs(actual - expected) <= tolerance,
                f"Independent oracle {label}: actual={actual}, "
                f"expected={expected}, tol={tolerance}",
            )
            return {"label": label, "actual": actual, "expected": expected, "tolerance": tolerance}

        def world_boundary(self, sid):
            return [edge["start"] for edge in self.w.project.world_geometry(sid)["boundary"]]

        def wall_page_points(self, wall):
            pid = self.w.project.surfaces[wall].part_id
            points = self.w.project.part_geometry(pid)["polygons"][wall][0]
            place = self.w.project.placements[pid]
            theta = math.radians(place.rotation_deg)
            return [
                [
                    place.x_mm + x * math.cos(theta) - y * math.sin(theta),
                    place.y_mm + x * math.sin(theta) + y * math.cos(theta),
                ]
                for x, y in points
            ]

        def linked_pick(self):
            self.action("focus_all")
            picked = None
            for sid in self.w.project.surfaces:
                geometry = self.w.project.world_geometry(sid)
                for triangle in geometry["triangles"]:
                    center = [
                        sum(geometry["vertices"][i][axis] for i in triangle) / 3
                        for axis in range(3)
                    ]
                    pixel = self.w.viewport.project_points([center])[0]
                    point = QPoint(round(pixel[0]), round(pixel[1]))
                    if (
                        self.w.viewport.rect().contains(point)
                        and self.w.viewport.surface_at(point) == sid
                    ):
                        QTest.mouseClick(self.w.viewport, Qt.MouseButton.LeftButton, pos=point)
                        QTest.qWait(70)
                        check(
                            self.w.selected_surface == sid, "Actual 3D pick did not select source"
                        )
                        check(
                            self.w.paper.selected_part == self.w.project.surfaces[sid].part_id,
                            "Actual 3D selection did not reach paper",
                        )
                        picked = {
                            "surface_id": sid,
                            "world_probe_mm": center,
                            "pixel": [point.x(), point.y()],
                        }
                        break
                if picked:
                    break
            check(picked is not None, "No visible 3D material probe could be clicked")
            step("actual_assembled_3D_pick_links_paper", **picked)

        def paper_drag(self, sid, *, locked):
            self.select(sid)
            self.action("focus")
            pid = self.w.project.surfaces[sid].part_id
            item = self.w.paper.part_items[pid]
            bounds = item.material.boundingRect()
            point = next(
                (
                    QPointF(
                        bounds.left() + bounds.width() * x / 10,
                        bounds.top() + bounds.height() * y / 10,
                    )
                    for x in range(1, 10)
                    for y in range(1, 10)
                    if item.material.contains(
                        QPointF(
                            bounds.left() + bounds.width() * x / 10,
                            bounds.top() + bounds.height() * y / 10,
                        )
                    )
                ),
                None,
            )
            check(point is not None, "No real paper material point to drag")
            pixel = self.w.paper.mapFromScene(item.mapToScene(point))
            before = copy.deepcopy(self.w.project.placements[pid])
            QTest.mousePress(self.w.paper.viewport(), Qt.MouseButton.LeftButton, pos=pixel)
            QTest.mouseMove(self.w.paper.viewport(), pixel + QPoint(18, 10), delay=70)
            QTest.mouseRelease(
                self.w.paper.viewport(), Qt.MouseButton.LeftButton, pos=pixel + QPoint(18, 10)
            )
            QTest.qWait(120)
            after = self.w.project.placements[pid]
            check(
                (after == before)
                if locked
                else math.hypot(after.x_mm - before.x_mm, after.y_mm - before.y_mm) > 0.001,
                "Actual paper drag did not respect the requested lock state",
            )
            check(
                self.w.selected_surface == self.w.project.parts[pid].frame.root_surface_id,
                "Actual paper selection did not link to root surface",
            )
            step(
                "actual_locked_paper_drag" if locked else "actual_unlocked_manual_paper_drag",
                part_id=pid,
                anchor_before=[before.x_mm, before.y_mm],
                anchor_after=[after.x_mm, after.y_mm],
            )

        def acknowledge_physical_warnings(self):
            # No guessed code is silently added. New adapter warnings require its
            # explicit reviewed API; digital errors never reach the acknowledgement.
            allowed = {"MATERIAL_CLEARANCE_UNVERIFIED"}
            issues = [issue for issue in self.w.project.validate_layout() if not issue.acknowledged]
            check(
                all(i.severity == "warning" and i.code in allowed for i in issues),
                "Unexpected issue blocks complete digital fixture: "
                + repr([(i.code, i.message) for i in issues]),
            )
            accepted = []
            for issue in issues:
                item = next(
                    self.w.issues.item(i)
                    for i in range(self.w.issues.count())
                    if self.w.issues.item(i).data(Qt.ItemDataRole.UserRole) == issue.id
                )
                self.w.issues.scrollToItem(item)
                QTest.mouseClick(
                    self.w.issues.viewport(),
                    Qt.MouseButton.LeftButton,
                    pos=self.w.issues.visualItemRect(item).center(),
                )
                QTest.qWait(45)
                self.click(self.w.ack_button)
                check(
                    next(
                        i for i in self.w.project.validate_layout() if i.id == issue.id
                    ).acknowledged,
                    "Explicit physical warning acknowledgement was not persisted",
                )
                accepted.append(
                    {
                        "id": issue.id,
                        "code": issue.code,
                        "message": issue.message,
                        "meaning": "digital_only_physical_NOT_RUN",
                    }
                )
            check(
                not any(i.severity == "error" for i in self.w.project.validate_layout()),
                "A digital error cannot be acknowledged as a physical limitation",
            )
            return accepted

        def camera_after_reopen(self, name):
            QTest.qWait(160)  # Allow the real deferred project-frame command to finish.
            view = self.w.paper
            viewport = view.viewport().rect()
            centers = []
            for pid, place in self.w.project.placements.items():
                if place.page_id is None:
                    continue
                item = view.part_items[pid]
                pixel_bounds = view.mapFromScene(item.sceneBoundingRect()).boundingRect()
                center = view.mapFromScene(item.mapToScene(item.boundingRect().center()))
                check(
                    viewport.contains(center) and viewport.contains(pixel_bounds),
                    "Native reopen failed to show all placed material without Home: " + pid,
                )
                centers.append(
                    {
                        "part_id": pid,
                        "center_pixel": [center.x(), center.y()],
                        "bounds_pixel": [
                            pixel_bounds.x(),
                            pixel_bounds.y(),
                            pixel_bounds.width(),
                            pixel_bounds.height(),
                        ],
                    }
                )
            check(len(centers) == len(self.w.project.parts), "Camera proof omitted a material part")
            self.capture(f"{name}-reopened-auto-frame-all-material")

            def camera():
                matrix = view.transform()
                center = view.mapToScene(view.viewport().rect().center())
                return (
                    [
                        matrix.m11(),
                        matrix.m12(),
                        matrix.m21(),
                        matrix.m22(),
                        matrix.dx(),
                        matrix.dy(),
                    ],
                    [center.x(), center.y()],
                )

            initial = camera()
            point = view.viewport().rect().center()
            window_point = view.viewport().mapTo(self.w, point)
            QTest.wheelEvent(
                self.w.windowHandle(),
                QPointF(window_point),
                QPoint(0, 120),
                stateKey=Qt.KeyboardModifier.ControlModifier,
            )
            QTest.qWait(60)
            QTest.mousePress(view.viewport(), Qt.MouseButton.MiddleButton, pos=point)
            QTest.mouseMove(view.viewport(), point + QPoint(17, 11), delay=70)
            QTest.mouseRelease(
                view.viewport(), Qt.MouseButton.MiddleButton, pos=point + QPoint(17, 11)
            )
            authored = camera()
            check(authored != initial, "Actual wheel/pan did not change the view camera")
            state = copy.deepcopy(self.w.project.to_dict())
            self.shortcut(Qt.Key.Key_R)  # Real ordinary UI refresh, already current material.
            check(camera() == authored, "Ordinary refresh reset the author's zoom/pan")
            check(
                self.w.project.to_dict() == state and not self.w.controller.dirty,
                "Camera-only proof or redundant recompute changed the reopened document",
            )
            step(
                f"{name}_reopen_auto_frame_and_refresh_preserves_authored_camera",
                all_centers_visible_without_Home=centers,
                authored_camera=authored,
            )

        def finish(self, name):
            accepted = self.acknowledge_physical_warnings()
            directory = output / name
            directory.mkdir()
            (directory / "export").mkdir()
            path = directory / f"{name}.apcraft"
            native_dialogs.schedule_path(path, report["dialogs"])
            self.shortcut(Qt.Key.Key_S)
            check(path.is_file() and not self.w.controller.dirty, "Native save failed")
            state = self.w.project.to_dict()
            self.shortcut(Qt.Key.Key_N)
            check(not self.w.project.surfaces, "New project did not clear the saved fixture")
            native_dialogs.schedule_path(path, report["dialogs"])
            self.shortcut(Qt.Key.Key_O)
            check(self.w.project.to_dict() == state, "Native reopen changed authorial state")
            self.camera_after_reopen(name)
            if name == "model-A":
                self.audit_authored_tabs()
            snapshot = self.w.project.snapshot()  # Observation only; actual export remains UI.
            (directory / "snapshot.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf8"
            )
            self.capture(f"{name}-reopened")
            expected_messages.extend(["Vektorový export", "Export dokončen"])
            native_dialogs.schedule_path(directory / "export", report["dialogs"])
            self.shortcut(Qt.Key.Key_E)
            check(not expected_messages, "Actual export confirmations did not finish")
            svgs = sorted((directory / "export").glob("*.svg"))
            pdf = PdfReader(directory / "export/model.pdf")
            check(
                len(svgs) == len(pdf.pages) == len(snapshot["pages"]), "Vector page count mismatch"
            )
            actual_parts = {
                g.attrib["data-part-id"]
                for svg in svgs
                for g in ET.parse(svg).getroot().iter()
                if "data-part-id" in g.attrib
            }
            check(actual_parts == set(self.w.project.parts), "SVG material coverage mismatch")
            for page in pdf.pages:
                check(not page["/Resources"].get("/XObject", {}), "PDF has raster/image XObjects")
                check(
                    any(op == b"l" for _, op in ContentStream(page.get_contents(), pdf).operations),
                    "PDF lacks actual vector lines",
                )
                self.near(float(page.mediabox.width) * 25.4 / 72, 210, "PDF A4 width")
            if name == "model-A":
                expected_tabs = report["oracle"]["authored_top_tabs"]
                south_part = self.w.project.surfaces[self.roles["south"]].part_id
                south_group = next(
                    g
                    for svg in svgs
                    for g in ET.parse(svg).getroot().iter()
                    if g.attrib.get("data-part-id") == south_part
                )
                south_cuts = next(g for g in south_group if g.attrib.get("data-role") == "CUT")
                south_cut_loops = [
                    loop for path in south_cuts for loop in svg_line_loops(path.attrib["d"])
                ]
                self.near(
                    sum(area(loop) for loop in south_cut_loops),
                    expected_tabs["wall_cut_area_mm2"],
                    "SVG south cut material+all tabs",
                    AREA_TOL,
                )
                tabs_group = next(g for g in south_group if g.attrib.get("data-role") == "TABS")
                exported_tabs = [
                    loop for path in tabs_group for loop in svg_line_loops(path.attrib["d"])
                ]
                actual_areas = sorted(area(loop) for loop in exported_tabs)
                check(len(actual_areas) == 4, "SVG omitted active top or existing bottom tab")
                for actual, expected in zip(actual_areas, [56, 60, 60, 144]):
                    self.near(actual, expected, "actual SVG authored tab area", AREA_TOL)
                check(
                    any(
                        len(loop) == 8 and abs(area(loop) - 56) <= AREA_TOL
                        for loop in exported_tabs
                    ),
                    "Actual SVG lost the eight-vertex stepped outline",
                )
                pdf_south = [
                    loop
                    for page_index, loop in pdf_stroked_loops(pdf)
                    if page_index == 0 and abs(area(loop) - 4320) <= AREA_TOL
                ]
                check(
                    len(pdf_south) == 1,
                    "PDF omitted/duplicated the south wall cut with4320mm2 material",
                )
                step(
                    "A_authored_split_off_custom_tabs_persist_in_SVG_and_PDF",
                    connector_id=self.authored_top["connector_id"],
                    tab_ids=self.authored_top["ids"],
                    svg_active_tab_areas_mm2=actual_areas,
                    pdf_cut_area_mm2=area(pdf_south[0]),
                )
                brace_part = self.w.project.surfaces[self.roles["brace"]].part_id
                group = next(
                    g
                    for svg in svgs
                    for g in ET.parse(svg).getroot().iter()
                    if g.attrib.get("data-part-id") == brace_part
                )
                cuts = next(g for g in group if g.attrib.get("data-role") == "CUT")
                svg_loops = [loop for path in cuts for loop in svg_line_loops(path.attrib["d"])]
                check(
                    any(abs(area(loop) - 300) <= AREA_TOL for loop in svg_loops),
                    "Independent SVG reader did not find actual 20×15mm brace opening cut",
                )
                # Brace is deliberately unrotated at[30,30] on page3, so its hole
                # has independent page bounds[50,40]→[70,55], with no raster masking.
                expected_bounds = [50, 40, 70, 55]
                pdf_holes = []
                for page_index, loop in pdf_stroked_loops(pdf):
                    if page_index == 2 and len(loop) == 4:
                        bounds = [
                            min(p[0] for p in loop),
                            min(p[1] for p in loop),
                            max(p[0] for p in loop),
                            max(p[1] for p in loop),
                        ]
                        if max(abs(a - b) for a, b in zip(bounds, expected_bounds)) <= LENGTH_TOL:
                            self.near(
                                area(loop), 300, "PDF actual hole cut area", tolerance=AREA_TOL
                            )
                            pdf_holes.append(loop)
                check(
                    len(pdf_holes) == 1, "Independent PDF reader missed/duplicated brace hole cut"
                )
                step("A_true_hole_preserved_in_both_vector_outputs", pdf_page_hole=pdf_holes[0])
            if name == "curves-planar":
                self.audit_curve_vectors(directory, svgs, pdf)
            if name.startswith("loft-"):
                self.audit_loft_vectors(name, directory, svgs, pdf)
            step(
                f"{name}_native_save_new_reopen_export",
                pages=len(svgs),
                parts=sorted(actual_parts),
                unfold_mode="EXACT",
                exact_scope=("certified ruled/planar family; no physical claim"
                             if name.startswith("loft-") else
                             "piecewise planar material; no curved-surface or physical claim"),
                digital_only_acknowledgements=accepted,
            )

        def audit_curve_vectors(self, directory, svgs, pdf):
            from vector_curve_oracle import pdf_stroked_areas, svg_signed_area

            expected = {
                self.roles["curve_facade"]: [400 * math.pi, 12000],
                self.roles["curve_panel"]: [2188],
                self.roles["curve_receiver"]: [800],
            }
            observations = []
            for svg in svgs:
                for group in ET.parse(svg).getroot():
                    if "data-part-id" not in group.attrib:
                        continue
                    pid = group.attrib["data-part-id"]
                    sid = next(sid for sid in expected
                               if self.w.project.surfaces[sid].part_id == pid)
                    cut = next(node for node in group if node.get("data-role") == "CUT")
                    values = sorted(abs(svg_signed_area(node.attrib["d"])) for node in cut)
                    check(len(values) == len(expected[sid]), "Native SVG lost a curve or hole loop")
                    for value, wanted in zip(values, sorted(expected[sid])):
                        observations.append(self.near(
                            value, wanted, "actual native SVG area", 0.01,
                        ))
                    text = " ".join(node.attrib["d"] for node in cut)
                    if sid == self.roles["curve_facade"]:
                        check("A " in text and len(cut) == 2, "Circle hole lost native SVG arcs")
                    elif sid == self.roles["curve_panel"]:
                        check("C " in text, "Bezier source became a polygon in SVG")
            values = sorted(value for _, value in pdf_stroked_areas(pdf))
            wanted = sorted(value for entries in expected.values() for value in entries)
            check(len(values) == len(wanted), "PDF omitted or duplicated actual CUT loops")
            manifest = json.loads((directory / "export/.author-export.json").read_text())
            delta = manifest["pdf_geometry_precision"]["combined_position_error_bound_mm"]
            check(0 <= delta <= 0.01, "PDF output exceeds the agreed paper-mm position budget")
            for value, target in zip(values, wanted):
                # A mathematically valid positional tube is NOT permission to
                # relax the separate normative area acceptance (V02).
                tolerance = max(0.01, 1e-6 * target)
                observations.append(self.near(value, target, "actual PDF Green area", tolerance))
            expected_net = 12000 - 400 * math.pi
            observations.append(self.near(
                values[-1] - values[1], expected_net, "PDF net material excluding real hole",
                max(0.01, 1e-6 * expected_net),
            ))
            check(manifest["actual_curve_output_checks"]["pdf"]["status"] == "VALID",
                  "Actual staged PDF manufacturing proof absent")
            step("native_curves_hole_tab_and_independent_vector_integrals",
                 expected_areas_mm2=wanted, observations=observations,
                 physical_build="NOT_RUN", novice_participants=0)

        def curves_planar(self):
            self.data(self.w.units, 1)
            self.number(self.w.scale_field, 100)
            facade = self.rectangle("curve_facade", 12000, 10000, "XZ")
            self.data(self.w.curve_mode, "arc")
            self.shortcut(Qt.Key.Key_H)
            self.sketch_points(self.w.sketch, [
                [4000, 5000], [6000, 3000], [8000, 5000], [6000, 7000], [4000, 5000],
            ])
            check(not self.w.sketch.drawing, "Two-arc hole did not become actual material void")
            hole = self.w.project.surfaces[facade].hole_profile_ids
            check(len(hole) == 1 and len(self.w.project.profiles[hole[0]].segments) == 2,
                  "Circular hole source is not two native authored arcs")
            self.capture("curves-native-circle-hole")
            self.data(self.w.plane, "XY")
            self.data(self.w.curve_mode, "cubic")
            previous = set(self.w.project.surfaces)
            self.shortcut(Qt.Key.Key_L)
            self.sketch_points(self.w.sketch, [[0, 0], [2000, 3000], [6000, 3000], [8000, 0]],
                               finish=False)
            self.data(self.w.curve_mode, "line")
            self.sketch_points(self.w.sketch, [[8000, -1000], [0, -1000], [0, 0]])
            check(len(set(self.w.project.surfaces) - previous) == 1,
                  "Mixed cubic/line outline did not create one own surface")
            panel = next(iter(set(self.w.project.surfaces) - previous))
            self.roles["curve_panel"] = panel
            self.select(panel)
            self.combo(self.w.curve_choice, 0)
            original = copy.deepcopy(self.w.project.to_dict())

            def cancel(dialog):
                self.click(dialog.details)
                self.number(dialog.fields["control1_y"], 3500)
                self.click(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))

            self.modal(lambda: self.action("edit_curve"), cancel)
            check(self.w.project.to_dict() == original, "Curve edit Cancel changed source")

            def edit(dialog):
                self.click(dialog.details)
                self.number(dialog.fields["control1_y"], 3500)
                self.ok(dialog)

            self.modal(lambda: self.action("edit_curve"), edit)
            check(self.w.project.to_dict() != original, "Numeric curve edit did not apply")
            self.shortcut(Qt.Key.Key_Z)
            check(self.w.project.to_dict() == original, "Curve edit Undo lost source or layout")
            receiver = self.rectangle("curve_receiver", 8000, 1000, "XY", [0, -2000, 0])
            aid = self.attach(panel, 2, receiver, direction=1)
            cid = self.tab(panel, aid, width=2)
            check(self.w.project.connectors[cid].enabled, "Actual straight tab was not created")
            self.shortcut(Qt.Key.Key_R)
            self.add_page()
            self.place(facade, 0, 20, 20)
            self.place(panel, 1, 40, 60, 17)
            self.place(receiver, 1, 40, 120)
            self.paper_drag(panel, locked=False)
            self.place(panel, 1, 40, 60, 17)
            self.click(self.w.position_lock)
            self.click(self.w.rotation_lock)
            self.paper_drag(panel, locked=True)
            self.linked_pick()
            self.capture("curves-authored-manual-layout")
            step("native_own_arcs_bezier_edit_cancel_undo_tab_and_manual_pages",
                 source_surface_ids=self.roles, circle_hole_profile=hole[0],
                 connector_id=cid, preset_used=False)
            self.finish("curves-planar")

        def author_commands(self, south):
            """Native user input, impact confirmation and reversible experimentation."""
            def rename(dialog):
                for field, text in (
                    (dialog.project_name, "Own open architectural model A"),
                    (dialog.surface_name, "South wall"),
                    (dialog.part_name, "South wall with authored tabs"),
                ):
                    self.visible(field).setFocus()
                    QTest.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
                    QTest.keyClicks(field, text)
                self.ok(dialog)

            self.modal(lambda: self.action("rename"), rename)
            check(self.w.project.surfaces[south].name == "South wall", "Typed name lost")
            self.capture("A-native-own-names")
            scrap = self.rectangle("temporary_scrap", 1000, 1000)
            profile = self.w.project.surfaces[scrap].profile_id
            state = copy.deepcopy(self.w.project.to_dict())

            def cancel(dialog):
                self.capture("A-native-delete-impact", dialog)
                self.click(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))

            self.modal(lambda: self.action("delete_part"), cancel)
            check(self.w.project.to_dict() == state, "Cancel removed or changed material")
            self.modal(lambda: self.action("delete_part"), self.ok)
            check(scrap not in self.w.project.surfaces, "Confirmed removal failed")
            check(profile in self.w.project.profiles, "Removal destroyed reusable source sketch")
            self.shortcut(Qt.Key.Key_Z)
            check(self.w.project.to_dict() == state, "Removal undo failed to restore source")
            self.shortcut(Qt.Key.Key_Y)
            check(scrap not in self.w.project.surfaces, "Removal redo failed")
            self.roles.pop("temporary_scrap")
            self.select(south)
            state = copy.deepcopy(self.w.project.to_dict())

            def paper(dialog):
                check(not dialog.known.isChecked(), "Default paper thickness falsely known")
                self.ok(dialog)

            self.modal(lambda: self.action("material"), paper)
            check(self.w.project.to_dict() == state, "Unchanged paper settings mutated document")
            step("native_own_names_delete_cancel_confirm_undo_redo_material_noop",
                 preserved_source_profile=profile,
                 physical_material="UNKNOWN; no physical clearance certificate")

        def building(self):
            self.data(self.w.units, 1)
            self.number(self.w.scale_field, 100)
            o = report["oracle"]
            south = self.rectangle("south", 10000, 4000, "XZ")
            self.author_commands(south)
            check(
                len(self.w.project.surfaces) == 1
                and len(self.w.project.world_geometry(south)["triangles"]) == 2,
                "Single open wall failed to create an ordinary valid material surface",
            )
            north = self.rectangle("north", 10000, 4000, "XZ", [0, 6000, 0])
            gable = [[0, 0], [6000, 0], [6000, 4000], [3000, 7000], [0, 4000]]
            west = self.polygon("west_gable", gable)
            east = self.polygon("east_gable", gable)
            self.transform(east, [10000, 0, 0], [0, 0, 0])
            roof_south = self.rectangle(
                "roof_south",
                10800,
                math.hypot(3500, 3500),
                position=[-400, -500, 3500],
                rotation=[45, 0, 0],
            )
            roof_north = self.rectangle(
                "roof_north",
                10800,
                math.hypot(3500, 3500),
                position=[-400, 3000, 7000],
                rotation=[-45, 0, 0],
            )
            self.fold(roof_south, 2, roof_north, 0, 90)
            base = self.rectangle("base", 13000, 10000, position=[-1500, -2000, 0])
            brace = self.polygon(
                "brace", [[0, 0], [6000, 0], [6000, 3000], [3000, 6000], [0, 3000]]
            )
            self.polygon(
                "brace_hole", [[2000, 1000], [4000, 1000], [4000, 2500], [2000, 2500]], hole=True
            )
            self.transform(brace, [5000, 0, 1000], [0, 0, 0])
            soffit = self.rectangle(
                "soffit", 8000, 1000, position=[1000, 4500, 5500], rotation=[-45, 0, 0]
            )
            self.data(self.w.front_side, "inside")
            check(
                self.w.project.parts[self.w.selected_part].front_side == "inside",
                "Soffit printed-side UI choice did not persist",
            )
            south_roof_aid = self.attach(south, 2, roof_south)
            north_roof_aid = self.attach(north, 2, roof_north, direction=-1)
            self.tab(south, south_roof_aid)
            self.tab(north, north_roof_aid)
            # Both gables remain independently authored open pieces with live roof contacts.
            for wall in [west, east]:
                self.attach(wall, 2, roof_north)
                self.attach(wall, 3, roof_south)
            for wall in [south, north, west, east]:
                aid = self.attach(
                    wall,
                    0,
                    base,
                    interval=[0.05, 0.95],
                    # A real drawn region includes a deliberate1mm paper margin
                    # around the wall footprint; pixel clicks cannot promise exact
                    # coincidence with a trace on its boundary. The base stays130×100.
                    region=[[1400, 1900], [11600, 1900], [11600, 8100], [1400, 8100]],
                )
                if wall == south:
                    self.tab(wall, aid, width=2)
            brace_aid = self.attach(brace, 3, roof_south)
            band = self.tab(brace, brace_aid, width=2, band=True)
            self.roles["band_root"] = self.w.project.parts[band].frame.root_surface_id
            self.select(soffit)

            def glue(dialog):
                self.data(dialog.receiver, roof_north)
                self.click(dialog.draw_target)
                self.sketch_points(
                    dialog.target_sketch, [[1000, 1800], [10000, 1800], [10000, 3500], [1000, 3500]]
                )
                check(
                    dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(),
                    "Soffit receiving glue region rejected: " + dialog.feedback.text(),
                )
                self.ok(dialog)

            self.modal(lambda: self.shortcut(Qt.Key.Key_J, shift=True), glue)
            self.shortcut(Qt.Key.Key_R)
            checks = []
            for role, key in [
                ("south", "long_wall"),
                ("north", "long_wall"),
                ("west_gable", "gable_wall"),
                ("east_gable", "gable_wall"),
                ("base", "base"),
                ("brace", "brace_net"),
                ("soffit", "soffit"),
                ("roof_south", "initial_half_roof"),
                ("roof_north", "initial_half_roof"),
            ]:
                checks.append(
                    self.near(
                        self.net_area(self.roles[role]),
                        o["areas_paper_mm2"][key],
                        role + " net area",
                        tolerance=AREA_TOL,
                    )
                )
            trace_before = copy.deepcopy(
                self.w.project.attachment_geometry(south_roof_aid)["target_uv"]
            )
            checks.append(
                self.near(
                    trace_before[0][1] * SCALE,
                    o["roof_wall_trace_paper_mm"],
                    "wall trace along initial roof",
                )
            )
            check(
                len(self.w.project.surfaces) == 11,
                "Unexpected implicit floor/closure or missing band",
            )
            self.capture("A-complete-before-asymmetric-edit")
            step(
                "A_full_open_building_base_brace_hole_band_soffit", checks=checks, roles=self.roles
            )
            self.relation(south, "attachment", south_roof_aid)
            before = copy.deepcopy(self.w.project.to_dict())

            def invalid(dialog):
                self.number(dialog.width, 20)
                check(
                    not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(),
                    "Out-of-roof adhesive footprint incorrectly accepted",
                )
                check("PARTIAL" in dialog.status.text(), "Wrong or missing material diagnostic")
                report["negative_cases"].append(
                    {
                        "status": "EXPECTED_REJECTION",
                        "kind": "outside_roof",
                        "feedback": dialog.status.text(),
                    }
                )
                self.capture("A-negative-outside-roof", dialog)
                self.click(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))

            self.modal(lambda: self.click(self.w.connectors_panel.edit), invalid)
            check(self.w.project.to_dict() == before, "Cancelled invalid flap mutated project")
            self.author_top_tabs(south, south_roof_aid)
            before = copy.deepcopy(self.w.project.to_dict())
            changed_y = -math.hypot(300, 300)
            self.vertex(roof_south, 0, y=changed_y)
            self.vertex(roof_south, 1, y=changed_y)
            check(
                self.w.project.parts[self.w.project.surfaces[roof_south].part_id].stale,
                "Overhang source edit did not mark the entire shared roof stale",
            )
            self.shortcut(Qt.Key.Key_R)
            trace_after = self.w.project.attachment_geometry(south_roof_aid)["target_uv"]
            check(
                max(math.dist(a, b) * SCALE for a, b in zip(trace_before, trace_after))
                <= LENGTH_TOL,
                "Asymmetric overhang edit moved authorial wall trace",
            )
            self.near(
                self.net_area(roof_south),
                o["areas_paper_mm2"]["changed_south_roof"],
                "one changed roof area",
                tolerance=AREA_TOL,
            )
            south_boundary = self.world_boundary(roof_south)
            self.near(min(point[1] for point in south_boundary) * SCALE, -8, "changed eave south Y")
            self.near(max(point[1] for point in south_boundary) * SCALE, 30, "unchanged ridge Y")
            self.near(
                min(point[0] for point in south_boundary) * SCALE, -4, "unchanged west overhang"
            )
            self.near(
                max(point[0] for point in south_boundary) * SCALE, 104, "unchanged east overhang"
            )
            local_minimum = min(
                point[1]
                for point in self.w.project.profiles[
                    self.w.project.surfaces[roof_south].profile_id
                ].points
            )
            self.near(
                (trace_after[0][1] - local_minimum) * SCALE,
                o["changed_trace_from_eave_paper_mm"],
                "changed trace-to-eave distance",
            )
            changed_state = copy.deepcopy(self.w.project.to_dict())
            for _ in range(3):  # Two source point commands and explicit recompute.
                self.shortcut(Qt.Key.Key_Z)
            check(
                self.w.project.to_dict() == before,
                "Undo did not restore complete pre-edit authorial work",
            )
            for _ in range(3):
                self.shortcut(Qt.Key.Key_Y)
            check(
                self.w.project.to_dict() == changed_state,
                "Redo did not restore complete overhang edit",
            )
            step(
                "A_asymmetric_500_to_800_model_mm_eave_preserves_live_trace",
                trace_before=trace_before,
                trace_after=trace_after,
            )
            self.add_page()
            self.add_page()
            for role, page, x, y, rotation in [
                ("south", 0, 30, 30, 5),
                ("north", 0, 30, 110, 0),
                ("west_gable", 0, 140, 30, 0),
                ("east_gable", 0, 140, 130, 0),
                ("roof_south", 1, 30, 30, 0),
                ("base", 1, 30, 160, 0),
                ("brace", 2, 30, 30, 0),
                ("soffit", 2, 100, 120, 0),
                ("band_root", 2, 40, 200, 0),
            ]:
                self.place(self.roles[role], page, x, y, rotation)
            self.place(brace, 0, 140, 210)
            self.place(brace, 2, 30, 30)
            step("A_manual_piece_transfer_between_existing_pages")
            self.linked_pick()
            self.paper_drag(south, locked=False)
            self.place(south, 0, 30, 30, 5)  # Return manually to the exact declared layout.
            self.capture("A-manual-three-page-layout")
            self.finish("model-A")

        def mixed(self):
            self.shortcut(Qt.Key.Key_N)
            self.roles = {}
            self.data(self.w.units, 1)
            wall = self.rectangle("mixed_wall", 10000, 4000, "XZ")
            roof = self.rectangle(
                "mixed_roof",
                10000,
                math.hypot(3000, 3000),
                position=[0, 0, 4000],
                rotation=[45, 0, 0],
            )
            self.fold(wall, 2, roof, 0, 45)
            base = self.rectangle("mixed_base", 13000, 10000, position=[-1500, -2000, 0])
            self.attach(wall, 0, base)
            self.shortcut(Qt.Key.Key_R)
            self.add_page()
            self.place(base, 0, 30, 30)
            self.place(wall, 1, 60, 60, 30)
            self.click(self.w.position_lock)
            self.click(self.w.rotation_lock)
            pid = self.w.project.surfaces[wall].part_id
            reference = self.wall_page_points(wall)
            for actual, expected in zip(
                reference, report["oracle"]["mixed"]["wall_page_points_paper_mm"]
            ):
                check(
                    math.dist(actual, expected) <= LENGTH_TOL, "Initial mixed wall anchor is wrong"
                )
            before = copy.deepcopy(self.w.project.placements[pid])
            new_slope = report["oracle"]["mixed"]["changed_slope_model_mm"]
            self.vertex(roof, 2, y=new_slope)
            self.vertex(roof, 3, y=new_slope)
            self.number(self.w.transform_fields[3], report["oracle"]["mixed"]["changed_angle_deg"])
            check(
                self.w.project.parts[pid].stale,
                "Mixed source edits did not stale whole material part",
            )
            check(self.wall_page_points(wall) == reference, "Stale cache moved root wall")
            self.capture("mixed-profile-edit-stale")
            self.shortcut(Qt.Key.Key_R)
            points = self.wall_page_points(wall)
            check(
                max(math.dist(a, b) for a, b in zip(points, reference)) <= LENGTH_TOL,
                "Recomputed mixed root wall moved on paper",
            )
            check(
                self.w.project.placements[pid] == before, "Recompute changed locked placement/frame"
            )
            roof_world = self.world_boundary(roof)
            self.near(max(p[2] for p in roof_world) * SCALE, 75, "mixed new ridge height")
            self.near(max(p[1] for p in roof_world) * SCALE, 30, "mixed fixed half span")
            check(
                all(
                    self.w.project.attachment_geometry(aid)["valid"]
                    for aid in self.w.project.attachments
                ),
                "Mixed base interior contact broke",
            )
            self.capture("mixed-rise3500-recomputed-locked")
            self.paper_drag(wall, locked=True)
            step(
                "mixed_source_profile_rise_change_and_interior_base_wall_points_invariant",
                wall_page_points_before=reference,
                wall_page_points_after=points,
                page2_anchor=[60, 60],
                rotation_deg=30,
                position_locked=True,
                rotation_locked=True,
            )
            self.finish("mixed-part")

    def run(window):
        driver = Driver(window)
        try:
            window.showMaximized()
            window.raise_()
            window.activateWindow()
            QTest.qWait(500)
            check(not window.project.surfaces, "Actual app did not start empty")
            check(window.viewport.isValid(), "Native OpenGL context absent")
            from OpenGL import GL

            window.viewport.makeCurrent()
            report["opengl"] = {
                name: GL.glGetString(key).decode("ascii", errors="replace")
                for name, key in [
                    ("version", GL.GL_VERSION),
                    ("vendor", GL.GL_VENDOR),
                    ("renderer", GL.GL_RENDERER),
                ]
            }
            window.viewport.doneCurrent()
            driver.capture("empty-real-app")
            if fixture in ("all", "model-A"):
                report["fixture_status"]["model-A"] = "RUNNING"
                driver.building()
                report["fixture_status"]["model-A"] = "PASS_TECHNICAL_UI"
            if fixture in ("all", "mixed-part"):
                report["fixture_status"]["mixed-part"] = "RUNNING"
                driver.mixed()
                report["fixture_status"]["mixed-part"] = "PASS_TECHNICAL_UI"
            if fixture == "curves-planar":
                report["fixture_status"]["curves-planar"] = "RUNNING"
                driver.curves_planar()
                report["fixture_status"]["curves-planar"] = "PASS_TECHNICAL_UI"
            if fixture.startswith("loft-"):
                report["fixture_status"][fixture] = "RUNNING"
                driver.loft_case(fixture)
                report["fixture_status"][fixture] = "PASS_TECHNICAL_UI"
            native = [record for record in report["dialogs"] if "native_seen" in record]
            check(
                len(native) == (6 if fixture == "all" else 3)
                and all(r["native_seen"] and r["accepted"] for r in native),
                "Each requested complete fixture requires native save/open/export",
            )
            check(
                git("rev-parse", "HEAD") == sha and source_files() == hashes,
                "Sources changed during proof; cannot attribute one CODE SHA",
            )
            report.update(
                status="PASS" if fixture == "all" else "PASS_REQUESTED_FIXTURE", failures=failures
            )
            exit_code[0] = 0
        except Exception:
            for name, status in report["fixture_status"].items():
                if status == "RUNNING":
                    report["fixture_status"][name] = "FAIL"
            report.update(status="FAIL", error=traceback.format_exc(), failures=failures)
            try:
                driver.capture("FAIL-last-state")
                # This is a failed partial run artifact, never a replacement injected fixture.
                (output / "FAIL-partial-observed-state.json").write_text(
                    json.dumps(window.project.to_dict(), ensure_ascii=False, indent=2),
                    encoding="utf8",
                )
            except Exception:
                report["capture_error"] = traceback.format_exc()
        finally:
            write_report()
            QApplication.instance().exit(exit_code[0])

    original = author_window.AuthorMainWindow

    def factory(*args, **kwargs):
        window = original(*args, settings=settings, **kwargs)
        windows.append(window)
        timer = QTimer(window)
        timer.timeout.connect(close_messages)
        timer.start(100)
        window._desktop_b_proof_timer = timer
        QTimer.singleShot(850, lambda: run(window))
        return window

    author_window.AuthorMainWindow = (
        factory  # Only isolated settings/harness; no document injection.
    )
    argv = sys.argv
    sys.argv = ["archpapercraft-desktop-b-proof"]
    try:
        entry.main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            exit_code[0] = 1
    except Exception:
        report.update(status="FAIL", error=traceback.format_exc())
    finally:
        author_window.AuthorMainWindow = original
        sys.argv = argv
        if report["status"] == "RUNNING":
            report.update(status="FAIL", error="Entry exited before complete proof")
        write_report()
    return exit_code[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-sha")
    parser.add_argument("--oracle-only", action="store_true")
    parser.add_argument(
        "--fixture",
        choices=["all", "model-A", "mixed-part", "curves-planar", "loft-B1", "loft-B2",
                 "loft-Bezier"],
        default="all",
        help="A partial checkpoint never replaces the full A+mixed proof",
    )
    args = parser.parse_args()
    if args.oracle_only:
        value = oracle()
        assert math.isclose(value["initial_roof_paper_mm"]["half_slope"], 49.49747468305833)
        assert math.isclose(value["areas_paper_mm2"]["brace_net"], 2400)
        assert area([[0, 0], [100, 0], [100, 40], [0, 40]]) == 4000
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        parser.error("Native proof requires the explicitly coordinated Windows desktop")
    if not args.output or not args.expected_sha:
        parser.error("Native proof requires --output and --expected-sha")
    if args.output.resolve().exists():
        parser.error("Evidence output must be a fresh nonexistent directory")
    return run_windows(args.output.resolve(), args.expected_sha, args.fixture)


if __name__ == "__main__":
    raise SystemExit(main())
