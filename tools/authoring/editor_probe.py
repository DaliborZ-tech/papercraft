"""Opt-in real Inkscape actions + Windows GUI round-trip of an author SVG copy.

Adapted from tools/panel/editor_probe.py at f9507e3. This tool never edits SVG
with XML APIs: they only read the result of actual Inkscape operations. Run
after desktop coordination and a source pin. Evidence directories are fresh.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "http://www.w3.org/2000/svg"
NS = {"s": SVG_NS}
ROLES = ("CUT", "FOLD_MOUNTAIN", "FOLD_VALLEY", "TABS", "LABELS", "ARTWORK", "GUIDES")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _bounds(text):
    found = {}
    for line in text.splitlines():
        columns = line.split(",")
        if len(columns) == 5:
            try:
                found[columns[0]] = list(map(float, columns[1:]))
            except ValueError:
                continue
    return found


def _path_signature(value):
    """Read the native absolute geometry, allowing harmless relative reserialization.

    The author writer emits M/L/C/A/Z. Inkscape commonly serializes subsequent
    lines as l/h/v; normalize these without flattening a native curve to a mesh.
    Refuse an unsupported representation rather than claiming equal geometry.
    """
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", value)
    result, current, start, index, op = [], [0.0, 0.0], None, 0, None
    while index < len(tokens):
        if tokens[index].isalpha():
            op = tokens[index]
            index += 1
        if op is None:
            raise AssertionError("Path representation lacks an initial command")
        absolute, relative = op.upper(), op.islower()
        if absolute == "Z":
            result.append(("Z",))
            current, op = list(start), None
            continue
        counts = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "A": 7}
        if absolute not in counts:
            raise AssertionError("Unsupported native path reserialization: " + absolute)
        count = counts[absolute]
        values = list(map(float, tokens[index : index + count]))
        assert len(values) == count
        index += count
        if absolute == "H":
            values, absolute = [values[0] + (current[0] if relative else 0), current[1]], "L"
        elif absolute == "V":
            values, absolute = [current[0], values[0] + (current[1] if relative else 0)], "L"
        elif relative:
            for offset in [5] if absolute == "A" else range(0, count, 2):
                values[offset] += current[0]
                values[offset + 1] += current[1]
        result.append((absolute, *values))
        current = values[-2:]
        if absolute == "M":
            start = list(current)
            op = "l" if relative else "L"
    return result


def _same_path(before, after):
    first, second = _path_signature(before), _path_signature(after)
    assert len(first) == len(second), "Path topology changed in the external editor"
    for a, b in zip(first, second):
        assert a[0] == b[0] and len(a) == len(b), "Native curve/line command kind changed"
        assert all(math.isclose(x, y, abs_tol=2e-5, rel_tol=0) for x, y in zip(a[1:], b[1:])), (
            "Part-local path coordinates changed beyond SVG serialization tolerance"
        )


def _send_keys(user32, text, foreground_guard):
    """Send Unicode text to the already verified foreground window without clipboard use."""
    pointer_type = ctypes.c_size_t

    class MouseInput(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", pointer_type),
        ]

    class KeyInput(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", pointer_type),
        ]

    class InputUnion(ctypes.Union):
        _fields_ = [("mi", MouseInput), ("ki", KeyInput)]

    class Input(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", InputUnion)]

    for char in text:
        foreground_guard()
        down = Input(type=1, ki=KeyInput(wVk=0, wScan=ord(char), dwFlags=4, time=0, dwExtraInfo=0))
        up = Input(type=1, ki=KeyInput(wVk=0, wScan=ord(char), dwFlags=6, time=0, dwExtraInfo=0))
        inputs = (Input * 2)(down, up)
        if user32.SendInput(2, inputs, ctypes.sizeof(Input)) != 2:
            raise RuntimeError("Windows refused Unicode input to the editor")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Actual author-export SVG")
    parser.add_argument("--output", type=Path, required=True, help="Fresh evidence directory")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument(
        "--inkscape",
        type=Path,
        default=Path(os.environ.get("TEMP", "."))
        / "papercraft-p2-editor-tools/inkscape/bin/inkscape.com",
    )
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Native GUI proof requires the coordinated Windows desktop")
    source_path, out = args.source.resolve(), args.output.resolve()
    if out.exists():
        parser.error("Output must not exist; previous evidence is never overwritten")
    if not source_path.is_file() or source_path.suffix.lower() != ".svg":
        parser.error("Source must be an existing exported SVG")
    if not args.inkscape.is_file():
        parser.error("Inkscape executable absent; this tool does not download or install it")
    sha = _git("rev-parse", "HEAD")
    if sha != args.expected_sha:
        parser.error(f"Expected HEAD {args.expected_sha}, found {sha}")
    executable = args.inkscape.with_suffix(".exe")
    if not executable.is_file():
        parser.error("Native inkscape.exe sibling is absent")
    script_hash = _sha(Path(__file__))
    bundle = {p.name: _sha(p) for p in sorted(source_path.parent.iterdir()) if p.is_file()}
    out.mkdir(parents=True)
    environment = dict(os.environ)
    environment["INKSCAPE_PROFILE_DIR"] = tempfile.mkdtemp(prefix="papercraft-author-inkscape-")
    environment["PYTHONUTF8"] = "1"
    report = {
        "status": "RUNNING",
        "source_sha": sha,
        "source_status_at_start": _git("status", "--porcelain=v1"),
        "script_sha256": script_hash,
        "origin_source": str(source_path),
        "origin_bundle_sha256": bundle,
        "commands": [],
        "physical_build": "NOT_RUN",
        "new_user_test": "NOT_RUN",
        "profile_directory": environment["INKSCAPE_PROFILE_DIR"],
        "editor_executables_sha256": {str(p): _sha(p) for p in {args.inkscape, executable}},
        "scope": "early actual author SVG editing; full AU17/DPI remains PC009",
    }
    process = None
    own_hwnd = None
    user32 = None
    started = time.monotonic()

    def save_report():
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["files_sha256"] = {
            p.name: _sha(p)
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != "editor-results.json"
        }
        (out / "editor-results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def command(arguments):
        beginning = time.monotonic()
        result = subprocess.run(
            [str(args.inkscape), *arguments],
            env=environment,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
        report["commands"].append(
            {
                "command": [str(args.inkscape), *arguments],
                "seconds": round(time.monotonic() - beginning, 3),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        save_report()
        if result.returncode:
            raise RuntimeError("Actual Inkscape command failed: " + result.stderr)
        return result.stdout.strip()

    try:
        report["inkscape_version"] = command(["--version"])
        original_copy = out / "editor-original.svg"
        original_copy.write_bytes(source_path.read_bytes())
        original = ET.parse(original_copy).getroot()
        parts = original.findall("s:g[@data-part-id]", NS)
        if not parts:
            raise AssertionError("Author SVG has no stable part-first group")
        part = max(parts, key=lambda p: len(p.findall("s:g[@data-role='CUT']/s:path", NS)))
        part_id = part.attrib["id"]
        label = part.find("s:g[@data-role='LABELS']/s:text", NS)
        if label is None:
            raise AssertionError("Selected actual part has no editable native text")
        label_id = label.attrib["id"]
        paths = {p.attrib["id"]: p.attrib["d"] for p in original.findall(".//s:path[@id]", NS)}
        moved_ids = {p.attrib["id"] for p in part.findall(".//s:path[@id]", NS)}
        before_bounds = _bounds(command([str(original_copy), "--query-all"]))
        edited = out / "editor-edited.svg"
        actions = (
            f"select-by-id:{part_id};transform-translate:10,15;select-clear;"
            f"select-clear;select-by-id:{label_id};object-set-property:fill,#b43d28;"
            f"export-filename:{edited};export-do"
        )
        command([str(original_copy), "--actions=" + actions])
        changed = ET.parse(edited).getroot()
        edited_label = changed.find(f".//s:text[@id='{label_id}']", NS)
        assert edited_label is not None
        assert "".join(edited_label.itertext()) == "".join(label.itertext())
        assert (
            "#b43d28" in edited_label.attrib.get("style", "")
            or edited_label.attrib.get("fill") == "#b43d28"
        )
        # Native editor actions change color/placement. Text content is changed
        # only by the individual GUI edit below. The historical uppercase
        # extension also affected unselected footer texts, so is not used.
        report["actual_inkscape_action_edits"] = {
            "part_id": part_id,
            "label_id": label_id,
            "translation_px": [10, 15],
            "fill": "#b43d28",
            "text": "unchanged_by_actions; individual_native_GUI_edit_below",
            "method": "Inkscape executable native actions, not XML writes",
        }
        process = subprocess.Popen(
            [
                str(executable),
                str(edited),
                "--with-gui",
                f"--actions=window-set-geometry:20,20,1200,850;zoom-page;select-by-id:{label_id}",
            ],
            env=environment,
        )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.PostMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        found = []
        observed = {}

        def visit(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == process.pid and user32.IsWindowVisible(hwnd):
                title, cls, rect = (
                    ctypes.create_unicode_buffer(2048),
                    ctypes.create_unicode_buffer(256),
                    wintypes.RECT(),
                )
                user32.GetWindowTextW(hwnd, title, len(title))
                user32.GetClassNameW(hwnd, cls, len(cls))
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width, height = rect.right - rect.left, rect.bottom - rect.top
                observed[int(hwnd)] = {
                    "hwnd": int(hwnd),
                    "title": title.value,
                    "class": cls.value,
                    "width": width,
                    "height": height,
                }
                # GTK can expose transient/helper windows before the document.
                # Only the actual large window for this disposable SVG is a
                # valid keyboard target, not the first visible HWND of its PID.
                if edited.name in title.value and width >= 600 and height >= 400:
                    found.append(hwnd)
            return True

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not found:
            user32.EnumWindows(callback_type(visit), 0)
            time.sleep(0.2)
        report["own_visible_windows"] = list(observed.values())
        save_report()
        if not found:
            raise AssertionError(
                "No real editor GUI window belonging to this proof PID was observed"
            )
        own_hwnd = found[0]
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        QTest.qWait(2200)
        before_foreground = user32.GetForegroundWindow()
        user32.ShowWindow(own_hwnd, 9)  # SW_RESTORE, only our verified document HWND.
        direct = bool(user32.SetForegroundWindow(own_hwnd))
        QTest.qWait(250)
        focus_record = {
            "own_hwnd": int(own_hwnd),
            "before_hwnd": int(before_foreground or 0),
            "direct_activation_returned": direct,
        }
        if user32.GetForegroundWindow() != own_hwnd:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentThreadId.restype = wintypes.DWORD
            current_thread = kernel32.GetCurrentThreadId()
            foreign_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
            attached = False
            try:
                if foreign_thread and foreign_thread != current_thread:
                    attached = bool(user32.AttachThreadInput(current_thread, foreign_thread, True))
                user32.BringWindowToTop(own_hwnd)
                focus_record["attached_activation_returned"] = bool(
                    user32.SetForegroundWindow(own_hwnd)
                )
                QTest.qWait(150)
            finally:
                if attached:
                    user32.AttachThreadInput(current_thread, foreign_thread, False)
            focus_record["input_queue_temporarily_attached"] = attached
        if user32.GetForegroundWindow() != own_hwnd:
            # Windows can reject programmatic focus even when the requested
            # document is visible. Activate it as a user would: a real click
            # on its own title bar, after verifying the desktop hit target.
            user32.SetWindowPos.argtypes = [
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            ]
            user32.WindowFromPoint.argtypes = [wintypes.POINT]
            user32.WindowFromPoint.restype = wintypes.HWND
            user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user32.GetAncestor.restype = wintypes.HWND
            user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
            cursor, rect = wintypes.POINT(), wintypes.RECT()
            user32.GetCursorPos(ctypes.byref(cursor))
            raised = bool(user32.SetWindowPos(own_hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x43))
            try:
                QTest.qWait(120)
                assert user32.GetWindowRect(own_hwnd, ctypes.byref(rect))
                point = wintypes.POINT((rect.left + rect.right) // 2, rect.top + 16)
                target = user32.WindowFromPoint(point)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(target, ctypes.byref(pid))
                assert pid.value == process.pid and user32.GetAncestor(target, 2) == own_hwnd, (
                    "Title-bar activation target is not this proof's editor; refusing mouse input"
                )
                assert user32.SetCursorPos(point.x, point.y)
                assert user32.WindowFromPoint(point) == target, (
                    "Activation target moved before click"
                )
                user32.mouse_event(0x0002, 0, 0, 0, 0)
                user32.mouse_event(0x0004, 0, 0, 0, 0)
                QTest.qWait(200)
                focus_record["verified_titlebar_click"] = {
                    "target_hwnd": int(target),
                    "target_pid": pid.value,
                    "x": point.x,
                    "y": point.y,
                }
            finally:
                if raised:
                    user32.SetWindowPos(own_hwnd, wintypes.HWND(-2), 0, 0, 0, 0, 0x43)
                user32.SetCursorPos(cursor.x, cursor.y)
        focus_record["after_hwnd"] = int(user32.GetForegroundWindow() or 0)
        report["initial_focus"] = focus_record
        save_report()

        def foreground():
            if user32.GetForegroundWindow() != own_hwnd:
                raise AssertionError(
                    "Own editor window lost foreground; refusing global keyboard input"
                )

        def chord(key, control=False):
            foreground()
            if control:
                user32.keybd_event(0x11, 0, 0, 0)
            try:
                user32.keybd_event(key, 0, 0, 0)
                user32.keybd_event(key, 0, 2, 0)
            finally:
                if control:
                    user32.keybd_event(0x11, 0, 2, 0)

        chord(0x77)  # F8 selects the text tool for the selected stable text ID.
        QTest.qWait(200)
        chord(0x41, control=True)
        foreground()
        gui_text = "Žluťoučký – vlastní díl"
        _send_keys(user32, gui_text, foreground)
        chord(0x53, control=True)
        QTest.qWait(1200)
        final = ET.parse(edited).getroot()
        gui_label = final.find(f".//s:text[@id='{label_id}']", NS)
        assert gui_label is not None and "".join(gui_label.itertext()) == gui_text, (
            "Real editor GUI did not save the requested individual native text edit"
        )
        assert "#b43d28" in gui_label.attrib.get("style", "") or (
            gui_label.attrib.get("fill") == "#b43d28"
        ), "GUI text edit lost the independently edited color"
        report["native_gui_text_edit"] = {
            "text": gui_text,
            "method": "F8/CtrlA/own-window Unicode SendInput/CtrlS",
            "own_pid": process.pid,
            "own_hwnd": int(own_hwnd),
            "foreground_verified_before_each_chord": True,
        }
        shot = app.primaryScreen().grabWindow(int(own_hwnd))
        assert not shot.isNull() and shot.save(str(out / "editor-gui.png"))
        report["gui_capture"] = {
            "method": "QScreen.grabWindow(actual_editor_hwnd)",
            "width": shot.width(),
            "height": shot.height(),
        }
        pixels = shot.toImage()
        sample = [
            pixels.pixelColor(x, y).value()
            for x in range(0, pixels.width(), 31)
            for y in range(0, pixels.height(), 31)
        ]
        if max(sample, default=0) == 0:
            # Some Windows compositors cannot capture a GTK window by HWND.
            # Preserve that raw result, then capture its actual desktop area.
            foreground()
            rect = wintypes.RECT()
            user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            assert user32.GetWindowRect(own_hwnd, ctypes.byref(rect))
            desktop = app.primaryScreen().grabWindow(
                0, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
            )
            assert desktop.save(str(out / "editor-gui-desktop-region.png"))
            report["gui_capture"].update(
                hwnd_capture_black=True,
                fallback="actual foreground editor rectangle on desktop; black raw image preserved",
            )
        user32.PostMessageW(own_hwnd, 0x0010, 0, 0)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        after_bounds = _bounds(command([str(edited), "--query-all"]))
        final_part = final.find(f".//s:g[@id='{part_id}']", NS)
        assert final_part is not None
        assert tuple(p.attrib["data-role"] for p in final_part.findall("s:g", NS)) == ROLES
        final_paths = {p.attrib["id"]: p.attrib["d"] for p in final.findall(".//s:path[@id]", NS)}
        assert len(final.findall(".//s:path[@id]", NS)) == len(final_paths), "Duplicate path IDs"
        assert paths.keys() <= final_paths.keys(), "An existing stable path ID was lost"
        assert len(original.findall(".//s:path", NS)) == len(final.findall(".//s:path", NS)), (
            "A path was lost or extra geometry was created"
        )
        unidentified = [p for p in original.findall(".//s:path", NS) if "id" not in p.attrib]
        assert all(p.attrib.get("data-calibration-mm") == "100" for p in unidentified), (
            "The probe cannot identify an original unlabelled non-calibration path"
        )
        added_ids = final_paths.keys() - paths.keys()
        displacements = {}
        for identity, geometry in paths.items():
            _same_path(geometry, final_paths[identity])
            old, new = before_bounds[identity], after_bounds[identity]
            expected_delta = [10, 15] if identity in moved_ids else [0, 0]
            delta = [new[0] - old[0], new[1] - old[1]]
            assert all(math.isclose(a, b, abs_tol=0.002) for a, b in zip(delta, expected_delta))
            assert all(math.isclose(a, b, abs_tol=0.002) for a, b in zip(old[2:], new[2:]))
            displacements[identity] = delta
        before_other_text = {
            p.attrib["id"]: "".join(p.itertext())
            for p in original.findall(".//s:text", NS)
            if p.attrib["id"] != label_id
        }
        after_other_text = {
            p.attrib["id"]: "".join(p.itertext())
            for p in final.findall(".//s:text", NS)
            if p.attrib["id"] != label_id
        }
        assert before_other_text == after_other_text, "Another text object was modified"
        for name in ("width", "height", "viewBox"):
            assert original.attrib[name] == final.attrib[name], "Physical page size changed"
        calibration = original.find(".//s:path[@data-calibration-mm='100']", NS)
        after_calibration = final.find(".//s:path[@data-calibration-mm='100']", NS)
        assert calibration is not None and after_calibration is not None
        _same_path(calibration.attrib["d"], after_calibration.attrib["d"])
        assert added_ids <= {after_calibration.attrib.get("id")}, (
            "An added ID belongs to something other than the original calibration path"
        )
        # This page-GUIDES path has no ID in the export, so query its parent.
        assert all(
            math.isclose(a, b, abs_tol=0.002)
            for a, b in zip(before_bounds["page-GUIDES"], after_bounds["page-GUIDES"])
        )
        cut_before = part.findall("s:g[@data-role='CUT']/s:path", NS)
        cut_after = final_part.findall("s:g[@data-role='CUT']/s:path", NS)
        assert len(cut_before) == len(cut_after)
        assert all(
            a.attrib.get("fill-rule", "evenodd") == b.attrib.get("fill-rule", "evenodd")
            for a, b in zip(cut_before, cut_after)
        ), "Hole fill-rule changed"
        assert {p.name: _sha(p) for p in source_path.parent.iterdir() if p.is_file()} == bundle
        assert _sha(original_copy) == _sha(source_path), "Original copy was unexpectedly edited"
        assert _git("rev-parse", "HEAD") == sha and _sha(Path(__file__)) == script_hash
        report["roundtrip_assertions"] = {
            "path_count": len(paths),
            "total_path_count_including_calibration": len(final.findall(".//s:path", NS)),
            "editor_added_id_to_existing_calibration": sorted(added_ids),
            "part_role_groups": list(ROLES),
            "native_path_commands_preserved": True,
            "all_local_coordinates_unchanged_mm_tolerance": 0.00002,
            "other_text_objects_unchanged": True,
            "original_bundle_unchanged": True,
            "calibration_100mm_and_page_size_unchanged": True,
            "cut_loop_count": len(cut_before),
            "all_path_displacements_px": displacements,
        }
        command(
            [
                str(edited),
                "--export-filename=" + str(out / "editor-final-render.png"),
                "--export-width=840",
            ]
        )
        report["status"] = "PASS"
    except Exception:
        report.update(status="FAIL", error=traceback.format_exc())
    finally:
        if process is not None and process.poll() is None:
            if own_hwnd is not None and user32 is not None:
                user32.PostMessageW(own_hwnd, 0x0010, 0, 0)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()  # Only the proof's own process and disposable edited copy.
                process.wait(timeout=5)
        report["origin_bundle_preserved_after_run"] = {
            p.name: _sha(p) for p in source_path.parent.iterdir() if p.is_file()
        } == bundle
        save_report()
    print(json.dumps({k: report[k] for k in ("status", "source_sha", "elapsed_seconds")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
