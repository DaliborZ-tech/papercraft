"""Previewed, reversible source subdivision; no hidden seam or geometry fit."""

from __future__ import annotations

import copy
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class SubdivisionDialog(QDialog):
    def __init__(
        self,
        project,
        profile_id,
        segment_id,
        *,
        joining=False,
        unit_factor=1,
        unit_label="mm",
        parent=None,
    ):
        super().__init__(parent)
        self.source = copy.deepcopy(project)
        self.profile_id, self.segment_id = profile_id, segment_id
        self.joining, self.unit_factor = joining, unit_factor
        self.result_spec = None
        self.setWindowTitle("Spojit původní úseky" if joining else "Rozdělit úsek obrysu")
        self.resize(650, 540)
        layout = QVBoxLayout(self)
        description = QLabel(
            "Spojte sousední úseky vzniklé stejným dělením. Původní obrys se nevyhlazuje "
            "ani nefituje. Vyberte více řádků pomocí Ctrl nebo Shift."
            if joining
            else "Přidejte bod do vybrané úsečky. Zadejte vzdálenost od jejího začátku "
            "v rozměrech modelu. Tvar, stávající spoje a poloha na stránce zůstanou zachované."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        note = QLabel("Dělení nevytváří šev ani chlopeň. Potvrzený krok lze vrátit pomocí Ctrl+Z.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.distance, self.choices = None, None
        profile = self.source.profiles[profile_id]
        edge = profile.segment(segment_id)
        self.length = math.dist(
            profile.vertex(edge.start_vertex_id).point, profile.vertex(edge.end_vertex_id).point
        )
        if joining:
            self.choices = QListWidget()
            self.choices.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            record = self.source._subdivision_record(profile_id, segment_id)
            for index, current in enumerate(profile.segments):
                if (
                    record is not None
                    and self.source._subdivision_record(profile_id, current.id) is record
                ):
                    item = QListWidgetItem(f"Úsek {index + 1}")
                    item.setData(Qt.ItemDataRole.UserRole, current.id)
                    self.choices.addItem(item)
                    item.setSelected(True)
            layout.addWidget(self.choices)
            self.choices.itemSelectionChanged.connect(self.preview)
        else:
            form = QFormLayout()
            self.distance = QDoubleSpinBox()
            self.distance.setDecimals(6)
            self.distance.setRange(0, self.length / unit_factor)
            self.distance.setKeyboardTracking(False)
            self.distance.setValue(self.length / (2 * unit_factor))
            self.initial_shown = self.distance.value()
            form.addRow(f"Vzdálenost od začátku ({unit_label})", self.distance)
            layout.addLayout(form)
            self.distance.valueChanged.connect(self.preview)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view, 1)
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
        self.preview()

    def parameters(self):
        if self.joining:
            return {
                "segment_ids": [
                    self.choices.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.choices.count())
                    if self.choices.item(i).isSelected()
                ]
            }
        if not self.distance.hasAcceptableInput():
            raise ValueError("Opravte rozepsanou vzdálenost před pokračováním.")
        self.distance.interpretText()
        parameter = (
            0.5
            if self.distance.value() == self.initial_shown
            else self.distance.value() * self.unit_factor / self.length
        )
        return {"segment_id": self.segment_id, "parameter": parameter}

    def preview(self):
        self.scene.clear()
        try:
            values = self.parameters()
            candidate = copy.deepcopy(self.source)
            if self.joining:
                candidate.merge_profile_segments(self.profile_id, values["segment_ids"])
            else:
                candidate.split_profile_segment(self.profile_id, **values)
            profile = candidate.profiles[self.profile_id]
            points = candidate.profile_outline(self.profile_id)
            path = QPainterPath()
            path.moveTo(points[0][0], -points[0][1])
            for x, y in points[1:]:
                path.lineTo(x, -y)
            if profile.closed:
                path.closeSubpath()
            pen = QPen(QColor("#245d71"), 2)
            pen.setCosmetic(True)
            self.scene.addPath(path, pen)
            radius = max(self.length / 70, 1e-6)
            for vertex in profile.vertices:
                x, y = vertex.point
                self.scene.addEllipse(
                    x - radius, -y - radius, 2 * radius, 2 * radius, pen, QColor("#ebf5f4")
                )
            self.view.fitInView(
                self.scene.itemsBoundingRect().adjusted(
                    -radius * 3, -radius * 3, radius * 3, radius * 3
                ),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            self.feedback.setText(
                f"Náhled: {len(profile.segments)} úseků. Potvrzení označí rozvin dotčeného "
                "dílu jako neaktuální; pokračujte příkazem Přepočítat. Poloha a zámky zůstanou."
            )
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            return values
        except (ValueError, KeyError) as exc:
            self.feedback.setText(str(exc))
            # Keep numeric correction reachable without Enter: accept() will
            # interpret the newly typed text and refuse an invalid candidate.
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not self.joining)
            return None

    def accept(self):
        # C-05: interpret and validate the visible uncommitted input first.
        result = self.preview()
        if result is not None:
            self.result_spec = result
            super().accept()
