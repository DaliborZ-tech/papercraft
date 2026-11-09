"""Independent final artifact audit of source63 native UI and both editor runs."""
import ast
import hashlib
import importlib.util
import io
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
E=ROOT/'docs/p2/implementation/evidence'
PIN='63ab275a5fe9b92bdb370a5ec3dedf1c5f70a65e'
PREVIOUS='3252544850c0d4a9c4465de8f359ec2a5350af27'
assert not subprocess.check_output(['git','diff',PREVIOUS,PIN,'--','src','pyproject.toml'],cwd=ROOT)
archive=subprocess.check_output(['git','archive','--format=tar',PIN,'src','tools','pyproject.toml'],cwd=ROOT)
isolated=Path(tempfile.mkdtemp(prefix='papercraft-final-planar-review-')).resolve()
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        assert (isolated/member.name).resolve().is_relative_to(isolated)
    source.extractall(isolated,filter='data')
sys.path.insert(0,str(isolated/'src'))
from archpapercraft.exporter import author_export,curve_output_validation
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions

# Import only the reviewer's mathematical oracle, never a production expected helper.
spec=importlib.util.spec_from_file_location('independent_cubic_integral',E/'pc007a-area-integration-review-own.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
# Reuse the independently written exact relative SVG reader, not the repaired harness reader.
tree=ast.parse((E/'pc007a-planar-artifact-review.py').read_text(encoding='utf8'))
fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='normalized_svg_path')
namespace={'re':re,'Fraction':Fraction}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'independent_svg_reader','exec'),namespace)
svg_path=namespace['normalized_svg_path']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fraction_area(commands):return oracle.loop_area(commands)

base=E/'pc007a-desktop-63ab275-run04'
run=json.loads((base/'results.json').read_text(encoding='utf8'))
assert run['source_sha']==PIN and run['status']=='PASS_REQUESTED_FIXTURE'
assert Path(run['actual_application_module']).resolve()==(ROOT/'src/archpapercraft/ui/author_window.py').resolve()
source_bindings={}
for relative,digest in run['source_files_sha256'].items():
    raw=subprocess.check_output(['git','show',PIN+':'+relative],cwd=ROOT)
    lf=raw.replace(b'\r\n',b'\n')
    candidates={'GIT_LF':hashlib.sha256(lf).hexdigest(),'WINDOWS_CRLF':hashlib.sha256(lf.replace(b'\n',b'\r\n')).hexdigest()}
    assert digest in candidates.values(),relative
    assert (isolated/relative).read_bytes().replace(b'\r\n',b'\n')==lf
    source_bindings[relative]=next(k for k,v in candidates.items() if v==digest)
for name,digest in run['files_sha256'].items():assert sha(base/name)==digest,name
assert run['failures']==[]
assert all(s['status']=='PASS' for s in run['steps'])
native=[d for d in run['dialogs'] if d.get('native_seen')]
assert len(native)==3 and all(d['accepted'] for d in native)
assert [d['title'] for d in run['dialogs'] if d.get('kind')=='real_QMessageBox']==['Vektorov\u00fd export','Export dokon\u010den']
counts={}
for event in run['inputs']:
    if event.get('event')=='observed_QAction_triggered':
        key=event['action'];assert event['count']==counts.get(key,0)+1;counts[key]=event['count']
    if event.get('event')=='shortcut_context':assert event['window_active'] and event['expected_actions']
for key,value in {'save':1,'new':1,'open':1,'export':1,'recompute':2,'hole':1,'draw':1,'undo':1,'attach_inside':1}.items():assert counts[key]==value

