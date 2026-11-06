"""Opt-in Windows proof through the real application entry point and visible UI.

Run only after desktop coordination: python tools/authoring/desktop_proof.py
--output <fresh-directory>. This is technical automation, not a novice-user test
or a physical build. No construction fixture is injected into the controller.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_files():
    paths = [
        *ROOT.joinpath("src").rglob("*.py"),
        Path(__file__),
        Path(__file__).with_name("native_dialogs.py"),
        ROOT / "pyproject.toml",
    ]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-sha", help="Refuse a different HEAD than the reviewed pin")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This proof requires the coordinated Windows desktop")
    output = args.output.resolve()
    if output.exists():
        parser.error(
            "--output must be a fresh, nonexistent directory; evidence is never overwritten"
        )
    sha = git("rev-parse", "HEAD")
    if args.expected_sha and sha != args.expected_sha:
        parser.error(f"Expected HEAD {args.expected_sha}, found {sha}")
    status = git("status", "--porcelain=v1")
    source_hashes = source_files()
    output.mkdir(parents=True)
    (output / "export").mkdir()
    report = {
        "status": "RUNNING",
        "source_sha": sha,
        "source_status_at_start": status,
        "source_files_sha256": source_hashes,
        "platform": platform.platform(),
        "python": sys.version,
        "pid": os.getpid(),
        "steps": [],
        "dialogs": [],
        "evidence_kind": "actual_app_main_QTest_widgets_and_own_PID_native_file_dialogs",
        "new_user": "NOT_RUN",
        "physical_build": "NOT_RUN",
        "started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    exit_code = [1]

    import native_dialogs
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    from PySide6 import __version__ as qt_version
    from PySide6.QtCore import QPoint, QPointF, QSettings, Qt, QTimer
    from PySide6.QtTest import QSignalSpy, QTest
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QMessageBox,
        QPushButton,
        QScrollArea,
    )

    from archpapercraft import app as entry
    from archpapercraft.ui import author_window

    report["pyside6"] = qt_version
    settings = QSettings(str(output / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("tips_enabled", True)
    expected_messages = []
    failures = []
    started = time.monotonic()
    window_holder = []

    def write_report():
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["files_sha256"] = {
            str(p.relative_to(output)).replace("\\", "/"): digest(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "results.json"
        }
        (output / "results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def capture(name):
        window = window_holder[0]
        QApplication.processEvents()
        QTest.qWait(120)
        screen = window.screen()
        assert screen.grabWindow(int(window.winId())).save(str(output / f"{name}-desktop.png"))
        assert window.viewport.grabFramebuffer().save(str(output / f"{name}-opengl.png"))

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        if failures:
            raise AssertionError("Unexpected modal dialog: " + repr(failures))

    def step(name, **details):
        check(True, name)
        report["steps"].append({"name": name, "status": "PASS", **details})
        write_report()

    def visible(widget):
        scroll = widget.parentWidget()
        while scroll and not isinstance(scroll, QScrollArea):
            scroll = scroll.parentWidget()
        if scroll:
            scroll.ensureWidgetVisible(widget)
        QTest.qWait(45)
        check(widget.isVisible() and widget.isEnabled(), "Required widget hidden or disabled")
        return widget

    def click(widget):
        visible(widget)
        if isinstance(widget, QCheckBox):
            # In a narrow, horizontally scrollable dock, the row's centre can
            # be clipped. Scroll the exact indicator point into view and check
            # that this real click toggled before attributing a lock failure.
            point = QPoint(8, widget.height() // 2)
            scroll = widget.parentWidget()
            while scroll and not isinstance(scroll, QScrollArea):
                scroll = scroll.parentWidget()
            if scroll:
                target = widget.mapTo(scroll.widget(), point)
                scroll.ensureVisible(target.x(), target.y(), 12, 12)
                QTest.qWait(45)
            before = widget.isChecked()
            QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=point)
            check(widget.isChecked() != before, "Checkbox indicator click did not toggle")
        else:
            QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        QTest.qWait(60)

    def number(widget, value):
        visible(widget).setFocus()
        QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(widget, str(value))
        QTest.keyClick(widget, Qt.Key.Key_Return)
        QTest.qWait(60)
        check(math.isclose(widget.value(), float(value), abs_tol=1e-6), "Numeric UI input lost")

    def combo(widget, index):
        check(0 <= index < widget.count(), "Requested combo option absent")
        visible(widget).setFocus()
        # Navigate the actual popup before committing. Changing the closed
        # edge combo through intermediate rows would start a connection to the
        # wrong edge before the intended target is reached.
        QTest.keyClick(widget, Qt.Key.Key_F4)
        QTest.qWait(50)
        view = widget.view()
        check(view.isVisible(), "Combo keyboard popup did not open")
        QTest.keyClick(view, Qt.Key.Key_Home)
        for _ in range(index):
            QTest.keyClick(view, Qt.Key.Key_Down)
        QTest.keyClick(view, Qt.Key.Key_Return)
        QTest.qWait(70)
        check(widget.currentIndex() == index, "Combo keyboard selection did not apply")

    def shortcut(window, key):
        window.setFocus()
        QTest.keyClick(window, key, Qt.KeyboardModifier.ControlModifier)
        QTest.qWait(80)

    def message_driver():
        modal = QApplication.activeModalWidget()
        if isinstance(modal, QMessageBox):
            title = modal.windowTitle()
            record = {"kind": "real_QMessageBox", "title": title, "text": modal.text()}
            report["dialogs"].append(record)
            if expected_messages and expected_messages[0] == title:
                expected_messages.pop(0)
                button = modal.button(QMessageBox.StandardButton.Ok)
                if button is None:
                    failures.append({"error": "Expected real message box lacks OK"})
                    modal.reject()
                else:
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                    record["clicked"] = "Ok"
            else:
                failures.append(record)
                for button in modal.buttons():
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                    break
        if time.monotonic() - started > 120:
            failures.append({"error": "120-second automation deadline exceeded"})
            report.update(status="FAIL", failures=failures)
            write_report()
            QApplication.instance().exit(1)

    def select(window, sid):
        item = next(
            window.tree.topLevelItem(i)
            for i in range(window.tree.topLevelItemCount())
            if window.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == sid
        )
        window.tree.scrollToItem(item)
        QTest.mouseClick(
            window.tree.viewport(),
            Qt.MouseButton.LeftButton,
            pos=window.tree.visualItemRect(item).center(),
        )
        QTest.qWait(60)
        check(window.selected_surface == sid, "Tree UI selection did not reach source surface")

    def polygon(window, points, *, hole=False):
        shortcut(window, Qt.Key.Key_H if hole else Qt.Key.Key_L)
        check(window.sketch.drawing, "Sketch mode did not start")
        for x, y in points:
            point = window.sketch.mapFromScene(QPointF(x, -y))
            check(window.sketch.viewport().rect().contains(point), "Sketch point outside viewport")
            QTest.mouseClick(window.sketch.viewport(), Qt.MouseButton.LeftButton, pos=point)
            QTest.qWait(30)
        QTest.keyClick(window.sketch, Qt.Key.Key_Return)
        QTest.qWait(100)
        check(not window.sketch.drawing, "Own sketch failed to become a surface/hole")

    def areas(window, sid):
        loops = window.project.part_geometry(window.project.surfaces[sid].part_id)["polygons"][sid]
        values = [
            abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1]))) / 2
            for loop in loops
        ]
        return {
            "outer_mm2": values[0],
            "holes_mm2": sum(values[1:]),
            "net_mm2": values[0] - sum(values[1:]),
        }

    def run(window):
        try:
            window.showMaximized()
            window.raise_()
            window.activateWindow()
            QTest.qWait(450)
            check(not window.project.surfaces, "Entry point did not start an empty project")
            check(window.viewport.isValid(), "Actual OpenGL context failed")
            from OpenGL import GL

            window.viewport.makeCurrent()
            report["opengl"] = {
                key: GL.glGetString(value).decode("ascii", errors="replace")
                for key, value in [
                    ("version", GL.GL_VERSION),
                    ("vendor", GL.GL_VENDOR),
                    ("renderer", GL.GL_RENDERER),
                ]
            }
            window.viewport.doneCurrent()
            step("actual_app_main_empty_workspace")
            combo(window.plane, 1)
            polygon(
                window, [(0, 0), (8000, 0), (8000, 6000), (5000, 6000), (5000, 3000), (0, 3000)]
            )
            sid_a = window.selected_surface
            polygon(window, [(5500, 500), (7000, 500), (7000, 2000), (5500, 2000)], hole=True)
            check(
                window.project.parts[window.selected_part].stale, "Hole failed to mark paper stale"
            )
            capture("01-own-concave-hole-stale")
            shortcut(window, Qt.Key.Key_R)
            values = areas(window, sid_a)
            check(
                values == {"outer_mm2": 3300.0, "holes_mm2": 225.0, "net_mm2": 3075.0},
                "Own concave/hole area disagrees with hand-computed oracle",
            )
            step("own_concave_polygon_and_true_hole", **values)
            combo(window.vertex_choice, 2)
            number(window.vertex_x, 9)
            check(
                window.project.parts[window.selected_part].stale,
                "Edit did not preserve stale cache",
            )
            check(areas(window, sid_a) == values, "Source edit silently recomputed paper")
            capture("02-edited-stale")
            shortcut(window, Qt.Key.Key_R)
            edited = areas(window, sid_a)
            check(
                edited == {"outer_mm2": 3600.0, "holes_mm2": 225.0, "net_mm2": 3375.0},
                "Edited area disagrees with analytic triangle increment",
            )
            step("numeric_vertex_edit_explicit_recompute", **edited)
            # Observe a true empty trim by clicking its projected centre, then
            # verify an actual material click links the 3D and paper selection.
            hole_pixel = window.viewport.project_points([[6250, 0, 1250]])[0]
            hole_point = QPoint(round(hole_pixel[0]), round(hole_pixel[1]))
            check(window.viewport.surface_at(hole_point) is None, "3D trim is incorrectly pickable")
            picked = QSignalSpy(window.viewport.surface_selected)
            QTest.mouseClick(window.viewport, Qt.MouseButton.LeftButton, pos=hole_point)
            check(
                picked.count() == 1 and picked.at(0) == [""],
                "Clicking the hole selected filled material",
            )
            check(
                window.selected_surface is None and window.paper.selected_part is None,
                "Clicking empty space did not clear linked selection",
            )
            material_pixel = window.viewport.project_points([[7500, 0, 3500]])[0]
            QTest.mouseClick(
                window.viewport,
                Qt.MouseButton.LeftButton,
                pos=QPoint(round(material_pixel[0]), round(material_pixel[1])),
            )
            check(
                window.selected_surface == sid_a
                and window.paper.selected_part == window.project.surfaces[sid_a].part_id,
                "3D material selection did not reach paper",
            )
            step("actual_3D_material_and_empty_hole_picking")
            polygon(window, [(0, 0), (1000, 0), (1000, 3000), (0, 3000)])
            sid_b = window.selected_surface
            select(window, sid_a)
            combo(window.edge_choice, 5)
            click(window.connect_button)
            check(window.connect_source is not None, "Two-step source edge not retained")
            select(window, sid_b)
            preview_record = {}

            def accept_preview():
                try:
                    dialog = QApplication.activeModalWidget()
                    check(isinstance(dialog, QDialog), "Assembly preview dialog absent")
                    field = dialog.findChild(QDoubleSpinBox)
                    number(field, 90)
                    capture("03-real-assembly-preview")
                    check(
                        dialog.screen()
                        .grabWindow(int(dialog.winId()))
                        .save(str(output / "03-assembly-dialog-desktop.png")),
                        "Preview capture failed",
                    )
                    from archpapercraft.ui.author_viewport import AuthorViewport

                    check(
                        dialog.findChild(AuthorViewport)
                        .grabFramebuffer()
                        .save(str(output / "03-assembly-dialog-opengl.png")),
                        "Preview GL capture failed",
                    )
                    buttons = dialog.findChild(QDialogButtonBox)
                    ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
                    check(ok.isEnabled(), "Assembly preview validation rejected matching edges")
                    preview_record.update(title=dialog.windowTitle(), angle_deg=field.value())
                    QTest.mouseClick(ok, Qt.MouseButton.LeftButton)
                except Exception:
                    failures.append({"preview": traceback.format_exc()})
                    modal = QApplication.activeModalWidget()
                    if modal:
                        modal.reject()

            # Commit the second rectangle edge (3000mm); do not transiently
            # connect its first, 1000mm edge while navigating the popup.
            QTimer.singleShot(250, accept_preview)
            combo(window.edge_choice, 1)
            check(len(window.project.joints) == 1, "Two-step edge connection did not commit")
            step("own_second_surface_real_assembly_preview", **preview_record)
            combo(window.joint_mode, 1)
            shortcut(window, Qt.Key.Key_R)
            check(len(window.project.parts) == 1, "Fold failed to form a shared paper part")
            capture("04-fold-shared-part")
            combo(window.joint_mode, 0)
            combo(window.tab_owner, window.tab_owner.findData(sid_b))
            number(window.tab_width, 7)
            shortcut(window, Qt.Key.Key_R)
            check(len(window.project.parts) == 2, "Cut failed to split paper parts")
            connector = next(iter(window.project.connectors.values()))
            check(
                connector.owner_surface_id == sid_b and connector.width_mm == 7,
                "Tab UI did not preserve its actual owner and width",
            )
            step("fold_cut_and_seven_mm_tab_on_B")
            select(window, sid_a)
            pid_a = window.project.surfaces[sid_a].part_id
            pid_b = window.project.surfaces[sid_b].part_id
            combo(window.page_choice, 1)
            number(window.paper_x, 60)
            number(window.paper_y, 50)
            number(window.paper_angle, 30)
            click(window.position_lock)
            click(window.rotation_lock)
            check(
                window.project.placements[pid_a].position_locked
                and window.project.placements[pid_a].rotation_locked,
                "Checkbox controls did not persist both locks on the selected A part",
            )
            add_page = next(b for b in window.findChildren(QPushButton) if b.text() == "Přidat A4")
            click(add_page)
            select(window, sid_b)
            combo(window.page_choice, 2)
            number(window.paper_x, 50)
            number(window.paper_y, 60)
            for pid, page_index, x, y, angle in [(pid_a, 0, 60, 50, 30), (pid_b, 1, 50, 60, 0)]:
                place = window.project.placements[pid]
                check(
                    [place.page_id, place.x_mm, place.y_mm, place.rotation_deg]
                    == [window.project.pages[page_index].id, x, y, angle],
                    "Manual placement mismatch",
                )
            place = window.project.placements[pid_a]
            check(place.position_locked and place.rotation_locked, "Independent locks not saved")
            shortcut(window, Qt.Key.Key_R)
            # Select the printed material by its actual view item and drag it.
            # Both locks must preserve the persisted anchor and rotation.
            window.paper.focus_part(pid_a)
            QTest.qWait(100)
            item = window.paper.part_items[pid_a]
            # The fixture's right wing has material at (75,35). Accommodate
            # front-side projection while checking the actual picking shape.
            local = next(
                (p for p in [QPointF(75, 35), QPointF(75, -35)] if item.shape().contains(p)), None
            )
            check(local is not None, "Paper material probe is not inside the part")
            point = window.paper.mapFromScene(item.mapToScene(local))
            before_lock = [place.x_mm, place.y_mm, place.rotation_deg]
            QTest.mousePress(window.paper.viewport(), Qt.MouseButton.LeftButton, pos=point)
            QTest.mouseMove(window.paper.viewport(), point + QPoint(20, 10), delay=50)
            QTest.mouseRelease(
                window.paper.viewport(), Qt.MouseButton.LeftButton, pos=point + QPoint(20, 10)
            )
            QTest.qWait(100)
            place = window.project.placements[pid_a]
            check(
                [place.x_mm, place.y_mm, place.rotation_deg] == before_lock,
                "Locked paper drag changed the anchor or rotation",
            )
            check(
                window.selected_surface == sid_a and window.viewport.selected_surfaces == {sid_a},
                "Actual paper selection did not reach 3D",
            )
            capture("05-manual-two-pages-tab-and-locks")
            snapshot = window.project.snapshot()  # Read-only observation after actual UI commands.
            (output / "snapshot.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            step("manual_two_A4_pages_and_independent_locks")
            project_path = output / "own-model.apcraft"
            native_dialogs.schedule_path(project_path, report["dialogs"])
            shortcut(window, Qt.Key.Key_S)
            check(project_path.is_file() and not window.controller.dirty, "Native save failed")
            saved_state = window.project.to_dict()
            shortcut(window, Qt.Key.Key_N)
            check(not window.project.surfaces, "New project did not clear the saved model")
            native_dialogs.schedule_path(project_path, report["dialogs"])
            shortcut(window, Qt.Key.Key_O)
            check(window.project.to_dict() == saved_state, "Native reopen changed author state")
            check(not window.controller.dirty, "Reopened file is unexpectedly dirty")
            capture("06-native-reopened")
            step("native_save_new_and_reopen_preserve_author_state")
            expected_messages.extend(["Vektorový export", "Export dokončen"])
            native_dialogs.schedule_path(output / "export", report["dialogs"])
            shortcut(window, Qt.Key.Key_E)
            check(not expected_messages, "Real export confirmation/completion was not clicked")
            svgs = sorted((output / "export").glob("*.svg"))
            pdf = PdfReader(output / "export/model.pdf")
            check(len(svgs) == len(pdf.pages) == 2, "Both vector outputs must contain two pages")
            roots = [ET.parse(p).getroot() for p in svgs]
            svg_ids = {
                g.attrib["data-part-id"]
                for root in roots
                for g in root.iter()
                if "data-part-id" in g.attrib
            }
            check(svg_ids == {pid_a, pid_b}, "SVG part coverage mismatch")
            check(
                all(
                    root.attrib["width"] == "210mm" and root.attrib["height"] == "297mm"
                    for root in roots
                ),
                "SVG physical page units mismatch",
            )
            for page in pdf.pages:
                check(
                    abs(float(page.mediabox.width) * 25.4 / 72 - 210) < 0.001,
                    "PDF A4 width mismatch",
                )
                check(
                    not page["/Resources"].get("/XObject", {}), "PDF contains raster/image object"
                )
                check(
                    any(op == b"l" for _, op in ContentStream(page.get_contents(), pdf).operations),
                    "PDF lacks vector line paths",
                )
            native_records = [d for d in report["dialogs"] if "native_seen" in d]
            check(
                len(native_records) == 3
                and all(d["native_seen"] and d["accepted"] for d in native_records),
                "Native file proof incomplete",
            )
            check(
                git("rev-parse", "HEAD") == sha and source_files() == source_hashes,
                "Sources changed during the proof; evidence cannot be assigned one pin",
            )
            step("native_export_SVG_PDF_independent_readers", parts=sorted(svg_ids), pages=2)
            report["status"] = "PASS"
            exit_code[0] = 0
        except Exception:
            report.update(status="FAIL", error=traceback.format_exc(), failures=failures)
            try:
                capture("FAIL-last-visible-state")
            except Exception:
                report["capture_error"] = traceback.format_exc()
        finally:
            write_report()
            QApplication.instance().exit(exit_code[0])

    original = author_window.AuthorMainWindow

    def factory(*a, **kw):
        window = original(*a, settings=settings, **kw)
        window_holder.append(window)
        watcher = QTimer(window)
        watcher.timeout.connect(message_driver)
        watcher.start(100)
        window._desktop_proof_watcher = watcher
        QTimer.singleShot(850, lambda: run(window))
        return window

    author_window.AuthorMainWindow = factory
    old_argv = sys.argv
    sys.argv = ["archpapercraft-desktop-proof"]
    try:
        entry.main()  # Actual entry: QApplication, style, main window, event loop.
    except SystemExit as exc:
        if exc.code not in (None, 0):
            exit_code[0] = 1
    except Exception:
        report.update(status="FAIL", error=traceback.format_exc())
    finally:
        author_window.AuthorMainWindow = original
        sys.argv = old_argv
        if report["status"] == "RUNNING":
            report.update(status="FAIL", error="Application exited before the proof finished")
        write_report()
    return exit_code[0]


if __name__ == "__main__":
    raise SystemExit(main())
