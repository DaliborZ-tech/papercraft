"""Author circular-rim flaps through public commands and detached fresh previews.

Paper CUT/TABS/GUIDES and source-space glue displays are different views of the
same selected slot. Displays never certify material, deformation or assembly.
The host owns undo; accepting a preview stores intent and leaves material STALE
until the author's explicit recompute. No preview proof/cache enters a document.
"""
# ruff: noqa: N802 -- Qt overrides retain framework names.

from __future__ import annotations

import copy
import hashlib
import json
from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import (
    QObject,
    QPointF,
    QRunnable,
    QSignalBlocker,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPolygonF, QTransform, QValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.authoring import ValidationError
from archpapercraft.authoring.commands import atomic
from archpapercraft.authoring.profile_curves import validate_native_path
from archpapercraft.ui.author_material import MaterialDialog
from archpapercraft.ui.author_paper import _path
from archpapercraft.ui.author_sketch import cosmetic


def _state(project):
    return copy.deepcopy(project.to_dict(validate=False))


def _digest(project):
    return hashlib.sha256(
        json.dumps(_state(project), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _title(project, sid):
    surface = project.surfaces[sid]
    return f"{surface.name} · P{project.parts[surface.part_id].number}"


def _message(text):
    if not isinstance(text, str):
        raise ValueError("Výsledek nemá srozumitelnou textovou zprávu.")
    prefix, separator, message = text.partition(": ")
    if separator and prefix.replace("_", "").isalnum() and prefix.isupper():
        return message
    return text


def _validate_packet(packet, request):
    """Validate detached display structure before any successful publication."""
    if packet["request"] != request:
        raise ValueError("Výsledek změnil aktuální autorské zadání.")
    _message(packet["message"])
    if (
        type(packet["can_confirm"]) is not bool
        or type(packet["can_create_authored_intent"]) is not bool
    ):
        raise ValueError("Výsledek nemá jednoznačný stav ověření.")
    ids = packet["slot_ids"]
    if (
        len(ids) != request["pool_count"]
        or len(set(ids)) != len(ids)
        or ids[: len(request["source_slot_ids"])] != request["source_slot_ids"]
    ):
        raise ValueError("Výsledek změnil stálé identity chlopní.")
    certified = packet["status"] == "CERTIFIED_APPROXIMATE"
    if packet["can_confirm"] != certified:
        raise ValueError("Výsledek nemá konzistentní certifikovaný stav.")
    if not certified:
        return
    geometry = packet["geometry"]
    expected = {
        "owner_surface_id": request["owner_id"],
        "receiver_surface_id": request["receiver_id"],
        "rim_side": request["rim_side"],
        "receiver_side": request["receiver_side"],
        "mode": "APPROXIMATE",
        "status": "CERTIFIED_APPROXIMATE",
        "display_is_proof": False,
    }
    if any(geometry.get(key) != value for key, value in expected.items()):
        raise ValueError("Náhled patří jinému vlastníku, příjemci nebo okraji.")
    if [row["id"] for row in geometry["all_tabs"]] != ids:
        raise ValueError("Náhled nepokrývá všechny skutečné sloty.")
    for role in ("CUT", "TABS", "GUIDES"):
        for path in packet["paper_paths"][role]:
            if "commands" in path:
                validate_native_path(path)
            else:
                points = np.asarray(path["points"], dtype=float)
                if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
                    raise ValueError("Materiálový náhled nemá konečné papírové souřadnice.")
    for mesh in (packet["owner_mesh"], packet["receiver_mesh"]):
        points, faces = np.asarray(mesh["vertices"], dtype=float), np.asarray(mesh["triangles"])
        if (
            points.ndim != 2
            or points.shape[1] != 3
            or not np.isfinite(points).all()
            or faces.ndim != 2
            or faces.shape[1] != 3
            or faces.dtype.kind not in "iu"
            or not len(faces)
            or faces.min() < 0
            or faces.max() >= len(points)
        ):
            raise ValueError("Prostorový náhled nemá platnou konečnou zobrazovací síť.")
    for row in geometry["all_tabs"]:
        if row["enabled"]:
            validate_native_path({"commands": row["paper_native_loop"], "closed": True})
            display = row["assembled_display"]
            if display["acceptance_uses_samples"] is not False or display["units"] != "model_mm":
                raise ValueError("Zobrazení nesmí vydávat vzorky za důkaz ani zaměnit jednotky.")
            for field in ("hinge_world", "glue_patch_world"):
                points = np.asarray(display[field], dtype=float)
                if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
                    raise ValueError("Náhled lepicí plochy nemá konečné modelové souřadnice.")


def _spin(value, *, low=0.000001, high=10000, decimals=6, suffix=" mm"):
    field = QDoubleSpinBox()
    field.setDecimals(decimals)
    field.setRange(low, high)
    field.setValue(value)
    field.setSuffix(suffix)
    field.setKeyboardTracking(False)
    return field


@atomic
def _apply_intent(project, request):
    """Apply only source choices. Indices address NEW slots in this one command.

    Existing slots always retain their UUID prefix. A new create/expansion may
    allocate a pool; explicit draft slot numbers then select that fresh pool.
    This is never a nearest-geometry or old-identity remapping operation.
    """
    if request.get("material_profile") is not None:
        project.set_material_profile(**request["material_profile"])
    params = copy.deepcopy(request["parameters"])
    current_count = params["count"]
    pool_count = max(current_count, request["pool_count"])
    params["count"] = pool_count
    cid = request["connector_id"]
    if cid is None:
        cid = project.add_curved_connector(
            request["owner_id"],
            request["rim_side"],
            request["receiver_id"],
            receiver_side=request["receiver_side"],
            **params,
        )
    else:
        old = project.curved_connectors[cid]
        if old.owner_surface_id != request["owner_id"] or old.rim_side != request["rim_side"]:
            raise ValueError("Vlastník nebo kruhový okraj se změnil. Otevřete nový návrh.")
        if old.slot_ids != request["source_slot_ids"]:
            raise ValueError("Identita jednotlivých chlopní se změnila. Otevřete nový návrh.")
        project.update_curved_connector(
            cid,
            receiver_surface_id=request["receiver_id"],
            receiver_side=request["receiver_side"],
            **params,
        )
    record = project.curved_connectors[cid]
    if record.slot_ids[: len(request["source_slot_ids"])] != request["source_slot_ids"]:
        raise ValueError("Zdrojové sloty nelze jednoznačně zachovat.")
    for index, override in request["overrides"].items():
        project.set_curved_tab(cid, record.slot_ids[int(index)], **override)
    if pool_count != current_count:
        project.update_curved_connector(cid, count=current_count)
    return cid


def _preview(project, request):
    """Fresh, public-command preview on a worker-owned project, no private math."""
    cid = _apply_intent(project, request)
    record = project.curved_connectors[cid]
    error = None
    try:
        project.recompute(
            None
            if request.get("material_profile") is not None
            else [project.part_for_surface(record.owner_surface_id)]
        )
    except (ValidationError, ValueError, KeyError, AttributeError) as exc:
        error = str(exc)
    geometry = project.curved_connector_geometry(cid)
    certified = geometry["status"] == "CERTIFIED_APPROXIMATE"
    return {
        "status": geometry["status"],
        "message": error or geometry["message"],
        "can_confirm": certified,
        "can_create_authored_intent": True,
        "request": copy.deepcopy(request),
        "geometry": geometry,
        "slot_ids": list(record.slot_ids),
        "paper_paths": copy.deepcopy(
            project.part_geometry(project.part_for_surface(record.owner_surface_id))["paths"]
        )
        if certified
        else {},
        "owner_mesh": project.world_geometry(record.owner_surface_id),
        "receiver_mesh": project.world_geometry(record.receiver_surface_id),
    }


class _Signals(QObject):
    finished = Signal(int, object, object)


class _Job(QRunnable):
    def __init__(self, token, cls, state, request, callback):
        super().__init__()
        self.token, self.cls, self.state, self.request, self.callback = (
            token,
            cls,
            state,
            request,
            callback,
        )
        self.signals = _Signals()

    def run(self):
        try:
            project = self.cls.from_dict(self.state)
            self.signals.finished.emit(
                self.token, self.callback(project, copy.deepcopy(self.request)), None
            )
        except Exception as exc:
            self.signals.finished.emit(self.token, None, str(exc))


class CurvedPaperPreview(QGraphicsView):
    """Actual supplied paths in the owner's paper frame, never reconstructed tabs."""

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setMinimumSize(250, 185)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAccessibleName("Skutečný rozvin a vybraná chlopeň · milimetry na papíře")
        self.packet = None

    def show_packet(self, packet=None, selected_index=0):
        self.scene().clear()
        self.packet = packet
        if not packet or packet.get("status") != "CERTIFIED_APPROXIMATE":
            return
        transform = QTransform().scale(1, -1)
        for role in ("TABS", "GUIDES", "CUT"):
            for source in packet.get("paper_paths", {}).get(role, []):
                self.scene().addPath(
                    transform.map(_path(source)),
                    cosmetic({"TABS": "#bd7a34", "GUIDES": "#8b9895", "CUT": "#244c40"}[role]),
                )
        rows = packet["geometry"]["all_tabs"]
        if 0 <= selected_index < len(rows) and rows[selected_index]["paper_native_loop"]:
            loop = rows[selected_index]["paper_native_loop"]
            self.scene().addPath(
                transform.map(_path({"commands": loop, "closed": True})), cosmetic("#ef7200", 3)
            )
        bounds = self.scene().itemsBoundingRect()
        if not bounds.isEmpty():
            self.fitInView(bounds.adjusted(-1, -1, 1, 1), Qt.AspectRatioMode.KeepAspectRatio)


class CurvedAssemblyPreview(QWidget):
    """Shared orthographic drawing of source meshes and current glue/hinge paths."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(250, 185)
        self.packet, self.slot = None, 0
        self.setAccessibleName("Plášť, skutečný příjemce a vybraná lepicí plocha · modelové mm")

    def show_packet(self, packet=None, selected_index=0):
        self.packet, self.slot = packet, selected_index
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f4f6f4"))
        if not self.packet or self.packet.get("status") != "CERTIFIED_APPROXIMATE":
            painter.drawText(QPointF(10, 35), "Aktuální prostorové ověření zatím chybí.")
            return
        packet = self.packet
        meshes = [packet["owner_mesh"], packet["receiver_mesh"]]
        arrays = [np.asarray(mesh["vertices"], dtype=float) for mesh in meshes]
        # Display projection only; all acceptance remains in the domain report.
        rotation = np.array([[0.866, -0.5, 0], [0.35, 0.6062, -0.7141], [0.357, 0.6184, 0.7]])
        projected = np.vstack(arrays) @ rotation.T
        center = (projected.max(0) + projected.min(0)) / 2
        extent = np.maximum(np.ptp(projected, axis=0), 1e-9)
        factor = min((self.width() - 24) / extent[0], (self.height() - 45) / extent[1])

        def mapped(points):
            xy = (np.asarray(points) @ rotation.T - center)[:, :2] * [factor, -factor]
            return QPolygonF([QPointF(x + self.width() / 2, y + self.height() / 2) for x, y in xy])

        for mesh, vertices, color in zip(meshes, arrays, ("#97bdb3", "#c3bcd2")):
            painter.setBrush(QColor(color))
            painter.setPen(cosmetic("#657a70", 0.5))
            for triangle in mesh["triangles"]:
                painter.drawPolygon(mapped(vertices[triangle]))
        rows = packet["geometry"]["all_tabs"]
        if self.slot < len(rows) and rows[self.slot].get("assembled_display"):
            display = rows[self.slot]["assembled_display"]
            painter.setBrush(QColor("#efb16d"))
            painter.setPen(cosmetic("#a65f00", 2))
            painter.drawPolygon(mapped(display["glue_patch_world"]))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(mapped(display["hinge_world"]))
        painter.setPen(QColor("#233d32"))
        painter.drawText(QPointF(8, self.height() - 8), "Zobrazení sestavy · není fyzický důkaz")


class CurvedConnectorDialog(QDialog):
    """A reversible authoring draft, with one active and one latest worker job."""

    def __init__(
        self,
        project,
        owner_surface_id,
        *,
        connector_id=None,
        selected_tab=None,
        parent=None,
        preview_function=None,
    ):
        super().__init__(parent)
        self.project, self.owner_id, self.connector_id = project, owner_surface_id, connector_id
        self.callback = preview_function or _preview
        self._token, self._running, self._pending, self._closed = 0, None, None, False
        self._packet = self._accepted = self._request = None
        self._loading = False
        self._active_tab = 0
        self._raw_text = {}
        self.material_override = None
        record = project.curved_connectors.get(connector_id)
        self.source_slot_ids = list(record.slot_ids) if record else []
        self.overrides = {
            str(i): copy.deepcopy(record.tab_overrides[sid])
            for i, sid in enumerate(self.source_slot_ids)
            if record and sid in record.tab_overrides
        }
        self.pool_count = len(self.source_slot_ids)
        self.setWindowTitle("Dělené chlopně kruhového okraje")
        self.resize(860, 780)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        layout.addWidget(QLabel("Vlastník chlopní: " + _title(project, self.owner_id)))
        self.help = QLabel(
            "Vyberte skutečný disk příjemce a jeho kontaktní stranu. Zadejte počet, "
            "šířku nebo mezeru a hloubku. Záložky lze jednotlivě vypnout nebo posunout "
            "jejich vrchol. Spočítejte náhled; po potvrzení přepočítejte celý díl (Ctrl+R)."
        )
        self.help.setWordWrap(True)
        layout.addWidget(self.help)
        self.help_toggle = QToolButton(text="Skrýt tipy", checkable=True, checked=True)
        self.help_toggle.toggled.connect(self.help.setVisible)
        self.help_toggle.toggled.connect(
            lambda on: self.help_toggle.setText("Skrýt tipy" if on else "Zobrazit tipy")
        )
        layout.addWidget(self.help_toggle)
        form = QFormLayout()
        self.rim, self.receiver, self.receiver_side = QComboBox(), QComboBox(), QComboBox()
        owner = project.surfaces[self.owner_id]
        for side, pid, label in zip(
            ("first", "second"), owner.source_profile_ids(), ("První", "Druhý")
        ):
            self.rim.addItem(label + " okraj · " + project.profiles[pid].name, side)
        for sid, surface in project.surfaces.items():
            if surface.kind == "planar" and surface.part_id != owner.part_id:
                self.receiver.addItem(_title(project, sid), sid)
        self.receiver.setPlaceholderText("Nejprve vytvořte skutečný disk příjemce")
        self.receiver.setCurrentIndex(-1)
        self.receiver_side.addItem("Vnitřní strana příjemce", "inside")
        self.receiver_side.addItem("Vnější strana příjemce", "outside")
        self.rim.setEnabled(record is None)
        if record is None:
            occupied = {
                r.rim_side
                for r in project.curved_connectors.values()
                if r.owner_surface_id == self.owner_id
            }
            for index in range(self.rim.count()):
                self.rim.model().item(index).setEnabled(self.rim.itemData(index) not in occupied)
            available = next(
                (i for i in range(self.rim.count()) if self.rim.itemData(i) not in occupied), -1
            )
            self.rim.setCurrentIndex(available)
            self.receiver_side.setCurrentIndex(
                self.receiver_side.findData(
                    "inside" if self.rim.currentData() == "first" else "outside"
                )
            )
        for label, control in (
            ("Okraj pláště", self.rim),
            ("Skutečný příjemce", self.receiver),
            ("Kontaktní strana", self.receiver_side),
        ):
            form.addRow(label, control)
        self.front = QLabel()
        self.front.setWordWrap(True)
        form.addRow("Potisk a papír", self.front)
        self.material_button = QPushButton("Papír pro celý projekt…")
        self.material_button.setAutoDefault(False)
        self.material_button.clicked.connect(self.edit_material)
        form.addRow(self.material_button)
        self.count = QSpinBox()
        self.count.setRange(1, 1000)
        self.count.setValue(12)
        self.count.setKeyboardTracking(False)
        self.width_mode = QComboBox()
        self.width_mode.addItem("Šířka základny chlopně", "width")
        self.width_mode.addItem("Minimální mezera mezi chlopněmi", "gap")
        self.fields = {
            "depth_mm": _spin(9.5),
            "relief_mm": _spin(0.6),
            "nominal_base_mm": _spin(0.24),
            "gap_mm": _spin(0.5, low=0),
            "min_glue_area_mm2": _spin(1, suffix=" mm²"),
            "max_position_mm": _spin(0.01),
            "max_differential_deformation": _spin(1, high=99.9, suffix=" %"),
            "publication_error_budget_mm": _spin(0.000001, decimals=9),
        }
        form.addRow("Počet záložek", self.count)
        form.addRow("Rozdělení okraje", self.width_mode)
        for key, label in (
            ("nominal_base_mm", "Šířka · papírové mm"),
            ("gap_mm", "Mezera · papírové mm"),
            ("depth_mm", "Hloubka · papírové mm"),
            ("relief_mm", "Nelepený pás pro ohyb"),
            ("min_glue_area_mm2", "Nejmenší lepicí plocha"),
        ):
            form.addRow(label, self.fields[key])
        layout.addLayout(form)
        self.advanced_toggle = QToolButton(text="Podrobné digitální meze", checkable=True)
        layout.addWidget(self.advanced_toggle)
        advanced = QWidget()
        advanced_form = QFormLayout(advanced)
        for key, label in (
            ("max_position_mm", "Největší polohová odchylka"),
            ("max_differential_deformation", "Geometrická mez deformace"),
            ("publication_error_budget_mm", "Rezerva výrobního výstupu"),
        ):
            advanced_form.addRow(label, self.fields[key])
        advanced.setVisible(False)
        self.advanced_toggle.toggled.connect(advanced.setVisible)
        layout.addWidget(advanced)
        disclaimer = QLabel(
            "Plášť může mít přesný rozvin; kruhové chlopně jsou omezená APROXIMACE. "
            "Geometrická mez 1 % nedokazuje pružnost, pevnost ani fyzickou sestavitelnost. "
            "Ty ověří až skutečný výtisk v P3."
        )
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)
        self.tabs = QComboBox()
        self.tab_enabled = QCheckBox("Vybranou chlopeň použít")
        self.tip = _spin(0, low=-10000)
        self.tip.setObjectName("curved_tip_offset")
        tab_form = QFormLayout()
        tab_form.addRow("Jednotlivá záložka", self.tabs)
        tab_form.addRow(self.tab_enabled)
        tab_form.addRow("Posun vrcholu · papírové mm", self.tip)
        layout.addLayout(tab_form)
        views = QSplitter()
        self.paper_preview, self.assembly_preview = CurvedPaperPreview(), CurvedAssemblyPreview()
        views.addWidget(self.paper_preview)
        views.addWidget(self.assembly_preview)
        layout.addWidget(
            QLabel(
                "Vlevo skutečné CUT/TABS/GUIDES v papírových mm; vpravo sestava v modelových mm."
            )
        )
        layout.addWidget(views)
        self.compute, self.cancel_compute = (
            QPushButton("Spočítat aktuální náhled (Ctrl+R)"),
            QPushButton("Zrušit výpočet"),
        )
        self.compute.setShortcut("Ctrl+R")
        for button in (self.compute, self.cancel_compute):
            button.setAutoDefault(False)
        self.cancel_compute.setEnabled(False)
        row = QHBoxLayout()
        row.addWidget(self.compute)
        row.addWidget(self.cancel_compute)
        outer.addLayout(row)
        self.feedback = QLabel(
            "Vyberte příjemce a zkontrolujte kontaktní stranu. Potom spočítejte náhled."
        )
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(self.feedback)
        self.retain = QCheckBox(
            "Uchovat pouze autorský návrh; ověření a export zůstanou blokované."
        )
        self.retain.hide()
        outer.addWidget(self.retain)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.apply_button.setText("Uložit návrh chlopní")
        self.apply_button.setAutoDefault(False)
        self.apply_button.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        if record:
            self.rim.setCurrentIndex(self.rim.findData(record.rim_side))
            self.receiver.setCurrentIndex(self.receiver.findData(record.receiver_surface_id))
            self.receiver_side.setCurrentIndex(self.receiver_side.findData(record.receiver_side))
            self.count.setValue(record.parameters["count"])
            for key, field in self.fields.items():
                value = record.parameters[key]
                if value is not None:
                    field.setValue(value * 100 if key == "max_differential_deformation" else value)
            self.width_mode.setCurrentIndex(
                0 if record.parameters["nominal_base_mm"] is not None else 1
            )
        for combo in (self.rim, self.receiver, self.receiver_side, self.width_mode):
            combo.currentIndexChanged.connect(self.invalidate)
        self.count.valueChanged.connect(self._count_changed)
        for field in [self.count, self.tip, *self.fields.values()]:
            field.lineEdit().textEdited.connect(lambda text, field=field: self._typed(field, text))
        for field in self.fields.values():
            field.valueChanged.connect(self.invalidate)
        self.tabs.currentIndexChanged.connect(self._choose_tab)
        self.tab_enabled.toggled.connect(self._edit_tab)
        self.tip.valueChanged.connect(self._edit_tab)
        self.compute.clicked.connect(self.request_preview)
        self.cancel_compute.clicked.connect(self.cancel_preview)
        self.retain.toggled.connect(self._update_accept)
        self._count_changed()
        if selected_tab in self.source_slot_ids:
            self.tabs.setCurrentIndex(self.source_slot_ids.index(selected_tab))
        self._refresh_labels()
        self._revision = project.revision
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._source_changed)
        self.timer.start()

    def _refresh_labels(self):
        receiver = self.project.surfaces.get(self.receiver.currentData())
        owner_part = self.project.parts[self.project.part_for_surface(self.owner_id)]
        contact = self.receiver_side.currentData()
        receiver_front = self.project.parts[receiver.part_id].front_side if receiver else None
        material = self.material_override or self.project.material_profile
        contact_label = (
            "kontakt na potištěné straně"
            if receiver_front == contact
            else "kontakt na nepotištěné straně"
        )
        printed = "vnější" if owner_part.front_side == "outside" else "vnitřní"
        thickness = material["thickness_mm"] if material["thickness_mm"] is not None else "neznámá"
        self.front.setText(
            f"Plášť: potisk {printed}. Příjemce: "
            f"{contact_label}. "
            f"Tloušťka {thickness} mm, vůle {material['clearance_mm']} mm. "
            "Změna papíru platí pro celý projekt; uloží se společně s tímto návrhem."
        )
        self.fields["nominal_base_mm"].setEnabled(self.width_mode.currentData() == "width")
        self.fields["gap_mm"].setEnabled(self.width_mode.currentData() == "gap")

    def edit_material(self):
        if not self.commit_fields():
            return
        source = SimpleNamespace(
            material_profile=copy.deepcopy(self.material_override or self.project.material_profile)
        )
        dialog = MaterialDialog(source, self)
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).setText(
            "Zahrnout papír do tohoto návrhu"
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.material_override = copy.deepcopy(dialog.result_profile)
            self.invalidate()

    def _typed(self, field, text):
        self._raw_text[field] = text
        self.invalidate()

    def commit_fields(self):
        for field in [self.count, self.tip, *self.fields.values()]:
            if not field.isEnabled():
                continue
            raw = self._raw_text.get(field)
            if (
                raw is not None and field.validate(raw, len(raw))[0] != QValidator.State.Acceptable
            ) or not field.hasAcceptableInput():
                if raw is not None:
                    field.lineEdit().setText(raw)
                field.setFocus()
                self.feedback.setText("Opravte rozepsané číslo; návrh ani projekt se nezměnily.")
                return False
        for field in [self.count, self.tip, *self.fields.values()]:
            if field.isEnabled():
                field.interpretText()
                self._raw_text.pop(field, None)
        return True

    def _count_changed(self, *_args):
        self.pool_count = max(self.pool_count, self.count.value())
        selected = self.tabs.currentIndex()
        with QSignalBlocker(self.tabs):
            self.tabs.clear()
            for index in range(self.pool_count):
                self.tabs.addItem(
                    f"Chlopeň {index + 1}"
                    + (" · mimo aktuální počet" if index >= self.count.value() else ""),
                    index,
                )
            self.tabs.setCurrentIndex(max(0, min(selected, self.pool_count - 1)))
        self._choose_tab()
        self.invalidate()

    def _choose_tab(self, *_args):
        raw = self._raw_text.get(self.tip)
        if raw is not None:
            if self.tip.validate(raw, len(raw))[0] != QValidator.State.Acceptable:
                with QSignalBlocker(self.tabs):
                    self.tabs.setCurrentIndex(self._active_tab)
                self.feedback.setText("Nejprve opravte rozepsaný posun vrcholu vybrané chlopně.")
                return
            self._loading = True
            self.tip.interpretText()
            self._loading = False
            previous = self.overrides.get(str(self._active_tab), {})
            self.overrides[str(self._active_tab)] = dict(previous, tip_offset_mm=self.tip.value())
            self._raw_text.pop(self.tip, None)
        self._loading = True
        index = self.tabs.currentIndex()
        self._active_tab = index
        override = self.overrides.get(str(index), {})
        self.tab_enabled.setChecked(override.get("enabled", True))
        self.tip.setValue(override.get("tip_offset_mm", 0))
        self._loading = False
        self._draw()

    def _edit_tab(self, *_args):
        if self._loading:
            return
        self.overrides[str(self.tabs.currentIndex())] = {
            "enabled": self.tab_enabled.isChecked(),
            "tip_offset_mm": self.tip.value(),
        }
        self.invalidate()

    def invalidate(self, *_args):
        if self._loading:
            return
        self._token += 1
        self._packet = self._accepted = self._pending = None
        self.retain.setChecked(False)
        self.retain.hide()
        self.apply_button.setEnabled(False)
        self.paper_preview.show_packet()
        self.assembly_preview.show_packet()
        self.feedback.setText("Návrh se změnil. Spočítejte nový náhled před jeho uložením.")
        self._refresh_labels()

    def parameters(self):
        values = {key: field.value() for key, field in self.fields.items()}
        values["count"] = self.count.value()
        values["max_differential_deformation"] /= 100
        values["gap_mm" if self.width_mode.currentData() == "width" else "nominal_base_mm"] = None
        return {
            "connector_id": self.connector_id,
            "owner_id": self.owner_id,
            "rim_side": self.rim.currentData(),
            "receiver_id": self.receiver.currentData(),
            "receiver_side": self.receiver_side.currentData(),
            "parameters": values,
            "source_slot_ids": list(self.source_slot_ids),
            "pool_count": self.pool_count,
            "overrides": copy.deepcopy(self.overrides),
            "material_profile": copy.deepcopy(self.material_override),
        }

    def request_preview(self):
        if self._closed or not self.commit_fields():
            return False
        request = self.parameters()
        if request["receiver_id"] is None:
            self.feedback.setText("Nejprve vytvořte a vyberte skutečný samostatný disk příjemce.")
            return False
        self.invalidate()
        request = self.parameters()
        state = _state(self.project)
        self._request = {
            "token": self._token,
            "parameters": request,
            "fingerprint": _digest(self.project),
        }
        pending = (self._token, state, request)
        self.feedback.setText(
            "Počítám celý materiál a prostor ohybu na odděleném návrhu. Můžete výpočet zrušit."
        )
        self.cancel_compute.setEnabled(True)
        if self._running is None:
            self._start(pending)
        else:
            self._pending = pending
        return True

    def _start(self, pending):
        token, state, request = pending
        self._running = _Job(token, type(self.project), state, request, self.callback)
        self._running.signals.finished.connect(self._finished)
        QThreadPool.globalInstance().start(self._running)

    def _finished(self, token, result, error):
        self._running = None
        if not self._closed and token == self._token:
            try:
                if _digest(self.project) != self._request["fingerprint"]:
                    raise ValueError(
                        "Zdroj se změnil. Zkontrolujte příjemce a znovu spočítejte náhled."
                    )
                if error:
                    raise ValueError(error)
                _validate_packet(result, self._request["parameters"])
                certified = (
                    result["status"] == "CERTIFIED_APPROXIMATE" and result["can_confirm"] is True
                )
                if certified and result["geometry"]["status"] != "CERTIFIED_APPROXIMATE":
                    raise ValueError("Zobrazení nemá aktuální ověřený materiál.")
                text = (
                    "APROXIMACE · aktuální digitální prostor a materiál jsou doložené. "
                    if certified
                    else "Spoj není digitálně doložený. "
                ) + _message(result["message"])
                text += " Po uložení přepočítejte celý díl (Ctrl+R). Fyzický výtisk zůstává P3."
                candidate = copy.deepcopy(result)
                self._packet = candidate
                self.feedback.setText(text)
                self.retain.setVisible(
                    not certified and result.get("can_create_authored_intent") is True
                )
                self._draw()
                self._update_accept()
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
                self._packet = None
                self.feedback.setText(
                    "Náhled nelze použít: "
                    + str(exc)
                    + " Upravte rozměry, kontaktní stranu, papír nebo příjemce."
                )
                self.apply_button.setEnabled(False)
        pending, self._pending = self._pending, None
        if not self._closed and pending is not None and pending[0] == self._token:
            self._start(pending)
        else:
            self.cancel_compute.setEnabled(False)

    def _draw(self):
        self.paper_preview.show_packet(self._packet, self.tabs.currentIndex())
        self.assembly_preview.show_packet(self._packet, self.tabs.currentIndex())

    def _update_accept(self, *_args):
        self.apply_button.setEnabled(
            self._packet is not None
            and (
                (
                    self._packet["can_confirm"] is True
                    and self._packet["status"] == "CERTIFIED_APPROXIMATE"
                )
                or (
                    self._packet.get("can_create_authored_intent") is True
                    and self.retain.isChecked()
                )
            )
        )

    def _source_changed(self):
        if self.project.revision != self._revision:
            self._revision = self.project.revision
            self.invalidate()
            self.feedback.setText(
                "Projekt se změnil. Zkontrolujte aktuální zdroje a spočítejte nový náhled."
            )

    def cancel_preview(self):
        self.invalidate()
        self.cancel_compute.setEnabled(False)
        self.feedback.setText(
            "Výpočet je zrušen; opožděný výsledek se nepoužije. Projekt zůstal zachovaný."
        )

    def accept(self):
        if not self.commit_fields() or not self.apply_button.isEnabled():
            return
        if (
            self.parameters() != self._request["parameters"]
            or _digest(self.project) != self._request["fingerprint"]
        ):
            self.invalidate()
            self.feedback.setText("Návrh nebo zdroj se změnil. Spočítejte aktuální náhled.")
            return
        self._accepted = copy.deepcopy(self._request)
        super().accept()

    def apply(self, project):
        if self._accepted is None or _digest(project) != self._accepted["fingerprint"]:
            raise ValueError("Nejprve potvrďte aktuální nezměněný návrh kruhových chlopní.")
        return _apply_intent(project, self._accepted["parameters"])

    def done(self, result):
        self._closed = True
        self._pending = None
        self._token += 1
        self.timer.stop()
        if result != QDialog.DialogCode.Accepted:
            self._accepted = None
        super().done(result)


class CurvedConnectorPanel(QWidget):
    """Stable live slot selection; context follows the selected set's owner."""

    def __init__(self, host):
        super().__init__(host)
        self.host, self.current_id, self.packet = host, None, None
        self._loading = False
        layout = QVBoxLayout(self)
        self.create = QPushButton("Dělené chlopně kruhového okraje…")
        self.create.clicked.connect(lambda: self.open_editor())
        layout.addWidget(self.create)
        self.sets, self.tabs = QComboBox(), QComboBox()
        self.sets.setObjectName("curved_connector_choice")
        self.tabs.setObjectName("curved_tab_choice")
        self.sets.currentIndexChanged.connect(self.choose_set)
        self.tabs.currentIndexChanged.connect(self.show_slot)
        layout.addWidget(self.sets)
        layout.addWidget(self.tabs)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.edit = QPushButton("Upravit sadu / vrchol vybrané chlopně…")
        self.edit.clicked.connect(lambda: self.open_editor(self.current_id))
        self.toggle = QPushButton("Vypnout vybranou chlopeň")
        self.toggle.clicked.connect(self.toggle_tab)
        self.remove = QPushButton("Odebrat sadu chlopní")
        self.remove.clicked.connect(self.remove_set)
        for widget in (self.edit, self.toggle, self.remove):
            layout.addWidget(widget)
        self.set_enabled = QCheckBox("Používat celou sadu chlopní")
        self.set_enabled.toggled.connect(self.toggle_set)
        layout.addWidget(self.set_enabled)

    def refresh(self):
        project, sid = self.host.project, self.host.selected_surface
        self._loading = True
        self.packet = None
        previous = self.tabs.currentData()
        with QSignalBlocker(self.sets), QSignalBlocker(self.tabs):
            self.sets.clear()
            self.sets.addItem("Vyberte sadu kruhových chlopní", None)
            for cid, record in project.curved_connectors.items():
                self.sets.addItem(
                    _title(project, record.owner_surface_id) + " · " + record.name, cid
                )
            if (
                self.current_id not in project.curved_connectors
                or project.curved_connectors[self.current_id].owner_surface_id != sid
            ):
                self.current_id = None
            self.sets.setCurrentIndex(max(0, self.sets.findData(self.current_id)))
            self.tabs.clear()
            if self.current_id:
                self.packet = project.curved_connector_geometry(self.current_id)
                for row in self.packet["all_tabs"]:
                    self.tabs.addItem(
                        f"Chlopeň {row['index'] + 1}"
                        + (" · vypnutá" if not row["enabled"] else "")
                        + (" · mimo počet" if not row["in_current_count"] else ""),
                        row["id"],
                    )
                self.tabs.setCurrentIndex(max(0, self.tabs.findData(previous)))
        surface = project.surfaces.get(sid)
        eligible = False
        # Recognition is source-derived in the public status, not a mesh fit.
        if surface and surface.kind == "ruled_loft":
            report = project.loft_status(sid)
            eligible = bool(report.get("representation", {}).get("circular_shell"))
            eligible = (
                eligible
                and len(
                    {
                        r.rim_side
                        for r in project.curved_connectors.values()
                        if r.owner_surface_id == sid
                    }
                )
                < 2
            )
        self.create.setEnabled(eligible)
        self.host.actions["curved_connector"].setEnabled(eligible)
        self.create.setToolTip(
            "Vyberte plášť ze dvou vlastních kruhových profilů."
            if not eligible
            else "Vytvořit sadu na vybraném plášti"
        )
        for widget in (self.edit, self.toggle, self.remove, self.tabs, self.set_enabled):
            widget.setEnabled(self.current_id is not None)
        self.set_enabled.setChecked(
            project.curved_connectors[self.current_id].enabled if self.current_id else False
        )
        status_title = (
            {
                "CERTIFIED_APPROXIMATE": "Digitálně doložená APROXIMACE",
                "STALE": "Neaktuální · přepočítat",
                "UNRESOLVED": "Nedoložený spoj",
                "NOT_APPLICABLE": "Vypnutá sada",
            }.get(self.packet["status"], "Vyžaduje kontrolu")
            if self.packet
            else ""
        )
        self.status.setText(
            (
                status_title
                + " · "
                + _message(self.packet["message"])
                + " Fyzický výtisk zůstává neověřený."
            )
            if self.packet
            else "Vyberte kruhový plášť. Disk příjemce vytvořte samostatně z vlastního obrysu."
        )
        self._loading = False
        self.show_slot()

    def choose_set(self, *_args):
        if self._loading or self.host._updating:
            return
        cid = self.sets.currentData()
        if not self.host._commit_pending_input():
            return
        self.current_id = cid
        if cid:
            owner = self.host.project.curved_connectors[cid].owner_surface_id
            self.host.selected_edge = self.host.selected_vertex = self.host.current_joint = None
            self.host.select_surface(owner)
        self.refresh()

    def show_slot(self, *_args):
        if self._loading:
            return
        self.host.viewport.curved_tab_id = self.tabs.currentData()
        relation = ("curved", self.current_id) if self.current_id else None
        if relation is not None or (
            self.host.viewport.relation and self.host.viewport.relation[0] == "curved"
        ):
            self.host.show_connector_relation(relation)
        if self.packet:
            row = next(
                (r for r in self.packet["all_tabs"] if r["id"] == self.tabs.currentData()), None
            )
            self.toggle.setText(
                "Vypnout vybranou chlopeň" if row and row["enabled"] else "Zapnout vybranou chlopeň"
            )
            loop = (
                row["paper_native_loop"]
                if row and self.packet["status"] == "CERTIFIED_APPROXIMATE"
                else None
            )
            self.host.paper.select_curved_tab(self.packet["owner_part_id"], loop)
        else:
            self.host.paper.select_curved_tab()

    def open_editor(self, cid=None):
        if not self.host._commit_pending_input():
            return
        owner = (
            self.host.project.curved_connectors[cid].owner_surface_id
            if cid
            else self.host.selected_surface
        )
        if owner not in self.host.project.surfaces:
            return
        dialog = CurvedConnectorDialog(
            self.host.project,
            owner,
            connector_id=cid,
            selected_tab=self.tabs.currentData(),
            parent=self.host,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = self.host.run(
                lambda: self.host.controller.execute("Upravit kruhové chlopně", dialog.apply)
            )
            if result:
                self.current_id = result
                self.host.select_surface(owner)
                self.refresh()

    def toggle_tab(self):
        if not self.current_id or not self.host._commit_pending_input():
            return
        sid, cid = self.tabs.currentData(), self.current_id
        record = self.host.project.curved_connectors[cid]
        enabled = record.tab_overrides.get(sid, {}).get("enabled", True)
        self.host.run(
            lambda: self.host.controller.execute(
                "Zapnout/vypnout kruhovou chlopeň",
                lambda p: p.set_curved_tab(cid, sid, enabled=not enabled),
            )
        )

    def toggle_set(self, enabled):
        if self._loading or self.host._updating or not self.current_id:
            return
        if self.host._commit_pending_input():
            cid = self.current_id
            self.host.run(
                lambda: self.host.controller.execute(
                    "Zapnout/vypnout sadu kruhových chlopní",
                    lambda p: p.update_curved_connector(cid, enabled=enabled),
                )
            )

    def remove_set(self):
        if self.current_id and self.host._commit_pending_input():
            cid = self.current_id
            self.host.run(
                lambda: self.host.controller.execute(
                    "Odebrat kruhové chlopně", lambda p: p.remove_curved_connector(cid)
                )
            )
