"""Object tree widget — reflects the scene_graph hierarchy."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from archpapercraft.scene_graph.node import SceneNode
from archpapercraft.scene_graph.scene import Scene


class ObjectTreeWidget(QTreeWidget):
    """Displays the scene node tree in a dock panel."""

    node_selected = Signal(str)  # emits node_id

    def __init__(self, scene: Scene | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Název", "Typ"])
        self.setColumnCount(2)
        self._scene = scene or Scene()
        self._rebuild()
        self.itemClicked.connect(self._on_item_clicked)

    def set_scene(self, scene: Scene) -> None:
        self._scene = scene
        self._rebuild()

    def _rebuild(self) -> None:
        self.clear()
        self._add_children(self._scene.root, None)
        self.expandAll()

    def _add_children(self, node: SceneNode, parent_item: QTreeWidgetItem | None) -> None:
        for child in node.children:
            item = QTreeWidgetItem()
            item.setText(0, child.name)
            item.setText(1, child.node_type.name)
            item.setData(0, Qt.ItemDataRole.UserRole, child.node_id)
            if parent_item is None:
                self.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            self._add_children(child, item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if node_id:
            self.node_selected.emit(node_id)

    def select_all(self) -> None:
        """Select all top-level items in the tree."""
        self.selectAll()
