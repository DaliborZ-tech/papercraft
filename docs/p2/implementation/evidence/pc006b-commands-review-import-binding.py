"""Fresh-process import binding oracle; never starts QApplication or desktop."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(r'C:\Users\dalib\projects\papercraft-bend-integration')
DRIVER = ROOT/'tools/authoring/desktop_b_proof.py'


def child(mode):
    import sys
    sys.path.insert(0, str(DRIVER.parent))
    if mode in ('baseline', 'cached-mismatch'):
        from archpapercraft.ui import author_window
        baseline = str(Path(author_window.__file__).resolve())
        if mode == 'baseline':
            assert 'papercraft\\src' in baseline
            return {'actual_module': baseline}
    tree = ast.parse(DRIVER.read_text(encoding='utf8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_windows')
    prefix = []
    for statement in function.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'sha' for t in statement.targets):
            break
        prefix.append(statement)
    block = ast.fix_missing_locations(ast.Module(body=prefix, type_ignores=[]))
    namespace = {'ROOT': ROOT, 'sys': sys, 'Path': Path}
    try:
        exec(compile(block, str(DRIVER), 'exec'), namespace)
    except ValueError as exc:
        assert mode == 'cached-mismatch' and 'outside the pinned worktree' in str(exc)
        return {'status': 'REJECTED_BEFORE_GUI_OR_OUTPUT', 'error': str(exc), 'cached_module': baseline}
    assert mode == 'bound'
    actual = Path(namespace['author_window'].__file__).resolve()
    expected = (ROOT/'src/archpapercraft/ui/author_window.py').resolve()
    assert actual == expected
    own_modules = {name: str(Path(module.__file__).resolve())
                   for name, module in sys.modules.items()
                   if name.startswith('archpapercraft') and getattr(module, '__file__', None)}
    assert all(Path(value).is_relative_to(ROOT/'src') for value in own_modules.values())
    return {'actual_module': str(actual), 'application_modules_loaded': len(own_modules), 'all_loaded_application_modules_in_worktree': True}


def dirty_guard_cases():
    tree = ast.parse(DRIVER.read_text(encoding='utf8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_windows')
    body, started = [], False
    for statement in fn.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'hashes' for t in statement.targets):
            started = True
        if started:
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Attribute) and statement.value.func.attr == 'mkdir':
                break
            body.append(statement)
    assert any(isinstance(n, ast.If) for n in body)
    code = compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(DRIVER), 'exec')
    results = {}
    for name, changed, hashes, tracked, expected in [
        ('clean', '', {'src/own.py': 'a'}, 'src/own.py', 'ACCEPTED'),
        ('modified-tracked', 'src/own.py', {'src/own.py': 'b'}, 'src/own.py', 'REJECTED'),
        ('staged-tracked', 'src/own.py', {'src/own.py': 'b'}, 'src/own.py', 'REJECTED'),
        ('untracked-covered', '', {'src/own.py': 'a', 'src/new.py': 'b'}, 'src/own.py', 'REJECTED'),
        ('untracked-doc-outside-coverage', '', {'src/own.py': 'a'}, 'src/own.py', 'ACCEPTED'),
    ]:
        def git(*args):
            return changed if args[0] == 'diff' else tracked
        namespace = {'git': git, 'source_files': lambda: hashes}
        try:
            exec(code, namespace)
            actual = 'ACCEPTED'
        except ValueError as exc:
            assert 'committed application and harness sources' in str(exc)
            actual = 'REJECTED'
        assert actual == expected
        results[name] = actual
    return results


if __name__ == '__main__':
    if len(sys.argv) == 2:
        print(json.dumps(child(sys.argv[1])))
    else:
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        results = {}
        for mode in ('baseline', 'bound', 'cached-mismatch'):
            run = subprocess.run([sys.executable, str(Path(__file__).resolve()), mode], cwd=ROOT/'tools/authoring', env=env, text=True, capture_output=True)
            results[mode] = {'returncode': run.returncode, 'stdout': run.stdout.strip(), 'stderr': run.stderr.strip()}
        payload = {'driver_sha256': hashlib.sha256(DRIVER.read_bytes()).hexdigest(), 'cases': results,
                   'dirty_guard_ast_cases': dirty_guard_cases(),
                   'evidence_kind': 'fresh_subprocess_imports_only_no_GUI', 'native': 'NOT_RUN',
                   'verdict': 'PASS' if all(r['returncode'] == 0 for r in results.values()) else 'FAIL'}
        Path(__file__).with_suffix('.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(payload['verdict'] != 'PASS')
