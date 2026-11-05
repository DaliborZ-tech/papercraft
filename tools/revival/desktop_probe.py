"""Run the actual application entry point and bounded Windows desktop diagnostics.

Only own-process native file dialogs are driven. No user settings or old projects
are written. UI snapshots complement, and do not replace, numeric evidence.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile
import traceback
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / (sys.argv[1] if len(sys.argv)>1 else "docs/revival/evidence")
OUT.mkdir(parents=True, exist_ok=True)
if (OUT/'desktop-project.apcraft').exists():
    raise FileExistsError('Use a fresh output directory to preserve prior desktop evidence')
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="papercraft-desktop-settings-")

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from OpenGL import GL
import archpapercraft.project_io.project as project_module
project_module._LOG_DIR = Path(tempfile.mkdtemp(prefix="papercraft-desktop-log-"))
from archpapercraft.ui.main_window import MainWindow
from archpapercraft.ui.wizard import ProjectWizard

REPORT = {"proof_kind": "Windows desktop, QTest actions and native dialog automation", "steps": [], "exceptions": []}
USER32 = ctypes.WinDLL("user32", use_last_error=True)
USER32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
USER32.SendMessageW.restype = wintypes.LPARAM
CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
USER32.EnumWindows.argtypes = [CALLBACK, wintypes.LPARAM]
USER32.EnumChildWindows.argtypes = [wintypes.HWND, CALLBACK, wintypes.LPARAM]


def window_info(hwnd):
    title = ctypes.create_unicode_buffer(1024)
    cls = ctypes.create_unicode_buffer(128)
    USER32.GetWindowTextW(hwnd, title, len(title))
    USER32.GetClassNameW(hwnd, cls, len(cls))
    return dict(hwnd=int(hwnd), title=title.value, cls=cls.value)


def native_dialogs():
    dialogs = []
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info = window_info(hwnd)
        if pid.value == os.getpid() and info["cls"] == "#32770" and USER32.IsWindowVisible(hwnd):
            dialogs.append(info)
        return True
    USER32.EnumWindows(CALLBACK(visit), 0)
    return dialogs


def drive_file_dialog(action, path):
    """Set file name in own-process native Windows dialog, then accept it."""
    attempts = [0]
    record = dict(action=action, path=str(path), native_seen=False, accepted=False)
    REPORT["steps"].append(record)
    def drive():
        attempts[0] += 1
        dialogs = native_dialogs()
        if dialogs:
            dlg = dialogs[0]
            record.update(native_seen=True, native_class=dlg['cls'], title=dlg['title'])
            controls = []
            def child(hwnd, _):
                controls.append(window_info(hwnd))
                return True
            USER32.EnumChildWindows(dlg['hwnd'], CALLBACK(child), 0)
            edits = [c for c in controls if c['cls'] == 'Edit' and USER32.IsWindowVisible(c['hwnd'])]
            if edits:
                value = ctypes.create_unicode_buffer(str(path))
                USER32.SendMessageW(edits[0]['hwnd'], 0x000C, 0, ctypes.addressof(value))
                USER32.PostMessageW(dlg['hwnd'], 0x0111, 1, 0)
                record['accepted'] = True
                return
        if attempts[0] < 20:
            QTimer.singleShot(250, drive)
        else:
            record['limit'] = 'Native file name control not reached in 5 seconds'
            for dlg in dialogs:
                USER32.PostMessageW(dlg['hwnd'], 0x0010, 0, 0)
    QTimer.singleShot(300, drive)


def steps(window):
    try:
        REPORT['platform'] = QApplication.platformName()
        REPORT['viewport_valid'] = window.viewport.isValid()
        window.viewport.makeCurrent()
        REPORT['opengl'] = {key: str(GL.glGetString(value)) for key, value in [('version',GL.GL_VERSION),('renderer',GL.GL_RENDERER),('vendor',GL.GL_VENDOR)]}
        window.viewport.doneCurrent()
        window.grab().save(str(OUT/'desktop-empty.png'))
        def accept_wizard():
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget,ProjectWizard):
                    widget._name.setText('P0 desktop diagnostic')
                    widget._units.setCurrentText('mm')
                    QTest.mouseClick(widget.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok),Qt.MouseButton.LeftButton)
        QTimer.singleShot(150,accept_wizard)
        window._shortcut_actions['new_project'].trigger()
        REPORT['steps'].append(dict(action='new_project_wizard',name=window.project.settings.name,units=window.project.settings.units))
        add = next(a for a in window.findChildren(QAction) if a.data() == 'PRIMITIVE_BOX')
        add.trigger()
        item = window.object_tree.topLevelItem(0)
        QTest.mouseClick(window.object_tree.viewport(), Qt.MouseButton.LeftButton, pos=window.object_tree.visualItemRect(item).center())
        for key,value in [('dx',100.),('dy',60.),('dz',40.)]:
            window.properties._param_spins[key].setValue(value)
        node = window.project.scene.root.children[0]
        REPORT['steps'].append(dict(action='add_select_edit',parameters=dict(node.parameters),selected=window._selected_node.node_id == node.node_id))
        drive_file_dialog('native_save',OUT/'desktop-project.apcraft')
        window._shortcut_actions['save_as'].trigger()
        REPORT['saved'] = (OUT/'desktop-project.apcraft').exists()
        drive_file_dialog('native_open',OUT/'desktop-project.apcraft')
        window._shortcut_actions['open_project'].trigger()
        REPORT['reopened'] = window.project.file_path == OUT/'desktop-project.apcraft'
        for button in [window.papercraft._btn_analyze,window.papercraft._btn_auto_seams,window.papercraft._btn_unfold]:
            QTest.mouseClick(button,Qt.MouseButton.LeftButton)
        REPORT['workflow'] = dict(analysis=window.papercraft._lbl_analyze.text(),seams=window.papercraft._lbl_seams.text(),unfold=window.papercraft._lbl_unfold.text(),parts=len(window.papercraft._unfolded_parts or []))
        for fmt, button in [('svg',window.papercraft._btn_svg),('pdf',window.papercraft._btn_pdf)]:
            drive_file_dialog('native_export_'+fmt,OUT/('desktop-export.'+fmt))
            def close_message():
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget,QMessageBox):
                        REPORT['steps'].append(dict(action='message',title=widget.windowTitle(),text=widget.text()))
                        widget.accept()
            timer = QTimer()
            timer.timeout.connect(close_message)
            timer.start(200)
            QTest.mouseClick(button,Qt.MouseButton.LeftButton)
            timer.stop()
        QTest.qWait(300)
        window._on_node_selected(window.project.scene.root.children[0].node_id)
        window._focus_selection()
        QTest.qWait(200)
        window.viewport.grabFramebuffer().save(str(OUT/'desktop-framebuffer.png'))
        window.grab().save(str(OUT/'desktop-model.png'))
        window._selected_node = None
        window.viewport.set_selected_node(None)
        QTest.mouseClick(window.viewport,Qt.MouseButton.LeftButton,pos=window.viewport.rect().center())
        REPORT['viewport_click_selection'] = window._selected_node is not None
        old_parts = window.papercraft._unfolded_parts
        old_mesh = window.papercraft._cached_mesh
        node = window.project.scene.root.children[0]
        window._on_node_selected(node.node_id)
        window.properties._param_spins['dx'].setValue(120.)
        REPORT['stale_after_edit'] = dict(cached_parts_same=window.papercraft._unfolded_parts is old_parts,cached_mesh_same=window.papercraft._cached_mesh is old_mesh,current_model_dx=node.parameters['dx'],mesh_current_x_extent=float(node.mesh.vertices[:,0].ptp()) if hasattr(node.mesh.vertices[:,0],'ptp') else float(__import__('numpy').ptp(node.mesh.vertices[:,0])),unfold_label=window.papercraft._lbl_unfold.text())
        # Undo path deliberately clears cached parts, unlike the direct parameter edit.
        window.command_stack.mark_saved()
    except Exception:
        REPORT['exceptions'].append(traceback.format_exc())
    finally:
        (OUT/'desktop-results.json').write_text(json.dumps(REPORT,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps(REPORT,indent=2,ensure_ascii=False),flush=True)
        QApplication.instance().quit()


original_show = MainWindow.show
def show_and_probe(self):
    original_show(self)
    QTimer.singleShot(1000,lambda: steps(self))
MainWindow.show = show_and_probe

if __name__ == '__main__':
    from archpapercraft.app import main
    main()
