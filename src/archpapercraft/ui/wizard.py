"""New-project wizard dialog."""

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
    """Simple wizard for creating a new project with basic settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit("My House")
        form.addRow("Project name:", self._name)

        self._units = QComboBox()
        self._units.addItems(["mm", "cm", "m"])
        form.addRow("Units:", self._units)

        self._scale = QComboBox()
        self._scale.addItems(["1:50", "1:72", "1:100", "1:200"])
        self._scale.setCurrentText("1:100")
        form.addRow("Scale:", self._scale)

        self._paper = QComboBox()
        self._paper.addItems(["A4", "A3", "Letter"])
        form.addRow("Paper:", self._paper)

        self._margin = QDoubleSpinBox()
        self._margin.setRange(0, 50)
        self._margin.setValue(10.0)
        self._margin.setSuffix(" mm")
        form.addRow("Margin:", self._margin)

        self._grammage = QComboBox()
        self._grammage.addItems(["160", "200", "250"])
        form.addRow("Paper weight (g/m²):", self._grammage)

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
