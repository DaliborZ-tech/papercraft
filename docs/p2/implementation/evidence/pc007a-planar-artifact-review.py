"""Independent hash/identity and exact polynomial Green-integral artifact audit."""
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
arch=json.loads((ROOT/'docs/p2/implementation/evidence/pc007a-connector-preview-review-archive-2944c0f.json').read_text(encoding='utf8'))
sys.path.insert(0,str(Path(arch['isolated_directory'])/'src'))
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions

base=ROOT/'docs/p2/implementation/evidence/pc007a-desktop-2944c0f-run02'
run=json.loads((base/'results.json').read_text(encoding='utf8'))
checks={}
for name,expected in run['files_sha256'].items():
    actual=hashlib.sha256((base/name).read_bytes()).hexdigest()
    assert actual==expected,(name,actual,expected)
    checks[name]=actual


def contribution(p):
    if len(p)==2:
        return (p[0][0]*p[1][1]-p[1][0]*p[0][1])/2
    powers=[]
    for axis in (0,1):
        a,b,c,d=(point[axis] for point in p)
        powers.append([a,3*(b-a),3*(c-2*b+a),d-3*c+3*b-a])
    x,y=powers
    # Exact integral of (x*y' - y*x')/2 in the ordinary power basis.
    return sum((x[i]*j*y[j]-y[i]*j*x[j])/Fraction(2*(i+j))
               for i in range(4) for j in range(1,4))


def loop_area(commands):
    total=Fraction(0)
    current=start=None
    for command in commands:
        if command[0]=='M': current=start=tuple(command[1:])
        elif command[0]=='L':
            end=tuple(command[1:]);total+=contribution([current,end]);current=end
        elif command[0]=='C':
            end=tuple(command[5:7]);total+=contribution([current,tuple(command[1:3]),tuple(command[3:5]),end]);current=end
        elif command[0]=='Z': total+=contribution([current,start]);current=start
        else: raise ValueError(command[0])
    return abs(total)


def normalized_svg_path(text):
    tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?',text)
    arities={'M':2,'L':2,'H':1,'V':1,'C':6,'A':7,'Z':0}
    current=start=(Fraction(0),Fraction(0))
    result=[];index=0;op=None
    while index<len(tokens):
        if tokens[index].isalpha():op=tokens[index];index+=1
        if op is None or op.upper() not in arities:raise ValueError('Unsupported editor path syntax')
        upper=op.upper();size=arities[upper]
        values=[Fraction(v) for v in tokens[index:index+size]];index+=size
        relative=op.islower()
        def point(x,y):return (x+current[0],y+current[1]) if relative else (x,y)
        if upper=='M':
            current=start=point(*values);result.append(('M',*current));op='l' if relative else 'L'
        elif upper in ('L','H','V'):
            end=point(*values) if upper=='L' else ((current[0]+values[0] if relative else values[0]),current[1]) if upper=='H' else (current[0],(current[1]+values[0] if relative else values[0]))
            if end!=current:result.append(('L',*end))
            current=end
        elif upper=='C':
            points=[point(*values[i:i+2]) for i in (0,2,4)]
            result.append(('C',*(v for p in points for v in p)));current=points[-1]
        elif upper=='A':
            end=point(*values[-2:]);result.append(('A',*values[:5],*end));current=end
        else:
            if current!=start:result.append(('L',*start))
            result.append(('Z',));current=start;op=None
    return result


