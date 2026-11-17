"""Independent, interactive Qt expert walkthrough; no domain writes or fixtures.

Commands are chosen after inspecting the actual visible UI. This is not a
novice/human usability test. Only own-process windows receive UI input.
"""
import ctypes
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGraphicsView, QLabel, QLineEdit, QPushButton, QScrollArea, QToolButton,
    QTreeWidget, QWidget, QListWidget, QCheckBox,
)
from shiboken6 import isValid
from archpapercraft.ui.author_window import AuthorMainWindow
import archpapercraft.ui.author_window as source

OUT = Path(__file__).parent
assert Path(source.__file__).resolve() == ROOT / "src/archpapercraft/ui/author_window.py"
app = QApplication(sys.argv)
app.setApplicationName("ArchPapercraft Studio")
app.setStyle("Fusion")
window = AuthorMainWindow(settings=QSettings(str(OUT / "settings.ini"), QSettings.IniFormat))
window.resize(1366, 768)
window.show()
user = ctypes.windll.user32
user.GetForegroundWindow.restype = ctypes.c_void_p
user.WindowFromPoint.restype = ctypes.c_void_p
user.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]


def log(value):
    with (OUT / "events.jsonl").open("a", encoding="utf8") as out:
        out.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def context():
    return app.activeModalWidget() or window


def fields():
    result = []
    for layout in context().findChildren(QFormLayout):
        for row in range(layout.rowCount()):
            label = layout.itemAt(row, QFormLayout.LabelRole)
            field = layout.itemAt(row, QFormLayout.FieldRole)
            if label and field and label.widget() and field.widget():
                result.append((label.widget().text(), field.widget()))
    return result


def dump():
    return dict(title=context().windowTitle(), size=[window.width(), window.height()],
                pid=os.getpid(), hwnd=int(window.winId()),
                dpi=window.devicePixelRatioF(), screen=app.primaryScreen().geometry().getRect(),
                logical_dpi=app.primaryScreen().logicalDotsPerInch(),
                frame=window.frameGeometry().getRect(), minimum_hint=[window.minimumSizeHint().width(),window.minimumSizeHint().height()],
                menus=[a.text() for a in window.menuBar().actions()],
                labels=[w.text() for w in context().findChildren(QLabel) if isValid(w) and w.isVisible()],
                issues=[list_widget.item(i).text() for list_widget in context().findChildren(QListWidget)
                        for i in range(list_widget.count())],
                buttons=[dict(text=w.text(), enabled=w.isEnabled()) for cls in (QPushButton,QToolButton)
                         for w in context().findChildren(cls) if w.isVisible()],
                fields=[dict(label=label, type=w.metaObject().className(), visible=w.isVisible(),
                             text=w.currentText() if isinstance(w,QComboBox) else w.text() if hasattr(w,"text") else "")
                        for label,w in fields()],
                combo_options={label:[w.itemText(i) for i in range(w.count())]
                               for label,w in fields() if isinstance(w,QComboBox)},
                tree=[window.tree.topLevelItem(i).text(0) for i in range(window.tree.topLevelItemCount())])


def expose(widget):
    parent = widget.parentWidget()
    while parent:
        if isinstance(parent, QScrollArea):
            parent.ensureWidgetVisible(widget)
        parent = parent.parentWidget()
    assert widget.isVisible() and widget.isEnabled(), (widget, widget.isVisible(), widget.isEnabled())


def click(widget):
    expose(widget)
    QTest.mouseClick(widget, Qt.LeftButton)


