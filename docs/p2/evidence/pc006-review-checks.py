"""Independent PC006 foundation review, pinned imports and isolated fixtures."""
from __future__ import annotations

import copy
import importlib.abc
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(sys.argv[1]).resolve()
PIN = '135a3a1d4fb7da1c74adf33574bde58e5fd9f0e7'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REVIEW, text=True).strip() == PIN
sys.path.insert(0, str(REVIEW / 'src'))


class NoQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('PySide6', 'PyQt5', 'PyQt6'):
            raise ImportError('Qt prohibited in independent core review')
        return None


sys.meta_path.insert(0, NoQt())
import numpy as np
from archpapercraft.domain import PanelProject, PaperFrame, Placement, Transform, ValidationError, ProjectFormatError, UnsupportedOperationError, LegacyProject, load_project
from archpapercraft.domain import project as persistence

started = time.perf_counter()
results = {}
house = PanelProject.new_house(length_mm=12000, width_mm=8000, wall_height_mm=5000, roof_rise_mm=3000)
surfaces = house.surfaces()
areas = {surface.name: surface.area * house.scale**2 for surface in surfaces.values()}
assert len(surfaces) == 8
assert abs(sum(areas.values()) - 34400) < .01
assert all(abs(s.area * house.scale**2 - 6000) < .01 for s in surfaces.values() if s.name.startswith('roof'))
results['nondefault_house'] = dict(surface_count=len(surfaces), area_paper_mm2=sum(areas.values()), roof_panel_area_paper_mm2=6000)
for value, unit in [(12, 'm'), (1200, 'cm'), (12000, 'mm')]:
    specimen = PanelProject.new_house()
    specimen.set_dimension('length_mm', value, unit)
    assert abs(specimen.surfaces()[specimen.surface_id('wall-left')].boundary[0].length * specimen.scale - 120) < .01
results['units'] = 'PASS: 12m/1200cm/12000mm -> 120 paper mm'
specimen = PanelProject.new_house()
local = Transform.from_trs(position_mm=(2, 3, 4))
parent_one = Transform.from_trs(position_mm=(100, 200, 300), rotation_deg=(0, 0, 90))
parent_two = Transform.from_trs(position_mm=(10, 20, 30), rotation_deg=(90, 0, 0))
specimen.set_transform(local, [parent_one, parent_two])
source = specimen.surfaces()[specimen.surface_id('roof-left')]
world = specimen.world_surfaces()[source.id]
expected = source.vertices[:, [2, 0, 1]] + [84, 212, 333]
error = float(np.max(np.abs(expected - world.vertices)))
assert error < 1e-7
results['two_parent_transform'] = dict(max_coordinate_error_mm=error, area_preserved=abs(source.area-world.area)<.01)
specimen = PanelProject.new_house()
before = specimen.to_dict()
rejected = []
for value in [float('nan'), float('inf'), -1, 0, 1e-8, True, '200']:
    try:
        specimen.set_dimension('width_mm', value)
    except ValidationError:
        assert specimen.to_dict() == before
        rejected.append(repr(value))
    else:
        raise AssertionError(f'Invalid dimension accepted: {value!r}')
results['transactional_invalid_dimensions'] = rejected

with tempfile.TemporaryDirectory(prefix='pc006-review-save-') as scratch:
    path = Path(scratch) / 'house.apcraft'
    specimen.save(path)
    original = path.read_bytes()
    specimen.set_dimension('length_mm', 11000)
    failure_results = []
    for target in ['fsync', 'replace']:
        with patch.object(persistence.os, target, side_effect=OSError('review injected IO failure')):
            try:
                specimen.save(path)
            except OSError:
                assert path.read_bytes() == original
                assert list(Path(scratch).iterdir()) == [path]
                failure_results.append(target)
            else:
                raise AssertionError('Injected save failure ignored')
    legacy = load_project(REVIEW / 'samples/house_with_dome.apcraft')
    assert isinstance(legacy, LegacyProject)
    legacy_copy = Path(scratch) / 'legacy.apcraft'
    legacy_copy.write_bytes(legacy.raw_bytes)
    try:
        specimen.save(legacy_copy)
    except UnsupportedOperationError:
        assert legacy_copy.read_bytes() == legacy.raw_bytes
    else:
        raise AssertionError('Legacy overwrite accepted')
    results['save_fault_and_legacy'] = dict(preserved_failures=failure_results, raw_legacy_preserved=True)

schema_cases = {}
base = PanelProject.new_house().to_dict()
for name, mutation in [
    ('future_schema', lambda d: d.update(schema_version=42)),
    ('unknown_field', lambda d: d.update(unknown={'data': 1})),
    ('duplicate_page_id', lambda d: d['pages'].__setitem__(1, copy.deepcopy(d['pages'][0]))),
    ('nan_parameter', lambda d: d['params'].update(length_mm=float('nan'))),
]:
    data = copy.deepcopy(base)
    mutation(data)
    try:
        PanelProject.from_dict(data)
    except ProjectFormatError:
        schema_cases[name] = 'rejected'
    else:
        raise AssertionError(f'Schema case accepted: {name}')
results['strict_schema'] = schema_cases

specimen = PanelProject.new_house()
specimen.set_transform(Transform.from_trs(scale=(2, 1, 1)))
sid = specimen.surface_id('wall-left')
results['nonrigid_transform_policy'] = dict(local_edge_mm=specimen.surfaces()[sid].boundary[0].length, world_edge_mm=specimen.world_surfaces()[sid].boundary[0].length)
specimen = PanelProject.new_house()
with np.errstate(over='ignore', invalid='ignore', under='ignore'):
    try:
        specimen.set_transform(Transform.from_trs(scale=(1e80, 1e80, 1e80)))
    except ValidationError as exc:
        results['finite_transform_overflow'] = dict(rejected=True, message=str(exc))
    else:
        areas = [s.area for s in specimen.world_surfaces().values()]
        results['finite_transform_overflow'] = dict(rejected=False, all_areas_finite=all(math.isfinite(a) for a in areas), world_areas_repr=[repr(a) for a in areas])

specimen = PanelProject.new_house()
all_surfaces = list(specimen.surfaces().values())
for index, surface in enumerate(all_surfaces):
    pid = f'part-{index}'
    specimen.paper_frames[pid] = PaperFrame(surface.id, surface.vertex_ids[0], surface.boundary[0].id)
    specimen.placements[pid] = Placement(pid, specimen.pages[0].id, 60, 60, 30)
    specimen.part_records[pid] = dict(id=pid, name=surface.name, surface_ids=[surface.id], source_revision=1, stale=False, lineage=[], review_state='current')
data = specimen.to_dict()
other = all_surfaces[1]
data['paper_state']['frames']['part-0'].update(root_surface_id=other.id, anchor_vertex_id=other.vertex_ids[0], axis_edge_id=other.boundary[0].id)
try:
    malformed = PanelProject.from_dict(data)
except ProjectFormatError as exc:
    results['frame_outside_part'] = dict(rejected=True, message=str(exc))
else:
    results['frame_outside_part'] = dict(rejected=False, part_surface=malformed.part_records['part-0']['surface_ids'], frame_root=malformed.paper_frames['part-0'].root_surface_id, review_state=malformed.part_records['part-0']['review_state'])

output = dict(code_sha=PIN, seconds=round(time.perf_counter()-started, 3), proof_kind='independent core review; defect probes are observations, not product PASS', results=results)
(ROOT/'docs/p2/evidence/pc006-review-results.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output, indent=2))
