"""Contextual connector editing with transactional core previews and stable tab IDs."""
# ruff: noqa: N802 -- Qt event overrides use the framework's method names.

from __future__ import annotations

import copy

from PySide6.QtCore import QPointF, QRectF, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring.model import Connector


def spin(low=0.01, high=10000, value=5):
    field = QDoubleSpinBox()
    field.setDecimals(4)
    field.setRange(low, high)
    field.setValue(value)
    field.setKeyboardTracking(False)
    return field


def choose(combo, value):
    # QVariant tuple matching is deliberately explicit, never an index identity.
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return


def title(project, sid):
    surface = project.surfaces[sid]
    part = project.parts[surface.part_id]
    return f"{surface.name} (P{part.number})"


class MaterialPreview(QGraphicsView):
    """Render only the material paths supplied by the preview document."""

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setMinimumSize(280, 170)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#fafbfc"))

    def show_part(self, project, part_id):
        self.scene().clear()
        data = project.part_geometry(part_id)
        for role, paths in data["paths"].items():
            for source in paths:
                points = source["points"]
                path = QPainterPath(QPointF(points[0][0], -points[0][1]))
                for x, y in points[1:]:
                    path.lineTo(x, -y)
                if source["closed"]:
                    path.closeSubpath()
                color = {"TABS": "#a75800", "GUIDES": "#777b84", "CUT": "#263541"}.get(
                    role, "#147d8e"
                )
                pen = QPen(QColor(color), 1.3)
                pen.setCosmetic(True)
                self.scene().addPath(path, pen)
        bounds = self.scene().itemsBoundingRect()
        if not bounds.isEmpty():
            self.fitInView(bounds.adjusted(-2, -2, 2, 2), Qt.AspectRatioMode.KeepAspectRatio)


