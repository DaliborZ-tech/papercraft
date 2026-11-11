"""An explicit manual grid gesture, without packing or automatic page choice."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QTransform, QValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from archpapercraft.ui.author_paper import _path
from archpapercraft.ui.author_segmentation import _digest, _state


class ManualGridDialog(QDialog):
    """The author selects pieces, page, anchor origin, pitch and optional angle."""

    def __init__(self, project, part_ids, parent=None):
        super().__init__(parent)
        self.project = project
        self._fingerprint = _digest(_state(project))
        self._preview_updates = self._accepted_updates = None
        self.setWindowTitle("Ruční rozmístění vybraných dílů")
        self.resize(830, 670)
        layout = QVBoxLayout(self)
        instructions = QLabel(
            "Vyberte díly (Ctrl/Shift), stránku a polohy kotev v pravidelné mřížce. "
            "Pořadí odpovídá seznamu. Náhled ukáže právě vaše zadání; "
            "nevybírá stránku, neotáčí ani neskládá díly automaticky. "
            "Jednotlivé díly pak můžete dál přetahovat."
        )
        instructions.setWordWrap(True)
        self.help_button = QPushButton("Skrýt tipy")
        self.help_button.setCheckable(True)
        self.help_button.setChecked(True)
        self.help_button.toggled.connect(
            lambda checked: (
                instructions.setVisible(checked),
                self.help_button.setText("Skrýt tipy" if checked else "Zobrazit tipy"),
            )
        )
        layout.addWidget(self.help_button)
        layout.addWidget(instructions)
        body = QHBoxLayout()
        self.parts = QListWidget()
        self.parts.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.parts.setAccessibleName("Díly pro ruční rozmístění; Ctrl a Shift rozšiřují výběr")
        printable = project.material_part_ids()
        if len(part_ids) != len(set(part_ids)) or not set(part_ids) <= printable:
            raise ValueError("Vyberte jednoznačné tiskové díly aktuální generace.")
        for pid in part_ids:
            placement = project.placements[pid]
            text = project.parts[pid].name
            if placement.position_locked or placement.rotation_locked:
                text += " · zámek polohy" if placement.position_locked else " · zámek úhlu"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, pid)
            self.parts.addItem(item)
        body.addWidget(self.parts, 1)
        self.view = QGraphicsView()
        self.view.setScene(QGraphicsScene(self.view))
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setAccessibleName("Náhled zvolených poloh na stránce")
        body.addWidget(self.view, 2)
        layout.addLayout(body, 1)
        selection_buttons = QHBoxLayout()
        self.select_all = QPushButton("Vybrat všechny zobrazené")
        self.select_none = QPushButton("Zrušit výběr")
        self.select_all.clicked.connect(self.parts.selectAll)
        self.select_none.clicked.connect(self.parts.clearSelection)
        selection_buttons.addWidget(self.select_all)
        selection_buttons.addWidget(self.select_none)
        layout.addLayout(selection_buttons)
        form = QFormLayout()
        self.page = QComboBox()
        for index, page in enumerate(project.pages):
            self.page.addItem(
                f"Stránka {index + 1} · {page.width_mm:g} × {page.height_mm:g} mm", page.id
            )
        self.page.setCurrentIndex(-1)
        self.page.setPlaceholderText("Vyberte cílovou stránku")
        form.addRow("Stránka", self.page)
        self.columns = QSpinBox()
        self.columns.setRange(1, max(1, len(part_ids)))
        self.columns.setValue(min(8, max(1, len(part_ids))))
        form.addRow("Počet sloupců", self.columns)
        self.x, self.y, self.pitch_x, self.pitch_y, self.angle = (
            QDoubleSpinBox() for _ in range(5)
        )
        for field in (self.x, self.y, self.pitch_x, self.pitch_y, self.angle):
            field.setDecimals(4)
            field.setRange(-1000000, 1000000)
            field.setKeyboardTracking(False)
        for field in (self.pitch_x, self.pitch_y):
            field.setRange(0.0001, 1000000)
            field.setValue(18)
        self.x.setValue(25)
        self.y.setValue(25)
        for label, field in (
            ("Kotva prvního dílu X (mm)", self.x),
            ("Kotva prvního dílu Y (mm)", self.y),
            ("Rozteč kotev vodorovně (mm)", self.pitch_x),
            ("Rozteč kotev svisle (mm)", self.pitch_y),
        ):
            form.addRow(label, field)
        self.rotate = QCheckBox("Zadat společný úhel (jinak zachovat jednotlivé úhly)")
        form.addRow(self.rotate, self.angle)
        self.angle.setEnabled(False)
        self.rotate.toggled.connect(self.angle.setEnabled)
        layout.addLayout(form)
        self.preview_button = QPushButton("Zobrazit zadané polohy")
        self.preview_button.clicked.connect(self.preview)
        layout.addWidget(self.preview_button)
        self.feedback = QLabel("Vyberte díly a cílovou stránku. Projekt se změní až potvrzením.")
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.feedback)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Umístit vybrané díly")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.parts.itemSelectionChanged.connect(self._invalidate)
        self.page.currentIndexChanged.connect(self._invalidate)
        self.rotate.toggled.connect(self._invalidate)
        for field in (self.columns, self.x, self.y, self.pitch_x, self.pitch_y, self.angle):
            field.valueChanged.connect(self._invalidate)
            field.lineEdit().textEdited.connect(self._invalidate)
        self._invalidate()

    def _invalidate(self, *_args):
        self._preview_updates = self._accepted_updates = None
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.view.scene().clear()
        self.feedback.setText("Zobrazte aktuálně zadané polohy; žádný díl se zatím nepřemístil.")

    def _updates(self):
        for field in (self.columns, self.x, self.y, self.pitch_x, self.pitch_y, self.angle):
            if (
                field.validate(field.lineEdit().text(), field.lineEdit().cursorPosition())[0]
                != QValidator.State.Acceptable
            ):
                field.setFocus()
                raise ValueError("Opravte neplatnou souřadnici, rozteč nebo úhel.")
            field.interpretText()
        if self.page.currentData() is None or not self.parts.selectedItems():
            raise ValueError("Vyberte alespoň jeden díl a cílovou stránku.")
        updates = {}
        # Visual list order, never selection-click order, determines the grid.
        selected = [
            self.parts.item(i) for i in range(self.parts.count()) if self.parts.item(i).isSelected()
        ]
        for index, item in enumerate(selected):
            pid = item.data(Qt.ItemDataRole.UserRole)
            placement = self.project.placements[pid]
            values = dict(
                page_id=self.page.currentData(),
                x_mm=self.x.value() + (index % self.columns.value()) * self.pitch_x.value(),
                y_mm=self.y.value() + (index // self.columns.value()) * self.pitch_y.value(),
            )
            if self.rotate.isChecked():
                values["rotation_deg"] = self.angle.value()
            if placement.position_locked and any(
                getattr(placement, key) != values[key] for key in ("page_id", "x_mm", "y_mm")
            ):
                raise ValueError(
                    f"{self.project.parts[pid].name}: poloha je zamčená. "
                    "Vyřaďte díl z výběru nebo jej nejprve výslovně odemkněte."
                )
            if (
                placement.rotation_locked
                and self.rotate.isChecked()
                and placement.rotation_deg != self.angle.value()
            ):
                raise ValueError(
                    f"{self.project.parts[pid].name}: úhel je zamčený. "
                    "Zachovejte jednotlivé úhly nebo nejprve odemkněte tento díl."
                )
            updates[pid] = values
        return updates

    def preview(self):
        self._invalidate()
        try:
            self._check_source(self.project)
            updates = self._updates()
            scene = self.view.scene()
            page = next(p for p in self.project.pages if p.id == self.page.currentData())
            scene.addRect(
                0, 0, page.width_mm, page.height_mm, QPen(QColor("#68776f"), 0.3), QColor("white")
            )
            margin = page.margin_mm
            scene.addRect(
                margin,
                margin,
                page.width_mm - 2 * margin,
                page.height_mm - 2 * margin,
                QPen(QColor("#9aaca2"), 0.2, Qt.PenStyle.DashLine),
            )
            for pid in self.project.material_part_ids():
                placement = self.project.placements[pid]
                values = updates.get(pid, {})
                if values.get("page_id", placement.page_id) != page.id:
                    continue
                transform = QTransform()
                transform.translate(
                    values.get("x_mm", placement.x_mm), values.get("y_mm", placement.y_mm)
                )
                transform.rotate(values.get("rotation_deg", placement.rotation_deg))
                for path in self.project.parts[pid].paths.get("CUT", []):
                    scene.addPath(
                        transform.map(_path(path)),
                        QPen(QColor("#007d78" if pid in updates else "#a0a9a4"), 0.3),
                    )
            self.view.fitInView(
                scene.itemsBoundingRect().adjusted(-5, -5, 5, 5), Qt.AspectRatioMode.KeepAspectRatio
            )
            self._preview_updates = copy.deepcopy(updates)
            self.feedback.setText(
                f"Ruční zadání pro {len(updates)} dílů. Zámky ani ostatní díly se nemění. "
                "Přesahy stránky a kolize zkontrolujte v náhledu; po potvrzení je aplikace "
                "uvede v seznamu problémů a chyby budou blokovat export."
            )
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except (ValueError, TypeError, KeyError) as exc:
            self._invalidate()
            self.feedback.setText(str(exc))

    def _check_source(self, project):
        if _digest(_state(project)) != self._fingerprint:
            raise ValueError("Projekt se změnil. Otevřete nové ruční rozmístění.")

    def accept(self):
        try:
            updates = self._updates()
            self._check_source(self.project)
            if self._preview_updates is None or updates != self._preview_updates:
                raise ValueError("Zadání se změnilo. Nejprve zobrazte aktuální polohy.")
            self._accepted_updates = copy.deepcopy(updates)
        except (ValueError, TypeError) as exc:
            self._invalidate()
            self.feedback.setText(str(exc))
            return
        super().accept()

    def apply(self, project):
        self._check_source(project)
        if self._accepted_updates is None:
            raise ValueError("Nejprve potvrďte zadané polohy.")
        project.set_placements(copy.deepcopy(self._accepted_updates))
