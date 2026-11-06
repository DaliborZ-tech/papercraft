"""Direct author sketching in model millimetres with stable vertex edits."""
# ruff: noqa: N802 -- Qt event overrides use the framework's method names.

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsScene, QGraphicsView


def cosmetic(color, width=1.0, style=Qt.PenStyle.SolidLine):
    pen = QPen(QColor(color), width, style)
    pen.setCosmetic(True)
    return pen


class VertexHandle(QGraphicsEllipseItem):
    def __init__(self, view, profile_id, vertex):
        super().__init__(-5, -5, 10, 10)
        self.view, self.profile_id, self.vertex_id = view, profile_id, vertex.id
        self.setPos(float(vertex.point[0]), -float(vertex.point[1]))
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(cosmetic("#007d78", 2))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setZValue(10)
        self.setToolTip("Bod obrysu · táhnout nebo upravit souřadnice ve vlastnostech")

    def mousePressEvent(self, event):
        self._before = self.pos()
        self._cancelled = False
        self.view.vertex_selected.emit(self.profile_id, self.vertex_id)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._cancelled:
            self.setPos(self._before)
            return
        point = self.pos()
        if point != self._before:
            x, y = self.view.snap_point(point, event.modifiers())
            view, profile_id, vertex_id = self.view, self.profile_id, self.vertex_id
            # A command refresh may delete this handle. Finish Qt's event first.
            QTimer.singleShot(
                0, view, lambda: view.vertex_moved.emit(profile_id, vertex_id, x, y)
            )

    def cancel_drag(self):
        self._cancelled = True
        self.setPos(self._before)