class OutlineCanvas(QGraphicsView):
    """A paper-mm source sketch; its two hinge points are immutable."""

    changed = Signal(list)

    def __init__(self, outline, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumSize(320, 190)
        self.points = copy.deepcopy(outline)
        self.drawing = False
        self.redraw()

    def redraw(self):
        self.scene().clear()
        if not self.points:
            return
        path = QPainterPath(QPointF(self.points[0][0], -self.points[0][1]))
        for x, y in self.points[1:]:
            path.lineTo(x, -y)
        if len(self.points) > 2:
            path.closeSubpath()
        pen = QPen(QColor("#b36912"), 1.5)
        pen.setCosmetic(True)
        self.scene().addPath(path, pen)
        base = QPen(QColor("#136f82"), 2.5)
        base.setCosmetic(True)
        self.scene().addLine(0, 0, self.points[1][0], 0, base)
        for index, (x, y) in enumerate(self.points):
            item = self.scene().addText(str(index + 1))
            item.setScale(0.08)
            item.setPos(x, -y)
        length = self.points[1][0]
        top = max([point[1] for point in self.points] + [5])
        self.setSceneRect(QRectF(-2, -top - 3, length + 4, top + 6))
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def start_drawing(self):
        self.points = self.points[:2]
        self.drawing = True
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocus()
        self.redraw()
        self.changed.emit(copy.deepcopy(self.points))

    def mousePressEvent(self, event):
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            if point.y() < 0:
                self.points.append([float(point.x()), float(-point.y())])
                self.redraw()
                self.changed.emit(copy.deepcopy(self.points))
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if self.drawing and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.drawing = False
            self.unsetCursor()
            self.changed.emit(copy.deepcopy(self.points))
            event.accept()
        elif self.drawing and event.key() == Qt.Key.Key_Backspace and len(self.points) > 2:
            self.points.pop()
            self.redraw()
            self.changed.emit(copy.deepcopy(self.points))
        else:
            super().keyPressEvent(event)


class ConnectorEditDialog(QDialog):
    """Preview a complete command on a clone, then replay once through host undo."""

    def __init__(self, host, relation, *, connector_id=None, tab_id=None, band=False):
        super().__init__(host)
        self.host, self.relation = host, relation
        self.connector_id, self.tab_id, self.band = connector_id, tab_id, band
        self.state = host.project.to_dict()
        self.preview_state, self.result_parameters = None, None
        self._updating = True
        project = host.project
        kind, rid = relation
        record = project.attachments[rid] if kind == "attachment" else project.joints[rid]
        self.source = record.source_surface_id if kind == "attachment" else record.surface_a
        self.target = record.target_surface_id if kind == "attachment" else record.surface_b
        connector = project.connectors.get(connector_id)
        overrides = connector.tab_overrides.get(tab_id, {}) if connector and tab_id else {}
        self.setWindowTitle(
            "Samostatný lepicí pásek"
            if band
            else "Upravit záložku"
            if tab_id
            else "Chlopeň a záložky"
        )
        self.resize(620, 690)
        layout = QVBoxLayout(self)
        self.receiver_label = QLabel(f"Protikus: {title(project, self.target)}")
        self.receiver_label.setWordWrap(True)
        layout.addWidget(self.receiver_label)
        form = QFormLayout()
        layout.addLayout(form)
        self.width = spin(value=overrides.get("width_mm", connector.width_mm if connector else 5))
        self.width.setObjectName("connector_width")
        self.width.setSuffix(" mm papír")
        form.addRow("Šířka poloviny pásku" if band else "Šířka záložky", self.width)
        self.taper = spin(0.01, 1, overrides.get("taper", connector.taper if connector else 0.6))
        self.taper.setObjectName("connector_taper")
        self.shape = QComboBox()
        self.shape.setObjectName("connector_shape")
        self.shape.addItem("Zkosená", "trapezoid")
        self.shape.addItem("Trojúhelníková", "triangle")
        if tab_id or (connector and connector.shape == "custom"):
            self.shape.addItem("Vlastní nakreslený obrys", "custom")
        choose(self.shape, overrides.get("shape", connector.shape if connector else "trapezoid"))
        if not band:
            form.addRow("Tvar", self.shape)
            form.addRow("Poměr vnější hrany", self.taper)
        self.enabled = QCheckBox("Tato záložka je zapnutá" if tab_id else "Chlopeň je zapnutá")
        self.enabled.setChecked(
            overrides.get("enabled", True) if tab_id else connector.enabled if connector else True
        )
        self.enabled.setObjectName("connector_enabled")
        advanced = QGroupBox("Další možnosti")
        advanced.setCheckable(True)
        advanced.setChecked(False)
        self.advanced_body = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.addWidget(self.advanced_body)
        advanced_form = QFormLayout(self.advanced_body)
        self.count = QSpinBox()
        self.count.setRange(1, 4096)
        self.count.setKeyboardTracking(False)
        self.count.setValue(connector.count if connector else 1)
        self.count.setObjectName("connector_count")
        self.gap = spin(0, 10000, connector.gap_mm if connector else 0)
        self.gap.setObjectName("connector_gap")
        self.gap.setSuffix(" mm papír")
        self.owner = QComboBox()
        self.owner.setObjectName("connector_owner")
        for sid in (self.source, self.target):
            self.owner.addItem(title(project, sid), sid)
        choose(self.owner, connector.owner_surface_id if connector else self.source)
        if kind == "attachment":
            self.owner.model().item(1).setEnabled(False)
            self.owner.setToolTip(
                "Uvnitř souvislé plochy nevznikne chlopeň bez řezu. "
                "Pro tento protikus použijte pásek."
            )
        self.receiver_side = QComboBox()
        self.receiver_side.addItem("Dosud neurčená", "unknown")
        self.receiver_side.addItem("Vnitřní strana", "inside")
        self.receiver_side.addItem("Vnější strana", "outside")
        choose(self.receiver_side, getattr(connector, "receiver_side", "unknown"))
        self.receiver_side.setObjectName("connector_receiver_side")
        self.source_side = QComboBox()
        self.source_side.addItem("Vnitřní strana", "inside")
        self.source_side.addItem("Vnější strana", "outside")
        if band:
            advanced_form.addRow("Strana zdrojové plochy", self.source_side)
        else:
            advanced_form.addRow(self.enabled)
            if not tab_id:
                advanced_form.addRow("Počet záložek", self.count)
                advanced_form.addRow("Mezera mezi záložkami", self.gap)
                advanced_form.addRow("Materiál chlopně patří", self.owner)
                if kind == "joint" and hasattr(Connector, "receiver_side"):
                    advanced_form.addRow("Lepit na stranu protikusu", self.receiver_side)
        self.advanced_body.setVisible(False)
        advanced.toggled.connect(self.advanced_body.setVisible)
        layout.addWidget(advanced)
        self.outline = copy.deepcopy(connector.outline_mm) if connector else []
        if tab_id:
            geometry = project.connector_geometry(connector_id)
            tab = next((t for t in geometry["all_tabs"] if t["id"] == tab_id), None)
            self.outline = copy.deepcopy(tab["outline_mm"]) if tab else []
        self.drawing_group = QGroupBox("Vlastní obrys v papírových mm")
        drawing_layout = QVBoxLayout(self.drawing_group)
        hint = QLabel(
            "Modrá základna zůstává pevná. Nakreslete vnější body od pravého konce "
            "zpět k levému; Enter dokončí, Backspace vrátí poslední bod."
        )
        hint.setWordWrap(True)
        drawing_layout.addWidget(hint)
        self.canvas = OutlineCanvas(self.outline)
        drawing_layout.addWidget(self.canvas)
        self.draw = QPushButton("Nakreslit vnější obrys")
        self.draw.setObjectName("connector_draw_outline")
        self.draw.setEnabled(len(self.outline) >= 2)
        self.draw.clicked.connect(self.canvas.start_drawing)
        drawing_layout.addWidget(self.draw)
        precise = QFormLayout()
        self.vertex = QComboBox()
        self.vertex.setObjectName("connector_outline_vertex")
        self.vertex.currentIndexChanged.connect(self.select_outline_vertex)
        self.vertex_x, self.vertex_y = spin(-10000, 10000, 0), spin(-10000, 10000, 0)
        self.vertex_x.setObjectName("connector_outline_x")
        self.vertex_y.setObjectName("connector_outline_y")
        for field in (self.vertex_x, self.vertex_y):
            field.setSuffix(" mm papír")
            field.valueChanged.connect(self.move_outline_vertex)
        precise.addRow("Vnější bod", self.vertex)
        precise.addRow("Vodorovně od začátku základny", self.vertex_x)
        precise.addRow("Vzdálenost od ohybu", self.vertex_y)
        drawing_layout.addLayout(precise)
        self.canvas.changed.connect(self.set_outline)
        layout.addWidget(self.drawing_group)
        self.preview = MaterialPreview()
        layout.addWidget(self.preview, 1)
        self.status = QLabel()
        self.status.setObjectName("connector_preview_status")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        caveat = QLabel(
            "Náhled ověřuje digitální materiál a lepicí kontakt. "
            "Prostor při ohýbání a fyzická pevnost konkrétního papíru nejsou tímto ověřeny."
        )
        caveat.setWordWrap(True)
        layout.addWidget(caveat)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for field in (self.width, self.taper, self.count, self.gap):
            field.valueChanged.connect(self.update_preview)
        for field in (self.shape, self.owner, self.receiver_side, self.source_side):
            if field is not self.owner:
                field.currentIndexChanged.connect(self.update_preview)
        self.owner.currentIndexChanged.connect(self.owner_changed)
        self.enabled.toggled.connect(self.update_preview)
        raw_width = overrides.get("width_mm", connector.width_mm if connector else 5)
        raw_taper = overrides.get("taper", connector.taper if connector else 0.6)
        raw_gap = connector.gap_mm if connector else 0
        self.initial_numbers = {
            self.width: (self.width.value(), raw_width),
            self.taper: (self.taper.value(), raw_taper),
            self.gap: (self.gap.value(), raw_gap),
        }
        self._updating = False
        self.fill_outline_vertices()
        self.initial_parameters = self.parameters()
        self.update_preview()

    def set_outline(self, points):
        self.outline = copy.deepcopy(points)
        self.fill_outline_vertices()
        self.update_preview()

    def fill_outline_vertices(self):
        with QSignalBlocker(self.vertex):
            self.vertex.clear()
            for index in range(2, len(self.outline)):
                self.vertex.addItem(f"Vnější bod {index - 1}", index)
            self.vertex.setCurrentIndex(self.vertex.count() - 1)
        self.select_outline_vertex()

    def select_outline_vertex(self, *_args):
        index = self.vertex.currentData()
        for field in (self.vertex_x, self.vertex_y):
            field.setEnabled(index is not None)
        if index is not None:
            for field, value in zip((self.vertex_x, self.vertex_y), self.outline[index]):
                with QSignalBlocker(field):
                    field.setValue(value)
            self.vertex_display = [self.vertex_x.value(), self.vertex_y.value()]

    def move_outline_vertex(self, *_args):
        index = self.vertex.currentData()
        if index is not None and not self._updating:
            displayed = [self.vertex_x.value(), self.vertex_y.value()]
            self.outline[index] = [
                raw if value == old else value
                for raw, value, old in zip(self.outline[index], displayed, self.vertex_display)
            ]
            self.vertex_display = displayed
            self.canvas.points = copy.deepcopy(self.outline)
            self.canvas.redraw()
            self.update_preview()

    def owner_changed(self, *_args):
        with QSignalBlocker(self.receiver_side):
            self.receiver_side.setCurrentIndex(0)
        self.update_preview()

    def parameters(self):
        def retained(field):
            shown, raw = self.initial_numbers[field]
            return raw if field.value() == shown else field.value()

        if self.band:
            return {"width_mm": retained(self.width), "source_side": self.source_side.currentData()}
        result = {
            "width_mm": retained(self.width),
            "taper": retained(self.taper),
            "shape": self.shape.currentData(),
            "enabled": self.enabled.isChecked(),
        }
        if result["shape"] == "custom":
            result["outline_mm"] = copy.deepcopy(self.outline)
        if not self.tab_id:
            result.update(
                count=self.count.value(), gap_mm=retained(self.gap), owner=self.owner.currentData()
            )
            if self.relation[0] == "joint" and hasattr(Connector, "receiver_side"):
                result["receiver_side"] = self.receiver_side.currentData()
        return result

    def apply(self, project, parameters=None):
        parameters = parameters if parameters is not None else self.result_parameters
        kind, rid = self.relation
        if self.band:
            return project.add_glue_band(rid, **parameters)
        cid = self.connector_id
        if cid is not None and parameters == self.initial_parameters:
            return cid
        if self.tab_id:
            project.set_connector_tab(cid, self.tab_id, **parameters)
            return cid
        if cid is None:
            base = {key: parameters[key] for key in ("width_mm", "taper", "shape")}
            if kind == "attachment":
                cid = project.set_attachment_tab(rid, **base)
            else:
                project.set_tab(rid, owner=parameters["owner"], **base)
                cid = project.joints[rid].connector_id
        project.set_connector(cid, **parameters)
        return cid

    def update_preview(self, *_args):
        if self._updating:
            return
        self.drawing_group.setVisible(bool(self.tab_id and self.shape.currentData() == "custom"))
        try:
            clone = AuthorProject.from_dict(self.state)
            result = self.apply(clone, self.parameters())
            pid = (
                result
                if self.band
                else clone.part_for_surface(clone.connectors[result].owner_surface_id)
            )
            clone.recompute([pid])
            self.preview.show_part(clone, pid)
            self.preview_state = clone.to_dict()
            if self.band:
                message = "Samostatný pásek má vlastní díl a dva skutečné protikusy."
            else:
                data = clone.connector_geometry(result)
                contacts = data["tabs"]
                area = sum(tab["available_area_mm2"] for tab in contacts)
                message = (
                    f"{len(contacts)} zapnutých záložek; dostupná lepicí plocha {area:.4g} mm²."
                )
                recipient = (
                    self.target
                    if clone.connectors[result].owner_surface_id == self.source
                    else self.source
                )
                self.receiver_label.setText(f"Protikus: {title(clone, recipient)}")
            related = {clone.part_for_surface(self.source), clone.part_for_surface(self.target)}
            conflicts = [
                issue.message
                for issue in clone.validate_layout()
                if issue.severity == "error"
                and issue.code.startswith("FOLDED_")
                and (issue.joint_id == self.relation[1] or related.intersection(issue.part_ids))
            ]
            if conflicts:
                message += "\nZbývá opravit: " + "\n".join(dict.fromkeys(conflicts))
                message += "\nNávrh lze dál upravovat; export tohoto stavu zůstává blokovaný."
            self.status.setText(message)
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except Exception as exc:
            self.preview_state = None
            self.status.setText(f"Upravte návrh: {exc}")
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def accept(self):
        # Commit text before taking the preview/result snapshot (C-05).
        for field in self.findChildren(QAbstractSpinBox):
            if not field.hasAcceptableInput():
                self.status.setText("Opravte rozepsané číslo před potvrzením.")
                field.setFocus()
                return
            field.interpretText()
        self.update_preview()
        if self.preview_state is not None:
            self.result_parameters = self.parameters()
            super().accept()


class ConnectorPanel(QWidget):
    relation_changed = Signal(object)

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        layout = QVBoxLayout(self)
        self.relationship = QComboBox()
        self.relationship.setObjectName("connector_relationship")
        self.relationship.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.relationship.setMinimumContentsLength(16)
        self.relationship.currentIndexChanged.connect(self.refresh_details)
        layout.addWidget(QLabel("Spoje vybrané plochy"))
        layout.addWidget(self.relationship)
        self.receiver = QLabel()
        self.receiver.setWordWrap(True)
        layout.addWidget(self.receiver)
        self.status = QLabel()
        self.status.setObjectName("connector_panel_status")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.show_receiver = QPushButton("Ukázat protikus")
        self.show_receiver.clicked.connect(self.select_receiver)
        self.edit = QPushButton("Přidat chlopeň…")
        self.edit.clicked.connect(self.edit_connector)
        self.remove = QPushButton("Odebrat chlopeň")
        self.remove.clicked.connect(self.remove_connector)
        self.band = QPushButton("Samostatný lepicí pásek…")
        self.band.clicked.connect(self.add_band)
        self.remove_relation = QPushButton("Odebrat vnitřní připojení")
        self.remove_relation.clicked.connect(self.remove_attachment)
        for button in (self.show_receiver, self.edit, self.remove, self.band, self.remove_relation):
            layout.addWidget(button)
        row = QHBoxLayout()
        self.tabs = QComboBox()
        self.tabs.setObjectName("connector_individual_tab")
        self.edit_tab = QPushButton("Upravit jednu…")
        self.edit_tab.clicked.connect(self.edit_individual)
        row.addWidget(self.tabs, 1)
        row.addWidget(self.edit_tab)
        layout.addLayout(row)
        self.refresh()

    @property
    def current_relation(self):
        return self.relationship.currentData()

    def refresh(self):
        project, selected = self.host.project, self.host.selected_surface
        previous = self.current_relation
        with QSignalBlocker(self.relationship):
            self.relationship.clear()
            if project and selected in project.surfaces:
                for jid, joint in project.joints.items():
                    if selected in (joint.surface_a, joint.surface_b):
                        other = joint.surface_b if selected == joint.surface_a else joint.surface_a
                        self.relationship.addItem(
                            f"J{joint.number} · {title(project, other)}", ("joint", jid)
                        )
                for aid, attachment in project.attachments.items():
                    if selected in (attachment.source_surface_id, attachment.target_surface_id):
                        other = (
                            attachment.target_surface_id
                            if selected == attachment.source_surface_id
                            else attachment.source_surface_id
                        )
                        self.relationship.addItem(
                            f"A{attachment.number} · {title(project, other)}", ("attachment", aid)
                        )
                choose(self.relationship, previous)
        self.refresh_details()

    def record(self):
        relation = self.current_relation
        if not relation or not self.host.project:
            return None
        kind, rid = relation
        return (
            self.host.project.attachments if kind == "attachment" else self.host.project.joints
        ).get(rid)

    def refresh_details(self, *_args):
        record = self.record()
        for control in (
            self.show_receiver,
            self.edit,
            self.remove,
            self.band,
            self.remove_relation,
            self.tabs,
            self.edit_tab,
        ):
            control.setEnabled(record is not None)
        with QSignalBlocker(self.tabs):
            self.tabs.clear()
        if record is None:
            self.receiver.setText("Vyberte plochu se spojenou hranou nebo vnitřním připojením.")
            self.status.setText(
                "Připojení dovnitř plochy vytvoříte příkazem Připojit hranu (Ctrl+J)."
            )
            self.relation_changed.emit(None)
            return
        project = self.host.project
        attachment = self.current_relation[0] == "attachment"
        a, b = (
            (record.source_surface_id, record.target_surface_id)
            if attachment
            else (record.surface_a, record.surface_b)
        )
        other = b if self.host.selected_surface == a else a
        self.receiver.setText(f"Protikus: {title(project, other)}")
        cid = record.connector_id
        self.edit.setText("Upravit chlopeň…" if cid else "Přidat chlopeň…")
        can_tab = record.source_edge_id is not None if attachment else record.mode == "cut"
        self.edit.setEnabled(can_tab)
        self.edit.setToolTip(
            "Plošné lepení bez hrany nevytváří chlopeň."
            if attachment
            else "Chlopeň patří k lepenému řezu; přehyb zůstává souvislým materiálem."
        )
        self.remove.setEnabled(bool(cid))
        self.remove_relation.setEnabled(attachment)
        self.band.setEnabled(attachment and record.kind == "surface_trace" and not cid)
        self.band.setToolTip(
            "Pásek je samostatný materiálový díl pro čárové připojení bez chlopně."
        )
        messages = []
        if attachment:
            data = project.attachment_geometry(record.id)
            messages.extend(data["issues"])
            messages.append(
                "Lepit na vnitřní stranu."
                if record.target_side == "inside"
                else "Lepit na vnější stranu."
            )
        elif record.unresolved:
            messages.append("Zdrojové hrany chybí. Opravte reference nebo odeberte původní spoj.")
        if cid:
            data = project.connector_geometry(cid)
            messages.extend(data.get("issues", []))
            for index, tab in enumerate(data["all_tabs"], 1):
                self.tabs.addItem(
                    f"Záložka {index}" + (" · vypnutá" if not tab["enabled"] else ""), tab["id"]
                )
            related = {project.part_for_surface(a), project.part_for_surface(b)}
            messages.extend(
                issue.message
                for issue in project.validate_layout()
                if issue.severity == "error"
                and issue.code.startswith("FOLDED_")
                and (issue.joint_id == record.id or related.intersection(issue.part_ids))
            )
        self.tabs.setEnabled(self.tabs.count() > 0)
        self.edit_tab.setEnabled(self.tabs.count() > 0 and can_tab)
        messages.append("Digitální kontakt nenahrazuje ověření ohybu a pevnosti výtiskem.")
        self.status.setText("\n".join(messages))
        self.relation_changed.emit(self.current_relation)

    def preflight(self):
        return self.host._commit_pending_input()

    def select_receiver(self):
        if not self.preflight():
            return
        record = self.record()
        if record:
            a, b = (
                (record.source_surface_id, record.target_surface_id)
                if self.current_relation[0] == "attachment"
                else (record.surface_a, record.surface_b)
            )
            self.host.select_surface(b if self.host.selected_surface == a else a)

    def open_editor(self, *, tab_id=None, band=False):
        if not self.preflight():
            return
        record = self.record()
        if record is None:
            return
        dialog = ConnectorEditDialog(
            self.host,
            self.current_relation,
            connector_id=record.connector_id,
            tab_id=tab_id,
            band=band,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = self.host.run(
                lambda: self.host.controller.execute(
                    "Upravit záložku"
                    if tab_id
                    else "Vytvořit lepicí pásek"
                    if band
                    else "Upravit chlopeň",
                    lambda project: dialog.apply(project),
                )
            )
            if band and result in self.host.project.parts:
                self.host.select_surface(self.host.project.parts[result].frame.root_surface_id)
        self.refresh()

    def edit_connector(self):
        self.open_editor()

    def edit_individual(self):
        if self.tabs.currentData():
            self.open_editor(tab_id=self.tabs.currentData())

    def add_band(self):
        self.open_editor(band=True)

    def remove_connector(self):
        if not self.preflight():
            return
        record = self.record()
        if record and record.connector_id:
            cid = record.connector_id
            self.host.run(
                lambda: self.host.controller.execute(
                    "Odebrat chlopeň", lambda p: p.remove_connector(cid)
                )
            )
            self.refresh()

    def remove_attachment(self):
        if not self.preflight():
            return
        if self.current_relation and self.current_relation[0] == "attachment":
            aid = self.current_relation[1]
            self.host.run(
                lambda: self.host.controller.execute(
                    "Odebrat vnitřní připojení", lambda p: p.remove_attachment(aid)
                )
            )
            self.refresh()
