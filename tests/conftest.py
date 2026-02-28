"""Konfigurace testovacího prostředí.

Přidá ``src/`` do sys.path, aby testy fungovaly i bez ``pip install -e .``.
Toto je záložní řešení — primárně se path nastavuje přes ``pyproject.toml``
(``pythonpath = ["src"]``), ale conftest zajistí kompatibilitu i se staršími
verzemi pytestu.

Navíc registruje markery ``core`` a ``ui`` — spusťte ``pytest -m 'not ui'``
pro core-only testy bez PySide6.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def pytest_collection_modifyitems(config, items):
    """Automaticky přidá marker ``ui`` testům, které importují PySide6."""
    ui_marker = pytest.mark.ui
    core_marker = pytest.mark.core

    ui_test_files = {
        "test_snap",
        "test_node_enhanced",  # Some enhanced tests may touch visibility/UI helpers
    }

    for item in items:
        module_name = item.module.__name__ if item.module else ""
        # Check if the test file name matches known UI tests
        is_ui = any(name in module_name for name in ui_test_files)
        if is_ui:
            item.add_marker(ui_marker)
        else:
            item.add_marker(core_marker)
