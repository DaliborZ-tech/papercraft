"""Source-pinned offline export audit; never presents it as a native UI run."""
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
EVIDENCE=ROOT/'docs/p2/implementation/evidence'
archive=json.loads((EVIDENCE/'pc007a-area-integration-review-archive-3252544.json').read_text(encoding='utf8'))
sys.path.insert(0,str(Path(archive['isolated_directory'])/'src'))
from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions

spec=importlib.util.spec_from_file_location('independent_polynomial_integral',EVIDENCE/'pc007a-area-integration-review-own.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
source_dir=EVIDENCE/'pc007a-desktop-3252544-run03'
snapshot=json.loads((source_dir/'curves-planar/snapshot.json').read_text(encoding='utf8'))
output=Path(tempfile.mkdtemp(prefix='papercraft-v02-artifact-review-'))
export_all(snapshot,output)
actual=read_pdf_cut_regions(output/'model.pdf')
values={pid:sorted((float(oracle.loop_area(loop)) for loop in record['loops']),reverse=True)
        for pid,record in actual['parts'].items()}
hole_pid=next(pid for pid,areas in values.items() if len(areas)==2)
outer,hole=values[hole_pid]
expected_net=12000-400*math.pi
manifest=json.loads((output/'.author-export.json').read_text(encoding='utf8'))
result={
    'source_sha':archive['source_sha'],
    'source_isolation':archive['isolated_directory'],
    'kind':'INDEPENDENT_OFFLINE_EXPORT_OF_NATIVE_SAVED_SNAPSHOT; NOT_A_NATIVE_EXPORT_REPLACEMENT',
    'snapshot_sha256':hashlib.sha256((source_dir/'curves-planar/snapshot.json').read_bytes()).hexdigest(),
    'artifact_directory':str(output),
    'artifact_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()},
    'method':'EXACT_FRACTION_GREEN_INTEGRAL_OF_ACTUAL_PDF_CUBICS; ANALYTIC_400_PI',
    'actual_loop_areas_mm2':values,
    'wall_outer':{'actual':outer,'expected':12000,'absolute_error':abs(outer-12000),'allowed':.012},
    'wall_hole':{'actual':hole,'expected':400*math.pi,'absolute_error':abs(hole-400*math.pi),'allowed':.01},
    'wall_net':{'actual':outer-hole,'expected':expected_net,'absolute_error':abs(outer-hole-expected_net),'allowed':max(.01,1e-6*expected_net)},
    'other_loop_oracles':{pid:{'actual':areas[0],'expected':2188 if areas[0]>1000 else 800,
                              'absolute_error':abs(areas[0]-(2188 if areas[0]>1000 else 800))}
                          for pid,areas in values.items() if pid!=hole_pid},
    'writer_area_agreement':manifest['actual_curve_output_checks']['area_agreement'],
    'actual_precision_attempts':manifest['pdf_arc_approximation']['precision_attempts'],
    'native_3252544_run03_status':json.loads((source_dir/'results.json').read_text(encoding='utf8'))['status'],
    'native_review_verdict':'PENDING_SUCCESSFUL_NATIVE_EXPORT_AND_ACTUAL_EDITOR_ROUNDTRIPS',
    'physical':'NOT_RUN','new_user_count':0,
}
assert result['wall_outer']['absolute_error']<=result['wall_outer']['allowed']
assert result['wall_hole']['absolute_error']<=result['wall_hole']['allowed']
assert result['wall_net']['absolute_error']<=result['wall_net']['allowed']
assert all(v['absolute_error']<.01 for v in result['other_loop_oracles'].values())
(EVIDENCE/'pc007a-area-integration-artifact-review-3252544.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({key:result[key] for key in ('source_sha','wall_outer','wall_hole','wall_net','other_loop_oracles','native_review_verdict')},indent=2))
