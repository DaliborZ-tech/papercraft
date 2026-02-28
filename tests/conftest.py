"""Konfigurace testovacího prostředí.

Přidá ``src/`` do sys.path, aby testy fungovaly i bez ``pip install -e .``.
Toto je záložní řešení — primárně se path nastavuje přes ``pyproject.toml``
(``pythonpath = ["src"]``), ale conftest zajistí kompatibilitu i se staršími
verzemi pytestu.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
