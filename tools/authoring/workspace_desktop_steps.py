"""Real widget navigation for existing proofs in the activity workspace.

This adapter changes neither domain geometry nor the native input guards.
Offscreen component checks of these helpers are not a native desktop proof.
"""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

SECTION_CONTEXTS = {
    "Jednotky a tvorba": "Modelování",
    "Profil a křivky": "Modelování",
    "Bod obrysu": "Modelování",
    "Umístění v prostoru": "Modelování",
    "Hrany, spoj a chlopeň": "Spoje a rozvin",
    "Autorské spoje a záložky": "Spoje a rozvin",
    "Díl na papíře": "Stránky",
}

HOUSE_NAMES = {
    "south": "Jizni stena", "north": "Severni stena",
    "west_gable": "Zapadni stit", "east_gable": "Vychodni stit",
    "roof_south": "Jizni strecha", "roof_north": "Severni strecha",
    "base": "Zakladna", "brace": "Vyztuha", "soffit": "Podhled",
    "band_root": "Lepici pasek", "temporary_scrap": "Docasny dil",
}


class WorkspaceDesktopSteps:
    def workspace(self, context):
        bar = getattr(self.w, "workspace_bar", None)
        if bar is None:
            return  # Historical windows have no activity navigation.
        if self.w.workspace_context != context:
            self.click(bar.buttons[context])
            self.check(self.w.workspace_context == context,
                       "Actual workspace button did not activate " + context)
            self.log("actual_workspace_button", context=context)

    def workspace_widget(self, widget):
        if not hasattr(self.w, "workspace_bar") or widget.window() is not self.w:
            return
        for title, (header, box) in self.w.sections.items():
            if widget is header or widget is box or box.isAncestorOf(widget):
                self.workspace(SECTION_CONTEXTS[title])
                return
        if widget is self.w.sketch or self.w.sketch.isAncestorOf(widget):
            self.workspace("Modelování")
            if not self.w.sketch.isVisible():
                self.click(self.w.workspace_bar.sketch_button)
                self.check(self.w.sketch.isVisible(), "Actual Skica toggle did not reveal sketch")
        elif widget is self.w.paper or self.w.paper.isAncestorOf(widget):
            if not self.w.paper.isVisible():
                self.workspace("Stránky")
        elif widget is self.w.viewport:
            if not self.w.viewport.isVisible():
                self.workspace("Modelování")
        elif widget in (self.w.tree, self.w.selection_name):
            if not widget.isVisible():
                self.workspace("Modelování")

    def name_house_surface(self, role, surface_id):
        if role not in HOUSE_NAMES or not hasattr(self.w, "selection_name"):
            return
        self.select(surface_id)
        field = self.visible(self.w.selection_name)
        field.setFocus()
        QTest.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(field, HOUSE_NAMES[role])
        QTest.keyClick(field, Qt.Key.Key_Return)
        QTest.qWait(60)
        self.check(self.w.project.surfaces[surface_id].name == HOUSE_NAMES[role],
                   "Inline user name was not committed")
        self.log("actual_inline_surface_name", role=role, text=HOUSE_NAMES[role])

    def view_home(self, view):
        self.visible(view)
        target = view.viewport() if hasattr(view, "viewport") else view
        QTest.mouseClick(target, Qt.MouseButton.LeftButton, pos=QPoint(8, 8))
        before = self.action_counts.get("focus_all", 0)
        QTest.keyClick(view, Qt.Key.Key_Home)
        QTest.qWait(60)
        self.check(self.action_counts.get("focus_all", 0) == before + 1,
                   "Actual Home did not trigger the active-view Fit All QAction")