class AuthorSketch(QGraphicsView):
    outline_finished = Signal(list, bool)
    open_profile_finished = Signal(list)
    vertex_selected = Signal(str, str)
    vertex_moved = Signal(str, str, float, float)
    edge_selected = Signal(str, str)
    status = Signal(str)
    draft_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#f7faf9"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.project = None
        self.surface_id = None
        self.profile_id = None
        self.drawing = False
        self.hole = False
        self.points = []
        self.grid_mm = 100.0
        self.display_unit, self.display_factor = "m", 1000.0
        self._visible_grid = self.grid_mm
        self._cursor_scene = None
        self._pan_start = None
        self._draft_items = []
        self._first_frame = True
        self.setSceneRect(-20000, -20000, 40000, 40000)

    def snap_point(self, point, modifiers=Qt.KeyboardModifier.NoModifier):
        x, y = float(point.x()), -float(point.y())
        if not modifiers & Qt.KeyboardModifier.AltModifier and self.grid_mm > 0:
            x, y = (round(value / self.grid_mm) * self.grid_mm for value in (x, y))
        return x, y

    def set_project(self, project, surface_id=None, profile_id=None):
        self.project, self.surface_id, self.profile_id = project, surface_id, profile_id
        self.redraw()
        if self._first_frame:
            self.fitInView(QRectF(-500, -6500, 11000, 7500), Qt.AspectRatioMode.KeepAspectRatio)
            self._first_frame = False

    def select_surface(self, surface_id):
        self.surface_id = surface_id
        self.profile_id = None
        self.redraw()

    def start_outline(self, *, hole=False):
        self.points = []
        self.drawing, self.hole = True, hole
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocus()
        self.redraw()
        self.draft_changed.emit()
        self.status.emit(
            "Klikněte na body otvoru. Enter uzavře, Esc zruší."
            if hole
            else "Klikněte na body vlastního dílu. Enter uzavře, Esc zruší."
        )

    def cancel_outline(self):
        self.drawing = False
        self.points = []
        self.unsetCursor()
        self.redraw()
        self.draft_changed.emit()
        self.status.emit("Rozpracovaný obrys zrušen. Projekt se nezměnil.")

    def finish_outline(self):
        if len(self.points) < 3:
            self.status.emit("Pro uzavřený díl jsou potřeba alespoň tři různé body.")
            return
        points, hole = self.points[:], self.hole
        self.drawing = False
        self.points = []
        self.unsetCursor()
        self.outline_finished.emit(points, hole)
        self.draft_changed.emit()

    def finish_open_profile(self):
        if self.hole or len(self.points) < 2:
            self.status.emit("Otevřený profil potřebuje alespoň dva body.")
            return
        points = self.points[:]
        self.drawing = False
        self.points = []
        self.unsetCursor()
        self.open_profile_finished.emit(points)
        self.draft_changed.emit()

    def redraw(self):
        self.scene().clear()
        if self.project and self.surface_id in self.project.surfaces:
            surface = self.project.surfaces[self.surface_id]
            profiles = [self.project.profiles[surface.profile_id]]
            profiles += [self.project.profiles[h] for h in surface.hole_profile_ids]
        elif self.project and self.profile_id in self.project.profiles:
            profiles = [self.project.profiles[self.profile_id]]
        else:
            profiles = []
        if profiles:
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for profile in profiles:
                polygon = QPolygonF([QPointF(float(x), -float(y)) for x, y in profile.points])
                if profile.closed:
                    path.addPolygon(polygon)
                    path.closeSubpath()
                else:
                    for index, point in enumerate(polygon):
                        path.moveTo(point) if index == 0 else path.lineTo(point)
            brush = (
                QBrush(QColor("#e1eeea"))
                if all(p.closed for p in profiles)
                else QBrush(Qt.BrushStyle.NoBrush)
            )
            self.scene().addPath(path, cosmetic("#315e58", 2), brush)
            for profile in profiles:
                for vertex in profile.vertices:
                    self.scene().addItem(VertexHandle(self, profile.id, vertex))
        if self.points:
            for first, second in zip(self.points, self.points[1:]):
                self.scene().addLine(
                    first[0], -first[1], second[0], -second[1], cosmetic("#007d78", 2)
                )
            for x, y in self.points:
                marker = self.scene().addEllipse(
                    -3, -3, 6, 6, cosmetic("#007d78"), QColor("#007d78")
                )
                marker.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
                marker.setPos(x, -y)
        self.viewport().update()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        step = self.grid_mm
        if step <= 0:
            step = 100.0
        scale = max(abs(self.transform().m11()), 1e-12)
        while step * scale < 12:
            step *= 2
        self._visible_grid = step
        if rect.width() / step > 300 or rect.height() / step > 300:
            return
        painter.setPen(cosmetic("#e3eae7"))
        left, top = math.floor(rect.left() / step) * step, math.floor(rect.top() / step) * step
        for i in range(int(rect.width() / step) + 2):
            x = left + i * step
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for i in range(int(rect.height() / step) + 2):
            y = top + i * step
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.setPen(cosmetic("#9db4ad", 1.2))
        painter.drawLine(QPointF(rect.left(), 0), QPointF(rect.right(), 0))
        painter.drawLine(QPointF(0, rect.top()), QPointF(0, rect.bottom()))

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if self.drawing and self.points and self._cursor_scene is not None:
            x, y = self.points[-1]
            painter.setPen(cosmetic("#007d78", 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, -y), self._cursor_scene)
        painter.save()
        painter.resetTransform()
        painter.setPen(QColor("#315c50"))
        painter.drawText(
            12,
            20,
            f"Obrys · viditelná síť {self._visible_grid / self.display_factor:g} "
            f"{self.display_unit}",
        )
        painter.restore()

    def focus_surface(self):
        if self.scene().items():
            rect = self.scene().itemsBoundingRect()
            if rect.width() > 0 and rect.height() > 0:
                self.fitInView(
                    rect.adjusted(-200, -200, 200, 200), Qt.AspectRatioMode.KeepAspectRatio
                )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            point = self.snap_point(self.mapToScene(event.position().toPoint()), event.modifiers())
            if not self.points or point != tuple(self.points[-1]):
                self.points.append(list(point))
                self.redraw()
                self.draft_changed.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_start is not None:
            delta = event.position() - self._pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            self._pan_start = event.position()
            event.accept()
            return
        if self.drawing:
            point = self.mapToScene(event.position().toPoint())
            x, y = self.snap_point(point, event.modifiers())
            self._cursor_scene = QPointF(x, -y)
            self.status.emit(
                f"Bod: {x / self.display_factor:g}, {y / self.display_factor:g} "
                f"{self.display_unit} · Enter dokončí, Esc zruší"
            )
            self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = None
            self.setCursor(
                Qt.CursorShape.CrossCursor if self.drawing else Qt.CursorShape.ArrowCursor
            )
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        if 0.00005 < self.transform().m11() * factor < 100:
            self.scale(factor, factor)
        event.accept()

    def keyPressEvent(self, event):
        if self.drawing and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.finish_open_profile()
            else:
                self.finish_outline()
        elif self.drawing and event.key() == Qt.Key.Key_Escape:
            self.cancel_outline()
        elif self.drawing and event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.points = self.points[:-1]
            self.redraw()
            self.draft_changed.emit()
        elif event.key() == Qt.Key.Key_F:
            self.focus_surface()
        else:
            super().keyPressEvent(event)
