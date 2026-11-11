"""Explicit, source-fenced approximation of a retained construction target.

The worker owns a detached project. Only a reviewed preview token, never its
display mesh, reaches the domain command. One running and one latest request
bound the work queue; obsolete and closed-dialog results are discarded.
"""
# ruff: noqa: N802 -- Qt virtual overrides.

from __future__ import annotations

import copy
import hashlib
import json
import math
from fractions import Fraction

import numpy as np
from PySide6.QtCore import QObject, QPointF, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _state(project):
    return copy.deepcopy(project.to_dict(validate=False))


def _digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, allow_nan=False).encode()).hexdigest()


class _Signals(QObject):
    finished = Signal(int, object, object)


class _Job(QRunnable):
    def __init__(self, token, project_type, state, target_id, parameters):
        super().__init__()
        self.token, self.project_type, self.state = token, project_type, state
        self.target_id, self.parameters = target_id, parameters
        self.signals = _Signals()

    def run(self):
        try:
            project = self.project_type.from_dict(self.state)
            result = project.preview_segmented_variant(self.target_id, **self.parameters)
            source_mesh = project.world_geometry(self.target_id)
            self.signals.finished.emit(self.token, (result, source_mesh), None)
        except Exception as exc:
            self.signals.finished.emit(self.token, None, str(exc))


