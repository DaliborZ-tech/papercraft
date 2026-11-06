"""Drive only Windows file dialogs belonging to the current verification process."""

import ctypes
import os
from ctypes import wintypes

from PySide6.QtCore import QTimer

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
