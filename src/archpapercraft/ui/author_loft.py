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
from uuid import UUID, uuid4

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
_UNSPECIFIED = object()


def _snapshot(project):
    return copy.deepcopy(project.to_dict(validate=False))


def _digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _matches(project, fingerprint):
    try:
        return _digest(_snapshot(project)) == fingerprint
    except (ValueError, TypeError, AttributeError):
        return False


def _is_uuid(value):
    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _default_preview(project, first, second, *, existing_surface_id=None, **parameters):
    if existing_surface_id is not None:
        parameters.pop("end_ruling_id", None)
        return project.preview_loft_update(
            existing_surface_id, second_profile_id=second, **parameters
        )
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
            if self.function is _default_preview and self.request.get("existing_surface_id"):
                parameters["existing_surface_id"] = self.request["existing_surface_id"]
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
        self._edit_mode = False
        self._loaded_first_profile_id = None
        self._edit_identity_error = False
        self.existing_surface_id = None
        self.load_error = None
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
        self.seam.activated.connect(self._seam_reselected)
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

    def load_parameters(self, first_profile_id, params, *, existing_surface_id):
        """Load authored correspondence for an explicitly selected existing loft.

        The first source cannot be retargeted by update_loft. Missing sources
        remain unmatched rows, never a fresh index-based proposal. A valid
        loaded mapping is already an author's explicit choice, not auto-pairing.
        No calculation, command or replacement of the document occurs here.
        """
        if self._closed:
            return False
        self._updating = True
        self._edit_mode = True
        self.existing_surface_id = existing_surface_id
        self._loaded_first_profile_id = first_profile_id
        self.first_profile.setEnabled(False)
        self.first_profile.setPlaceholderText("Původní první profil chybí")
        self.second_profile.setPlaceholderText("Vyberte druhý profil")
        self.first_profile.setCurrentIndex(self.first_profile.findData(first_profile_id))
        valid_envelope = isinstance(params, dict) and isinstance(
            params.get("correspondences"), list
        )
        params = copy.deepcopy(params) if isinstance(params, dict) else {}
        self.second_profile.setCurrentIndex(
            self.second_profile.findData(params.get("second_profile_id"))
        )
        self._end_ruling_id = params.get("end_ruling_id")
        self._edit_identity_error = not (
            valid_envelope and _is_uuid(existing_surface_id) and _is_uuid(self._end_ruling_id)
        )
        self._pending_numeric_text.clear()
        tolerance, maximum = params.get("tolerance_mm", 0.005), params.get("max_segments", 16384)
        valid_budgets = (
            type(tolerance) in (int, float)
            and 0.000001 <= tolerance <= 0.01
            and type(maximum) is int
            and 2 <= maximum <= 65536
        )
        if valid_budgets:
            self.tolerance.setValue(tolerance)
            self.max_segments.setValue(maximum)
        else:
            self._edit_identity_error = True
        self.pair_rows = []
        for record in params.get("correspondences", []) if valid_envelope else []:
            record = record if isinstance(record, dict) else {}
            row = self._make_row(record.get("first_segment_id"), record.get("second_segment_id"))
            row["id"], row["ruling_id"] = record.get("id"), record.get("ruling_id")
            row["identity_error"] = not (
                _is_uuid(row["id"])
                and _is_uuid(row["ruling_id"])
                and record.get("first_interval") in ([0, 1], [1, 0])
                and record.get("second_interval") in ([0, 1], [1, 0])
            )
            row["reverse_first"].setChecked(record.get("first_interval") == [1, 0])
            row["reverse_second"].setChecked(record.get("second_interval") == [1, 0])
            self.pair_rows.append(row)
        self._rebuild_rows()
        self.seam.setCurrentIndex(self.seam.findData(params.get("seam_patch_id")))
        self._updating = False
        self.setWindowTitle("Upravit plochu mezi profily")
        error = self._structural_error()
        code = "LOFT_MAPPING_UNRESOLVED"
        if not valid_envelope or not valid_budgets:
            code = "LOFT_PARAMETERS_INVALID"
        elif any(profile is None for profile in self._profiles()):
            code = "LOFT_SOURCE_PROFILE_MISSING"
        elif any(
            row[side].currentData() is None
            for row in self.pair_rows
            for side in ("first", "second")
        ):
            code = "LOFT_SOURCE_SEGMENT_MISSING"
        elif self._edit_identity_error or any(row.get("identity_error") for row in self.pair_rows):
            code = "LOFT_REFERENCE_IDENTITY_INVALID"
        elif self.seam.currentIndex() < 0:
            code = "LOFT_SEAM_UNRESOLVED"
        if not error and params.get("reference_state", "BOUND") != "BOUND":
            error = (
                "Uložené zdrojové vazby čekají na opravu. Zkontrolujte a potvrďte každou dvojici."
            )
            code = "LOFT_REFERENCE_UNRESOLVED"
        self.load_error = {"code": code, "message": error} if error else None
        self.confirm_pairs.blockSignals(True)
        self.confirm_pairs.setChecked(error is None)
        self.confirm_pairs.blockSignals(False)
        message = error or (
            "Načtena původní autorská korespondence včetně směru a začátku spoje. "
            "Spočítejte aktuální náhled před potvrzením změny."
        )
        self._invalidate(message)
        self.feedback.setText(message)
        self._redraw()
        return error is None

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
        if self._updating:
            return
        self._updating = True
        if self._edit_mode:
            # update_loft cannot retarget the first source. A new second source
            # leaves existing rows present but unmatched, never paired by index.
            self.first_profile.setCurrentIndex(
                self.first_profile.findData(self._loaded_first_profile_id)
            )
        else:
            self._end_ruling_id = None
            self.pair_rows = []
            self.seam.clear()
            first, second = self._profiles()
            if first is not None and second is not None and first.id != second.id:
                for a, b in zip(first.segments, second.segments):
                    self.pair_rows.append(self._make_row(a.id, b.id))
        self._rebuild_rows()
        self._updating = False
        self._mapping_changed()

    def _make_row(self, first_id=_UNSPECIFIED, second_id=_UNSPECIFIED):
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
                if selected is not _UNSPECIFIED:
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
        initial_proposal = self.seam.count() == 0 and not self._edit_mode
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
                    "identity_error": row.get("identity_error", False),
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
            row["identity_error"] = record["identity_error"]
            row["reverse_first"].setChecked(record["reverse_first"])
            row["reverse_second"].setChecked(record["reverse_second"])
            self.pair_rows.append(row)
            for column, key in enumerate(("first", "reverse_first", "second", "reverse_second")):
                self.pairs.setCellWidget(index, column, row[key])
            description = row["first"].currentText().split(" · ")
            kind = description[1] if len(description) > 1 else "vyberte úsek"
            self.seam.addItem(f"Dvojice {index + 1} · {kind}", row["id"])
        found = self.seam.findData(selected)
        self.seam.setCurrentIndex(0 if selected is None and initial_proposal else found)
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
        first, _second = self._profiles()
        if self.sender() is self.seam and first is not None and first.closed:
            index = next(
                (i for i, row in enumerate(self.pair_rows) if row["id"] == self.seam.currentData()),
                -1,
            )
            if index > 0:
                # Choosing a seam is an authored cut: make the reordered
                # request visible BEFORE any preview, not a backend side effect.
                self._updating = True
                self.pair_rows = self.pair_rows[index:] + self.pair_rows[:index]
                self._rebuild_rows()
                self._updating = False
        self.confirm_pairs.blockSignals(True)
        self.confirm_pairs.setChecked(False)
        self.confirm_pairs.blockSignals(False)
        if self._edit_mode:
            error = self._structural_error()
            self.load_error = (
                {"code": "LOFT_MAPPING_UNRESOLVED", "message": error} if error else None
            )
        self._invalidate(
            "Autorská korespondence se změnila. Zkontrolujte zachované dvojice a směry, "
            "opravte nevybrané úseky a potvrďte aktuální mapu."
            if self._edit_mode
            else "Dvojice podle pořadí jsou pouze návrh. Zkontrolujte úseky, směry a začátek "
            "spoje, potvrďte je a spočítejte náhled."
        )
        self._redraw()

    def _seam_reselected(self, *_args):
        first, _second = self._profiles()
        if (
            first is not None
            and first.closed
            and self.pair_rows
            and self.seam.currentData() != self.pair_rows[0]["id"]
        ):
            self._mapping_changed()

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
        if self._edit_mode and first is None:
            return (
                "První zdrojový profil chybí. Opravte původní zdroj v modelu "
                "a otevřete úpravu znovu."
            )
        if self._edit_mode and second is None:
            return (
                "Druhý zdrojový profil chybí. Vyberte jiný profil a výslovně opravte dvojice úseků."
            )
        if first is None or second is None:
            return "Nejprve nakreslete a vyberte dva vlastní profily."
        if first.id == second.id:
            return (
                "Vyberte dva různé profily; druhý nakreslete nebo vytvořte jako upravitelnou kopii."
            )
        if not self.pair_rows:
            return "Přidejte alespoň jednu odpovídající dvojici úseků."
        if self._edit_identity_error or any(row.get("identity_error") for row in self.pair_rows):
            return "Uložené spojení ztratilo stálou identitu. Vadnou dvojici nahraďte výslovně."
        if len({row["id"] for row in self.pair_rows}) != len(self.pair_rows):
            return "Dvě uložené dvojice mají tutéž identitu. Vadnou dvojici nahraďte výslovně."
        if self.seam.currentData() not in {row["id"] for row in self.pair_rows}:
            return "Vyberte začátek rozvíjení mezi zachovanými dvojicemi úseků."
        if first.closed and self.seam.currentData() != self.pair_rows[0]["id"]:
            return (
                "Zvolený začátek spoje musí být první dvojicí. Přesuňte ji na začátek "
                "nebo ji znovu zvolte v nabídce začátku rozvíjení."
            )
        for side in ("first", "second"):
            values = [row[side].currentData() for row in self.pair_rows]
            profile = first if side == "first" else second
            if None in values or any(profile.segment(value) is None for value in values):
                return (
                    "Zdrojový úsek chybí. Vyberte pro každou označenou dvojici nový úsek výslovně."
                )
            if len(values) != len(set(values)):
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
            "Uchovat konstrukční cíl"
            if self.keep_target.isChecked()
            else "Použít změnu plochy"
            if self._edit_mode
            else "Vytvořit plochu"
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
            "existing_surface_id": self.existing_surface_id,
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
                        "Výsledek neodpovídá zadaným dvojicím, jejich pořadí, "
                        "směru nebo stálým vazbám. "
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
        candidate = copy.deepcopy(result)
        requested = request["parameters"]
        params = candidate.get("params")
        planar_without_loft = (
            candidate["status"] == "EXACT"
            and candidate.get("family") == "PLANAR_REGION"
            and params == {}
        )
        if planar_without_loft:
            # A planar B2 region has no persistent loft/ruling records. Keep
            # the explicit input map for add_loft's planar public dispatch.
            params = copy.deepcopy(requested)
        if not isinstance(params, dict):
            raise ValueError("Preview did not return explicit authored parameters")
        expected = requested["correspondences"]
        expected_pairs = {pair["id"]: pair for pair in expected}
        actual_pairs = params["correspondences"]
        if [pair["id"] for pair in actual_pairs] != [pair["id"] for pair in expected]:
            raise ValueError("Preview changed authored correspondence identity or order")
        if params.get("seam_patch_id") != requested["seam_patch_id"]:
            raise ValueError("Preview changed authored seam")
        issued = [pair["id"] for pair in actual_pairs]
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
            if not planar_without_loft:
                ruling = pair.get("ruling_id")
                if not _is_uuid(ruling) or (
                    original.get("ruling_id") is not None and ruling != original["ruling_id"]
                ):
                    raise ValueError("Preview lost or replaced a persistent ruling identity")
                issued.append(ruling)
        if not planar_without_loft:
            end = params.get("end_ruling_id")
            if not _is_uuid(end) or (
                requested.get("end_ruling_id") is not None and end != requested["end_ruling_id"]
            ):
                raise ValueError("Preview lost or replaced the end ruling identity")
            issued.append(end)
            if len(set(issued)) != len(issued):
                raise ValueError("Preview assigned duplicate persistent identities")
        for key in ("second_profile_id", "tolerance_mm", "max_segments"):
            if key in params and params[key] != requested[key]:
                raise ValueError("Preview changed explicit source or computation parameters")
        staged_parameters = {
            "first_profile_id": request["parameters"]["first_profile_id"],
            "second_profile_id": request["parameters"]["second_profile_id"],
            **{
                key: copy.deepcopy(params[key] if key in params else request["parameters"].get(key))
                for key in _APPLY_KEYS
                if key in params or key in request["parameters"]
            },
        }
        by_id = {row["id"]: row for row in self.pair_rows}
        adoptions = [
            (by_id[pair["id"]], pair["ruling_id"])
            for pair in staged_parameters["correspondences"]
            if pair.get("ruling_id")
        ]
        status = candidate["status"]
        family = candidate.get("family", "")
        message = candidate.get(
            "message", "Návrh je připravený k vytvoření." if status == "EXACT" else ""
        )
        if not isinstance(family, str) or not isinstance(message, str):
            raise ValueError("Preview presentation fields must be plain text")
        if status == "EXACT":
            kind = (
                "Rovinný pás"
                if family in ("PLANAR_REGION", "CONCENTRIC_PLANAR_ARC_BAND")
                else "Plocha mezi profily"
            )
            feedback = kind + " · přesný režim s doloženou numerickou mezí. " + message
        else:
            feedback = (
                (
                    "Přesný rozvin byl odmítnut. "
                    if status == "REJECTED"
                    else "Přesný rozvin není doložený. "
                )
                + message
                + " Opravte profily či jejich párování, nebo výslovně uchovejte "
                "jen konstrukční cíl bez tiskového dílu."
            )
        published = copy.deepcopy(candidate)
        # Staging, text construction and copies must all succeed BEFORE any
        # draft identity changes or a successful preview becomes observable.
        self.preview_result = candidate
        self._parameters_for_apply = staged_parameters
        self._end_ruling_id = staged_parameters.get("end_ruling_id")
        for row, ruling_id in adoptions:
            row["ruling_id"] = ruling_id
        self._result_digest = request["fingerprint"]
        self.feedback.setText(feedback)
        self.keep_target.setVisible(status != "EXACT")
        self.preview_changed.emit(published)

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
            if self._edit_mode and self._structural_error():
                self.load_error = {
                    "code": "LOFT_SOURCE_SEGMENT_MISSING",
                    "message": self._structural_error(),
                }
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

    def check_source(self, project):
        """Fence both creation and host-owned update commands after acceptance."""
        if self.result() != QDialog.DialogCode.Accepted or self.result_parameters is None:
            raise ValueError("Nejprve potvrďte aktuální náhled plochy.")
        if not _matches(project, self._accepted_digest):
            raise ValueError("Projekt se od potvrzení změnil. Otevřete nový náhled plochy.")
        return True

    def apply(self, project):
        """Create inside one host undo command; updates use check_source first."""
        self.check_source(project)
        if self._edit_mode:
            raise ValueError("Existující plochu upravte veřejným příkazem pro aktualizaci.")
        params = copy.deepcopy(self.result_parameters)
        first, second = params.pop("first_profile_id"), params.pop("second_profile_id")
        return project.add_loft(
            first, second, **{key: params[key] for key in _APPLY_KEYS if key in params}
        )
