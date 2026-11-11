"""Small independent backend timing probe; no UI or statistical acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring import loft_surface

p=argparse.ArgumentParser();p.add_argument('--source-sha',required=True);p.add_argument('--archive',required=True);p.add_argument('--output',required=True);args=p.parse_args()
actual=Path(loft_surface.__file__).resolve();assert actual.is_relative_to(Path(args.archive).resolve())
fixture=Path(r'C:\Users\dalib\projects\papercraft-loft-integration\docs\p2\implementation\evidence\pc007a-loft-B1-desktop-a9d155a-run01\FAIL-partial-observed-state.json')
raw=fixture.read_bytes();result={'source_sha':args.source_sha,'module':str(actual),'module_sha256':hashlib.sha256(actual.read_bytes()).hexdigest(),'fixture':str(fixture),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'scope':'ONE_LOCAL_BACKEND_TIMING_RUN; NOT_NATIVE_UI_OR_NOVICE_OR_STATISTICAL_PASS','operations':{}}
def measure(name,op):
    start=time.perf_counter();value=op();result['operations'][name]=time.perf_counter()-start;print(name,result['operations'][name],flush=True);return value
project=measure('cold_load',lambda:AuthorProject.from_dict(json.loads(raw)))
sid=next(s.id for s in project.surfaces.values() if s.kind=='ruled_loft');pid=project.part_for_surface(sid)
measure('warm_world_1',lambda:project.world_geometry(sid));measure('warm_world_2',lambda:project.world_geometry(sid));measure('warm_validate',project.validate)
result['status']=project.loft_status(sid)['status'];result['fixture_unchanged']=fixture.read_bytes()==raw
Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf8')
