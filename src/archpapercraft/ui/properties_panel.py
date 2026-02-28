"""Properties panel — shows and edits parameters of the selected SceneNode."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.scene_graph.node import SceneNode


class PropertiesPanel(QWidget):
    """Editable property sheet for the currently selected node."""

    param_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._node: SceneNode | None = None

        self._layout = QVBoxLayout(self)
        self._info_label = QLabel("No selection")
        self._layout.addWidget(self._info_label)

        # Transform group
        self._tf_group = QGroupBox("Transform")
        self._tf_form = QFormLayout()
        self._tf_group.setLayout(self._tf_form)
        self._pos_x = self._spin("Position X")
        self._pos_y = self._spin("Position Y")
        self._pos_z = self._spin("Position Z")
        self._rot_x = self._spin("Rotation X", -360, 360)
        self._rot_y = self._spin("Rotation Y", -360, 360)
        self._rot_z = self._spin("Rotation Z", -360, 360)
        self._layout.addWidget(self._tf_group)

        # Parameters group (dynamic)
        self._param_group = QGroupBox("Parameters")
        self._param_form = QFormLayout()
        self._param_group.setLayout(self._param_form)
        self._layout.addWidget(self._param_group)

        self._layout.addStretch()
        self._param_spins: dict[str, QDoubleSpinBox] = {}

    def _spin(self, label: str, lo: float = -10000, hi: float = 10000) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setDecimals(3)
        sb.setSingleStep(0.1)
        self._tf_form.addRow(label, sb)
        sb.valueChanged.connect(self._on_transform_changed)
        return sb

    def set_node(self, node: SceneNode | None) -> None:
        self._node = node
        if node is None:
            self._info_label.setText("No selection")
            return

        self._info_label.setText(f"{node.name}  ({node.node_type.name})")

        # populate transform
        self._pos_x.blockSignals(True)
        self._pos_y.blockSignals(True)
        self._pos_z.blockSignals(True)
        self._rot_x.blockSignals(True)
        self._rot_y.blockSignals(True)
        self._rot_z.blockSignals(True)

        self._pos_x.setValue(node.transform.position[0])
        self._pos_y.setValue(node.transform.position[1])
        self._pos_z.setValue(node.transform.position[2])
        self._rot_x.setValue(node.transform.rotation[0])
        self._rot_y.setValue(node.transform.rotation[1])
        self._rot_z.setValue(node.transform.rotation[2])

        self._pos_x.blockSignals(False)
        self._pos_y.blockSignals(False)
        self._pos_z.blockSignals(False)
        self._rot_x.blockSignals(False)
        self._rot_y.blockSignals(False)
        self._rot_z.blockSignals(False)

        # rebuild parameter form
        self._rebuild_params(node)

    def _rebuild_params(self, node: SceneNode) -> None:
        # clear old
        while self._param_form.rowCount() > 0:
            self._param_form.removeRow(0)
        self._param_spins.clear()

        for key, value in node.parameters.items():
            if isinstance(value, (int, float)):
                sb = QDoubleSpinBox()
                sb.setRange(-100000, 100000)
                sb.setDecimals(3)
                sb.setValue(float(value))
                sb.setObjectName(key)
                sb.valueChanged.connect(self._on_param_changed)
                self._param_form.addRow(key, sb)
                self._param_spins[key] = sb

    def _on_transform_changed(self) -> None:
        if self._node is None:
            return
        self._node.transform.position[0] = self._pos_x.value()
        self._node.transform.position[1] = self._pos_y.value()
        self._node.transform.position[2] = self._pos_z.value()
        self._node.transform.rotation[0] = self._rot_x.value()
        self._node.transform.rotation[1] = self._rot_y.value()
        self._node.transform.rotation[2] = self._rot_z.value()
        self._node.mark_dirty()
        self.param_changed.emit()

    def _on_param_changed(self) -> None:
        if self._node is None:
            return
        for key, sb in self._param_spins.items():
            self._node.set_param(key, sb.value())
        self.param_changed.emit()
