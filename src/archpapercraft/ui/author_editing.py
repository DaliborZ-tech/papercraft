"""Small author dialogs; the host commits pending input and owns one undo command."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from archpapercraft.authoring.editing import (
    delete_material_part,
    part_deletion_impact,
    rename_author_entities,
)
from archpapercraft.authoring.errors import ValidationError


def _label(text):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


def _surface_title(surface):
    return f"{surface['name']} (P{surface['part']['number']})"


class DeletePartDialog(QDialog):
    def __init__(self, project, part_id, parent=None):
        super().__init__(parent)
        self.impact = part_deletion_impact(project, part_id)
        self.part_id = part_id
        self.setWindowTitle("Odstranit papírový díl")
        self.resize(560, 470)
        layout = QVBoxLayout(self)
        part = self.impact["part"]
        layout.addWidget(_label(f"Odstranit celý díl P{part['number']}: {part['name']}?"))
        lines = ["Plochy tohoto dílu:"]
        lines.extend(
            f"  {i}. {_surface_title(s)}" for i, s in enumerate(self.impact["surfaces"], 1)
        )
        lines.append("\nSpoje, které se odstraní s dílem:")
        for key, prefix in (("joints", "J"), ("attachments", "A")):
            for relation in self.impact[key]:
                a, b = relation["surfaces"]
                lines.append(
                    f"  {prefix}{relation['number']}: {_surface_title(a)} ↔ {_surface_title(b)}"
                )
        if not self.impact["joints"] and not self.impact["attachments"]:
            lines.append("  Žádné spoje s další plochou.")
        lines.append(f"\nOdstraněné spojovací prvky s chlopněmi: {len(self.impact['connectors'])}.")
        if self.impact["affected_parts"]:
            lines.append("\nTyto protikusy zůstanou na svých stránkách:")
            lines.extend(f"  P{p['number']}: {p['name']}" for p in self.impact["affected_parts"])
        lines.append("\nZachované obrysové profily (znovu použitelné skici):")
        lines.extend(f"  {p['name']}" for p in self.impact["preserved_profiles"])
        self.details = QPlainTextEdit("\n".join(lines))
        self.details.setReadOnly(True)
        self.details.setObjectName("delete_part_impact")
        layout.addWidget(self.details, 1)
        layout.addWidget(
            _label(
                "Původní profily zůstanou v projektu. Polohy a zámky ostatních dílů "
                "se nezmění. Jejich značení spojů aktualizujete příkazem Přepočítat díly. "
                "Celé odstranění lze vrátit příkazem Vrátit změnu."
            )
        )
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Odstranit celý díl")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Zachovat díl")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def apply(self, project):
        if self.result() != QDialog.DialogCode.Accepted:
            raise ValidationError("Odstranění dílu nebylo potvrzeno.")
        if part_deletion_impact(project, self.part_id) != self.impact:
            raise ValidationError(
                "Projekt se od náhledu změnil. Znovu otevřete přehled odstranění."
            )
        return delete_material_part(project, self.part_id)


class RenameDialog(QDialog):
    def __init__(self, project, *, surface_id=None, part_id=None, parent=None):
        super().__init__(parent)
        self.project_id = project.project_id
        self.surface_id, self.part_id = surface_id, part_id
        self.source = copy.deepcopy(project)
        self.changes = None
        self.setWindowTitle("Pojmenovat model a díl")
        layout = QVBoxLayout(self)
        layout.addWidget(
            _label(
                "Srozumitelné vlastní názvy vám pomohou vybrat plochu a její protikus. "
                "Čísla dílů, konstrukce a rozmístění zůstanou zachované."
            )
        )
        form = QFormLayout()
        layout.addLayout(form)
        self.project_name = QLineEdit(project.name)
        self.project_name.setObjectName("rename_project")
        form.addRow(_label("Model"), self.project_name)
        self.surface_name, self.part_name = None, None
        if surface_id is not None:
            if surface_id not in project.surfaces:
                raise ValidationError("Vybraná plocha už v projektu není.")
            self.surface_name = QLineEdit(project.surfaces[surface_id].name)
            self.surface_name.setObjectName("rename_surface")
            form.addRow(_label("Vybraná plocha"), self.surface_name)
        if part_id is not None:
            if part_id not in project.parts:
                raise ValidationError("Vybraný papírový díl už v projektu není.")
            self.part_name = QLineEdit(project.parts[part_id].name)
            self.part_name.setObjectName("rename_part")
            form.addRow(_label(f"Papírový díl P{project.parts[part_id].number}"), self.part_name)
        self.status = _label("")
        layout.addWidget(self.status)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Použít názvy")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for field in (self.project_name, self.surface_name, self.part_name):
            if field is not None:
                field.textChanged.connect(self.validate_names)
        self.validate_names()

    def proposed_changes(self):
        result = {}
        if self.project_name.text() != self.source.name:
            result["project_name"] = self.project_name.text()
        if (
            self.surface_name is not None
            and self.surface_name.text() != self.source.surfaces[self.surface_id].name
        ):
            result.update(surface_id=self.surface_id, surface_name=self.surface_name.text())
        if (
            self.part_name is not None
            and self.part_name.text() != self.source.parts[self.part_id].name
        ):
            result.update(part_id=self.part_id, part_name=self.part_name.text())
        return result

    def validate_names(self, *_args):
        try:
            clone = copy.deepcopy(self.source)
            rename_author_entities(clone, **self.proposed_changes())
            self.status.setText("Popisky na papíře aktualizujete příkazem Přepočítat díly.")
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            return True
        except ValidationError as exc:
            self.status.setText(str(exc))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return False

    def accept(self):
        if self.validate_names():
            self.changes = self.proposed_changes()
            super().accept()

    def apply(self, project):
        if (
            self.result() != QDialog.DialogCode.Accepted
            or project.project_id != self.project_id
            or self.changes is None
        ):
            raise ValidationError("Názvy nejsou potvrzené pro tento projekt.")
        return rename_author_entities(project, **self.changes)
