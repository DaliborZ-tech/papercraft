"""Independent arithmetic/contract review; never a P2 implementation test."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
REVIEW_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
BASE = '42b3d80158fda64af39a99416f2b5e52be2bc72a'
CODE = '95be72c6de6665b98efd10c58dae941f3b91fe83'
started = time.perf_counter()


def git(*args):
    return subprocess.run(['git', *args], cwd=REVIEW_ROOT, capture_output=True, text=True, encoding='utf-8')


assert git('rev-parse', 'HEAD').stdout.strip() == CODE
assert git('merge-base', '--is-ancestor', BASE, CODE).returncode == 0
cosine, sine = math.sqrt(3) / 2, 0.5


def page(point, anchor=(60.0, 60.0)):
    x, y = point
    return [anchor[0] + cosine * x - sine * y,
            anchor[1] + sine * x + cosine * y]


def outline(slope, anchor=(60.0, 60.0)):
    return [page(p, anchor) for p in [(0, 0), (100, 0), (100, 40 + slope), (0, 40 + slope)]]


def bounds(points):
    return [[min(p[i] for p in points) for i in (0, 1)],
            [max(p[i] for p in points) for i in (0, 1)]]


old_slope = math.hypot(30, 30)
new_slope = math.hypot(30, 35)
assert abs(old_slope - 42.426406871) < 1e-9
assert abs(new_slope - 46.097722286) < 1e-9
wall = [page(p) for p in [(0, 0), (100, 0), (100, 40), (0, 40)]]
expected = [[60, 60], [146.602540378, 110], [126.602540378, 144.641016151], [40, 94.641016151]]
assert max(math.dist(a, b) for a, b in zip(wall, expected)) < 1e-9
old_bounds, new_bounds = bounds(outline(old_slope)), bounds(outline(new_slope))
assert all(0 <= p[0] <= 210 and 0 <= p[1] <= 297 for p in outline(new_slope))
old_negative = bounds(outline(old_slope, (30, 60)))
new_negative = bounds(outline(new_slope, (30, 60)))
assert old_negative[0][0] < 0 and new_negative[0][0] < 0

# Intersection of a roof rectangle [0,100] x [40,40+s] with
# the separate material rectangle [10,20] x [84,85]. A rigid rotation
# has determinant one, so its area is unchanged on the page.
def overlap_area(slope):
    return max(0.0, min(100, 20) - max(0, 10)) * max(0.0, min(40 + slope, 85) - max(40, 84))


assert overlap_area(old_slope) == 0
assert overlap_area(new_slope) == 10
old_dependency = page((0, 40 + 2 * old_slope))
new_dependency = page((0, 40 + 2 * new_slope))
assert math.dist(old_dependency, new_dependency) > 7

q = json.loads(git('show', CODE + ':05_WORK_QUEUE.json').stdout)
assert q['product_gate']['contract_version'] == '1.1'
assert q['product_gate']['status'] == 'PO_PENDING'
assert not q['product_gate']['accepted_by_owner']
assert all(not t['execution_authorized_on_realization'] for t in q['tickets'] if t['stage'] not in ('P0', 'P1'))
tickets = {t['id']: t for t in q['tickets']}
assert tickets['PC-008']['mixed_part_layout_contract']['anchor_page_mm'] == [60, 60]
assert tickets['PC-008']['mixed_part_layout_contract']['verification_status'] == 'NOT_RUN'
assert tickets['PC-009']['mixed_part_export_check']['status'] == 'NOT_RUN'
assert tickets['PC-007']['join_preserves_receiving_part_anchor'] is True
assert tickets['PC-006']['paper_frame_schema_contract'].endswith('MIXED_PART_LAYOUT_CONTRACT.md')
for ticket in q['tickets']:
    if ticket['stage'] == 'P2':
        assert all(value == 'NOT_RUN' for value in ticket['acceptance_state'].values())
assert tickets['PC-006']['estimate_refresh_required']['when'] == 'after_PC-006_before_PC-007'
assert q['estimate_policy']['agent_runtime_estimate'] is False
assert q['estimate_policy']['unit'] == 'person_days'
text = git('show', CODE + ':docs/revival/MIXED_PART_LAYOUT_CONTRACT.md').stdout
for token in ['root_surface_id', 'anchor_vertex_id', 'axis_edge_id', 'ANCHOR_UNRESOLVED',
              'kompletní export je blokován', 'Žádný fallback', 'lineage', 'undo',
              'dotčená závislostí', 'přijímající díl', '**NOT_RUN**']:
    assert token in text, token
assert not git('diff', BASE + '..' + CODE, '--', 'src', 'tests', 'pyproject.toml').stdout
assert git('diff', '--check', BASE + '..' + CODE).returncode == 0
validation = subprocess.run([sys.executable, 'tools/revival/validate_delivery.py'], cwd=REVIEW_ROOT,
                            capture_output=True, text=True, encoding='utf-8')
assert validation.returncode == 0
result = {
    'base_sha': BASE, 'code_sha': CODE, 'seconds': round(time.perf_counter() - started, 3),
    'review_worktree': str(REVIEW_ROOT),
    'proof_kind': 'independent arithmetic and static contract checks only',
    'p2_implementation_verification': 'NOT_RUN',
    'slopes_mm': [old_slope, new_slope], 'wall_corners_page_mm': wall,
    'old_bounds_without_tabs_mm': old_bounds, 'new_bounds_without_tabs_mm': new_bounds,
    'positive_fixture_inside_A4': True,
    'old_anchor_30_bounds_mm': old_negative, 'new_anchor_30_bounds_mm': new_negative,
    'negative_fixture_overflows_both_times': True,
    'collision_area_without_top_tabs_mm2': [overlap_area(old_slope), overlap_area(new_slope)],
    'bbox_min_delta_mm': [new_bounds[0][i] - old_bounds[0][i] for i in (0, 1)],
    'dependency_wall_reference_before_mm': old_dependency,
    'dependency_wall_reference_after_mm': new_dependency,
    'dependency_wall_reference_movement_mm': math.dist(old_dependency, new_dependency),
    'lost_anchor_contract_static_check': {
        'unresolved_state_explicit': True, 'complete_export_blocked': True,
        'fallback_forbidden': True, 'explicit_author_action_and_lineage_required': True,
        'implementation_proof': 'NOT_RUN',
    },
    'p2_gate_accepted': False, 'p2_execution_authorized': False,
    'estimate_refresh_before_PC007': True, 'validate_delivery_exit': validation.returncode,
    'validate_delivery_output': validation.stdout,
}
(ROOT / 'docs/revival/evidence/mixed-part-review-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
