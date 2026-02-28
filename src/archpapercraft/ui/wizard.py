"""Průvodce novým projektem."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from archpapercraft.project_io.project import ProjectSettings


class ProjectWizard(QDialog):
    """Jednoduchý průvodce pro vytvoření nového projektu."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nový projekt")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit("Můj dům")
        form.addRow("Název projektu:", self._name)

        self._units = QComboBox()
        self._units.addItems(["mm", "cm", "m"])
        self._units.setCurrentText("m")
        form.addRow("Jednotky:", self._units)

        self._scale = QComboBox()
        self._scale.addItems(["1:10", "1:25", "1:50", "1:72", "1:100", "1:200"])
        self._scale.setCurrentText("1:100")
        form.addRow("Měřítko:", self._scale)

        self._paper = QComboBox()
        self._paper.addItems(["A4", "A3", "A2", "A1", "Letter"])
        form.addRow("Papír:", self._paper)

        self._margin = QDoubleSpinBox()
        self._margin.setRange(0, 50)
        self._margin.setValue(10.0)
        self._margin.setSuffix(" mm")
        form.addRow("Okraj:", self._margin)

        self._grammage = QComboBox()
        self._grammage.addItems(["120", "160", "200", "250", "300"])
        self._grammage.setCurrentText("160")
        form.addRow("Gramáž papíru (g/m²):", self._grammage)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self) -> ProjectSettings:
        return ProjectSettings(
            name=self._name.text(),
            units=self._units.currentText(),
            scale=self._scale.currentText(),
            paper=self._paper.currentText(),
            paper_margin_mm=self._margin.value(),
            paper_grammage=int(self._grammage.currentText()),
        )