material=base/'curves-planar';bundle=material/'export'
project=json.loads((material/'curves-planar.apcraft').read_text(encoding='utf8'))
snapshot=json.loads((material/'snapshot.json').read_text(encoding='utf8'))
manifest=json.loads((bundle/'.author-export.json').read_text(encoding='utf8'))
assert project['project_id']==snapshot['project_id']==manifest['project_id']
assert author_export.canonical_digest(snapshot)==manifest['snapshot_digest']
assert len(project['parts'])==len(project['surfaces'])==3 and len(project['pages'])==len(snapshot['pages'])==2
parts={part['id']:part for page in snapshot['pages'] for part in page['parts']}
assert set(parts)==set(project['parts'])
for part in parts.values():assert set(part['surface_ids'])<=set(project['surfaces'])
actual=read_pdf_cut_regions(bundle/'model.pdf')
assert len(actual['pages'])==2 and set(actual['parts'])==set(parts)
for pid,part in actual['parts'].items():
    assert part['page_index']==next(i for i,page in enumerate(snapshot['pages']) if any(p['id']==pid for p in page['parts']))
areas={pid:sorted((float(fraction_area(loop)) for loop in part['loops']),reverse=True) for pid,part in actual['parts'].items()}
hole_pid=next(pid for pid,values in areas.items() if len(values)==2)
outer,hole=areas[hole_pid];net=outer-hole;expected_net=12000-400*math.pi
assert abs(outer-12000)<.012 and abs(hole-400*math.pi)<.01
assert abs(net-expected_net)<max(.01,1e-6*expected_net)
for pid,values in areas.items():
    if pid!=hole_pid:assert abs(values[0]-(2188 if values[0]>1000 else 800))<.01
assert manifest['actual_curve_output_checks']['area_agreement']['status']=='VERIFIED'
ns='{http://www.w3.org/2000/svg}'
svg_pages={}
native_arcs=native_cubics=0
for path in sorted(bundle.glob('*.svg')):
    root=ET.parse(path).getroot()
    assert root.get('data-project-id')==project['project_id']
    assert root.get('width')=='210mm' and root.get('height')=='297mm' and root.get('viewBox')=='0 0 210 297'
    assert root.get('data-snapshot-digest')==manifest['snapshot_digest']
    page_parts={g.get('data-part-id') for g in root.findall(ns+'g') if g.get('data-part-id')}
    assert page_parts<=set(parts)
    for pathnode in root.iter(ns+'path'):
        commands=svg_path(pathnode.get('d'))
        native_arcs+=sum(cmd[0]=='A' for cmd in commands);native_cubics+=sum(cmd[0]=='C' for cmd in commands)
    svg_pages[path.name]=sorted(page_parts)
assert native_arcs>=4 and native_cubics>=1
assert set(pid for page in svg_pages.values() for pid in page)==set(parts)

