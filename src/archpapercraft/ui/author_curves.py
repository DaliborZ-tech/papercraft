"""Direct curve drafting and staged visual editing of authored source segments."""
# ruff: noqa: N802 -- Qt event overrides retain framework names.

from __future__ import annotations

import copy
import math

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.authoring.curves import Curve, evaluate
from archpapercraft.authoring.profile_curves import (
    _mapped_commands,
    arc_from_bulge,
    profile_native_path,
)
from archpapercraft.ui.author_paper import _path
from archpapercraft.ui.author_sketch import AuthorSketch, cosmetic


def arc_through_points(start, via, end):
    """Construct the directed circular arc passing through the middle click."""
    a, m, b = (np.asarray(point, dtype=float) for point in (start, via, end))
    first, second = m - a, b - a
    determinant = float(first[0] * second[1] - first[1] * second[0])
    if abs(determinant) <= 1e-12 * max(1.0, np.linalg.norm(first) * np.linalg.norm(second)):
        raise ValueError("Tři body oblouku nesmějí ležet na jedné přímce. Upravte prostřední bod.")
    center = a + np.linalg.solve(2 * np.array([first, second]),
                                 np.array([first @ first, second @ second]))
    angles = [math.atan2(*(point - center)[::-1]) for point in (a, m, b)]
    turn, middle = (angles[2] - angles[0]) % math.tau, (angles[1] - angles[0]) % math.tau
    if middle > turn:
        turn -= math.tau
    data = {"center": center.tolist(), "sweep_deg": math.degrees(turn)}
    Curve(tuple(start), tuple(end), "arc", data)
    return data


