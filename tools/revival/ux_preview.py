"""Render the offline UX proposal in a hidden Qt WebEngine window; no hosting."""
import json
from pathlib import Path
import sys
from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

root=Path(__file__).resolve().parents[2]
out=root/'docs/revival/evidence/ux-preview'
out.mkdir(exist_ok=True)
app=QApplication([])
view=QWebEngineView()
view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,True)
view.resize(1440,1000)
states=iter(['empty','house','joint','stale','collision','export'])
records=[]
def capture_next():
    state=next(states,None)
    if state is None:
        (out/'render-results.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        app.quit()
        return
    def rendered(_):
        def capture():
            target=out/f'{state}.png'
            saved=view.grab().save(str(target))
            records.append(dict(state=state,screenshot_saved=saved))
            capture_next()
        QTimer.singleShot(150,capture)
    view.page().runJavaScript(f"showState('{state}')",rendered)
def loaded(ok):
    if not ok:
        print('HTML load failed')
        app.exit(1)
        return
    capture_next()
view.loadFinished.connect(loaded)
view.load(QUrl.fromLocalFile(str(root/'docs/revival/ux-prototype.html')))
view.show()
QTimer.singleShot(20000,lambda: app.exit(124))
sys.exit(app.exec())
