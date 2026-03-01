"""Panel vlastností — zobrazuje a edituje parametry vybraného uzlu scény."""

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
    """Editovatelný formulář vlastností aktuálně vybraného uzlu."""

    param_changed = Signal()
    # Signal(str, float) — (param_key, new_value) for undo
    param_value_changed = Signal(str, float)
    # Signal() — transform changed, for undo snapshot
    transform_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._node: SceneNode | None = None

        self._layout = QVBoxLayout(self)
        self._info_label = QLabel("Žádný výběr")
        self._layout.addWidget(self._info_label)

        # Transform group
        self._tf_group = QGroupBox("Transformace")
        self._tf_form = QFormLayout()
        self._tf_group.setLayout(self._tf_form)
        self._pos_x = self._spin("Pozice X")
        self._pos_y = self._spin("Pozice Y")
        self._pos_z = self._spin("Pozice Z")
        self._rot_x = self._spin("Rotace X", -360, 360)
        self._rot_y = self._spin("Rotace Y", -360, 360)
        self._rot_z = self._spin("Rotace Z", -360, 360)
        self._layout.addWidget(self._tf_group)

        # Parameters group (dynamic)
        self._param_group = QGroupBox("Parametry")
        self._param_form = QFormLayout()
        self._param_group.setLayout(self._param_form)
        self._layout.addWidget(self._param_group)

        self._layout.addStretch()
        self._param_spins: dict[str, QDoubleSpinBox] = {}
        self._last_transform_snapshot: tuple[tuple[float, ...], tuple[float, ...]] | None = None

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
            self._info_label.setText("Žádný výběr")
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

        # Snapshot transformace pro undo
        self._last_transform_snapshot = (
            tuple(node.transform.position.tolist()),
            tuple(node.transform.rotation.tolist()),
        )

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
        self.transform_changed.emit()
        self.param_changed.emit()

    def _on_param_changed(self) -> None:
        if self._node is None:
            return
        sender = self.sender()
        key = sender.objectName() if sender else None
        # Uložit starou hodnotu PŘED aplikací změny (pro undo)
        old_value = self._node.parameters.get(key) if key else None
        for k, sb in self._param_spins.items():
            self._node.set_param(k, sb.value())
        if key and old_value is not None:
            self.param_value_changed.emit(key, old_value)
        self.param_changed.emit()
