"""Optional measured-paper settings, expressed in physical paper millimetres."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)


class MaterialDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Papír a místo pro ohyb")
        self.resize(580, 420)
        self.project, self.result_profile = project, None
        self.raw_profile = dict(project.material_profile)
        self.shown = {}
        layout = QVBoxLayout(self)
        description = QLabel(
            "Tyto rozměry platí pro papír celého projektu, nezávisle na měřítku modelu. "
            "Tloušťku zadávejte podle měření nebo údajů materiálu; gramáž ji neurčuje. "
            "Změna ponechá ruční stránky a označí díly k přepočtu a kontrole."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        layout.addLayout(form)
        profile = project.material_profile
        self.known = QCheckBox("Znám skutečnou tloušťku papíru")
        self.known.setChecked(profile["thickness_mm"] is not None)
        form.addRow(self.known)
        self.fields = {}
        for key, label, minimum, default in [
            ("thickness_mm", "Tloušťka papíru", 0.0001, 0.2),
            ("clearance_mm", "Požadovaná vůle", 0, 0),
            ("bend_radius_mm", "Rezerva kolem ohybu", 0, 0),
            ("crease_zone_mm", "Pás ohybu na každou stranu", 0, 0.5),
        ]:
            field = QDoubleSpinBox()
            field.setRange(minimum, 1000)
            field.setDecimals(4)
            field.setKeyboardTracking(False)
            field.setSuffix(" mm na papíře")
            field.setValue(profile[key] if profile[key] is not None else default)
            self.fields[key] = field
            self.shown[key] = field.value()
            form.addRow(label, field)
        self.fields["thickness_mm"].setEnabled(self.known.isChecked())
        self.known.toggled.connect(self.fields["thickness_mm"].setEnabled)
        detail = QLabel(
            "Místní pás kolem přehybu je deformující se oblast papíru; výpočet ji "
            "neposuzuje jako tuhý plát. Není to výřez a nemění obrys dílu. Jeho rozsah "
            "se zaznamená do kontroly. Skutečné ohnutí, slepení a pevnost ověří výtisk. "
            "Bez známé tloušťky se neprohlašuje ověřená materiálová vůle."
        )
        detail.setWordWrap(True)
        layout.addWidget(detail)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Použít pro projekt")
        buttons.accepted.connect(self.confirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def confirm(self):
        for field in self.findChildren(QAbstractSpinBox):
            if not field.isEnabled():
                continue
            if not field.hasAcceptableInput():
                self.feedback.setText("Opravte rozepsaný rozměr před potvrzením.")
                field.setFocus()
                return
            field.interpretText()
        candidate = {
            key: self.raw_profile[key]
            if field.value() == self.shown[key] and self.raw_profile[key] is not None
            else field.value()
            for key, field in self.fields.items()
        }
        if not self.known.isChecked():
            candidate["thickness_mm"] = None
        self.result_profile = candidate
        self.accept()
