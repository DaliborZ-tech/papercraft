"""Manual paper layout: scene units are paper mm; all edits go through signals.

The view never changes the document or rebuilds geometry. It previews a drag,
then requests one application command. A cancelled gesture emits no mutation.
"""
# Qt virtual overrides must retain the framework's camelCase method names.
# ruff: noqa: N802

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsScene, QGraphicsView


def _polygon(points):
    return QPolygonF([QPointF(float(x), float(y)) for x, y in points])


def _outline(loops):
    result = QPainterPath()
    result.setFillRule(Qt.FillRule.OddEvenFill)
    for loop in loops:
        result.addPolygon(_polygon(loop))
        result.closeSubpath()
    return result


def _path(data):
    if "points" in data:
        result = QPainterPath()
        points = data["points"]
        if not points:
            return result
        result.moveTo(*points[0])
        for point in points[1:]:
            result.lineTo(*point)
        if data.get("closed"):
            result.closeSubpath()
    else:
        # This projection adapter consumes the same native commands as export;
        # it is never used as the construction or printing authority.
        from archpapercraft.exporter.author_export import _arc, _arc_cubics, _commands

        result, current, start = QPainterPath(), None, None
        for command in _commands(data):
            op = command[0]
            if op == "M":
                current = start = command[1:3]
                result.moveTo(*current)
            elif op == "L":
                current = command[1:3]
                result.lineTo(*current)
            elif op == "C":
                result.cubicTo(*command[1:])
                current = command[-2:]
            elif op == "A":
                for curve in _arc_cubics(_arc(current, command))[0]:
                    result.cubicTo(*curve)
                current = command[-2:]
            else:
                result.closeSubpath()
                current = start
    result.setFillRule(
        Qt.FillRule.OddEvenFill
        if data.get("fill_rule", "evenodd") == "evenodd"
        else Qt.FillRule.WindingFill
    )
    return result


def _distance(point, start, end):
    dx, dy = end.x() - start.x(), end.y() - start.y()
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(point.x() - start.x(), point.y() - start.y())
    t = max(0.0, min(1.0, ((point.x() - start.x()) * dx + (point.y() - start.y()) * dy) / length2))
    return math.hypot(point.x() - start.x() - t * dx, point.y() - start.y() - t * dy)


def _font(painter, size_mm):
    font = QFont("Arial")
    font.setPointSizeF(size_mm * 72 / painter.device().logicalDpiY())
    painter.setFont(font)


