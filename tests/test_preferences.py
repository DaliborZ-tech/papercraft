"""Testy pro preferences/settings.py — systém předvoleb."""

import json
import tempfile
from pathlib import Path

import pytest

from archpapercraft.preferences.settings import (
    Preferences,
    GeneralSettings,
    ViewportSettings,
    SnapPreferences,
    ExportSettings,
    KeyboardShortcuts,
)


class TestGeneralSettings:
    def test_defaults(self):
        gs = GeneralSettings()
        assert gs.language == "cs"
        assert gs.default_units == "mm"
        assert gs.theme == "system"
        assert gs.autosave_interval_sec == 120
        assert gs.max_undo_depth == 200


class TestPreferences:
    def test_roundtrip(self):
        prefs = Preferences()
        prefs.general.language = "en"
        prefs.general.theme = "light"
        prefs.export.default_format = "svg"

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            prefs.save(path)
            assert path.exists()

            loaded = Preferences.load(path)
            assert loaded.general.language == "en"
            assert loaded.general.theme == "light"
            assert loaded.export.default_format == "svg"

    def test_reset(self):
        prefs = Preferences()
        prefs.general.language = "en"
        prefs = Preferences.reset()
        assert prefs.general.language == "cs"

    def test_load_missing_file(self):
        prefs = Preferences.load(Path("/nonexistent/path/settings.json"))
        assert prefs.general.language == "cs"  # výchozí hodnoty

    def test_load_corrupt_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text("not json", encoding="utf-8")
            prefs = Preferences.load(path)
            assert prefs.general.language == "cs"


class TestExportSettings:
    def test_paper_size(self):
        es = ExportSettings()
        assert es.default_paper == "A4"
        assert es.png_dpi == 150

    def test_tab_shape(self):
        es = ExportSettings()
        assert es.tab_shape == "tapered"


class TestKeyboardShortcuts:
    def test_defaults(self):
        ks = KeyboardShortcuts()
        assert ks.undo == "Ctrl+Z"
        assert ks.redo == "Ctrl+Y"
        assert ks.save_project == "Ctrl+S"