def editor_audit():
    reports=[];ns='{http://www.w3.org/2000/svg}'
    for folder in sorted((ROOT/'docs/p2/implementation/evidence').glob('pc007a-inkscape-2944c0f-*')):
        data=folder/'editor-results.json'
        if not data.exists():continue
        report=json.loads(data.read_text(encoding='utf8'))
        for name,sha in report['files_sha256'].items():
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==sha
        original=ET.parse(folder/'editor-original.svg').getroot()
        edited=ET.parse(folder/'editor-edited.svg').getroot()
        for key in ('width','height','viewBox'):assert original.get(key)==edited.get(key)
        paths={p.get('id'):p for p in edited.iter(ns+'path') if p.get('id')}
        count=0
        for p in original.iter(ns+'path'):
            if p.get('id'):
                assert normalized_svg_path(p.get('d'))==normalized_svg_path(paths[p.get('id')].get('d'))
                count+=1
        selected=report['actual_inkscape_action_edits']['label_id']
        label=next(n for n in edited.iter(ns+'text') if n.get('id')==selected)
        assert ''.join(label.itertext())=='\u017dlu\u0165ou\u010dk\u00fd \u2013 vlastn\u00ed d\u00edl'
        source=Path(report['origin_source'])
        assert hashlib.sha256(source.read_bytes()).hexdigest()==hashlib.sha256((folder/'editor-original.svg').read_bytes()).hexdigest()
        for name,sha in report['origin_bundle_sha256'].items():
            assert hashlib.sha256((source.parent/name).read_bytes()).hexdigest()==sha
        reports.append({'directory':folder.name,'recorded_harness_status':report['status'],
                        'actual_local_native_geometry_unchanged':True,'identified_paths_checked':count,
                        'page_units_unchanged':True,'exact_unicode_label':True,'original_bundle_unchanged':True,
                        'note':'Explicit closing L versus implicit Z normalized with same geometric closure; historical harness result not overwritten'})
    return reports


material=base/'curves-planar'
project=json.loads((material/'curves-planar.apcraft').read_text(encoding='utf8'))
snapshot=json.loads((material/'snapshot.json').read_text(encoding='utf8'))
manifest=json.loads((material/'export/.author-export.json').read_text(encoding='utf8'))
assert project['project_id']==snapshot['project_id']==manifest['project_id']
assert len(project['surfaces'])==len(project['parts'])==3
assert len(project['pages'])==len(snapshot['pages'])==2
assert {p['id'] for page in snapshot['pages'] for p in page['parts']}==set(project['parts'])
actual=read_pdf_cut_regions(material/'export/model.pdf')
assert set(actual['parts'])==set(project['parts'])
areas={pid:[float(loop_area(loop)) for loop in record['loops']] for pid,record in actual['parts'].items()}
hole_pid=next(pid for pid,values in areas.items() if len(values)==2)
outer,hole=sorted(areas[hole_pid],reverse=True)
expected_hole=400*math.pi
expected_net=12000-expected_hole
actual_net=outer-hole
delta_hole=abs(hole-expected_hole)
delta_net=abs(actual_net-expected_net)
output={
    'source_sha':run['source_sha'],'pdf_reader_module':str(Path(sys.modules['archpapercraft.exporter.curve_output_validation'].__file__).resolve()),
    'artifact_hashes_checked':len(checks),'hashes':checks,
    'project_id':project['project_id'],'parts':list(project['parts']),
    'physical_pdf_loop_areas_mm2':areas,
    'pdf_circle_area':{'expected':expected_hole,'actual':hole,'absolute_error':delta_hole,'normative_limit':max(0.01,1e-6*expected_hole)},
    'pdf_net_wall_area':{'expected':expected_net,'actual':actual_net,'absolute_error':delta_net,'normative_limit':max(0.01,1e-6*expected_net)},
    'area_verdict':'PASS' if delta_hole<=0.01 and delta_net<=max(0.01,1e-6*expected_net) else 'FAIL',
    'method':'EXACT_FRACTION_GREEN_INTEGRAL_OF_ACTUAL_SERIALIZED_CUBIC_POLYNOMIALS; analytic 400pi oracle',
    'independent_editor_artifact_audits':editor_audit(),
    'full_PC007A':'NOT_APPROVED','physical_build':'NOT_RUN','novice_participants':0,
}
path=ROOT/'docs/p2/implementation/evidence/pc007a-planar-artifact-review-2944c0f.json'
path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in output.items() if k not in ('hashes','parts')},indent=2))
