"""Reversible profile copying and placement before constructing a surface."""

from __future__ import annotations

import copy
import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class ProfilePlacementDialog(QDialog):
    def __init__(self, project, profile_id, *, copying=False, unit_factor=1,
                 unit_label="mm", parent=None):
        super().__init__(parent)
        self.source = copy.deepcopy(project.profiles[profile_id])
        self.unit_factor, self.copying = unit_factor, copying
        self.result_spec = None
        self.setWindowTitle("Kopie zdrojového profilu" if copying else "Rovina zdrojového profilu")
        layout = QVBoxLayout(self)
        description = QLabel(
            "Zvolte hloubku proti původní rovině. Souřadnice jsou rozměry modelu, "
            "nikoli papíru. Změna se použije najednou a lze ji vrátit. "
            + ("Kopie bude samostatně editovatelná; původní profil zůstane zachovaný."
               if copying else "Plochu mezi dvěma profily vytvoříte až dalším příkazem.")
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        layout.addLayout(form)
        self.name = QLineEdit(self.source.name + (" · kopie" if copying else ""))
        self.name.setVisible(copying)
        if copying:
            form.addRow("Název kopie", self.name)
        self.fields, self.raw, self.shown = {}, {}, {}
        for key, label, raw, low in [
            ("depth", f"Hloubka ({unit_label})", 0, -1e9),
            ("factor", "Poměr velikosti kopie", 1.2 if copying else 1, 0.000001),
            ("origin_x", f"Počátek roviny X ({unit_label})", self.source.plane.origin[0], -1e9),
            ("origin_y", f"Počátek roviny Y ({unit_label})", self.source.plane.origin[1], -1e9),
            ("origin_z", f"Počátek roviny Z ({unit_label})", self.source.plane.origin[2], -1e9),
            ("angle", "Otočení v původní rovině (°)", 0, -360000),
        ]:
            field = QDoubleSpinBox()
            field.setRange(low, 1e9)
            field.setDecimals(6)
            field.setKeyboardTracking(False)
            factor = 1 if key in ("factor", "angle") else unit_factor
            field.setValue(raw / factor)
            self.fields[key], self.raw[key], self.shown[key] = field, raw, field.value()
            if key != "factor" or copying:
                form.addRow(label, field)
            else:
                field.hide()
        self.feedback = QLabel()
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def accept(self):
        values = {}
        for key, field in self.fields.items():
            if not field.hasAcceptableInput():
                self.feedback.setText("Opravte rozepsaný rozměr před pokračováním.")
                field.setFocus()
                return
            field.interpretText()
            factor = 1 if key in ("factor", "angle") else self.unit_factor
            values[key] = (self.raw[key] if field.value() == self.shown[key]
                           else field.value() * factor)
        if self.copying and not self.name.text().strip():
            self.feedback.setText("Zadejte název samostatného profilu.")
            self.name.setFocus()
            return
        source = self.source.plane
        a = math.radians(values["angle"])
        u, v = np.asarray(source.u), np.asarray(source.v)
        origin = np.array([values["origin_x"], values["origin_y"], values["origin_z"]])
        origin += values["depth"] * np.cross(u, v)
        plane = {"origin": origin.tolist(),
                 "u": (math.cos(a) * u + math.sin(a) * v).tolist(),
                 "v": (-math.sin(a) * u + math.cos(a) * v).tolist()}
        self.result_spec = {"plane": plane, "factor": values["factor"], "name": self.name.text()}
        super().accept()