class CurveSketch(AuthorSketch):
    """Line-compatible sketch with native arc/cubic input and reversible clicks.

    A curved draft remains live after its finish signal until the host calls
    complete_curve_draft following a successful document command.
    """

    curve_profile_finished = Signal(list, bool, bool)
    segment_mode_changed = Signal(str)

    def __init__(self, parent=None):
        self.segment_mode = "line"
        self.curve_segments = []
        self.pending_points = []
        self._input_history = []
        super().__init__(parent)

    def set_segment_mode(self, mode):
        if mode not in ("line", "arc", "cubic"):
            raise ValueError("Unknown source curve tool")
        if self.pending_points and mode != self.segment_mode:
            self.status.emit("Dokončete rozpracovaný úsek nebo vraťte jeho úchopy Backspace.")
            self.segment_mode_changed.emit(self.segment_mode)
            return False
        # The existing host may have supplied a line-only draft directly.
        if self.points and not self.curve_segments:
            self.curve_segments = [
                {"kind": "line", "start": a[:], "end": b[:], "data": {}}
                for a, b in zip(self.points, self.points[1:])
            ]
        self.segment_mode = mode
        self.segment_mode_changed.emit(mode)
        self._next_step()
        return True

    def _next_step(self):
        if not self.drawing:
            return
        self.status.emit(self.instruction_text())

    def instruction_text(self):
        if not self.points:
            text = "Klikněte na počáteční bod profilu."
        elif self.segment_mode == "line":
            text = ("Úsečka: klikněte na další konec. Enter uzavře, "
                    "Ctrl+Enter uloží otevřený profil.")
        elif self.segment_mode == "arc":
            text = ("Oblouk: klikněte na bod, kterým má procházet."
                    if not self.pending_points else "Oblouk: klikněte na koncový bod.")
        else:
            text = ("Křivka: klikněte na první úchop od počátečního bodu."
                    if not self.pending_points else
                    "Křivka: klikněte na druhý úchop u budoucího konce."
                    if len(self.pending_points) == 1 else "Křivka: klikněte na koncový bod.")
        return text

    def start_outline(self, *, hole=False):
        self.curve_segments, self.pending_points, self._input_history = [], [], []
        super().start_outline(hole=hole)
        self._next_step()

    def cancel_outline(self):
        self.curve_segments, self.pending_points, self._input_history = [], [], []
        super().cancel_outline()

    def complete_curve_draft(self):
        self.drawing = False
        self.points, self.curve_segments, self.pending_points, self._input_history = [], [], [], []
        self.unsetCursor()
        self.redraw()
        self.draft_changed.emit()

    def undo_draft_point(self):
        if not self.drawing:
            return False
        if self._input_history:
            points, segments, pending, mode = self._input_history.pop()
            self.points, self.curve_segments, self.pending_points = points, segments, pending
            self.segment_mode = mode
            self.segment_mode_changed.emit(mode)
        else:
            self.points = self.points[:-1]
            self.curve_segments = self.curve_segments[:max(0, len(self.points) - 1)]
        self.redraw()
        self.draft_changed.emit()
        self._next_step()
        return True

    def _add_point(self, point):
        old = (copy.deepcopy(self.points), copy.deepcopy(self.curve_segments),
               copy.deepcopy(self.pending_points), self.segment_mode)
        point = list(point)
        if not self.points:
            self.points = [point]
        else:
            start = self.points[-1]
            required = {"line": 1, "arc": 2, "cubic": 3}[self.segment_mode]
            proposed = [*self.pending_points, point]
            if len(proposed) < required:
                self.pending_points = proposed
            else:
                try:
                    data = {}
                    if self.segment_mode == "arc":
                        data = arc_through_points(start, proposed[0], point)
                    elif self.segment_mode == "cubic":
                        data = {"control1": proposed[0], "control2": proposed[1]}
                    Curve(tuple(start), tuple(point), self.segment_mode, data)
                except ValueError as exc:
                    self.status.emit(str(exc))
                    return
                self.curve_segments.append({"kind": self.segment_mode, "start": start[:],
                                            "end": point[:], "data": data})
                self.points.append(point)
                self.pending_points = []
        self._input_history.append(old)
        self.redraw()
        self.draft_changed.emit()
        self._next_step()

    def _finish_curves(self, closed):
        if self.pending_points:
            self.status.emit("Nejprve dokončete poslední úsek nebo vraťte jeho úchopy Backspace.")
            return
        if not any(s["kind"] != "line" for s in self.curve_segments):
            (super().finish_outline if closed else super().finish_open_profile)()
            if not self.drawing:
                self.curve_segments, self._input_history = [], []
            return
        if not self.curve_segments or (closed and len(set(map(tuple, self.points))) < 2):
            self.status.emit("Profil potřebuje alespoň dva různé body a nenulové úseky.")
            return
        segments = copy.deepcopy(self.curve_segments)
        if closed and segments[-1]["end"] != segments[0]["start"]:
            segments.append({"kind": "line", "start": segments[-1]["end"][:],
                             "end": segments[0]["start"][:], "data": {}})
        self.curve_profile_finished.emit(segments, closed, self.hole)

    def finish_outline(self):
        self._finish_curves(True)

    def finish_open_profile(self):
        if self.hole:
            self.status.emit("Otvor potřebuje uzavřený obrys.")
            return
        self._finish_curves(False)

    def redraw(self):
        points, self.points = self.points, []
        super().redraw()
        self.points = points
        if not self.drawing:
            return
        mapping = (np.diag([1.0, -1.0]), np.zeros(2))
        for spec in self.curve_segments:
            curve = Curve(tuple(spec["start"]), tuple(spec["end"]), spec["kind"], spec["data"])
            self.scene().addPath(_path({"commands": _mapped_commands(curve, mapping),
                                       "closed": False}), cosmetic("#007d78", 2))
        preview = [*self.points[-1:], *self.pending_points]
        for a, b in zip(preview, preview[1:]):
            self.scene().addLine(a[0], -a[1], b[0], -b[1],
                                 cosmetic("#bd7620", 1, Qt.PenStyle.DashLine))
        for index, (x, y) in enumerate([*self.points, *self.pending_points]):
            color = "#bd7620" if index >= len(self.points) else "#007d78"
            marker = self.scene().addEllipse(-3, -3, 6, 6, cosmetic(color), QColor(color))
            marker.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            marker.setPos(x, -y)

    def mousePressEvent(self, event):
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            point = self.snap_point(self.mapToScene(event.position().toPoint()), event.modifiers())
            self._add_point(point)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.drawing:
            self._next_step()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if not self.drawing or not self.points or self._cursor_scene is None:
            return
        cursor = [self._cursor_scene.x(), -self._cursor_scene.y()]
        try:
            if self.segment_mode == "arc" and len(self.pending_points) == 1:
                data = arc_through_points(self.points[-1], self.pending_points[0], cursor)
            elif self.segment_mode == "cubic" and len(self.pending_points) == 2:
                data = {"control1": self.pending_points[0], "control2": self.pending_points[1]}
            else:
                return
            curve = Curve(tuple(self.points[-1]), tuple(cursor), self.segment_mode, data)
            commands = _mapped_commands(curve, (np.diag([1.0, -1.0]), np.zeros(2)))
            painter.setPen(cosmetic("#007d78", 1.5, Qt.PenStyle.DashLine))
            painter.drawPath(_path({"commands": commands, "closed": False}))
        except ValueError:
            pass  # Incomplete/collinear cursor input stays a draft, never source geometry.

    def keyPressEvent(self, event):
        if self.drawing and (
            event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
            or (event.key() == Qt.Key.Key_Z
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            self.undo_draft_point()
            event.accept()
            return
        super().keyPressEvent(event)


class _ControlHandle(QGraphicsEllipseItem):
    def __init__(self, editor, index, point):
        super().__init__(-6, -6, 12, 12)
        self.editor, self.index = editor, index
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                      | QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setBrush(QColor("#df962d"))
        self.setPen(cosmetic("#75480f", 1))
        self.setPos(point[0], -point[1])
        self.setZValue(10)
        self.setToolTip("Táhněte úchop; Esc vrátí rozpracované tažení.")
        self.cancelled = False

    def mousePressEvent(self, event):
        self.before, self.cancelled = self.pos(), False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.cancelled:
            self.setPos(self.before)
            return
        position = self.pos()
        if position != self.before:
            QTimer.singleShot(0, self.editor, lambda: self.editor.set_handle(
                self.index, [position.x(), -position.y()]
            ))

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        position = self.pos()
        self.editor.preview_handle(self.index, [position.x(), -position.y()])

    def cancel_drag(self):
        self.cancelled = True
        self.setPos(self.before)
        self.editor.preview_handle(self.index, [self.before.x(), -self.before.y()])


class CurveEditorDialog(QDialog):
    """Stage one native source edit; the host owns the actual undo command."""

    def __init__(self, project, profile_id, segment_id, *, unit_factor=1, parent=None):
        super().__init__(parent)
        self.source = copy.deepcopy(project)
        self.profile_id, self.segment_id, self.unit_factor = profile_id, segment_id, unit_factor
        self.profile = self.source.profiles[profile_id]
        self.segment = self.profile.segment(segment_id)
        if self.segment is None:
            raise ValueError("Vybraný úsek už v profilu není.")
        self.start = self.profile.vertex(self.segment.start_vertex_id).point[:]
        self.end = self.profile.vertex(self.segment.end_vertex_id).point[:]
        self.result_spec, self._updating = None, False
        self._raw, self._shown = {}, {}
        self.handles = []
        self.setWindowTitle("Upravit úsek profilu")
        self.resize(700, 600)
        layout = QVBoxLayout(self)
        description = QLabel("Zvolte tvar a táhněte oranžové úchopy. Konce úseku a ostré rohy "
                             "zůstanou zachované. Přesné rozměry lze rozbalit níže.")
        description.setWordWrap(True)
        layout.addWidget(description)
        self.kind = QComboBox()
        for label, value in (("Úsečka", "line"), ("Kruhový oblouk", "arc"),
                             ("Bézierova křivka", "cubic")):
            self.kind.addItem(label, value)
        self.kind.setCurrentIndex(self.kind.findData(self.segment.kind))
        layout.addWidget(self.kind)
        self.preview = QGraphicsView()
        self.preview.setScene(QGraphicsScene(self.preview))
        self.preview.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.preview.setMinimumHeight(260)
        layout.addWidget(self.preview, 1)
        self.details = QToolButton(text="Přesné rozměry")
        self.details.setCheckable(True)
        layout.addWidget(self.details)
        self.numeric = QWidget()
        self.form = QFormLayout(self.numeric)
        self.fields = {}
        for key, label in (("angle", "Úhel oblouku (°)"),
                           ("control1_x", "První úchop X"), ("control1_y", "První úchop Y"),
                           ("control2_x", "Druhý úchop X"), ("control2_y", "Druhý úchop Y")):
            field = QDoubleSpinBox()
            field.setRange(-359.9999 if key == "angle" else -1e9,
                           359.9999 if key == "angle" else 1e9)
            field.setDecimals(6)
            field.setKeyboardTracking(False)
            field.setObjectName("curve_" + key)
            self.fields[key] = field
            self.form.addRow(label, field)
            field.editingFinished.connect(self.refresh_preview)
        self.angle = self.fields["angle"]
        self.numeric.setVisible(False)
        self.details.toggled.connect(self.numeric.setVisible)
        layout.addWidget(self.numeric)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.feedback)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Použít změnu úseku")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._load_fields()
        self.kind.currentIndexChanged.connect(self.change_kind)
        self.refresh_preview(frame=True)

    def _load_fields(self):
        self._updating = True
        a, b = np.asarray(self.start), np.asarray(self.end)
        controls = [a + (b - a) / 3, a + 2 * (b - a) / 3]
        angle = self.segment.data.get("sweep_deg", 90)
        for i in (1, 2):
            control = self.segment.data.get("control" + str(i), controls[i - 1])
            for axis, value in zip(("x", "y"), control):
                self._raw[f"control{i}_{axis}"] = float(value)
        self._raw["angle"] = angle
        for key, field in self.fields.items():
            field.setValue(self._raw[key] / (1 if key == "angle" else self.unit_factor))
            self._shown[key] = field.value()
        self._updating = False

    def value(self, key):
        field = self.fields[key]
        return (self._raw[key] if field.value() == self._shown[key]
                else field.value() * (1 if key == "angle" else self.unit_factor))

    def specification(self):
        kind = self.kind.currentData()
        if kind == "line":
            return {"kind": "line", "data": {}}
        if kind == "arc":
            angle = self.value("angle")
            data = (copy.deepcopy(self.segment.data)
                    if self.segment.kind == "arc" and angle == self.segment.data["sweep_deg"]
                    else arc_from_bulge(self.start, self.end, angle))
        else:
            data = {"control" + str(i): [self.value(f"control{i}_{axis}") for axis in ("x", "y")]
                    for i in (1, 2)}
        return {"kind": kind, "data": data}

    def change_kind(self):
        self.refresh_preview(frame=True)

    def refresh_preview(self, *_args, frame=False):
        if self._updating:
            return False
        kind = self.kind.currentData()
        for key, field in self.fields.items():
            visible = (key == "angle") == (kind == "arc") and kind != "line"
            field.setVisible(visible)
            self.form.labelForField(field).setVisible(visible)
        try:
            spec = self.specification()
            curve = Curve(tuple(self.start), tuple(self.end), spec["kind"], spec["data"])
            clone = copy.deepcopy(self.source)
            clone.set_profile_segment(self.profile_id, self.segment_id, **spec)
            self.preview.scene().clear()
            mapping = (np.diag([1.0, -1.0]), np.zeros(2))
            context = profile_native_path(clone.profiles[self.profile_id], mapping)
            self.preview.scene().addPath(_path(context), cosmetic("#79928b", 1))
            data = {"commands": _mapped_commands(curve, mapping), "closed": False}
            self.curve_item = self.preview.scene().addPath(_path(data), cosmetic("#007d78", 3))
            self.handles = []
            positions = ([evaluate(curve, 0.5)] if kind == "arc" else
                         [spec["data"]["control1"], spec["data"]["control2"]]
                         if kind == "cubic" else [])
            for index, point in enumerate(positions):
                handle = _ControlHandle(self, index, point)
                self.preview.scene().addItem(handle)
                self.handles.append(handle)
            for point in (self.start, self.end):
                item = self.preview.scene().addEllipse(-4, -4, 8, 8, cosmetic("#315e58"),
                                                       QColor("#ffffff"))
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
                item.setPos(point[0], -point[1])
            if frame:
                rect = self.preview.scene().itemsBoundingRect()
                margin = max(rect.width(), rect.height(), 1) * 0.2
                self.preview.fitInView(rect.adjusted(-margin, -margin, margin, margin),
                                       Qt.AspectRatioMode.KeepAspectRatio)
            self.feedback.setText(
                "Změna se použije najednou a lze ji vrátit. Zrušit zachová profil."
            )
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            return True
        except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
            self.feedback.setText(str(exc))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return False

    def preview_handle(self, index, point):
        try:
            spec = self.specification()
            if self.kind.currentData() == "arc":
                spec["data"] = arc_through_points(self.start, point, self.end)
            else:
                spec["data"]["control" + str(index + 1)] = point
            curve = Curve(tuple(self.start), tuple(self.end), spec["kind"], spec["data"])
            commands = _mapped_commands(curve, (np.diag([1.0, -1.0]), np.zeros(2)))
            self.curve_item.setPath(_path({"commands": commands, "closed": False}))
        except ValueError as exc:
            self.feedback.setText(str(exc))

    def set_handle(self, index, point):
        try:
            if self.kind.currentData() == "arc":
                data = arc_through_points(self.start, point, self.end)
                self._raw["angle"] = data["sweep_deg"]
                self.angle.setValue(data["sweep_deg"])
                self._shown["angle"] = self.angle.value()
            else:
                for key, value in zip((f"control{index + 1}_x", f"control{index + 1}_y"), point):
                    self._raw[key] = value
                    self.fields[key].setValue(value / self.unit_factor)
                    self._shown[key] = self.fields[key].value()
            self.refresh_preview()
        except ValueError as exc:
            self.refresh_preview()
            self.feedback.setText(str(exc))

    def accept(self):
        for field in self.findChildren(QAbstractSpinBox):
            if not field.isVisible():
                continue
            if not field.hasAcceptableInput():
                self.feedback.setText("Opravte rozepsaný rozměr před potvrzením.")
                field.setFocus()
                return
            field.interpretText()
        if self.refresh_preview():
            self.result_spec = copy.deepcopy(self.specification())
            super().accept()

    def keyPressEvent(self, event):
        grabber = self.preview.scene().mouseGrabberItem()
        if event.key() == Qt.Key.Key_Escape and isinstance(grabber, _ControlHandle):
            grabber.cancel_drag()
            event.accept()
            return
        super().keyPressEvent(event)