class AuthorPartItem(QGraphicsObject):
    def __init__(self, part, placement, geometry, view):
        super().__init__()
        self.part, self.placement, self.geometry, self.view = part, placement, geometry, view
        self.material = QPainterPath()
        for loops in geometry.get("polygons", {}).values():
            self.material = self.material.united(_outline(loops))
        for tab in geometry.get("paths", {}).get("TABS", []):
            self.material = self.material.united(_path(tab))
        self._empty = self.material.isEmpty()
        self._origin, self._press_scene = QPointF(), QPointF()
        self._dragging, self._cancelled = False, False
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not placement.position_locked)
        self.setZValue(3)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if placement.position_locked
            else Qt.CursorShape.OpenHandCursor
        )
        self.setToolTip(
            f"{part.name}"
            + (" · neaktuální rozvin" if part.stale else "")
            + (" · poloha uzamčena" if placement.position_locked else " · tažením přesunete")
            + (" · natočení uzamčeno" if placement.rotation_locked else " · Alt+kolečko natočí")
        )

    def boundingRect(self):
        if self._empty:
            return QRectF(-2, -6, 42, 10)
        return self.material.boundingRect().adjusted(-3, -4, 3, 3)

    def shape(self):
        if self._empty:
            result = QPainterPath()
            result.addRect(self.boundingRect())
            return result
        return self.material

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._empty:
            painter.setPen(QColor("#966022"))
            _font(painter, 2.5)
            painter.drawText(QPointF(0, 0), self.part.name + " · čeká na rozvin")
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ece8da"))
        for loops in self.geometry.get("polygons", {}).values():
            painter.drawPath(_outline(loops))
        painter.setBrush(QColor("#eee0bc"))
        for path in self.geometry.get("paths", {}).get("TABS", []):
            painter.drawPath(_path(path))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for role, color, style in (
            ("CUT", "#273d38", Qt.PenStyle.SolidLine),
            ("FOLD_MOUNTAIN", "#28615a", Qt.PenStyle.DashLine),
            ("FOLD_VALLEY", "#8b603a", Qt.PenStyle.DashDotLine),
            ("GUIDES", "#9caba4", Qt.PenStyle.DotLine),
        ):
            painter.setPen(QPen(QColor(color), 0.25 if role != "GUIDES" else 0.15, style))
            for path in self.geometry.get("paths", {}).get(role, []):
                painter.drawPath(_path(path))
        if self.part.stale:
            painter.setPen(QPen(QColor("#bd7c23"), 0.45, Qt.PenStyle.DashLine))
            painter.drawRect(self.boundingRect())
            _font(painter, 2.0)
            painter.drawText(
                self.boundingRect().topLeft() + QPointF(0, 2.5), "Neaktuální · přepočítat"
            )
        if self.isSelected():
            painter.setPen(QPen(QColor("#13816b"), 0.6))
            painter.drawPath(self.material)
        if self.view.selected_edge:
            painter.setPen(QPen(QColor("#d67625"), 0.9))
            for edge in self.geometry.get("edges", []):
                if (edge["surface_id"], edge["edge_id"]) == self.view.selected_edge:
                    painter.drawLine(QPointF(*edge["start"]), QPointF(*edge["end"]))
        painter.setPen(QPen(QColor("#287568"), 0.25))
        painter.drawLine(QPointF(-1.4, 0), QPointF(1.4, 0))
        painter.drawLine(QPointF(0, -1.4), QPointF(0, 1.4))
        painter.setPen(QColor("#294e43"))
        for label in self.geometry.get("labels", []):
            _font(painter, label.get("size_mm", 2.5))
            painter.drawText(QPointF(label["x"], label["y"]), label["text"])

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self._origin, self._press_scene = self.pos(), event.scenePos()
        self._dragging, self._cancelled = False, False
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.view.select(self.part.id)
        self.view.part_selected.emit(self.part.id)
        edge = self.view.nearest_edge(event.scenePos(), only=self.part.id)
        if edge:
            self.view.selected_edge = edge[1:]
            self.view.edge_selected.emit(*edge[1:])
            self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._cancelled or self.placement.position_locked:
            event.accept()
            return
        delta = event.scenePos() - self._press_scene
        if not self._dragging:
            pixels = self.view.viewportTransform().map(
                event.scenePos()
            ) - self.view.viewportTransform().map(self._press_scene)
            self._dragging = math.hypot(pixels.x(), pixels.y()) >= 3
        if self._dragging:
            point = self._origin + delta
            payload = self.view.resolve_placement(point, event.scenePos())
            if not event.modifiers() & Qt.KeyboardModifier.AltModifier:
                payload["x_mm"], payload["y_mm"] = round(payload["x_mm"]), round(payload["y_mm"])
            origin = self.view.page_origins.get(payload["page_id"], self.view.tray_origin)
            self.setPos(origin + QPointF(payload["x_mm"], payload["y_mm"]))
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if self._cancelled:
            self.setPos(self._origin)
        elif self._dragging:
            # Re-evaluate the unsnapped pointer delta on release. A user may
            # press Alt after the last mouse-move event to disable the snap.
            anchor = self._origin + event.scenePos() - self._press_scene
            payload = self.view.resolve_placement(anchor, event.scenePos())
            if not event.modifiers() & Qt.KeyboardModifier.AltModifier:
                payload["x_mm"], payload["y_mm"] = round(payload["x_mm"]), round(payload["y_mm"])
            payload["rotation_deg"] = self.placement.rotation_deg
            origin = self.view.page_origins.get(payload["page_id"], self.view.tray_origin)
            self.setPos(origin + QPointF(payload["x_mm"], payload["y_mm"]))
            unchanged = all(
                payload[name] == getattr(self.placement, name)
                for name in ("page_id", "x_mm", "y_mm", "rotation_deg")
            )
            view, identity = self.view, self.part.id
            # The receiving command may rebuild the scene. Queue it after this
            # item's event stack, with the view as Qt lifetime context.
            if not unchanged:
                QTimer.singleShot(0, view, lambda: view.placement_changed.emit(identity, payload))
        self._dragging = False
        event.accept()

    def cancel_drag(self):
        self._cancelled, self._dragging = True, False
        self.setPos(self._origin)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_drag()
            event.accept()
        else:
            super().keyPressEvent(event)


