"""Explicit profile correspondence with detached, asynchronous loft previews.

The host owns the single undo command. A preview never replaces live project
state, and apply reuses its persistent correspondence/ruling identities through
the public domain API. The small scheduler runs one job and retains at most one
latest request; invalidated, cancelled and closed-dialog results are discarded.
"""
# ruff: noqa: N802 -- Qt virtual overrides use framework method names.

from __future__ import annotations

import copy
import hashlib
import json
from uuid import uuid4

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QTransform, QValidator
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
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from archpapercraft.authoring.profile_curves import (
    _mapped_commands,
    profile_native_path,
    source_curve,
)
from archpapercraft.ui.author_paper import _path
from archpapercraft.ui.author_sketch import cosmetic

_KINDS = {"line": "úsečka", "arc": "kruhový oblouk", "cubic": "Bézierova křivka"}
_APPLY_KEYS = ("correspondences", "seam_patch_id", "end_ruling_id", "tolerance_mm", "max_segments")


def _snapshot(project):
    return copy.deepcopy(project.to_dict(validate=False))


def _digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _matches(project, fingerprint):
    try:
        return _digest(_snapshot(project)) == fingerprint
    except (ValueError, TypeError, AttributeError):
        return False


def _default_preview(project, first, second, **parameters):
    return project.preview_loft(first, second, **parameters)


class _PreviewSignals(QObject):
    finished = Signal(int, object, object)


class _PreviewJob(QRunnable):
    def __init__(self, token, project_type, request, function):
        super().__init__()
        self.token, self.project_type, self.request, self.function = (
            token,
            project_type,
            request,
            function,
        )
        self.signals = _PreviewSignals()

    def run(self):
        try:
            # from_dict may validate geometry, so cloning also belongs here.
            clone = self.project_type.from_dict(copy.deepcopy(self.request["state"]))
            parameters = copy.deepcopy(self.request["parameters"])
            first, second = parameters.pop("first_profile_id"), parameters.pop("second_profile_id")
            result = self.function(clone, first, second, **parameters)
            self.signals.finished.emit(self.token, result, None)
        except Exception as exc:
            self.signals.finished.emit(self.token, None, str(exc))


class _ProfileComparison(QGraphicsView):
    """Native 2D source outlines and explicitly selected endpoint pairings."""

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setInteractive(False)
        self.setMinimumHeight(210)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAccessibleName("Porovnání obrysů a směrů odpovídajících úseků")

    def show_profiles(self, first, second, rows, active_row):
        scene = self.scene()
        scene.clear()
        if first is None or second is None:
            return
        transforms, colors = [], ("#007d78", "#ba5700")
        offset = 0.0
        for profile, color in zip((first, second), colors):
            path = _path(profile_native_path(profile, (np.eye(2), np.zeros(2))))
            bounds = path.boundingRect()
            transform = QTransform(1, 0, 0, -1, offset - bounds.left(), bounds.bottom())
            item = scene.addPath(transform.map(path), cosmetic(color, 1.5))
            item.setToolTip(profile.name + " · původní obrys")
            transforms.append(transform)
            offset += max(bounds.width(), 10) + max(10, bounds.width() * 0.3)
        for index, row in enumerate(rows):
            first_segment = first.segment(row["first"].currentData())
            second_segment = second.segment(row["second"].currentData())
            if first_segment is None or second_segment is None:
                continue
            starts, ends = [], []
            for profile, segment, transform, reverse in zip(
                (first, second),
                (first_segment, second_segment),
                transforms,
                (row["reverse_first"].isChecked(), row["reverse_second"].isChecked()),
            ):
                start = profile.vertex(
                    segment.end_vertex_id if reverse else segment.start_vertex_id
                )
                end = profile.vertex(segment.start_vertex_id if reverse else segment.end_vertex_id)
                starts.append(transform.map(*start.point))
                ends.append(transform.map(*end.point))
            if index == active_row:
                for profile, segment, transform, start, color in zip(
                    (first, second), (first_segment, second_segment), transforms, starts, colors
                ):
                    native = _mapped_commands(
                        source_curve(profile, segment), (np.eye(2), np.zeros(2))
                    )
                    selected = _path({"commands": native, "closed": False})
                    scene.addPath(transform.map(selected), cosmetic(color, 3))
                    label = scene.addSimpleText(f"{index + 1} →")
                    label.setBrush(QColor(color))
                    label.setPos(*start)
                    label.setScale(max(0.15, offset / 700))
                scene.addLine(*starts[0], *starts[1], cosmetic("#777777", 1, Qt.PenStyle.DashLine))
                scene.addLine(*ends[0], *ends[1], cosmetic("#aaaaaa", 1, Qt.PenStyle.DotLine))
        bounds = scene.itemsBoundingRect()
        margin = max(2, max(bounds.width(), bounds.height()) * 0.06)
        self.fitInView(
            bounds.adjusted(-margin, -margin, margin, margin), Qt.AspectRatioMode.KeepAspectRatio
        )


