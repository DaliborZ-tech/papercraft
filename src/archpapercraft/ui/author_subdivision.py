"""Previewed, reversible source subdivision; no hidden seam or geometry fit."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from fractions import Fraction

from PySide6.QtCore import (
    QObject,
    QRectF,
    QRunnable,
    QSignalBlocker,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainterPath, QPen, QValidator
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
    QPushButton,
    QVBoxLayout,
)

from archpapercraft.authoring.profile_curves import source_curve


def _state(project):
    return copy.deepcopy(project.to_dict(validate=False))


def _digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _curve_preview(project, profile_id, segment_id, request):
    """Detached public commands; returned state never replaces the real document."""
    length = project.profile_segment_length(profile_id, segment_id)
    if length.get("status") != "CERTIFIED" or length.get("units") != "model_mm":
        raise ValueError("Délku obrysu nelze doložit. Opravte profil nebo vyberte jiný úsek.")
    lower, upper = length["lower"], length["upper"]
    if not (math.isfinite(lower) and math.isfinite(upper) and 0 < lower <= upper):
        raise ValueError("Náhled nevrátil doložené meze délky obrysu.")
    point, measurement, distance = None, None, None
    if request["joining"]:
        parameters = {"segment_ids": request["segment_ids"]}
        project.merge_profile_segments(profile_id, parameters["segment_ids"])
    else:
        distance = request["distance"]
        if distance is None:
            # Certify the distance the spinbox will actually show, including
            # initial midpoint rounding in the chosen model units.
            factor = request["unit_factor"]
            distance = round((lower + upper) / (4 * factor), request["decimals"]) * factor
        measurement = project.profile_segment_parameter_at_length(profile_id, segment_id, distance)
        error = measurement.get("actual_error_bound_model_mm")
        if (measurement.get("status") != "CERTIFIED"
                or not isinstance(measurement.get("parameter"), Fraction)
                or not 0 < measurement["parameter"] < 1
                or not isinstance(error, (int, float)) or not math.isfinite(error)
                or not 0 <= error <= .001 / project.scale):
            raise ValueError("Bod po obrysu nelze doložit v požadované přesnosti. "
                             "Změňte vzdálenost nebo vyberte jiný úsek.")
        parameters = {"segment_id": segment_id, "parameter": measurement["parameter"]}
        result = project.split_profile_segment(profile_id, **parameters)
        point = project.profiles[profile_id].vertex(result["vertex_id"]).point
    project.recompute()
    return {"request": request, "parameters": parameters,
            "profile": copy.deepcopy(project.profiles[profile_id]), "length": length,
            "distance": distance, "measurement": measurement, "split_point": point}


def _validate_packet(packet, request, profile_id, segment_id, scale):
    if packet["request"] != request or packet["profile"].id != profile_id:
        raise ValueError("Náhled neodpovídá zadané vzdálenosti a výběru.")
    parameters, length = packet["parameters"], packet["length"]
    if (length["status"] != "CERTIFIED" or length["units"] != "model_mm"
            or not all(math.isfinite(length[key]) for key in ("lower", "upper"))
            or not 0 < length["lower"] <= length["upper"]):
        raise ValueError("Náhled nemá doloženou délku obrysu.")
    if request["joining"]:
        if parameters != {"segment_ids": request["segment_ids"]}:
            raise ValueError("Náhled změnil pořadí nebo výběr spojovaných úseků.")
    else:
        measured = packet["measurement"]
        error = measured["actual_error_bound_model_mm"]
        bounds = measured["distance_bounds_model_mm"]
        if (set(parameters) != {"segment_id", "parameter"}
                or parameters["segment_id"] != segment_id
                or not isinstance(parameters["parameter"], Fraction)
                or not 0 < parameters["parameter"] < 1
                or measured["status"] != "CERTIFIED"
                or measured["parameter"] != parameters["parameter"]
                or not math.isfinite(error) or not 0 <= error <= .001 / scale
                or not math.isfinite(packet["distance"])
                or len(bounds) != 2 or not all(math.isfinite(x) for x in bounds)
                or not bounds[0] <= bounds[1]
                or (request["distance"] is not None and packet["distance"] != request["distance"])):
            raise ValueError("Náhled nemá doložený bod v zadané vzdálenosti po obrysu.")


class _Signals(QObject):
    finished = Signal(int, object, object)


class _Job(QRunnable):
    def __init__(self, token, project_type, state, profile_id, segment_id, request, callback):
        super().__init__()
        self.token, self.project_type, self.state = token, project_type, state
        self.profile_id, self.segment_id = profile_id, segment_id
        self.request, self.callback = request, callback
        self.signals = _Signals()

    def run(self):
        try:
            clone = self.project_type.from_dict(self.state)
            result = self.callback(clone, self.profile_id, self.segment_id, self.request)
            self.signals.finished.emit(self.token, result, None)
        except Exception as exc:
            self.signals.finished.emit(self.token, None, str(exc))


def _native_outline(profile):
    """Display actual source primitives. This path is not a geometry certificate."""
    path = QPainterPath()
    for index, segment in enumerate(profile.segments):
        curve = source_curve(profile, segment)
        if index == 0:
            path.moveTo(curve.start[0], -curve.start[1])
        if curve.kind == "line":
            path.lineTo(curve.end[0], -curve.end[1])
        elif curve.kind == "cubic":
            a, b = curve.data["control1"], curve.data["control2"]
            path.cubicTo(a[0], -a[1], b[0], -b[1], curve.end[0], -curve.end[1])
        else:
            cx, cy = curve.data["center"]
            radius = math.dist(curve.start, (cx, cy))
            angle = math.degrees(math.atan2(curve.start[1] - cy, curve.start[0] - cx))
            path.arcTo(QRectF(cx-radius, -cy-radius, radius*2, radius*2),
                       angle, curve.data["sweep_deg"])
    if profile.closed:
        path.closeSubpath()
    return path


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
        preview_function=None,
    ):
        super().__init__(parent)
        self.project = project
        self.asynchronous = project.profiles[profile_id].segment(segment_id).kind != "line"
        self.source = project if self.asynchronous else copy.deepcopy(project)
        self._fingerprint = _digest(_state(project))
        self._token, self._running, self._pending = 0, None, None
        self._closed, self._packet, self._raw = False, None, None
        self._callback = preview_function or _curve_preview
        self._request = None
        self._accept_when_ready = False
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
            else "Přidejte bod do obrysu. Vzdálenost měříme po skutečné úsečce, oblouku "
            "nebo křivce od označeného začátku, v rozměrech modelu. "
            "Tvar, stávající spoje a poloha na stránce zůstanou zachované."
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
            self.choices.itemSelectionChanged.connect(self._changed)
        else:
            form = QFormLayout()
            self.distance = QDoubleSpinBox()
            decimals = max(6, min(15, math.ceil(math.log10(project.scale * unit_factor / .0001))))
            self.distance.setDecimals(decimals if self.asynchronous else 6)
            self.distance.setRange(0, 1e12 if self.asynchronous else self.length / unit_factor)
            self.distance.setKeyboardTracking(False)
            self.distance.setValue(self.length / (2 * unit_factor))
            self.initial_shown = self.distance.value()
            form.addRow(f"Vzdálenost po obrysu od začátku ({unit_label})", self.distance)
            layout.addLayout(form)
            self.distance.valueChanged.connect(self._changed)
            self.distance.lineEdit().textEdited.connect(self._typed)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setAccessibleName("Skutečný obrys a nový bod dělení")
        layout.addWidget(self.view, 1)
        self.dimensions = QLabel()
        self.dimensions.setWordWrap(True)
        self.dimensions.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.dimensions)
        self.compute = QPushButton("Spočítat aktuální náhled")
        self.compute.clicked.connect(self.preview)
        self.compute.setVisible(self.asynchronous)
        layout.addWidget(self.compute)
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
        self.unit_label = unit_label
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._source_changed)
        self.timer.start()
        if self.asynchronous:
            self.compute.setDefault(True)
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setAutoDefault(False)
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.feedback.setText("Počítám délku skutečného obrysu. Náhled můžete zrušit.")
            QTimer.singleShot(0, self._initial_preview)
        else:
            self.preview()

    def parameters(self):
        if self.asynchronous:
            self._curve_request()
            if self._packet is None:
                raise ValueError("Nejprve spočítejte aktuální náhled po obrysu.")
            return copy.deepcopy(self._packet["parameters"])
        if self.joining:
            return {
                "segment_ids": [
                    self.choices.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.choices.count())
                    if self.choices.item(i).isSelected()
                ]
            }
        if ((self._raw is not None and self.distance.validate(self._raw, len(self._raw))[0]
             != QValidator.State.Acceptable) or not self.distance.hasAcceptableInput()):
            if self._raw is not None:
                self.distance.lineEdit().setText(self._raw)
            raise ValueError("Opravte rozepsanou vzdálenost před pokračováním.")
        self.distance.interpretText()
        self._raw = None
        parameter = (
            0.5
            if self.distance.value() == self.initial_shown
            else self.distance.value() * self.unit_factor / self.length
        )
        return {"segment_id": self.segment_id, "parameter": parameter}

    def preview(self, *_args, initial=False):
        if self.asynchronous:
            return self._preview_curve(initial=initial)
        if _digest(_state(self.project)) != self._fingerprint:
            self._source_changed()
            return None
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
        if self.asynchronous:
            try:
                self._curve_request()
                if _digest(_state(self.project)) != self._fingerprint:
                    self._source_changed()
                elif self._packet is not None:
                    self.result_spec = self.parameters()
                    self._close_worker()
                    super().accept()
                elif self._preview_curve():
                    self._accept_when_ready = True
            except (ValueError, KeyError, TypeError) as exc:
                self.feedback.setText(str(exc))
            return
        result = self.preview()
        if result is not None:
            self.result_spec = result
            super().accept()

    def _initial_preview(self):
        if not self._closed and self._token == 0:
            self._preview_curve(initial=True)

    def _typed(self, text):
        self._raw = text
        if self.asynchronous:
            self._invalidate()

    def _changed(self, *_args):
        if self.asynchronous:
            self._invalidate()
        else:
            self.preview()

    def _invalidate(self):
        self._token += 1
        self._packet = self._pending = None
        self._accept_when_ready = False
        self.scene.clear()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.feedback.setText("Návrh se změnil. Spočítejte aktuální náhled; projekt se nezměnil.")

    def _source_changed(self):
        if not self._closed and _digest(_state(self.project)) != self._fingerprint:
            self._invalidate()
            self.compute.setEnabled(False)
            self.feedback.setText("Zdroj se změnil. Zavřete návrh a vyberte úsek znovu; "
                                  "starý výsledek se nepoužije.")

    def _curve_request(self, *, initial=False):
        if self.joining:
            return {"joining": True, "segment_ids": [
                self.choices.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.choices.count()) if self.choices.item(i).isSelected()]}
        if ((self._raw is not None and self.distance.validate(self._raw, len(self._raw))[0]
             != QValidator.State.Acceptable) or not self.distance.hasAcceptableInput()):
            if self._raw is not None:
                self.distance.lineEdit().setText(self._raw)
            raise ValueError("Opravte rozepsanou vzdálenost před pokračováním.")
        self.distance.interpretText()
        self._raw = None
        return {"joining": False,
                "distance": None if initial else self.distance.value() * self.unit_factor,
                "unit_factor": self.unit_factor, "decimals": self.distance.decimals()}

    def _preview_curve(self, *, initial=False):
        if self._closed:
            return False
        try:
            if _digest(_state(self.project)) != self._fingerprint:
                self._source_changed()
                return False
            request = self._curve_request(initial=initial)
            self._invalidate()
            self._request = copy.deepcopy(request)
            pending = (self._token, _state(self.project), copy.deepcopy(request))
            self.feedback.setText("Počítám délku, bod a změnu obrysu na odděleném návrhu. "
                                  "Zrušit nezmění projekt.")
            if self._running is None:
                self._start(pending)
            else:
                self._pending = pending
            return True
        except (ValueError, KeyError, TypeError) as exc:
            self.feedback.setText(str(exc))
            return False

    def _start(self, pending):
        token, state, request = pending
        self._running = _Job(token, type(self.project), state, self.profile_id,
                             self.segment_id, request, self._callback)
        self._running.signals.finished.connect(self._finished)
        QThreadPool.globalInstance().start(self._running)

    def _finished(self, token, packet, error):
        self._running = None
        if not self._closed and token == self._token:
            try:
                if _digest(_state(self.project)) != self._fingerprint:
                    self._source_changed()
                elif error:
                    raise ValueError(error)
                else:
                    _validate_packet(packet, self._request, self.profile_id,
                                     self.segment_id, self.project.scale)
                    profile = packet["profile"]
                    length = packet["length"]
                    lower = length["lower"] / self.unit_factor
                    upper = length["upper"] / self.unit_factor
                    dimensions = (f"Délka po obrysu: {lower:.6f}–{upper:.6f} "
                                  f"{self.unit_label}.")
                    original = self.project.profiles[self.profile_id]
                    curve = source_curve(original, original.segment(self.segment_id))
                    if curve.kind == "arc":
                        radius = math.dist(curve.start, curve.data["center"]) / self.unit_factor
                        dimensions += f" Poloměr: {radius:.6f} {self.unit_label}."
                    self._draw_curve(profile, packet["split_point"])
                    if not self.joining:
                        with QSignalBlocker(self.distance):
                            self.distance.setMaximum(upper)
                            self.distance.setValue(packet["distance"] / self.unit_factor)
                    self.dimensions.setText(dimensions)
                    self._packet = packet
                    self.feedback.setText(
                        f"Náhled: {len(profile.segments)} úseků. Po potvrzení přepočítejte "
                        "dotčený rozvin (Ctrl+R). Tvar, poloha a zámky zůstávají; "
                        "celý krok vrátíte Ctrl+Z.")
                    self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
                    if self._accept_when_ready:
                        self.accept()
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                self._packet = None
                self.feedback.setText("Náhled nelze použít: " + str(exc))
                self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        pending, self._pending = self._pending, None
        if not self._closed and pending is not None and pending[0] == self._token:
            self._start(pending)

    def _draw_curve(self, profile, point):
        self.scene.clear()
        pen = QPen(QColor("#245d71"), 2)
        pen.setCosmetic(True)
        self.scene.addPath(_native_outline(profile), pen)
        bounds = self.scene.itemsBoundingRect()
        radius = max(bounds.width(), bounds.height(), 1e-5) / 70
        original = self.project.profiles[self.profile_id]
        start = original.vertex(original.segment(self.segment_id).start_vertex_id).point
        markers = [(start, "Začátek měření", "#ffffff")]
        if point is not None:
            markers.append((point, "Nový bod", "#e88a24"))
        for (x, y), text, color in markers:
            self.scene.addEllipse(x-radius, -y-radius, radius*2, radius*2, pen, QColor(color))
            label = self.scene.addText(text)
            label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
            label.setPos(x, -y)
        self.view.fitInView(bounds.adjusted(-radius*3, -radius*3, radius*3, radius*3),
                            Qt.AspectRatioMode.KeepAspectRatio)

    def _close_worker(self):
        self._closed = True
        self._token += 1
        self._pending = None
        self.timer.stop()

    def done(self, result):
        self._close_worker()
        super().done(result)