class AuthorPaperView(QGraphicsView):
    part_selected = Signal(str)
    edge_selected = Signal(str, str)
    placement_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#e0e7e1"))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(
            "Vyberte díl. Tažením jej rozmístíte, Alt vypne přichycení. "
            "Ctrl+kolečko přiblíží, Alt+kolečko natočí. "
            "Esc vrátí tažení, F najde vybraný díl."
        )
        self.project = None
        self.part_items, self.page_origins = {}, {}
        self.selected_part, self.selected_edge = None, None
        self.tray_origin = QPointF(500, 0)
        self.issue_overlays = []
        self._initialized, self._panning = False, False
        self._pan_at = QPointF()

    def set_project(self, project, *, frame=False):
        # Read-only projection previews also work without a persisted document UUID.
        previous_id = getattr(self.project, "project_id", id(self.project))
        if frame or previous_id != getattr(project, "project_id", id(project)):
            self._initialized = False
        self.project = project
        self.scene().clear()
        self.part_items, self.page_origins, self.issue_overlays = {}, {}, []
        widths = [
            max((p.width_mm for i, p in enumerate(project.pages) if i % 2 == col), default=0.0)
            for col in (0, 1)
        ]
        row_y = 0.0
        for row in range((len(project.pages) + 1) // 2):
            for index in range(row * 2, min(row * 2 + 2, len(project.pages))):
                page = project.pages[index]
                origin = QPointF(0 if index % 2 == 0 else widths[0] + 25, row_y)
                self.page_origins[page.id] = origin
                self.scene().addRect(
                    QRectF(origin.x(), origin.y(), page.width_mm, page.height_mm),
                    QPen(QColor("#adbcb2"), 0.25),
                    QBrush(QColor("white")),
                )
                margin = page.margin_mm
                self.scene().addRect(
                    QRectF(
                        origin.x() + margin,
                        origin.y() + margin,
                        page.width_mm - 2 * margin,
                        page.height_mm - 2 * margin,
                    ),
                    QPen(QColor("#c2ccc4"), 0.2, Qt.PenStyle.DashLine),
                )
                self.scene().addLine(
                    origin.x() + 10,
                    origin.y() + page.height_mm - 15,
                    origin.x() + 110,
                    origin.y() + page.height_mm - 15,
                    QPen(QColor("#94a59c"), 0.25),
                )
                self._text(
                    "100 mm · tisk 100 % / skutečná velikost",
                    origin + QPointF(10, page.height_mm - 12),
                    2.4,
                )
                self._text(f"Stránka {index + 1}", origin + QPointF(0, page.height_mm + 3), 3.0)
            row_y += max(p.height_mm for p in project.pages[row * 2 : row * 2 + 2]) + 30
        right = max((self.page_origins[p.id].x() + p.width_mm for p in project.pages), default=0.0)
        self.tray_origin = QPointF(right + 45, 0)
        self._text(
            "Odkládací plocha · díly bez stránky čekají na umístění",
            self.tray_origin + QPointF(0, -10),
            3.0,
        )
        for identity, part in project.parts.items():
            placement = project.placements[identity]
            geometry = project.part_geometry(identity)
            item = AuthorPartItem(part, placement, geometry, self)
            self.scene().addItem(item)
            origin = self.page_origins.get(placement.page_id, self.tray_origin)
            item.setPos(origin + QPointF(placement.x_mm, placement.y_mm))
            item.setRotation(math.remainder(placement.rotation_deg, 360.0))
            item.setSelected(identity == self.selected_part)
            self.part_items[identity] = item
        self.scene().setSceneRect(self.scene().itemsBoundingRect().adjusted(-15, -20, 25, 25))
        if not self._initialized:
            QTimer.singleShot(0, self, self._initial_fit)

    def _initial_fit(self):
        if not self._initialized:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._initialized = True

    def _text(self, value, point, size_mm):
        item = self.scene().addSimpleText(value, QFont("Arial", 10))
        item.setScale(size_mm / 13.3)
        item.setBrush(QColor("#506b5c"))
        item.setPos(point)
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        return item

    def select(self, part_id, edge=None):
        self.selected_part = part_id or None
        self.selected_edge = tuple(edge) if edge else None
        for identity, item in self.part_items.items():
            item.setSelected(identity == part_id)
            item.update()

    def focus_part(self, part_id):
        if part_id in self.part_items:
            item = self.part_items[part_id]
            self.fitInView(
                item.sceneBoundingRect().adjusted(-12, -12, 12, 12),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def resolve_placement(self, anchor, target=None):
        target = target if target is not None else anchor
        for page in self.project.pages:
            origin = self.page_origins[page.id]
            if QRectF(origin.x(), origin.y(), page.width_mm, page.height_mm).contains(target):
                return {
                    "page_id": page.id,
                    "x_mm": anchor.x() - origin.x(),
                    "y_mm": anchor.y() - origin.y(),
                }
        return {
            "page_id": None,
            "x_mm": anchor.x() - self.tray_origin.x(),
            "y_mm": anchor.y() - self.tray_origin.y(),
        }

    def nearest_edge(self, point, only=None):
        viewport_point = self.viewportTransform().map(point)
        best = None
        for identity, item in self.part_items.items():
            if only is not None and identity != only:
                continue
            for edge in item.geometry.get("edges", []):
                start = self.viewportTransform().map(item.mapToScene(QPointF(*edge["start"])))
                end = self.viewportTransform().map(item.mapToScene(QPointF(*edge["end"])))
                distance = _distance(viewport_point, start, end)
                if distance <= 7 and (best is None or distance < best[0]):
                    best = distance, identity, edge["surface_id"], edge["edge_id"]
        return (best[1], best[2], best[3]) if best else None

    def show_issue(self, issue):
        for overlay in self.issue_overlays:
            self.scene().removeItem(overlay)
        self.issue_overlays = []
        items = [self.part_items[p] for p in issue.part_ids if p in self.part_items]
        paths = [item.sceneTransform().map(item.material) for item in items]
        highlight = QPainterPath()
        if len(paths) > 1:
            for index, a in enumerate(paths):
                for b in paths[index + 1 :]:
                    highlight = highlight.united(a.intersected(b))
        elif items:
            placement = items[0].placement
            page = next((p for p in self.project.pages if p.id == placement.page_id), None)
            if page and issue.code in ("PHYSICAL_OVERFLOW", "PRINT_MARGIN", "PRINT_GUIDE_OVERLAP"):
                origin = self.page_origins[page.id]
                region = QPainterPath()
                if issue.code == "PRINT_GUIDE_OVERLAP":
                    region.addRect(
                        QRectF(
                            origin.x() + 10,
                            origin.y() + page.height_mm - 18,
                            page.width_mm - 20,
                            16,
                        )
                    )
                    highlight = paths[0].intersected(region)
                else:
                    margin = page.margin_mm if issue.code == "PRINT_MARGIN" else 0
                    region.addRect(
                        QRectF(
                            origin.x() + margin,
                            origin.y() + margin,
                            page.width_mm - 2 * margin,
                            page.height_mm - 2 * margin,
                        )
                    )
                    highlight = paths[0].subtracted(region)
        if not highlight.isEmpty():
            overlay = self.scene().addPath(
                highlight, QPen(QColor("#c14628"), 0.4), QBrush(QColor(220, 65, 35, 100))
            )
            overlay.setZValue(10)
            overlay.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.issue_overlays.append(overlay)
        if items:
            self.focus_part(items[0].part.id)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning, self._pan_at = True, event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            hit = next(
                (
                    item
                    for item in self.items(event.position().toPoint())
                    if isinstance(item, AuthorPartItem)
                ),
                None,
            )
            if hit is None:
                edge = self.nearest_edge(point)
                if edge:
                    self.select(edge[0], edge[1:])
                    self.part_selected.emit(edge[0])
                    self.edge_selected.emit(*edge[1:])
                    event.accept()
                    return
                self.select(None)
                self.part_selected.emit("")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_at
            self._pan_at = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - round(delta.x())
            )
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - round(delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if (
            event.modifiers() & Qt.KeyboardModifier.AltModifier
            and self.selected_part in self.part_items
        ):
            item = self.part_items[self.selected_part]
            placement = item.placement
            if not placement.rotation_locked and event.angleDelta().y():
                payload = {
                    "page_id": placement.page_id,
                    "x_mm": placement.x_mm,
                    "y_mm": placement.y_mm,
                    "rotation_deg": placement.rotation_deg
                    + (5 if event.angleDelta().y() > 0 else -5),
                }
                self.placement_changed.emit(item.part.id, payload)
            event.accept()
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y():
                factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
                self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            item = self.scene().mouseGrabberItem()
            if isinstance(item, AuthorPartItem):
                item.cancel_drag()
                event.accept()
                return
        if event.key() == Qt.Key.Key_F and self.selected_part:
            self.focus_part(self.selected_part)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Home:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            event.accept()
            return
        super().keyPressEvent(event)
