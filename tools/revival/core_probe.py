"""Run a focused core subset with Qt imports prohibited, and red diagnostics separately."""
import importlib.abc
import json
import os
from pathlib import Path
import sys
import pytest

os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'

class NoQt(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('PySide6','PyQt6','PyQt5'):
            raise ImportError('Qt prohibited by pure-core diagnostic harness')
        return None

sys.meta_path.insert(0,NoQt())
root = Path(__file__).resolve().parents[2]
os.chdir(root)
core_code = pytest.main(['tests/test_core_geometry.py','tests/test_unfolder.py','tests/test_seam_graph.py','tests/test_units.py','-ra','--junitxml=docs/revival/evidence/core-only.xml'])
diagnostic_code = pytest.main(['tools/revival/test_diagnostic_contracts.py','-ra','--junitxml=docs/revival/evidence/diagnostic-contracts.xml'])
(root/'docs/revival/evidence/core-results.json').write_text(json.dumps(dict(core_exit=int(core_code),diagnostic_exit=int(diagnostic_code),qt_imports_prohibited=True),indent=2),encoding='utf-8')
raise SystemExit(core_code)
