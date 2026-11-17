"""Atomic author commands and content-based save points, independent of Qt."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from archpapercraft.authoring import AuthorProject, load_project


class AuthorController:
    def __init__(self, on_change=None):
        self.project = None
        self.file_path = None
        self.copy_source_path = None
        self.on_change = on_change or (lambda: None)
        self.on_document_event = lambda _event: None
        self.before_document_replace = lambda: True
        self._undo, self._redo = [], []
        self._saved_digest = None
        self.recovered = False

    @staticmethod
    def digest(state):
        return hashlib.sha256(
            json.dumps(state, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
        ).hexdigest()

    @property
    def dirty(self):
        return (
            self.project is not None and self.digest(self.project.to_dict()) != self._saved_digest
        )

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def new(self, name="Nový model", scale=0.01):
        project = AuthorProject.new(name=name, scale=scale)
        if not self.before_document_replace():
            return None
        self.project = project
        self.file_path = None
        self.copy_source_path = None
        self.recovered = False
        self._undo.clear()
        self._redo.clear()
        self._saved_digest = self.digest(self.project.to_dict())
        self.on_change()
        self.on_document_event("replaced")

    def open(self, path):
        loaded = load_project(path)
        if not isinstance(loaded, AuthorProject):
            return loaded
        if not self.before_document_replace():
            return None
        self.project = loaded
        self.copy_source_path = Path(path) if loaded.requires_save_as else None
        self.file_path = None if self.copy_source_path else Path(path)
        self.recovered = False
        self._undo.clear()
        self._redo.clear()
        self._saved_digest = self.digest(loaded.to_dict())
        self.on_change()
        self.on_document_event("replaced")
        return loaded

    def save(self, path=None):
        if self.project is None:
            raise ValueError("Nejprve vytvořte projekt.")
        target = Path(path) if path else self.file_path
        if target is None:
            raise ValueError("Vyberte umístění projektu.")
        if self.copy_source_path and target.resolve() == self.copy_source_path.resolve():
            raise ValueError("Původní projekt zůstává beze změny. Uložte kopii pod novým názvem.")
        self.project.save(target)
        self.file_path = target
        self.copy_source_path = None
        self.recovered = False
        self._saved_digest = self.digest(self.project.to_dict())
        self.on_change()
        self.on_document_event("saved")
        return target

    def restore_recovery(self, state, original_path=None):
        # Parse completely before replacing any live work. Recovery is an unsaved
        # copy, so Ctrl+S must ask for a new path and retain the source-file guard.
        recovered = AuthorProject.from_dict(state)
        self.project = recovered
        self.file_path = None
        self.copy_source_path = Path(original_path) if original_path else None
        self._saved_digest = None
        self._undo.clear()
        self._redo.clear()
        self.recovered = True
        self.on_change()

    def execute(self, description, operation, *, recompute=False):
        if self.project is None:
            raise ValueError("Nejprve vytvořte projekt.")
        before = copy.deepcopy(self.project.to_dict())
        try:
            result = operation(self.project)
            if recompute:
                self.project.recompute()
            self.project.validate()
            after = copy.deepcopy(self.project.to_dict())
        except Exception:
            self.project = AuthorProject.from_dict(before)
            self.on_change()
            raise
        if before != after:
            self._undo.append((description, before, after))
            self._undo = self._undo[-200:]
            self._redo.clear()
        self.on_change()
        return result

    def recompute(self):
        self.execute("Přepočítat díly", lambda p: p.recompute())

    def _restore(self, state):
        self.project = AuthorProject.from_dict(copy.deepcopy(state))

    def undo(self):
        if self._undo:
            entry = self._undo.pop()
            self._restore(entry[1])
            self._redo.append(entry)
            self.on_change()

    def redo(self):
        if self._redo:
            entry = self._redo.pop()
            self._restore(entry[2])
            self._undo.append(entry)
            self.on_change()
