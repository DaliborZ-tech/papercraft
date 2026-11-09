"""Run review against exact Git module snapshot without disturbing shared edits."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
import archpapercraft.authoring.curves

PIN='55c4443d40beb36c83d26f8ae940b987c4facf9c'
name='archpapercraft.authoring.curve_topology'
path='src/archpapercraft/authoring/curve_topology.py'
source=subprocess.check_output(['git','show',f'{PIN}:{path}'],cwd=ROOT)
module=types.ModuleType(name)
module.__file__=f'git:{PIN}:{path}'
module.__package__='archpapercraft.authoring'
sys.modules[name]=module
exec(compile(source,module.__file__,'exec'),module.__dict__)
Path(__file__).with_suffix('.json').write_text(json.dumps({
    'source_sha':PIN,'module_source_sha256':hashlib.sha256(source).hexdigest(),
    'method':'exact_git_blob_in_fresh_process_no_worktree_mutation',
    'runtime_curves_module':archpapercraft.authoring.curves.__file__,
},indent=2)+'\n',encoding='utf8')
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
