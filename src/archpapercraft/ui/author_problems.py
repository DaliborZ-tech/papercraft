"""Actionable, grouped authoring problems without changing validation evidence."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def _group_key(issue):
    # Acknowledging one warning must never acknowledge another member or hide
    # an outstanding error. Keep each original issue ID and digest untouched.
    return issue.code, issue.message, issue.severity, issue.acknowledged


def _priority(issue):
    if issue.acknowledged:
        return 4
    if issue.severity.lower() == "error":
        return {"STALE": 1, "UNPLACED": 2}.get(issue.code, 0)
    return 3


def _group_text(members):
    first, count = members[0], len(members)
    if first.code == "UNPLACED":
        return ("1 díl čeká na umístění" if count == 1 else
                f"{count} díly čekají na umístění" if count < 5 else
                f"{count} dílů čeká na umístění")
    if first.code == "STALE":
        return ("1 díl potřebuje přepočet" if count == 1 else
                f"{count} díly potřebují přepočet" if count < 5 else
                f"{count} dílů potřebuje přepočet")
    prefix = "Přijato · " if first.acknowledged else ""
    return prefix + (f"{count}× " if count > 1 else "") + first.message


class AuthorProblemsPanel(QWidget):
    """One compact readiness summary, expandable details and direct navigation.

    The host retains its existing canonical ``select_issue`` and acknowledge
    commands through ``issues`` and ``ack_button``. ``action_requested`` asks
    the host to invoke its regular guarded QAction, never a domain shortcut.
    """

    action_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("authorProblems")
        self._groups = []
        self._issues_by_id = {}
        self._part_names = {}
        self._has_parts = False
        self._updating = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)
        row = QHBoxLayout()
        self.summary = QLabel("Vytvořte svůj první díl.")
        self.summary.setWordWrap(True)
        self.summary.setAccessibleName("Připravenost modelu")
        row.addWidget(self.summary, 1)
        self.primary = QPushButton("Vytvořit první díl")
        self.primary.clicked.connect(self._activate)
        row.addWidget(self.primary)
        self.details = QToolButton()
        self.details.setText("Podrobnosti")
        self.details.setCheckable(True)
        self.details.toggled.connect(self._show_details)
        row.addWidget(self.details)
        layout.addLayout(row)
        self.issues = QListWidget()
        self.issues.setAccessibleName("Problémy a dotčené díly")
        self.issues.setMinimumHeight(48)
        self.issues.setMaximumHeight(130)
        self.issues.currentItemChanged.connect(self._selection_changed)
        layout.addWidget(self.issues)
        controls = QHBoxLayout()
        self.next_part = QPushButton("Další dotčený díl")
        self.next_part.clicked.connect(self._next_member)
        controls.addWidget(self.next_part)
        controls.addStretch(1)
        self.ack_button = QPushButton("Přijmout vybrané varování pro tento stav")
        self.ack_button.setEnabled(False)
        controls.addWidget(self.ack_button)
        self.detail_controls = QWidget()
        self.detail_controls.setLayout(controls)
        layout.addWidget(self.detail_controls)
        self._show_details(False)

    def set_issues(self, issues, project):
        """Present the supplied canonical results; perform no new validation."""
        previous = self.issues.currentItem()
        previous_id = previous.data(Qt.ItemDataRole.UserRole) if previous else None
        grouped = {}
        for issue in issues:
            grouped.setdefault(_group_key(issue), []).append(issue)
        self._groups = sorted(grouped.values(), key=lambda group: _priority(group[0]))
        self._issues_by_id = {issue.id: issue for group in self._groups for issue in group}
        self._part_names = ({pid: part.name for pid, part in project.parts.items()}
                            if project else {})
        try:
            self._has_parts = bool(project and project.material_part_ids())
        except (KeyError, ValueError, AttributeError):
            # An INVALID_PROJECT result must remain displayable even when its
            # broken reference prevents computing the printable material view.
            self._has_parts = False
        self._updating = True
        try:
            with QSignalBlocker(self.issues):
                self.issues.clear()
                for members in self._groups:
                    item = QListWidgetItem(_group_text(members))
                    selected = next((i for i in members if i.id == previous_id), members[0])
                    item.setData(Qt.ItemDataRole.UserRole, selected.id)
                    item.setToolTip(self._member_description(members, selected))
                    self.issues.addItem(item)
                    if selected.id == previous_id:
                        self.issues.setCurrentItem(item)
        finally:
            self._updating = False
        pending = [group for group in self._groups if not group[0].acknowledged]
        if pending:
            self.summary.setText(" · ".join(_group_text(group) for group in pending[:2]) +
                                 (f" · +{len(pending)-2} další" if len(pending) > 2 else ""))
        elif self._has_parts:
            self.summary.setText("Kontrola dokončena. Model je připraven k exportu.")
        else:
            self.summary.setText("Vytvořte svůj první díl.")
        self.details.setEnabled(bool(self._groups))
        self._selection_changed()

    def _members(self):
        item = self.issues.currentItem()
        if item is None:
            return []
        identity = item.data(Qt.ItemDataRole.UserRole)
        return next((group for group in self._groups if any(i.id == identity for i in group)), [])

    def _member_description(self, members, selected):
        names = [self._part_names.get(pid, "Díl") for issue in members for pid in issue.part_ids]
        return ("Dotčené díly: " + ", ".join(dict.fromkeys(names)) + "\n" if names else "") + (
            selected.message
        )

    def _selection_changed(self, *_args):
        if self._updating:
            return
        item = self.issues.currentItem()
        selected = self._issues_by_id.get(item.data(Qt.ItemDataRole.UserRole)) if item else None
        pending = next((group[0] for group in self._groups if not group[0].acknowledged), None)
        target = selected if selected and not selected.acknowledged else pending
        self.primary.setText(
            "Umístit díly na stránky" if target and target.code == "UNPLACED" else
            "Přepočítat papírové díly" if target and target.code == "STALE" else
            "Zkontrolovat varování" if target and target.severity.lower() == "warning" else
            "Přejít k nápravě" if target else
            "Export SVG/PDF" if self._has_parts else "Vytvořit první díl"
        )
        self.next_part.setEnabled(len(self._members()) > 1)

    def _activate(self):
        item = self.issues.currentItem()
        selected = self._issues_by_id.get(item.data(Qt.ItemDataRole.UserRole)) if item else None
        if selected is None or selected.acknowledged:
            index = next((n for n, group in enumerate(self._groups)
                          if not group[0].acknowledged), None)
            if index is not None:
                self.issues.setCurrentRow(index)
                item = self.issues.currentItem()
                selected = self._issues_by_id[item.data(Qt.ItemDataRole.UserRole)]
        if selected and not selected.acknowledged:
            if selected.severity.lower() == "warning":
                # Review and the explicit per-issue accept command must be
                # visible at the destination, rather than another hidden step.
                self.show_problems()
            self.issues.itemActivated.emit(item)
            if selected.code == "STALE":
                self.action_requested.emit("recompute")
        else:
            self.action_requested.emit("export" if self._has_parts else "draw")

    def _next_member(self):
        members, item = self._members(), self.issues.currentItem()
        if len(members) < 2 or item is None:
            return
        current = next(n for n, issue in enumerate(members)
                       if issue.id == item.data(Qt.ItemDataRole.UserRole))
        selected = members[(current+1) % len(members)]
        item.setData(Qt.ItemDataRole.UserRole, selected.id)
        item.setToolTip(self._member_description(members, selected))
        self.issues.itemActivated.emit(item)
        self.issues.currentItemChanged.emit(item, item)

    def _show_details(self, visible):
        self.issues.setVisible(visible)
        self.detail_controls.setVisible(visible)
        self.details.setText("Skrýt podrobnosti" if visible else "Podrobnosti")

    def show_problems(self):
        """Keyboard/menu entry to the same visible, individually navigable list."""
        self.details.setChecked(True)
        if self.issues.currentItem() is None and self.issues.count():
            self.issues.setCurrentRow(0)
        self.issues.setFocus()
