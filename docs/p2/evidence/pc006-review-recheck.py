"""Re-review fixed core policy/reference validation, independent of in-flight UI."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(sys.argv[1]).resolve()
PIN = sys.argv[2]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REVIEW, text=True).strip() == PIN
sys.path.insert(0, str(REVIEW / 'src'))
import numpy as np
from archpapercraft.domain import PanelProject, PaperFrame, Placement, Transform, ProjectFormatError, ValidationError

started = time.perf_counter()
result = {}
specimen = PanelProject.new_house()
original = specimen.to_dict()
unsupported = {}
for name, linear in [('nonuniform_scale', np.diag([2., 1., 1.])), ('uniform_scale', 2*np.eye(3)),
                     ('huge_scale', 1e80*np.eye(3)), ('shear', np.array([[1., .2, 0], [0, 1., 0], [0, 0, 1.]]))]:
    matrix = np.eye(4)
    matrix[:3, :3] = linear
    try:
        specimen.set_transform(Transform(matrix))
    except ValidationError as exc:
        assert exc.code == 'UNSUPPORTED_TRANSFORM'
        assert specimen.to_dict() == original
        unsupported[name] = 'typed rejection; unchanged project'
    else:
        raise AssertionError(f'{name} accepted')
    malformed = copy.deepcopy(original)
    malformed['local_transform'] = matrix.tolist()
    try:
        PanelProject.from_dict(malformed)
    except ProjectFormatError:
        pass
    else:
        raise AssertionError(f'{name} deserialized')
result['nonrigid_policy'] = unsupported

surfaces = list(specimen.surfaces().values())
for index, surface in enumerate(surfaces):
    pid = f'part-{index}'
    specimen.paper_frames[pid] = PaperFrame(surface.id, surface.vertex_ids[0], surface.boundary[0].id)
    specimen.placements[pid] = Placement(pid, specimen.pages[0].id, 60, 60, 30)
    specimen.part_records[pid] = dict(id=pid, name=surface.name, surface_ids=[surface.id], source_revision=1, stale=False, lineage=[], review_state='current')
valid = specimen.to_dict()
frame_results = {}
for name, updates in [
    ('foreign_root', dict(root_surface_id=surfaces[1].id)),
    ('foreign_vertex', dict(anchor_vertex_id=surfaces[1].vertex_ids[0])),
    ('foreign_axis', dict(axis_edge_id=surfaces[1].boundary[0].id)),
    ('missing_axis', dict(axis_edge_id='missing-axis')),
    ('wrong_axis_orientation', dict(orientation=-1)),
]:
    payload = copy.deepcopy(valid)
    payload['paper_state']['frames']['part-0'].update(updates)
    try:
        PanelProject.from_dict(payload)
    except ProjectFormatError:
        pass
    else:
        raise AssertionError(f'{name} current frame accepted')
    payload['paper_state']['parts']['part-0']['review_state'] = 'ANCHOR_UNRESOLVED'
    payload['paper_state']['parts']['part-0']['stale'] = True
    payload['paper_state']['placements']['part-0']['review_state'] = 'ANCHOR_UNRESOLVED'
    restored = PanelProject.from_dict(payload)
    assert restored.to_dict() == payload
    frame_results[name] = 'current rejected; explicit unresolved/stale draft preserved exactly'
result['frame_integrity'] = frame_results

with tempfile.TemporaryDirectory(prefix='pc006-review-fixed-') as temp:
    path = Path(temp)/'unresolved.apcraft'
    restored.save(path)
    assert PanelProject.load(path).to_dict() == payload
result['unresolved_save_reopen'] = 'PASS'

translation = PanelProject.new_house()
before = translation.to_dict()
try:
    translation.set_transform(Transform.from_trs(position_mm=(1e20, 0, 0)))
except ValidationError as exc:
    assert translation.to_dict() == before
    result['large_rigid_translation'] = dict(rejected=True, code=exc.code, original_preserved=True)
    malformed = copy.deepcopy(before)
    malformed['local_transform'] = Transform.from_trs(position_mm=(1e20, 0, 0)).matrix.tolist()
    with tempfile.TemporaryDirectory(prefix='pc006-review-precision-') as temp:
        path = Path(temp)/'precision.apcraft'
        raw = json.dumps(malformed).encode('utf-8')
        path.write_bytes(raw)
        try:
            PanelProject.load(path)
        except ProjectFormatError:
            assert path.read_bytes() == raw
            result['large_rigid_translation']['deserialization_rejected_without_file_change'] = True
        else:
            raise AssertionError('Precision-losing transform deserialized')
else:
    sid = translation.surface_id('wall-left')
    local = translation.surfaces()[sid]
    world = translation.world_surfaces()[sid]
    result['large_rigid_translation'] = dict(rejected=False, original_preserved=translation.to_dict()==before,
        expected_edge_mm=local.boundary[0].length, actual_edge_mm=world.boundary[0].length,
        expected_area_mm2=local.area, actual_area_mm2=world.area)

result.update(code_sha=PIN, seconds=round(time.perf_counter()-started, 3), scope='PC006 core only; no GUI/export approval')
(ROOT/'docs/p2/evidence'/f'pc006-review-recheck-{PIN[:7]}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
