"""Draw an actual receiving line/region and preview construction before committing."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainterPath
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_sketch import AuthorSketch, cosmetic
from archpapercraft.ui.author_viewport import AuthorViewport


def number(low=-1e9, high=1e9, decimals=6):
    field = QDoubleSpinBox()
    field.setRange(low, high)
    field.setDecimals(decimals)
    field.setKeyboardTracking(False)
    return field


class ReceivingSketch(AuthorSketch):
    """Reuse the author sketch vocabulary; the result is an attachment, never a cut."""

    trace_changed = Signal(list)
    region_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.purpose = "trace"
        self.trace, self.region = [], []
        self.open_profile_finished.connect(self._trace_ready)
        self.outline_finished.connect(self._region_ready)

    def start_receiving(self, purpose):
        self.purpose = purpose
        self.start_outline()
        self.status.emit(
            "Klikněte na začátek a směr čáry. Enter dokončí, Esc zruší."
            if purpose == "trace" else
            "Nakreslete lepicí oblast; nebude se vystřihovat. Enter dokončí, Esc zruší."
        )

    def focus_surface(self):
        if self.scene().items():
            rect = self.scene().itemsBoundingRect()
            margin = max(rect.width(), rect.height()) * 0.08
            if margin > 0:
                self.fitInView(
                    rect.adjusted(-margin, -margin, margin, margin),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )

    def finish_outline(self):
        if self.purpose == "trace":
            if len(self.points) != 2:
                self.status.emit("Připojovací čáru určete právě dvěma body; Enter dokončí.")
                return
            self.finish_open_profile()
        else:
            super().finish_outline()

    def finish_open_profile(self):
        if self.purpose == "region":
            self.finish_outline()
        elif len(self.points) != 2:
            self.status.emit(
                "Připojovací čáru určete právě dvěma body; ostatní lze vrátit Backspace."
            )
        else:
            super().finish_open_profile()

    def _trace_ready(self, points):
        if self.purpose == "trace" and len(points) == 2:
            self.trace = points
            self.trace_changed.emit(points)
            self.redraw()

    def _region_ready(self, points, _hole):
        if self.purpose == "region":
            self.region = points
            self.region_changed.emit(points)
            self.redraw()

    def redraw(self):
        super().redraw()
        for points, closed, color in [
            (getattr(self, "trace", []), False, "#bd5d00"),
            (getattr(self, "region", []), True, "#975ca8"),
        ]:
            if points:
                path = QPainterPath()
                path.moveTo(points[0][0], -points[0][1])
                for x, y in points[1:]:
                    path.lineTo(x, -y)
                if closed:
                    path.closeSubpath()
                item = self.scene().addPath(path, cosmetic(color, 2, Qt.PenStyle.DashLine))
                if closed:
                    item.setBrush(QColor(151, 92, 168, 35))
                item.setZValue(8)


class AttachmentDialog(QDialog):
    def __init__(self, project, source, *, unit="m", unit_factor=1000, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Připojit hranu dovnitř plochy")
        self.resize(1040, 820)
        self.project, self.source = project, source
        self.unit_factor = unit_factor
        self.result_spec = None
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Vyberte přijímající plochu. Klikněte na začátek a směr připojovací čáry "
            "a potvrďte Enter; její délka odpovídá vybrané hraně automaticky. "
            "Čára se nebude vystřihovat a vnější přesah zůstane. "
            "Náhled ukáže sestavenou polohu před potvrzením."
        )
        intro.setWordWrap(True)
        if parent is not None and hasattr(parent, "tips_action"):
            intro.setVisible(parent.tips_action.isChecked())
        layout.addWidget(intro)
        form = QFormLayout()
        layout.addLayout(form)
        self.receiver = QComboBox()
        for sid, surface in project.surfaces.items():
            if sid != source[0]:
                self.receiver.addItem(surface.name, sid)
        form.addRow("Přijímající plocha", self.receiver)
        self.mode = QComboBox()
        self.mode.addItem("Umístit na nakreslenou čáru", "place")
        self.mode.addItem("Připojit v současné prostorové poloze", "contact")
        form.addRow("Postup", self.mode)
        self.angle = number(-180, 180, 3)
        self.angle.setSuffix("°")
        self.angle.setValue(90)
        form.addRow("Úhel mezi plochami", self.angle)
        self.side = QComboBox()
        self.side.addItem("Vnitřní strana plochy", "inside")
        self.side.addItem("Vnější strana plochy", "outside")
        form.addRow("Strana příjemce", self.side)
        self.direction = QComboBox()
        self.direction.addItem("První strana připojovací čáry", 1)
        self.direction.addItem("Opačná strana připojovací čáry", -1)
        form.addRow("Kam se přehne chlopeň", self.direction)
        self.start_fraction, self.end_fraction = number(0, 100, 4), number(0, 100, 4)
        self.end_fraction.setValue(100)
        row = QHBoxLayout()
        self.draw_line = QPushButton("Nakreslit připojovací čáru")
        self.draw_region = QPushButton("Nakreslit lepicí oblast")
        self.use_region = QCheckBox("Omezit lepení nakreslenou oblastí")
        row.addWidget(self.draw_line)
        row.addWidget(self.draw_region)
        row.addWidget(self.use_region)
        layout.addLayout(row)
        splitter = QSplitter()
        self.sketch = ReceivingSketch()
        self.sketch.display_unit, self.sketch.display_factor = unit, unit_factor
        self.sketch.grid_mm = 0.1 * unit_factor
        self.viewport = AuthorViewport()
        splitter.addWidget(self.sketch)
        splitter.addWidget(self.viewport)
        layout.addWidget(splitter, 1)
        precise = QGroupBox(f"Přesný rozsah hrany a poloha čáry na protikusu ({unit})")
        precise.setCheckable(True)
        precise.setChecked(False)
        box_layout = QVBoxLayout(precise)
        self.coordinates = QWidget()
        precise_form = QFormLayout(self.coordinates)
        self.fields = [number() for _ in range(4)]
        for label, field in [
            ("Od místa na zdrojové hraně (%)", self.start_fraction),
            ("Do místa na zdrojové hraně (%)", self.end_fraction),
        ]:
            precise_form.addRow(label, field)
            field.editingFinished.connect(self.interval_changed)
        for label, field in zip(
            ("Začátek vodorovně", "Začátek svisle", "Konec vodorovně", "Konec svisle"),
            self.fields,
        ):
            precise_form.addRow(label, field)
            field.editingFinished.connect(self.numeric_trace)
        self.coordinates.setVisible(False)
        precise.toggled.connect(self.coordinates.setVisible)
        box_layout.addWidget(self.coordinates)
        layout.addWidget(precise)
        self.feedback = QLabel("Nakreslete čáru nebo zvolte připojení již přiléhající hrany.")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Použít připojení")
        self.buttons.accepted.connect(self.confirm)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.receiver.currentIndexChanged.connect(self.change_receiver)
        self.mode.currentIndexChanged.connect(self.update_preview)
        self.side.currentIndexChanged.connect(self.update_preview)
        self.direction.currentIndexChanged.connect(self.update_preview)
        self.angle.editingFinished.connect(self.update_preview)
        self.use_region.toggled.connect(self.update_preview)
        self.draw_line.clicked.connect(lambda: self.sketch.start_receiving("trace"))
        self.draw_region.clicked.connect(lambda: self.sketch.start_receiving("region"))
        self.sketch.trace_changed.connect(self.trace_ready)
        self.sketch.region_changed.connect(lambda _: self.use_region.setChecked(True))
        self.sketch.region_changed.connect(self.update_preview)
        self.sketch.status.connect(self.feedback.setText)
        self.sketch.draft_changed.connect(self.update_preview)
        self.change_receiver()

    def change_receiver(self):
        self.sketch.cancel_outline()
        self.sketch.trace, self.sketch.region = [], []
        self.use_region.setChecked(False)
        self.sketch.set_project(self.project, self.receiver.currentData())
        self.sketch.focus_surface()
        self.update_preview()

    def trace_ready(self, points):
        # Drawing sets origin and direction; a rigid join retains the source's length.
        # Requiring two mouse clicks to encode an exact metric length is unusable.
        edge = next(
            edge for edge in self.project.world_geometry(self.source[0])["boundary"]
            if edge["id"] == self.source[1]
        )
        source_length = math.dist(edge["start"], edge["end"]) * (
            self.end_fraction.value() - self.start_fraction.value()
        ) / 100
        direction_length = math.dist(*points)
        if direction_length == 0:
            return
        points = [points[0], [
            points[0][i] + (points[1][i] - points[0][i]) * source_length / direction_length
            for i in range(2)
        ]]
        self.sketch.trace = points
        self.sketch.redraw()
        for field, value in zip(self.fields, [*points[0], *points[1]]):
            field.setValue(value / self.unit_factor)
        self.update_preview()

    def interval_changed(self):
        if len(self.sketch.trace) == 2 and self.mode.currentData() == "place":
            self.trace_ready(self.sketch.trace)
        else:
            self.update_preview()

    def numeric_trace(self):
        values = [field.value() * self.unit_factor for field in self.fields]
        self.sketch.trace = [values[:2], values[2:]]
        self.sketch.redraw()
        self.update_preview()

    def specification(self):
        return {
            "source": self.source,
            "target": self.receiver.currentData(),
            "mode": self.mode.currentData(),
            "trace": self.sketch.trace,
            "angle_deg": self.angle.value(),
            "target_side": self.side.currentData(),
            "glue_direction": self.direction.currentData(),
            "region": self.sketch.region if self.use_region.isChecked() else None,
            "interval": [self.start_fraction.value() / 100, self.end_fraction.value() / 100],
        }

    @staticmethod
    def apply(project, spec):
        options = {key: spec[key] for key in ("target_side", "glue_direction")}
        options["interval"] = spec.get("interval", [0, 1])
        if spec["mode"] == "contact":
            aid = project.attach_edge_to_surface(*spec["source"], spec["target"], **options)
        else:
            aid = project.place_and_attach_edge(
                *spec["source"], spec["target"], *spec["trace"],
                angle_deg=spec["angle_deg"], **options,
            )
        if spec["region"]:
            project.update_attachment(aid, target_region_uv=spec["region"])
        return aid

    def update_preview(self, *_):
        placing = self.mode.currentData() == "place"
        self.draw_line.setEnabled(placing)
        self.angle.setEnabled(placing)
        for field in self.fields:
            field.setEnabled(placing)
        try:
            if not self.receiver.currentData():
                raise ValueError("Nejprve vytvořte další vlastní plochu jako příjemce.")
            if self.sketch.drawing and self.sketch.points:
                raise ValueError("Dokončete připojovací čáru nebo oblast klávesou Enter.")
            if placing and len(self.sketch.trace) != 2:
                raise ValueError("Nakreslete dva body čáry uvnitř přijímající plochy.")
            if self.use_region.isChecked() and len(self.sketch.region) < 3:
                raise ValueError("Lepicí oblast potřebuje vlastní uzavřený obrys.")
            clone = AuthorProject.from_dict(self.project.to_dict())
            aid = self.apply(clone, self.specification())
            geometry = clone.attachment_geometry(aid)
            if not geometry["valid"]:
                raise ValueError("; ".join(geometry["issues"]))
            if not placing and geometry.get("target_uv"):
                self.sketch.trace = geometry["target_uv"]
                self.sketch.redraw()
            self.viewport.set_project(clone, frame=True)
            self.viewport.select([*self.source[:1], self.receiver.currentData()])
            self.viewport.select_relation(("attachment", aid))
            self.feedback.setText(
                "Připojení odpovídá skutečnému materiálu. Zkontrolujte polohu a stranu "
                "v náhledu. Chlopeň nebo pásek vytvoříte následně; zrušení nic nezmění."
            )
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except Exception as exc:
            self.viewport.set_project(self.project)
            self.viewport.select([self.source[0], self.receiver.currentData()])
            self.feedback.setText(str(exc))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def confirm(self):
        # Apply pending numeric fields before validating the state to be committed (C-05).
        for field in [self.angle, self.start_fraction, self.end_fraction, *self.fields]:
            if field.hasFocus() or field.lineEdit().hasFocus():
                if not field.hasAcceptableInput():
                    self.feedback.setText("Opravte neúplné číslo před potvrzením.")
                    return
                field.interpretText()
                field.editingFinished.emit()
        self.update_preview()
        if self.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            self.result_spec = self.specification()
            self.accept()


class GlueRegionDialog(QDialog):
    """Author two real contacting patches without inventing boundary pairs."""

    def __init__(self, project, source, *, unit="m", unit_factor=1000, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Přilepit plochu lepicí oblastí")
        self.resize(1060, 880)
        self.project, self.source, self.result_spec = project, source, None
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Plochy musí již přiléhat v sestaveném modelu. Na protikusu nakreslete "
            "oblast pro lepidlo, Enter dokončí. Původní obrysy ani otvory se nezmění. "
            "Volitelně omezte lepenou část také na zdrojové ploše."
        )
        intro.setWordWrap(True)
        if parent is not None and hasattr(parent, "tips_action"):
            intro.setVisible(parent.tips_action.isChecked())
        layout.addWidget(intro)
        form = QFormLayout()
        self.receiver = QComboBox()
        for sid, surface in project.surfaces.items():
            if sid != source:
                self.receiver.addItem(surface.name, sid)
        form.addRow("Přijímající plocha", self.receiver)
        self.side = QComboBox()
        self.side.addItem("Vnitřní strana plochy", "inside")
        self.side.addItem("Vnější strana plochy", "outside")
        form.addRow("Strana příjemce", self.side)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.draw_target = QPushButton("Nakreslit lepicí oblast na protikusu")
        self.draw_source = QPushButton("Omezit lepenou část zdrojové plochy")
        self.use_source = QCheckBox("Lepit pouze nakreslenou část zdroje")
        for widget in [self.draw_target, self.draw_source, self.use_source]:
            row.addWidget(widget)
        layout.addLayout(row)
        sketches = QSplitter()
        self.source_sketch, self.target_sketch = ReceivingSketch(), ReceivingSketch()
        for label, sketch in [
            (f"Zdroj: {project.surfaces[source].name} ({unit})", self.source_sketch),
            (f"Příjemce ({unit})", self.target_sketch),
        ]:
            box = QWidget()
            content = QVBoxLayout(box)
            content.addWidget(QLabel(label))
            content.addWidget(sketch)
            sketch.display_unit, sketch.display_factor = unit, unit_factor
            sketch.grid_mm = 0.1 * unit_factor
            sketches.addWidget(box)
        layout.addWidget(sketches, 2)
        self.viewport = AuthorViewport()
        layout.addWidget(self.viewport, 1)
        self.feedback = QLabel("Nakreslete oblast na přijímající ploše.")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Použít lepicí oblast")
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.confirm)
        self.buttons.rejected.connect(self.reject)
        self.receiver.currentIndexChanged.connect(self.change_receiver)
        self.side.currentIndexChanged.connect(self.update_preview)
        self.use_source.toggled.connect(self.update_preview)
        self.draw_target.clicked.connect(lambda: self.target_sketch.start_receiving("region"))
        self.draw_source.clicked.connect(lambda: self.source_sketch.start_receiving("region"))
        self.source_sketch.region_changed.connect(lambda _: self.use_source.setChecked(True))
        for sketch in [self.source_sketch, self.target_sketch]:
            sketch.region_changed.connect(self.update_preview)
            sketch.draft_changed.connect(self.update_preview)
            sketch.status.connect(self.feedback.setText)
        self.source_sketch.set_project(project, source)
        self.change_receiver()

    def change_receiver(self):
        self.target_sketch.cancel_outline()
        self.target_sketch.region = []
        self.target_sketch.set_project(self.project, self.receiver.currentData())
        self.target_sketch.focus_surface()
        self.source_sketch.focus_surface()
        self.update_preview()

    def specification(self):
        return {
            "source": self.source,
            "target": self.receiver.currentData(),
            "target_region": self.target_sketch.region,
            "source_region": self.source_sketch.region if self.use_source.isChecked() else None,
            "side": self.side.currentData(),
        }

    @staticmethod
    def apply(project, spec):
        return project.set_glue_region(
            spec["source"], spec["target"], spec["target_region"],
            source_outline_uv=spec["source_region"], target_side=spec["side"],
        )

    def update_preview(self, *_):
        try:
            if not self.receiver.currentData():
                raise ValueError("Nejprve vytvořte další plochu jako příjemce.")
            if any(s.drawing and s.points for s in [self.source_sketch, self.target_sketch]):
                raise ValueError("Dokončete rozpracovanou oblast klávesou Enter.")
            if len(self.target_sketch.region) < 3:
                raise ValueError("Nakreslete lepicí oblast na protikusu.")
            if self.use_source.isChecked() and len(self.source_sketch.region) < 3:
                raise ValueError("Nakreslete lepenou část zdrojové plochy.")
            clone = AuthorProject.from_dict(self.project.to_dict())
            aid = self.apply(clone, self.specification())
            geometry = clone.attachment_geometry(aid)
            self.viewport.set_project(clone, frame=True)
            self.viewport.select([self.source, self.receiver.currentData()])
            self.viewport.select_relation(("attachment", aid))
            self.feedback.setText(
                f"Plochy přiléhají. Skutečný lepený otisk má "
                f"{geometry['available_area_mm2']:g} mm² na papíře. "
                "Pevnost materiálu ověří až výtisk. Zrušení nic nezmění."
            )
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except Exception as exc:
            self.viewport.set_project(self.project)
            self.viewport.select([self.source, self.receiver.currentData()])
            self.feedback.setText(str(exc))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def confirm(self):
        self.update_preview()
        if self.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            self.result_spec = self.specification()
            self.accept()
