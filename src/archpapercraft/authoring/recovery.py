"""Separate atomic recovery drafts; never a writer for the user's project file."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

RECOVERY_APPLICATION = "ArchPapercraft Studio Recovery"


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("Koncept obsahuje opakovaný klíč.")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("Koncept obsahuje neplatné číslo.")


class RecoveryStore:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()

    def path(self, session_id):
        identifier = str(UUID(str(session_id)))
        return self.directory / (identifier + ".recovery.json")

    def _owned_path(self, path):
        value = Path(path)
        if value.resolve().parent != self.directory or not value.name.endswith(".recovery.json"):
            raise ValueError("Koncept není v adresáři pro obnovu.")
        identifier = UUID(value.name.removesuffix(".recovery.json"))
        if value.name != str(identifier) + ".recovery.json":
            raise ValueError("Soubor nemá název vlastního konceptu.")
        return value.resolve()

    def candidates(self):
        if not self.directory.is_dir():
            return []
        values = []
        for path in self.directory.glob("*.recovery.json"):
            try:
                self._owned_path(path)
                values.append((path.stat().st_mtime, path))
            except (OSError, ValueError):
                continue
        return [path for _, path in sorted(values, reverse=True)]

    def read(self, path):
        data = json.loads(self._owned_path(path).read_text("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant)
        if (not isinstance(data, dict) or data.get("application") != RECOVERY_APPLICATION
                or type(data.get("recovery_version")) is not int
                or data["recovery_version"] != 1 or not isinstance(data.get("document"), dict)
                or not isinstance(data.get("ui_draft"), dict)
                or data.get("original_path") is not None
                and not isinstance(data["original_path"], str)
                or not isinstance(data.get("saved_at"), str)):
            raise ValueError("Tento koncept nelze bezpečně načíst.")
        return data

    def write(self, session_id, document, ui_draft, original_path=None):
        envelope = {
            "application": RECOVERY_APPLICATION,
            "recovery_version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "original_path": str(Path(original_path).resolve()) if original_path else None,
            "document": document,
            "ui_draft": ui_draft,
        }
        # Serialize first: even a malformed/nonfinite candidate cannot truncate the old draft.
        content = json.dumps(envelope, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._owned_path(self.path(session_id))
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(prefix=".recovery-", suffix=".tmp",
                                                      dir=self.directory)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
        return target

    def discard(self, path):
        self._owned_path(path).unlink(missing_ok=True)