editors=[]
for folder in (E/'pc007a-inkscape-63ab275-page1-run03',E/'pc007a-inkscape-63ab275-page2-run04'):
    r=json.loads((folder/'editor-results.json').read_text(encoding='utf8'))
    assert r['source_sha']==PIN and r['status']=='PASS'
    assert r['script_sha256']==run['source_files_sha256']['tools/authoring/editor_probe.py']
    for name,digest in r['files_sha256'].items():assert sha(folder/name)==digest
    for name,digest in r['origin_bundle_sha256'].items():assert sha(bundle/name)==digest
    origin=Path(r['origin_source']);assert origin.parent==bundle and sha(origin)==sha(folder/'editor-original.svg')
    original=ET.parse(folder/'editor-original.svg').getroot();edited=ET.parse(folder/'editor-edited.svg').getroot()
    for key in ('width','height','viewBox'):assert original.get(key)==edited.get(key)
    by_id={node.get('id'):node for node in edited.iter() if node.get('id')}
    checked=[];arc_count=cubic_count=0
    for node in original.iter(ns+'path'):
        if node.get('id'):
            target=by_id[node.get('id')];before=svg_path(node.get('d'));after=svg_path(target.get('d'))
            assert before==after,node.get('id')
            arc_count+=sum(cmd[0]=='A' for cmd in after);cubic_count+=sum(cmd[0]=='C' for cmd in after)
            checked.append(node.get('id'))
    # Includes anonymous100mm calibration paths, even if Inkscape adds an ID.
    orig_guides=original.find(ns+'g[@id="page-GUIDES"]');edit_guides=edited.find(ns+'g[@id="page-GUIDES"]')
    op=list(orig_guides.iter(ns+'path'));ep=list(edit_guides.iter(ns+'path'))
    assert len(op)==len(ep)==1
    before=svg_path(op[0].get('d'));assert before==svg_path(ep[0].get('d'))
    points=[c[1:] for c in before if c[0] in ('M','L')]
    assert len(points)==2 and points[1][0]-points[0][0]==100 and points[0][1]==points[1][1]
    selected=r['actual_inkscape_action_edits']['label_id']
    text=''.join(by_id[selected].itertext())
    assert text=='\u017dlu\u0165ou\u010dk\u00fd \u2013 vlastn\u00ed d\u00edl'
    assert '#b43d28' in (by_id[selected].get('style','')+by_id[selected].get('fill',''))
    for node in original.iter(ns+'text'):
        if node.get('id')!=selected:assert ''.join(node.itertext())==''.join(by_id[node.get('id')].itertext())
    assert r['native_gui_text_edit']['foreground_verified_before_each_chord']
    assert all(c['exit_code']==0 for c in r['commands'])
    assert r['physical_build']=='NOT_RUN' and r['new_user_test']=='NOT_RUN'
    editors.append({'directory':folder.name,'paths_checked':checked,'native_arcs':arc_count,'native_cubics':cubic_count,
                    'exact_local_geometry_preserved':True,'calibration_100mm':True,'unicode_text_exact':text,
                    'original_bundle_hashes_unchanged':True,'recorded_elapsed_seconds':r['elapsed_seconds']})
assert sum(x['native_arcs'] for x in editors)>=4 and sum(x['native_cubics'] for x in editors)>=1

suite=ET.parse(E/'pc007a-suite-63ab275-run03.xml').getroot()
test_suites=list(suite.iter('testsuite'));assert test_suites
assert sum(int(s.attrib['tests']) for s in test_suites)==908
assert sum(int(s.attrib.get('errors',0))+int(s.attrib.get('failures',0))+int(s.attrib.get('skipped',0)) for s in test_suites)==0
result={'source_sha':PIN,'production_source_unchanged_since':PREVIOUS,'archive_sha256':hashlib.sha256(archive).hexdigest(),
        'isolated_directory':str(isolated),'actual_pdf_parser':curve_output_validation.__file__,
        'source_hash_bindings_count':len(source_bindings),'source_hash_binding_modes':sorted(set(source_bindings.values())),
        'native_artifact_hash_count':len(run['files_sha256']),'native_status':run['status'],'native_elapsed_seconds':run['elapsed_seconds'],
        'observed_native_dialogs':len(native),'observed_action_counts':counts,
        'project_id':project['project_id'],'snapshot_digest':manifest['snapshot_digest'],'pages':svg_pages,
        'actual_pdf_loop_areas_mm2':areas,'wall_net_error_mm2':abs(net-expected_net),'wall_net_limit_mm2':max(.01,1e-6*expected_net),
        'hole_error_mm2':abs(hole-400*math.pi),'hole_limit_mm2':.01,
        'method':'EXACT_FRACTION_GREEN_INTEGRAL_OF_ACTUAL_RAW_PDF_CUBICS; INDEPENDENT_EXACT_SVG_RELATIVE_READER',
        'actual_editor_audits':editors,'full_original_suite_tests':908,'suite_failures_errors_skipped':0,
        'verdict':'APPROVED_IN_BOUNDED_PLANAR_AUTHORING_SLICE_SCOPE','V02':'CLOSED_ON_ACTUAL_NATIVE_SOURCE63_ARTIFACT',
        'whole_PC007A':'IN_PROGRESS; LOFT_UI_NOT_APPROVED','P2':'NOT_COMPLETE','novice_participants':0,'physical':'NOT_RUN'}
(E/'pc007a-planar-final-artifact-review-63ab275.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,indent=2,ensure_ascii=True))