class SegmentationPreview(QWidget):
    """Shared-camera source and actual material meshes; display is not a proof."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 230)
        self.setAccessibleName("Původní cíl a rovinné díly vedle sebe")
        self.meshes = []
        self.yaw, self.pitch = 30.0, 55.0
        self.zoom = 1.0
        self._last = None

    def set_meshes(self, source=None, material=None):
        self.meshes = [source, material] if source and material else []
        self.zoom = 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f3f6f5"))
        painter.setPen(QColor("#263c36"))
        half = self.width() / 2
        for i, label in enumerate(("Původní cíl", "Samostatné rovinné díly")):
            painter.drawText(QPointF(i * half + 12, 22), label)
        if not self.meshes:
            painter.drawText(
                QPointF(12, 65), "Spočítejte náhled; původní konstrukce zůstane zachována."
            )
            return
        yaw, pitch = np.radians([self.yaw, self.pitch])
        c, s, a, b = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        rotation = np.array([[c, -s, 0], [a * s, a * c, -b], [b * s, b * c, a]])
        arrays = [np.asarray(mesh["vertices"], dtype=float) @ rotation.T for mesh in self.meshes]
        points = np.vstack(arrays)
        center = (points.min(0) + points.max(0)) / 2
        extents = np.maximum(np.ptp(points, axis=0), 1e-9)
        factor = min((half - 32) / extents[0], (self.height() - 62) / extents[1]) * self.zoom
        for index, (mesh, vertices) in enumerate(zip(self.meshes, arrays)):
            vertices = vertices - center
            projected = vertices[:, :2] * [factor, -factor]
            projected += [(index + 0.5) * half, (self.height() + 35) / 2]
            painter.save()
            painter.setClipRect(int(index * half), 30, int(half), self.height() - 30)
            for face in sorted(mesh["triangles"], key=lambda f: float(vertices[f, 2].mean())):
                polygon = QPolygonF([QPointF(*projected[i]) for i in face])
                painter.setBrush(QColor("#c4d2ce" if index == 0 else "#edd2a8"))
                painter.setPen(QPen(QColor("#6b817a" if index == 0 else "#815d30"), 0.7))
                painter.drawPolygon(polygon)
            painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last = event.position()

    def mouseMoveEvent(self, event):
        if self._last is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position() - self._last
            self.yaw += delta.x() * 0.5
            self.pitch = max(-89, min(89, self.pitch + delta.y() * 0.5))
            self._last = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self._last = None

    def wheelEvent(self, event):
        self.zoom = max(0.2, min(8, self.zoom * 1.2 ** (event.angleDelta().y() / 120)))
        self.update()


class SegmentedVariantDialog(QDialog):
    """Choose a hard budget, inspect a concrete result, then explicitly confirm."""

    preview_changed = Signal(object)

    def __init__(self, project, target_surface_id, *, variant_id=None, parent=None):
        super().__init__(parent)
        self.project, self.target_id, self.variant_id = project, target_surface_id, variant_id
        self.setWindowTitle("Odvozené rovinné díly — řízená aproximace")
        self.resize(800, 690)
        self._token, self._running, self._pending, self._closed = 0, None, None, False
        self._preview = self._accepted = None
        self._request = None
        layout = QVBoxLayout(self)
        title = QLabel(project.surfaces[target_surface_id].name)
        title.setWordWrap(True)
        layout.addWidget(title)
        self.guidance = QLabel(
            "Přesný rozvin hladkého cíle tímto nevznikne. Zadejte povolenou odchylku, "
            "spočítejte a porovnejte náhled. Potvrzení vytvoří nové samostatné rovinné "
            "díly na odkládací ploše; původní cíl i starší rozmístění zachová. "
            "Náhled otáčíte tažením a zvětšujete kolečkem."
        )
        self.guidance.setWordWrap(True)
        self.help_button = QPushButton("Skrýt tipy")
        self.help_button.setCheckable(True)
        self.help_button.setChecked(True)
        self.help_button.toggled.connect(self._toggle_help)
        layout.addWidget(self.help_button)
        layout.addWidget(self.guidance)
        form = QFormLayout()
        self.deviation = QDoubleSpinBox()
        self.deviation.setDecimals(6)
        self.deviation.setRange(0.000001, 100)
        self.deviation.setValue(0.25)
        self.deviation.setSuffix(" mm na papíře")
        self.cells = QSpinBox()
        self.cells.setRange(1, 65536)
        self.cells.setValue(4096)
        self.depth = QSpinBox()
        self.depth.setRange(0, 32)
        self.depth.setValue(16)
        for field in (self.deviation, self.cells, self.depth):
            field.setKeyboardTracking(False)
            field.setCorrectionMode(field.CorrectionMode.CorrectToPreviousValue)
        form.addRow("Největší povolená odchylka", self.deviation)
        form.addRow("Výpočetní rozpočet buněk", self.cells)
        form.addRow("Největší počet zjemnění", self.depth)
        layout.addLayout(form)
        if variant_id is not None:
            params = project.segmented_variants[variant_id].parameters
            self.deviation.setValue(params["max_deviation_mm"])
            self.cells.setValue(params["max_cells"])
            self.depth.setValue(params["max_depth"])
        self.preview_button = QPushButton("Spočítat náhled")
        self.preview_button.clicked.connect(self.request_preview)
        layout.addWidget(self.preview_button)
        self.view = SegmentationPreview()
        layout.addWidget(self.view, 1)
        self.feedback = QLabel(
            "Zadejte mez a spočítejte náhled. Zrušit ponechá projekt beze změny."
        )
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        self.feedback.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.feedback)
        self.confirm = QCheckBox("Přijímám tento konkrétní aproximovaný tvar a jeho uvedené meze.")
        self.confirm.toggled.connect(self._update_accept)
        layout.addWidget(self.confirm)
        layout.addWidget(
            QLabel("Digitální geometrie nedokazuje fyzickou sestavitelnost. Výtisk je nutný.")
        )
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Vytvořit odvozené díly")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for field in (self.deviation, self.cells, self.depth):
            field.valueChanged.connect(self._invalidate)
            field.lineEdit().textEdited.connect(self._invalidate)
        self._update_accept()

    def _toggle_help(self, checked):
        self.guidance.setVisible(checked)
        self.help_button.setText("Skrýt tipy" if checked else "Zobrazit tipy")

    def _invalidate(self, *_args):
        self._token += 1
        self._preview = self._accepted = None
        self.confirm.setChecked(False)
        self.view.set_meshes()
        self.feedback.setText("Náhled není aktuální. Spočítejte jej pro právě zadané hodnoty.")
        self._update_accept()

    def _parameters(self):
        for field in (self.deviation, self.cells, self.depth):
            editor = field.lineEdit()
            if (
                field.validate(editor.text(), editor.cursorPosition())[0]
                != QValidator.State.Acceptable
            ):
                field.setFocus()
                raise ValueError("Opravte neplatnou mez nebo výpočetní rozpočet.")
            field.interpretText()
        return dict(
            max_deviation_mm=self.deviation.value(),
            max_cells=self.cells.value(),
            max_depth=self.depth.value(),
        )

    def request_preview(self):
        try:
            params = self._parameters()
            state = _state(self.project)
        except (ValueError, TypeError) as exc:
            self._invalidate()
            self.feedback.setText(str(exc))
            return
        self._invalidate()
        request = dict(
            token=self._token, state=state, fingerprint=_digest(state), parameters=params
        )
        if self._running is not None:
            self._pending = request
            self.feedback.setText("Čeká poslední zadaný náhled; předchozí výsledek nebude použit.")
        else:
            self._start(request)

    def _start(self, request):
        self._request = request
        self._running = _Job(
            request["token"],
            type(self.project),
            request["state"],
            self.target_id,
            request["parameters"],
        )
        self._running.signals.finished.connect(self._finished)
        self.feedback.setText(
            "Počítám ověřenou mez a skutečné rovinné díly. Zrušit zachová projekt."
        )
        QThreadPool.globalInstance().start(self._running)

    def _finished(self, token, result, error):
        request = self._request
        self._running = None
        if not self._closed and token == self._token:
            try:
                if error:
                    raise ValueError(error)
                if _digest(_state(self.project)) != request["fingerprint"]:
                    raise ValueError("Projekt se změnil; spočítejte nový náhled.")
                preview, source = result
                self._publish(preview, source, request)
            except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                self._invalidate()
                self.feedback.setText("Náhled nelze potvrdit: " + str(exc))
        pending, self._pending = self._pending, None
        if pending is not None and not self._closed and pending["token"] == self._token:
            self._start(pending)

    def _publish(self, preview, source, request):
        if preview.get("target_surface_id") != self.target_id:
            raise ValueError("Výsledek patří jinému cíli.")
        if preview.get("status") != "APPROXIMATE" or preview.get("can_confirm") is not True:
            self.feedback.setText(
                "Mez není doložená; odvozené díly nevznikly. "
                + str(preview.get("message", ""))
                + " Změňte tvar/profily, přidejte skutečné švy nebo upravte mez a rozpočet."
            )
            self._update_accept()
            self.preview_changed.emit(copy.deepcopy(preview))
            return
        if preview["parameters"] != request["parameters"] or not preview.get("preview_digest"):
            raise ValueError("Výsledek změnil autorské zadání nebo nemá potvrzovací vazbu.")
        cert = preview["certificate"]
        metrics = cert["material_frame"]
        deviation, length, angle = (
            Fraction(metrics[key])
            for key in (
                "max_target_to_material_deviation_paper_mm_exact",
                "max_source_edge_to_flat_length_difference_bound_paper_mm_exact",
                "max_material_normal_angle_deg_exact",
            )
        )
        if not 0 <= deviation <= Fraction(request["parameters"]["max_deviation_mm"]):
            raise ValueError("Výsledek překročil povolenou odchylku.")
        if length < 0 or not 0 <= angle <= 180:
            raise ValueError("Výsledek nemá konečné platné meze.")
        counts = cert["math"]["counts"]
        geometry = preview["preview_geometry"]
        if geometry["mode"] != "APPROXIMATE" or len(geometry["triangles"]) != counts["triangles"]:
            raise ValueError("Náhled neodpovídá počtu odvozených dílů.")
        for mesh in (geometry, source):
            vertices = np.asarray(mesh["vertices"], dtype=float)
            faces = np.asarray(mesh["triangles"], dtype=int)
            if (
                vertices.ndim != 2
                or vertices.shape[1] != 3
                or not np.isfinite(vertices).all()
                or faces.ndim != 2
                or faces.shape[1] != 3
                or not len(faces)
                or faces.min() < 0
                or faces.max() >= len(vertices)
            ):
                raise ValueError("Náhled má neplatnou zobrazovací geometrii.")
        text = (
            f"APROXIMACE · {counts['triangles']} samostatných dílů · "
            f"{counts['paired_cut_seams']} párovaných řezaných spojů.\n"
            f"Prokázaná mez odchylky celých ploch ≤ {float(deviation):.6g} mm na papíře "
            f"(povoleno {request['parameters']['max_deviation_mm']:g}).\n"
            f"Mez rozdílu délky hrany ≤ {float(length):.6g} mm; "
            f"mez odchylky normály ≤ {float(angle):.6g}°.\n"
            "Nejde o přesný rozvin hladkého cíle. Nové díly rozmístíte ručně; "
            "jejich lepicí spoje je třeba samostatně navrhnout."
        )
        candidate = copy.deepcopy(preview)
        self.view.set_meshes(copy.deepcopy(source), copy.deepcopy(geometry))
        self.feedback.setText(text)
        self._preview = candidate
        self._update_accept()
        self.preview_changed.emit(copy.deepcopy(candidate))

    def _update_accept(self, *_args):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self._preview is not None and self.confirm.isChecked()
        )

    def accept(self):
        try:
            params = self._parameters()
            if self._preview is None or not self.confirm.isChecked():
                return
            if params != self._request["parameters"]:
                raise ValueError("Hodnoty se změnily; spočítejte nový náhled.")
            self.check_source(self.project)
            self._accepted = copy.deepcopy(self._preview)
        except ValueError as exc:
            self._invalidate()
            self.feedback.setText(str(exc))
            return
        self._closed = True
        self._pending = None
        super().accept()

    def check_source(self, project):
        if self._request is None or _digest(_state(project)) != self._request["fingerprint"]:
            raise ValueError("Projekt se od náhledu změnil; otevřete a potvrďte nový náhled.")

    def apply(self, project):
        self.check_source(project)
        if self._accepted is None:
            raise ValueError("Nejprve výslovně potvrďte konkrétní náhled.")
        kwargs = dict(self._accepted["parameters"], preview_digest=self._accepted["preview_digest"])
        if self.variant_id is None:
            return project.add_segmented_variant(self.target_id, **kwargs)
        return project.update_segmented_variant(self.variant_id, **kwargs)

    def reject(self):
        self._closed, self._pending = True, None
        self._token += 1
        self._accepted = None
        super().reject()

    def closeEvent(self, event):
        self.reject()
        event.accept()
