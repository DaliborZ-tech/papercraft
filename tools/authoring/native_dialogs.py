"""Drive only Windows file dialogs belonging to the current verification process."""

import ctypes
import os
from ctypes import wintypes

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest

USER32 = ctypes.WinDLL("user32", use_last_error=True)
USER32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
USER32.SendMessageW.restype = wintypes.LPARAM
CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
USER32.EnumWindows.argtypes = [CALLBACK, wintypes.LPARAM]
USER32.EnumChildWindows.argtypes = [wintypes.HWND, CALLBACK, wintypes.LPARAM]


def info(hwnd):
    title = ctypes.create_unicode_buffer(1024)
    cls = ctypes.create_unicode_buffer(128)
    USER32.GetWindowTextW(hwnd, title, len(title))
    USER32.GetClassNameW(hwnd, cls, len(cls))
    return dict(hwnd=int(hwnd), title=title.value, cls=cls.value)


def wheel_at(window, viewport, point, records):
    """Real Windows wheel at a verified own client point, with cursor restoration.

    QTest6.12's QWindow wheel helper forwards logical coordinates to the native
    handler without the mouse helper's DPI conversion. Native client mapping
    avoids that mismatch and verifies the real desktop hit before global input.
    """
    USER32.GetForegroundWindow.restype = wintypes.HWND
    USER32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    USER32.GetAncestor.restype = wintypes.HWND
    USER32.WindowFromPoint.argtypes = [wintypes.POINT]
    USER32.WindowFromPoint.restype = wintypes.HWND
    USER32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    USER32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    USER32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    USER32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, wintypes.WPARAM]
    USER32.mouse_event.argtypes = [wintypes.DWORD] * 4 + [wintypes.WPARAM]
    window.raise_()
    window.activateWindow()
    QTest.qWait(100)
    hwnd, pid = int(window.winId()), wintypes.DWORD()
    USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    assert pid.value == os.getpid() and USER32.GetForegroundWindow() == hwnd, (
        "Native wheel requires this proof's foreground window")
    assert not any(USER32.GetAsyncKeyState(key) & 0x8000 for key in (16, 17, 18, 1, 2, 4)), (
        "Refusing wheel input while an existing user modifier or mouse button is held")
    logical = viewport.mapTo(window, point)
    rect, origin, previous = wintypes.RECT(), wintypes.POINT(), wintypes.POINT()
    assert USER32.GetClientRect(hwnd, ctypes.byref(rect))
    assert USER32.ClientToScreen(hwnd, ctypes.byref(origin))
    assert USER32.GetCursorPos(ctypes.byref(previous))
    sx, sy = rect.right/window.width(), rect.bottom/window.height()
    ratio = window.devicePixelRatioF()
    assert abs(sx-ratio) <= 2/window.width() and abs(sy-ratio) <= 2/window.height(), (
        "Native client and logical window dimensions have an unproved DPI mapping")
    target = wintypes.POINT(origin.x+round(logical.x()*sx), origin.y+round(logical.y()*sy))
    hit = USER32.WindowFromPoint(target)
    assert USER32.GetAncestor(hit, 2) == hwnd, "Native wheel target is obscured by another window"
    record = dict(own_pid=pid.value, own_hwnd=hwnd, hit_hwnd=int(hit),
                  target_native=[target.x, target.y], target_logical=[logical.x(), logical.y()],
                  native_client=[rect.right, rect.bottom], device_pixel_ratio=ratio,
                  method="Win32 actual cursor Ctrl+wheel, verified own root HWND")
    records.append(record)
    held = False
    try:
        assert USER32.SetCursorPos(target.x, target.y)
        assert USER32.GetAncestor(USER32.WindowFromPoint(target), 2) == hwnd
        assert USER32.GetForegroundWindow() == hwnd
        USER32.keybd_event(17, 0, 0, 0)
        held = True
        QTest.qWait(40)
        assert USER32.GetForegroundWindow() == hwnd
        USER32.mouse_event(0x0800, 0, 0, 120, 0)
        QTest.qWait(100)
    finally:
        if held:
            USER32.keybd_event(17, 0, 2, 0)
        USER32.SetCursorPos(previous.x, previous.y)
        QTest.qWait(40)


def schedule_path(path, records):
    record = dict(path=str(path), native_seen=False, accepted=False)
    records.append(record)
    attempts = [0]

    def drive():
        attempts[0] += 1
        dialogs = []

        def visit(hwnd, _):
            pid = wintypes.DWORD()
            USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            item = info(hwnd)
            if (
                pid.value == os.getpid()
                and item["cls"] == "#32770"
                and USER32.IsWindowVisible(hwnd)
            ):
                dialogs.append(item)
            return True

        USER32.EnumWindows(CALLBACK(visit), 0)
        if dialogs:
            dialog = dialogs[0]
            if path.is_dir():
                # The app deliberately starts this directory picker in the saved
                # project's existing export folder; confirm that real native choice.
                record.update(native_seen=True,title=dialog['title'],directory_confirmation=True)
                USER32.PostMessageW(dialog['hwnd'],0x0111,1,0)
                record['accepted']=True
                return
            controls = []

            def child(hwnd, _):
                controls.append(info(hwnd))
                return True

            USER32.EnumChildWindows(dialog["hwnd"], CALLBACK(child), 0)
            edits = [
                c for c in controls if c["cls"] == "Edit" and USER32.IsWindowVisible(c["hwnd"])
            ]
            if edits:
                record.update(native_seen=True, title=dialog["title"])
                value = ctypes.create_unicode_buffer(str(path))
                USER32.SendMessageW(edits[0]["hwnd"], 0x000C, 0, ctypes.addressof(value))
                USER32.PostMessageW(dialog["hwnd"], 0x0111, 1, 0)
                record["accepted"] = True
                return
        if attempts[0] < 30:
            QTimer.singleShot(200, drive)
        else:
            record["error"] = "File dialog name control not reached"
            for dialog in dialogs:
                USER32.PostMessageW(dialog["hwnd"], 0x0010, 0, 0)

    QTimer.singleShot(250, drive)