def execute(command):
    op=command["op"]
    if op == "dump":
        (OUT / "ui.json").write_text(json.dumps(dump(),ensure_ascii=False,indent=2),encoding="utf8")
    elif op == "screen":
        app.primaryScreen().grabWindow(int(context().winId())).save(str(OUT / (command["name"]+".png")))
    elif op == "menu":
        menus=window.menuBar()
        action=next(a for a in menus.actions() if command["path"][0] in a.text())
        QTest.mouseClick(menus,Qt.LeftButton,pos=menus.actionGeometry(action).center())
        menu=action.menu()
        target=next(a for a in menu.actions() if command["path"][1] in a.text())
        assert target.isEnabled()
        QTest.mouseClick(menu,Qt.LeftButton,pos=menu.actionGeometry(target).center())
    elif op == "button":
        matches=[w for cls in (QPushButton,QToolButton) for w in context().findChildren(cls)
                 if w.text()==command["text"] and w.isVisible()]
        assert len(matches)==1, [(w.text(),w.isVisible()) for w in matches]
        click(matches[0])
    elif op in ("field","choose"):
        matches=[w for label,w in fields() if label.startswith(command["label"])]
        assert len(matches)==1, command
        widget=matches[0];expose(widget)
        if op == "choose":
            assert isinstance(widget,QComboBox)
            index=widget.findText(command["text"])
            assert index>=0, command
            widget.setFocus();QTest.keyClick(widget,Qt.Key_Home)
            for _ in range(index):QTest.keyClick(widget,Qt.Key_Down)
        else:
            widget.setFocus();QTest.keyClick(widget,Qt.Key_A,Qt.ControlModifier)
            QTest.keyClicks(widget,command["text"])
            if command.get("commit",True):QTest.keyClick(widget,Qt.Key_Tab)
    elif op == "key":
        QTest.keySequence(app.focusWidget() or context(),command["key"])
    elif op == "path":
        # Reuse only the verified own-PID native file-picker adapter, never a
        # standard model/workflow driver or a fake file-dialog return value.
        sys.path.insert(0,str(ROOT / "tools/authoring"))
        from native_dialogs import schedule_path
        schedule_path(Path(command["path"]),native_records)
    elif op == "check":
        widget=next(w for w in context().findChildren(QCheckBox) if w.text()==command["text"])
        click(widget)
    elif op == "issue":
        matches=[(widget,i) for widget in context().findChildren(QListWidget)
                 for i in range(widget.count()) if command["text"] in widget.item(i).text()]
        assert len(matches)==1
        widget,i=matches[0];widget.scrollToItem(widget.item(i))
        QTest.mouseClick(widget.viewport(),Qt.LeftButton,pos=widget.visualItemRect(widget.item(i)).center())
    elif op == "tree":
        tree=window.tree
        matches=tree.findItems(command["text"],Qt.MatchContains | Qt.MatchRecursive)
        assert len(matches)==1, len(matches)
        tree.scrollToItem(matches[0]);QTest.mouseClick(tree.viewport(),Qt.LeftButton,pos=tree.visualItemRect(matches[0]).center())
    elif op == "canvas":
        views=[v for v in context().findChildren(QGraphicsView) if v.metaObject().className()==command["class"] and v.isVisible()]
        assert len(views)==1
        view=views[0]
        from PySide6.QtCore import QPointF
        point=view.mapFromScene(QPointF(*command["point"]))
        assert view.viewport().rect().contains(point), (point,view.viewport().rect())
        QTest.mouseClick(view.viewport(),Qt.LeftButton,pos=point)
    elif op == "native_file":
        hwnd=user.GetForegroundWindow();pid=ctypes.c_ulong()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        assert pid.value==os.getpid(), (hwnd,pid.value,os.getpid())
        user.GetDlgItem.restype=ctypes.c_void_p
        user.GetDlgItem.argtypes=[ctypes.c_void_p,ctypes.c_int]
        edit=user.GetDlgItem(hwnd,1148)
        assert edit, "Native file-name edit missing"
        user.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_void_p]
        user.SendMessageW(edit,12,0,ctypes.cast(ctypes.c_wchar_p(command["path"]),ctypes.c_void_p))
        button=user.GetDlgItem(hwnd,1);assert button
        log(dict(native_hwnd=hwnd,pid=pid.value,file_edit=edit,button=button))
        user.SendMessageW(button,245,0,None)
    elif op == "state":
        # Read-only observation. Never used to construct or alter the model.
        (OUT / "observed.json").write_text(json.dumps(window.project.to_dict(),ensure_ascii=False,indent=2),encoding="utf8")
    elif op == "resize":
        window.resize(*command["size"])
        window.move(20,35)
    elif op == "quit":
        app.quit()
    else:raise ValueError(op)


count=0
native_records=[]
def poll():
    global count
    path=OUT/"commands.jsonl"
    if not path.exists():return
    lines=path.read_text(encoding="utf8").splitlines()
    for line in lines[count:count+1]:
        count+=1
        command=json.loads(line)
        def do(command=command):
            try:
                execute(command)
                log(dict(command=command,status="DONE"))
            except BaseException:
                log(dict(command=command,status="ERROR",traceback=traceback.format_exc()))
        QTimer.singleShot(0,do)

timer=QTimer();timer.timeout.connect(poll);timer.start(200)
app.aboutToQuit.connect(lambda: log(dict(about_to_quit=True,window_visible=window.isVisible(),title=window.windowTitle(),state=window.project.to_dict())))
heartbeat=QTimer();heartbeat.timeout.connect(lambda:(log(dict(heartbeat=True,visible=window.isVisible(),title=window.windowTitle())), (OUT/'native-dialogs.json').write_text(json.dumps(native_records,indent=2),encoding='utf8')));heartbeat.start(10000)
log(dict(start=True,pid=os.getpid(),hwnd=int(window.winId()),source=source.__file__,
         evidence_type="EXPERT_NATIVE_QT_WIDGET_AUTOMATION_NOT_NOVICE_HUMAN"))
app.exec()