class LoftProfilesDialog(QDialog):
    """Create one loft from checked profile pairs; host calls apply in one undo.

    `preview_function(clone, first_id, second_id, **kwargs)` is a component-test
    seam. Production always uses clone.preview_loft. Injected callbacks are not
    evidence of actual B geometry, desktop operation or novice usability.
    """

    preview_changed = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, project, first_profile_id=None, parent=None, *, preview_function=None):
        super().__init__(parent)
        self.project = project
        self.preview_function = preview_function or _default_preview
        self.result_parameters = None
        self.preview_result = None
        self.pair_rows = []
        self._updating = False
        self._closed = False
        self._generation = self._serial = 0
        self._running_job = self._pending_request = None
        self._latest_token = None
        self._accepted_digest = None
        self._end_ruling_id = None
        self._pending_numeric_text = {}
        self._source_revision = project.revision
        self.setWindowTitle("Plocha mezi dvěma profily")
        self.resize(920, 800)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.guidance = QLabel(
            "1. Vyberte přední a zadní profil. 2. Zkontrolujte dvojice úseků, jejich směr "
            "a začátek spoje. 3. Spočítejte náhled a potom vytvořte plochu. "
            "Ostré rohy zůstanou zachované; nevytvářejí se nevyžádaná víka."
        )
        self.guidance.setWordWrap(True)
        layout.addWidget(self.guidance)
        self.help_button = QToolButton(text="Skrýt tipy")
        self.help_button.setCheckable(True)
        self.help_button.setChecked(True)
        self.help_button.toggled.connect(self._toggle_help)
        layout.addWidget(self.help_button)
        form = QFormLayout()
        self.first_profile, self.second_profile = QComboBox(), QComboBox()
        self.first_profile.setObjectName("loft_first_profile")
        self.second_profile.setObjectName("loft_second_profile")
        for profile in project.profiles.values():
            for combo in (self.first_profile, self.second_profile):
                combo.addItem(self._profile_label(profile), profile.id)
        if first_profile_id is not None:
            self.first_profile.setCurrentIndex(self.first_profile.findData(first_profile_id))
        if self.second_profile.count() > 1:
            self.second_profile.setCurrentIndex(1 if self.first_profile.currentIndex() == 0 else 0)
        form.addRow("První profil (modrozelený)", self.first_profile)
        form.addRow("Druhý profil (oranžový)", self.second_profile)
        self.placement_note = QLabel()
        self.placement_note.setWordWrap(True)
        form.addRow("Počátky v modelu", self.placement_note)
        layout.addLayout(form)
        self.comparison = _ProfileComparison()
        layout.addWidget(self.comparison, 1)
        note = QLabel(
            "Porovnání ve vlastních rovinách profilů · spojnice ukazují vybranou dvojici, "
            "nikoli hotový prostorový rozvin."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.pairs = QTableWidget(0, 4)
        self.pairs.setObjectName("loft_correspondences")
        self.pairs.setHorizontalHeaderLabels(
            ["První úsek", "Obrátit směr", "Druhý úsek", "Obrátit směr"]
        )
        self.pairs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pairs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.pairs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pairs.setMinimumHeight(135)
        layout.addWidget(self.pairs)
        actions = QHBoxLayout()
        for text, action in (
            ("Přidat dvojici", self.add_pair),
            ("Odebrat dvojici", self.remove_pair),
            ("Posunout výš", lambda: self.move_pair(-1)),
            ("Posunout níž", lambda: self.move_pair(1)),
        ):
            button = QPushButton(text)
            button.setAutoDefault(False)
            button.clicked.connect(action)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.seam = QComboBox()
        self.seam.setObjectName("loft_seam")
        form = QFormLayout()
        form.addRow("Začátek rozvíjení / spoj", self.seam)
        layout.addLayout(form)
        self.confirm_pairs = QCheckBox("Zkontroloval(a) jsem dvojice, směry a začátek spoje.")
        self.confirm_pairs.setObjectName("loft_confirm_pairs")
        layout.addWidget(self.confirm_pairs)
        self.advanced = QToolButton(text="Přesnost a výpočetní limit")
        self.advanced.setCheckable(True)
        layout.addWidget(self.advanced)
        self.advanced_panel = QWidget()
        advanced_layout = QFormLayout(self.advanced_panel)
        self.tolerance = QDoubleSpinBox()
        self.tolerance.setObjectName("loft_tolerance")
        self.tolerance.setRange(0.000001, 0.01)
        self.tolerance.setDecimals(6)
        self.tolerance.setValue(0.005)
        self.tolerance.setSuffix(" mm na papíře")
        self.tolerance.setKeyboardTracking(False)
        self.max_segments = QSpinBox()
        self.max_segments.setObjectName("loft_segment_limit")
        self.max_segments.setRange(2, 65536)
        self.max_segments.setValue(16384)
        self.max_segments.setKeyboardTracking(False)
        advanced_layout.addRow("Numerická mez", self.tolerance)
        advanced_layout.addRow("Nejvýše výpočetních úseků", self.max_segments)
        self.advanced_panel.setVisible(False)
        self.advanced.toggled.connect(self.advanced_panel.setVisible)
        layout.addWidget(self.advanced_panel)
        computation = QHBoxLayout()
        self.calculate = QPushButton("Spočítat náhled (Ctrl+R)")
        self.calculate.setObjectName("loft_calculate")
        self.calculate.setShortcut("Ctrl+R")
        self.calculate.setAutoDefault(False)
        self.cancel_calculation = QPushButton("Zrušit výpočet")
        self.cancel_calculation.setAutoDefault(False)
        self.cancel_calculation.setEnabled(False)
        self.calculate.clicked.connect(self.request_preview)
        self.cancel_calculation.clicked.connect(self.cancel_preview)
        computation.addWidget(self.calculate)
        computation.addWidget(self.cancel_calculation)
        outer.addLayout(computation)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        self.feedback.setObjectName("loft_feedback")
        outer.addWidget(self.feedback)
        self.keep_target = QCheckBox(
            "Uchovat pouze konstrukční cíl bez přesného rozvinu; export zůstane zablokovaný."
        )
        self.keep_target.setObjectName("loft_keep_target")
        self.keep_target.setVisible(False)
        outer.addWidget(self.keep_target)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.apply_button.setText("Vytvořit plochu")
        self.apply_button.setAutoDefault(False)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Zrušit")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self.first_profile.currentIndexChanged.connect(self._profiles_changed)
        self.second_profile.currentIndexChanged.connect(self._profiles_changed)
        self.seam.currentIndexChanged.connect(self._mapping_changed)
        self.confirm_pairs.toggled.connect(self._confirmation_changed)
        self.keep_target.toggled.connect(self._update_actions)
        self.tolerance.valueChanged.connect(self._settings_changed)
        self.max_segments.valueChanged.connect(self._settings_changed)
        # A pending spin-box edit invalidates a preview before editingFinished.
        for field in (self.tolerance, self.max_segments):
            field.lineEdit().textEdited.connect(
                lambda text, field=field: self._numeric_edited(field, text)
            )
        self.pairs.currentCellChanged.connect(self._redraw)
        self._profiles_changed()
        self._source_timer = QTimer(self)
        self._source_timer.setInterval(150)
        self._source_timer.timeout.connect(self._check_source_revision)
        self._source_timer.start()

    @staticmethod
    def _profile_label(profile):
        native = profile_native_path(profile, (np.eye(2), np.zeros(2)))
        bounds = _path(native).boundingRect()
        width, height = bounds.width(), bounds.height()
        return (
            f"{profile.name} · {width:g} × {height:g} mm · "
            f"{'uzavřený' if profile.closed else 'otevřený'} · {len(profile.segments)} úseků"
        )

    def _profiles(self):
        return (
            self.project.profiles.get(self.first_profile.currentData()),
            self.project.profiles.get(self.second_profile.currentData()),
        )

    def _toggle_help(self, checked):
        self.guidance.setVisible(checked)
        self.help_button.setText("Skrýt tipy" if checked else "Zobrazit tipy")

    def _profiles_changed(self, *_args):
        self._updating = True
        self._end_ruling_id = None
        self.pair_rows = []
        first, second = self._profiles()
        if first is not None and second is not None and first.id != second.id:
            for a, b in zip(first.segments, second.segments):
                self.pair_rows.append(self._make_row(a.id, b.id))
        self._rebuild_rows()
        self._updating = False
        self._mapping_changed()

    def _make_row(self, first_id=None, second_id=None):
        row = {"id": str(uuid4())}
        for side, profile, selected in zip(
            ("first", "second"), self._profiles(), (first_id, second_id)
        ):
            combo = QComboBox()
            combo.setPlaceholderText("Vyberte odpovídající úsek")
            if profile is not None:
                for index, segment in enumerate(profile.segments):
                    start, end = (
                        profile.vertex(segment.start_vertex_id),
                        profile.vertex(segment.end_vertex_id),
                    )
                    combo.addItem(
                        f"{index + 1} · {_KINDS[segment.kind]} · "
                        f"({start.point[0]:g}, {start.point[1]:g}) → "
                        f"({end.point[0]:g}, {end.point[1]:g})",
                        segment.id,
                    )
                if selected is not None:
                    combo.setCurrentIndex(combo.findData(selected))
            row[side] = combo
            reverse = QCheckBox("Zpět")
            reverse.setAccessibleName(
                "Obrátit směr " + ("prvního" if side == "first" else "druhého") + " úseku"
            )
            row["reverse_" + side] = reverse
            combo.currentIndexChanged.connect(self._mapping_changed)
            reverse.toggled.connect(self._mapping_changed)
        return row

    def _rebuild_rows(self):
        selected = self.seam.currentData()
        # QTableWidget owns cell widgets and deletes them when their row goes
        # away. Preserve draft values/IDs, never reparent those owned widgets.
        records = []
        for row in self.pair_rows:
            records.append(
                {
                    "id": row["id"],
                    "first_id": row["first"].currentData(),
                    "second_id": row["second"].currentData(),
                    "reverse_first": row["reverse_first"].isChecked(),
                    "reverse_second": row["reverse_second"].isChecked(),
                    "ruling_id": row.get("ruling_id"),
                }
            )
            for key in ("first", "second", "reverse_first", "reverse_second"):
                if row[key].parent() is None:
                    row[key].deleteLater()
        self.pairs.blockSignals(True)
        self.seam.blockSignals(True)
        self.pairs.setRowCount(0)
        self.pairs.setRowCount(len(records))
        self.seam.clear()
        self.pair_rows = []
        for index, record in enumerate(records):
            row = self._make_row(record["first_id"], record["second_id"])
            row["id"], row["ruling_id"] = record["id"], record["ruling_id"]
            row["reverse_first"].setChecked(record["reverse_first"])
            row["reverse_second"].setChecked(record["reverse_second"])
            self.pair_rows.append(row)
            for column, key in enumerate(("first", "reverse_first", "second", "reverse_second")):
                self.pairs.setCellWidget(index, column, row[key])
            description = row["first"].currentText().split(" · ")
            kind = description[1] if len(description) > 1 else "vyberte úsek"
            self.seam.addItem(f"Dvojice {index + 1} · {kind}", row["id"])
        found = self.seam.findData(selected)
        self.seam.setCurrentIndex(max(0, found))
        if self.pair_rows:
            self.pairs.selectRow(0)
        self.pairs.blockSignals(False)
        self.seam.blockSignals(False)

    def add_pair(self):
        self._updating = True
        self.pair_rows.append(self._make_row())
        self._rebuild_rows()
        self._updating = False
        self._mapping_changed()

    def remove_pair(self):
        row = self.pairs.currentRow()
        if 0 <= row < len(self.pair_rows):
            self._updating = True
            self.pair_rows.pop(row)
            self._rebuild_rows()
            self._updating = False
            self._mapping_changed()

    def move_pair(self, direction):
        index = self.pairs.currentRow()
        other = index + direction
        if 0 <= index < len(self.pair_rows) and 0 <= other < len(self.pair_rows):
            self._updating = True
            self.pair_rows[index], self.pair_rows[other] = (
                self.pair_rows[other],
                self.pair_rows[index],
            )
            self._rebuild_rows()
            self.pairs.selectRow(other)
            self._updating = False
            self._mapping_changed()

    def _redraw(self, *_args):
        try:
            origins = []
            for profile in self._profiles():
                if profile is not None:
                    origins.append(
                        ", ".join(
                            f"{axis} {value:g}"
                            for axis, value in zip(("X", "Y", "Z"), profile.plane.origin)
                        )
                        + " mm"
                    )
            self.placement_note.setText(" · ".join(origins))
            self.comparison.show_profiles(
                *self._profiles(), self.pair_rows, self.pairs.currentRow()
            )
        except (ValueError, AttributeError, KeyError):
            self.comparison.scene().clear()

    def _mapping_changed(self, *_args):
        if self._updating:
            return
        self.confirm_pairs.blockSignals(True)
        self.confirm_pairs.setChecked(False)
        self.confirm_pairs.blockSignals(False)
        self._invalidate(
            "Dvojice podle pořadí jsou pouze návrh. Zkontrolujte úseky, směry a začátek "
            "spoje, potvrďte je a spočítejte náhled."
        )
        self._redraw()

    def _settings_changed(self, *_args):
        if not self._updating:
            self._invalidate("Přesnost se změnila. Aktualizujte náhled před vytvořením plochy.")

    def _numeric_edited(self, field, text):
        # A focus-out correction must not erase an invalid edit just before a
        # mouse click starts a computation with the previous numeric value.
        self._pending_numeric_text[field] = text
        self._settings_changed()

    def _confirmation_changed(self, checked):
        if not checked:
            self._invalidate("Nejprve zkontrolujte dvojice úseků a potvrďte jejich směry.")
        self._update_actions()

    def _invalidate(self, message):
        self._generation += 1
        self._latest_token = None
        self._pending_request = None
        self.preview_result = self.result_parameters = None
        self.keep_target.blockSignals(True)
        self.keep_target.setChecked(False)
        self.keep_target.setVisible(False)
        self.keep_target.blockSignals(False)
        self.feedback.setText(message)
        self.preview_changed.emit(None)
        self._update_actions()

    def _structural_error(self):
        first, second = self._profiles()
        if first is None or second is None:
            return "Nejprve nakreslete a vyberte dva vlastní profily."
        if first.id == second.id:
            return (
                "Vyberte dva různé profily; druhý nakreslete nebo vytvořte jako upravitelnou kopii."
            )
        if not self.pair_rows:
            return "Přidejte alespoň jednu odpovídající dvojici úseků."
        for side in ("first", "second"):
            values = [row[side].currentData() for row in self.pair_rows]
            profile = first if side == "first" else second
            if (
                None in values
                or len(values) != len(set(values))
                or any(profile.segment(value) is None for value in values)
            ):
                return "Každý úsek smí být v návrhu pouze jednou. Opravte vybranou dvojici."
        return None

    def _update_actions(self, *_args):
        error = self._structural_error()
        confirmed = self.confirm_pairs.isChecked()
        self.calculate.setEnabled(not self._closed and error is None and confirmed)
        self.calculate.setToolTip(
            error
            or (
                "Nejprve potvrďte zkontrolované dvojice."
                if not confirmed
                else "Spočítat aktuální návrh bez změny projektu"
            )
        )
        valid = self.preview_result is not None and (
            self.preview_result.get("status") == "EXACT"
            or (
                self.preview_result.get("status") in ("REJECTED", "UNRESOLVED")
                and self.keep_target.isChecked()
            )
        )
        self.apply_button.setEnabled(not self._closed and valid and confirmed)
        self.apply_button.setText(
            "Uchovat konstrukční cíl" if self.keep_target.isChecked() else "Vytvořit plochu"
        )
        if error:
            self.feedback.setText(error)

    def _commit_fields(self):
        for field in (self.tolerance, self.max_segments):
            raw = self._pending_numeric_text.get(field)
            if raw is not None and field.validate(raw, len(raw))[0] != QValidator.State.Acceptable:
                self.advanced.setChecked(True)
                field.lineEdit().setText(raw)
                self.feedback.setText("Opravte rozepsanou přesnost nebo výpočetní limit.")
                field.setFocus()
                return False
            if not field.hasAcceptableInput():
                self.feedback.setText("Opravte rozepsanou přesnost nebo výpočetní limit.")
                field.setFocus()
                return False
        for field in (self.tolerance, self.max_segments):
            field.interpretText()
        self._pending_numeric_text.clear()
        return True

    def _parameters(self):
        correspondences = []
        for row in self.pair_rows:
            item = {
                "id": row["id"],
                "first_segment_id": row["first"].currentData(),
                "second_segment_id": row["second"].currentData(),
                "first_interval": [1, 0] if row["reverse_first"].isChecked() else [0, 1],
                "second_interval": [1, 0] if row["reverse_second"].isChecked() else [0, 1],
            }
            if row.get("ruling_id"):
                item["ruling_id"] = row["ruling_id"]
            correspondences.append(item)
        result = {
            "first_profile_id": self.first_profile.currentData(),
            "second_profile_id": self.second_profile.currentData(),
            "correspondences": correspondences,
            "seam_patch_id": self.seam.currentData(),
            "tolerance_mm": self.tolerance.value(),
            "max_segments": self.max_segments.value(),
        }
        if self._end_ruling_id is not None:
            result["end_ruling_id"] = self._end_ruling_id
        return result

    def request_preview(self):
        self._check_source_revision()
        if self._closed or not self._commit_fields():
            return False
        error = self._structural_error()
        if error or not self.confirm_pairs.isChecked():
            self.feedback.setText(error or "Nejprve potvrďte zkontrolované dvojice a směry.")
            return False
        try:
            state = _snapshot(self.project)
            fingerprint = _digest(state)
        except (ValueError, TypeError) as exc:
            self.feedback.setText("Aktuální projekt nelze bezpečně zobrazit: " + str(exc))
            return False
        self._invalidate("Počítám aktuální návrh. Můžete upravit dvojice nebo výpočet zrušit.")
        self._serial += 1
        token = self._serial
        request = {
            "token": token,
            "generation": self._generation,
            "state": state,
            "fingerprint": fingerprint,
            "parameters": self._parameters(),
        }
        self._latest_token = token
        self.cancel_calculation.setEnabled(True)
        if self._running_job is None:
            self._start(request)
        else:
            self._pending_request = request
            self.feedback.setText(
                "Aktuální návrh čeká na dokončení předchozího výpočtu. "
                "Použije se jen poslední požadavek."
            )
        return True

    def _start(self, request):
        job = _PreviewJob(request["token"], type(self.project), request, self.preview_function)
        self._running_job = job
        job.signals.finished.connect(self._finished)
        self.busy_changed.emit(True)
        QThreadPool.globalInstance().start(job)

    def _finished(self, token, result, error):
        job = self._running_job
        if job is None or job.token != token:
            return
        self._running_job = None
        request = job.request
        if (
            not self._closed
            and token == self._latest_token
            and request["generation"] == self._generation
        ):
            if not _matches(self.project, request["fingerprint"]):
                self._invalidate(
                    "Projekt se během výpočtu změnil. Zkontrolujte profily a vytvořte nový náhled."
                )
            elif error:
                self.feedback.setText(
                    "Návrh nelze spočítat: "
                    + error
                    + " Opravte dvojice, směr nebo zdrojové profily a zkuste znovu."
                )
            else:
                try:
                    self._show_result(result, request)
                except (KeyError, ValueError, TypeError):
                    self.preview_result = None
                    self.feedback.setText(
                        "Výsledek neodpovídá zadaným dvojicím nebo jejich směru. "
                        "Návrh nelze použít; opakujte výpočet."
                    )
        pending, self._pending_request = self._pending_request, None
        if not self._closed and pending is not None and pending["generation"] == self._generation:
            self._start(pending)
        else:
            self.busy_changed.emit(False)
            self.cancel_calculation.setEnabled(False)
        self._update_actions()

    def _show_result(self, result, request):
        if not isinstance(result, dict) or result.get("status") not in (
            "EXACT",
            "REJECTED",
            "UNRESOLVED",
        ):
            self.feedback.setText(
                "Výpočet nevrátil ověřitelný náhled. Upravte zadání a opakujte výpočet."
            )
            return
        self.preview_result = copy.deepcopy(result)
        params = result.get("params") or request["parameters"]
        expected_pairs = {pair["id"]: pair for pair in request["parameters"]["correspondences"]}
        actual_pairs = params["correspondences"]
        if {pair["id"] for pair in actual_pairs} != set(expected_pairs) or len(actual_pairs) != len(
            expected_pairs
        ):
            raise ValueError("Preview changed authored correspondence identities")
        for pair in actual_pairs:
            original = expected_pairs[pair["id"]]
            if any(
                pair[key] != original[key]
                for key in (
                    "first_segment_id",
                    "second_segment_id",
                    "first_interval",
                    "second_interval",
                )
            ):
                raise ValueError("Preview changed authored source pairing")
        self._parameters_for_apply = {
            "first_profile_id": request["parameters"]["first_profile_id"],
            "second_profile_id": request["parameters"]["second_profile_id"],
            **{
                key: copy.deepcopy(params[key] if key in params else request["parameters"].get(key))
                for key in _APPLY_KEYS
                if key in params or key in request["parameters"]
            },
        }
        self._end_ruling_id = self._parameters_for_apply.get("end_ruling_id")
        # Store IDs created by the detached preview; do not re-pair by index.
        by_id = {row["id"]: row for row in self.pair_rows}
        for pair in self._parameters_for_apply["correspondences"]:
            if pair["id"] in by_id and pair.get("ruling_id"):
                by_id[pair["id"]]["ruling_id"] = pair["ruling_id"]
        self._result_digest = request["fingerprint"]
        status = result["status"]
        if status == "EXACT":
            kind = (
                "Rovinný pás"
                if result.get("family") in ("PLANAR_REGION", "CONCENTRIC_PLANAR_ARC_BAND")
                else "Plocha mezi profily"
            )
            self.feedback.setText(
                kind
                + " · přesný režim s doloženou numerickou mezí. "
                + result.get("message", "Návrh je připravený k vytvoření.")
            )
        else:
            self.keep_target.setVisible(True)
            self.feedback.setText(
                (
                    "Přesný rozvin byl odmítnut. "
                    if status == "REJECTED"
                    else "Přesný rozvin není doložený. "
                )
                + result.get("message", "")
                + " Opravte profily či jejich párování, nebo výslovně uchovejte "
                "jen konstrukční cíl bez tiskového dílu."
            )
        self.preview_changed.emit(copy.deepcopy(result))

    def _check_source_revision(self):
        if not self._closed and self.project.revision != self._source_revision:
            self._source_revision = self.project.revision
            self._updating = True
            for combo in (self.first_profile, self.second_profile):
                selected = combo.currentData()
                combo.blockSignals(True)
                combo.clear()
                for profile in self.project.profiles.values():
                    combo.addItem(self._profile_label(profile), profile.id)
                combo.setCurrentIndex(combo.findData(selected))
                combo.blockSignals(False)
            self._rebuild_rows()
            self._updating = False
            self.confirm_pairs.blockSignals(True)
            self.confirm_pairs.setChecked(False)
            self.confirm_pairs.blockSignals(False)
            self._invalidate(
                "Zdrojový projekt se změnil. Zkontrolujte výběr profilů a spočítejte nový náhled."
            )
            self._redraw()

    def cancel_preview(self):
        self._invalidate("Výpočet byl zrušen. Pozdější výsledek se nepoužije; projekt se nezměnil.")
        self.cancel_calculation.setEnabled(False)

    def accept(self):
        if not self._commit_fields() or not self.apply_button.isEnabled():
            return
        if not _matches(self.project, self._result_digest):
            self._invalidate("Projekt se od náhledu změnil. Před vytvořením aktualizujte náhled.")
            return
        self.result_parameters = copy.deepcopy(self._parameters_for_apply)
        self._accepted_digest = self._result_digest
        super().accept()

    def done(self, result):
        self._closed = True
        self._generation += 1
        self._latest_token = None
        self._pending_request = None
        self._source_timer.stop()
        if result != QDialog.DialogCode.Accepted:
            self.result_parameters = None
            self.preview_result = None
            self.preview_changed.emit(None)
        super().done(result)

    def apply(self, project):
        """Called inside the host's one undo/rollback command; no state injection."""
        if self.result() != QDialog.DialogCode.Accepted or self.result_parameters is None:
            raise ValueError("Nejprve potvrďte aktuální náhled plochy.")
        if not _matches(project, self._accepted_digest):
            raise ValueError("Projekt se od potvrzení změnil. Otevřete nový náhled plochy.")
        params = copy.deepcopy(self.result_parameters)
        first, second = params.pop("first_profile_id"), params.pop("second_profile_id")
        return project.add_loft(
            first, second, **{key: params[key] for key in _APPLY_KEYS if key in params}
        )
