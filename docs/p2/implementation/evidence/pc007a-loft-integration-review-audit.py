"""Independent pinned artifact audit. No production geometry helpers as area oracle."""
import os, sys, json, re, hashlib, subprocess, math
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D, getcontext
from collections import Counter
import xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[4]
E=ROOT/'docs/p2/implementation/evidence'
CODE='a46f179331a5ab94fec7b68ba52b2f9431ac699b'
META='382a364d81e7975cb9c76f4a8eb1dfd72abc0c79'
ARCHIVE=Path(r'C:\Users\dalib\AppData\Local\Temp\pc007a-review-integrated-a46-rbgi46_a')
os.chdir(ROOT)
sys.path.insert(0,str(ARCHIVE/'src'))
getcontext().prec=80
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(p,ref=META):return git('show',ref+':'+p.as_posix())
def data(p):return json.loads(p.read_text(encoding='utf-8'))
def dec(q):return D(q.numerator)/D(q.denominator) if isinstance(q,F) else D(q)
def atan(x):
    if x<0:return -atan(-x)
    if x>1:return PI/2-atan(1/x)
    if x>D('.5'):return 2*atan(x/(1+(1+x*x).sqrt()))
    v=x;s=x;n=1
    while abs(v)>D('1e-75'):
        v*=-x*x;n+=2;s+=v/n
    return s
PI=16*atan(D(1)/5)-4*atan(D(1)/239)
NUM=r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
def green_curve(p,controls):
    pts=[p,*controls]; x=[];y=[]
    for axis,out in [(0,x),(1,y)]:
        a,b,c,d=[v[axis] for v in pts]
        out.extend([a,3*(b-a),3*(a-2*b+c),d-3*c+3*b-a])
    return sum(F(j,2*(i+j))*(x[i]*y[j]-y[i]*x[j]) for i in range(4) for j in range(1,4))
def loop_areas(commands):
    areas=[];total=D(0);current=start=None
    for op,v in commands:
        v=list(map(F,v))
        if op=='M':
            if current is not None:assert current==start
            current=start=tuple(v);total=D(0);continue
        end=start if op=='Z' else tuple(v[-2:])
        if op in ['L','Z']:total+=dec((current[0]*end[1]-current[1]*end[0])/2)
        elif op=='C':total+=dec(green_curve(current,[v[:2],v[2:4],v[4:6]]))
        elif op=='A':
            rx,ry,rot,large,sweep,ex,ey=v;assert rx==ry and rot==0
            dx,dy=(current[0]-ex)/2,(current[1]-ey)/2;dd=dx*dx+dy*dy
            rr=max(rx*rx,dd);k=(dec((rr-dd)/dd)).sqrt()*(1 if large!=sweep else -1)
            cx=dec((current[0]+ex)/2)+k*dec(dy);cy=dec((current[1]+ey)/2)-k*dec(dx)
            angle=PI if rr==dd else 2*atan((dec(dd/(rr-dd))).sqrt())
            if large:angle=2*PI-angle
            if not sweep:angle=-angle
            total+=(dec(rr)*angle+cx*dec(ey-current[1])-cy*dec(ex-current[0]))/2
        else:raise AssertionError(op)
        current=end
        if op=='Z':areas.append(abs(total));current=start=None
    assert current is None
    return sorted(areas,reverse=True)
def svg_commands(d):
    toks=re.findall('[MLCAZHVmlcazhv]|'+NUM,d);out=[];i=0;current=(F(0),F(0));start=current
    while i<len(toks):
        if toks[i].isalpha():op=toks[i];i+=1
        upper=op.upper();n={'M':2,'L':2,'C':6,'A':7,'Z':0,'H':1,'V':1}[upper]
        v=list(map(F,toks[i:i+n]));i+=n;relative=op.islower()
        if upper in ['H','V']:
            v=[(current[0]+v[0] if relative else v[0]),current[1]] if upper=='H' else [current[0],(current[1]+v[0] if relative else v[0])];upper='L'
        elif relative and upper!='Z':
            axes=range(0,n,2) if upper!='A' else [5]
            for j in axes:v[j]+=current[0];v[j+1]+=current[1]
        if upper=='Z':current=start
        else:current=tuple(v[-2:])
        if upper=='M':start=current
        out.append((upper,v))
        if upper=='M':op='l' if relative else 'L'
    return out
def pdf_commands(b):
    out=[];stack=[]
    for t in re.findall(rb'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?|[A-Za-z]+',b):
        s=t.decode()
        if re.fullmatch(NUM,s):stack.append(s)
        else:
            if s in ['m','l','c','h']:
                n={'m':2,'l':2,'c':6,'h':0}[s];assert len(stack)==n
                out.append(({'m':'M','l':'L','c':'C','h':'Z'}[s],stack.copy()))
            stack=[]
    return out
def net(areas):return areas[0]-sum(areas[1:])
def simpson(f,end,n=4096):
    h=end/n;return h*(f(D(0))+f(end)+sum((4 if i%2 else 2)*f(i*h) for i in range(1,n)))/3
def source_interval(kind,scale):
    factor=dec((100*F(scale))**2)
    if kind=='gothic':
        f=lambda t:65*(116+272*t*t+181*t**4).sqrt()/(1+t*t)**2
        a=440+D('2.2')*simpson(f,D(2)/3);err=D('2.2')*(D(2)/3)*(D(2)/3/4096)**4*D('1e8')/180+D('1e-9')
    elif kind=='wall':a=12000-(D('32.5')**2*2*atan(D(2)/3)-375);err=D('1e-7')
    elif kind in ['disk','ring']:a=(400 if kind=='disk' else 176)*PI;err=D('1e-40')
    else:
        f=lambda t:(11700-18000*t+32400*t*t-28800*t**3+14400*t**4).sqrt()
        a=10*simpson(f,D(1),8192)
        q1,q2,q3,q4,m=map(D,[226800,410400,518400,345600,60])
        m4=q4/(2*m)+(4*q1*q3+3*q2*q2)/(4*m**3)+18*q1*q1*q2/(8*m**5)+15*q1**4/(16*m**7)
        err=10*m4/(180*D(8192)**4)+D('1e-40')
    return (a-err)*factor,(a+err)*factor

report={'code':CODE,'metadata':META,'reader':'Independent Fraction Green L/C, Decimal80 circular A and analytic source integrals; PDF original numeric bytes via pypdf decompression only','native':[],'editor':[],'vectors':[],'source_eol_only_differences':[]}
assert not git('diff','--name-only',CODE,META,'--','src','tests','tools','pyproject.toml').strip()
assert not git('diff','--name-only','7ee42b397e0491bff87a0f76b7c07850ef5b56c3',CODE,'--','src','tests','tools','pyproject.toml').strip()
report['runtime_equal_approved_V4']=True
import archpapercraft.authoring.project as proj
import archpapercraft.exporter.author_export as writer
report['actual_imports']={m.__name__:str(Path(m.__file__).resolve()) for m in [proj,writer]}
for m in [proj,writer]:assert Path(m.__file__).resolve().is_relative_to(ARCHIVE)

ns={'s':'http://www.w3.org/2000/svg'}
for fixture in ['B1','B2','Bezier']:
    print('AUDIT',fixture,flush=True)
    folder=E/f'pc007a-loft-{fixture}-desktop-a46f179-run01';p=folder/'results.json';d=data(p)
    assert d['status']=='PASS_REQUESTED_FIXTURE' and d['source_sha']==CODE and not d['failures']
    assert p.read_bytes()==blob(p.relative_to(ROOT))
    for rel,h in d['source_files_sha256'].items():
        raw=(ARCHIVE/rel).read_bytes()
        if sha(raw)!=h:
            pinned=blob(Path(rel),CODE);assert raw.replace(b'\r\n',b'\n')==pinned.replace(b'\r\n',b'\n') and h in [sha(pinned),sha(raw.replace(b'\r\n',b'\n'))],(fixture,rel,'source footprint')
            report['source_eol_only_differences'].append({'fixture':fixture,'file':rel,'archive':sha(raw),'native_and_git':h})
    for rel,h in d['files_sha256'].items():
        f=folder/rel;assert sha(f.read_bytes())==h and f.read_bytes()==blob(f.relative_to(ROOT))
    project_file=folder/f'loft-{fixture}'/f'loft-{fixture}.apcraft';saved=data(project_file);loaded=proj.load_project(project_file)
    assert not loaded.validate_layout();assert loaded.to_dict()==saved
    snapshot=loaded.snapshot();assert snapshot
    report['native'].append({'fixture':fixture,'seconds':d['elapsed_seconds'],'artifact_hashes_git_equal':len(d['files_sha256']),'source_footprint_equal':len(d['source_files_sha256']),'reopen_snapshot_valid':True,'dialogs':d['dialogs'],'opengl':d['opengl']})
    export=project_file.parent/'export';reader=PdfReader(export/'model.pdf')
    for page in reader.pages:
        assert all(obj.get_object().get('/Subtype')!='/Image' for obj in page.get('/Resources',{}).get('/XObject',{}).values())
        stream=page.get_contents().get_data();pid=re.search(rb'/APPart_([^\s]+) BMC',stream).group(1).decode()
        cut=re.search(rb'/APRole_CUT BMC(.*?)EMC',stream,re.S).group(1)
        prefix=stream.split(b'/APPart_',1)[0];cms=re.findall((rb'('+NUM.encode()+rb')\s+('+NUM.encode()+rb')\s+('+NUM.encode()+rb')\s+('+NUM.encode()+rb')\s+('+NUM.encode()+rb')\s+('+NUM.encode()+rb')\s+cm'),prefix)
        determinant=F(1)
        for a,b,c,d,tx,ty in cms:determinant*=F(a.decode())*F(d.decode())-F(b.decode())*F(c.decode())
        pdf_areas=[a*dec(abs(determinant)*F(127,360)**2) for a in loop_areas(pdf_commands(cut))]
        svgfile=next(f for f in export.glob('page-*.svg') if f'data-part-id="{pid}"' in f.read_text(encoding='utf-8'))
        svg=ET.parse(svgfile).getroot();assert svg.attrib['width']=='210mm' and svg.attrib['height']=='297mm' and not svg.findall('.//s:image',ns)
        role=svg.find('.//s:g[@data-role="CUT"]',ns)
        if role is None:role=svg.find('.//s:g[@id="CUT"]',ns)
        if role is None:
            role=next(x for x in svg.findall('.//s:g',ns) if x.attrib.get('id','').endswith('-CUT'))
        commands=[]
        for path in role.findall('.//s:path',ns):commands.extend(svg_commands(path.attrib['d']))
        svg_areas=loop_areas(commands);assert len(svg_areas)==len(pdf_areas)
        kind=('wall' if len(svg_areas)==2 else 'gothic') if fixture=='B1' else ('ring' if len(svg_areas)==2 else 'disk') if fixture=='B2' else 'bezier'
        lo,hi=source_interval(kind,saved['scale']);tol=max(D('.01'),lo*D('1e-6'))
        errors={name:max(abs(net(a)-lo),abs(net(a)-hi)) for name,a in [('svg',svg_areas),('pdf',pdf_areas)]}
        assert max(errors.values())<=tol,(kind,errors,tol)
        report['vectors'].append({'kind':kind,'page_svg':str(svgfile.relative_to(ROOT)),'part_id':pid,'svg_native_command_counts':dict(Counter(x[0] for x in commands)),'true_cut_loops':len(svg_areas),'source_area_interval_mm2':[str(lo),str(hi)],'actual_svg_net_mm2':str(net(svg_areas)),'actual_pdf_net_mm2':str(net(pdf_areas)),'direct_source_error_upper_mm2':{k:str(v) for k,v in errors.items()},'original_area_tolerance_mm2':str(tol),'pdf_no_image':True})

for p in sorted(E.glob('pc007a-loft-*-inkscape-a46*-run01/editor-results.json')):
    d=data(p);assert d['status']=='PASS' and d['source_sha']==CODE
    assert p.read_bytes()==blob(p.relative_to(ROOT));folder=p.parent
    for rel,h in d['files_sha256'].items():
        f=folder/rel;assert sha(f.read_bytes())==h and f.read_bytes()==blob(f.relative_to(ROOT))
    origin=Path(d['origin_source']);assert (folder/'editor-original.svg').read_bytes()==origin.read_bytes()
    for rel,h in d['origin_bundle_sha256'].items():assert sha((origin.parent/rel).read_bytes())==h
    assert d['script_sha256']==sha((ARCHIVE/'tools/authoring/editor_probe.py').read_bytes())
    edit=d['native_gui_text_edit'];assert edit['text']=='Žluťoučký – vlastní díl' and edit['foreground_verified_before_each_chord'] and edit['own_pid'] and edit['own_hwnd']
    edited=ET.parse(folder/'editor-edited.svg').getroot();assert any(''.join(t.itertext())==edit['text'] for t in edited.findall('.//s:text',ns))
    report['editor'].append({'run':folder.name,'source_original_exact':True,'all4_output_hashes_and_original_bundle_equal':True,'source_sha':CODE,'native_gui_text_edit':edit,'assertions':d.get('assertions',{})})

suite=ET.parse(E/'pc007a-integrated-suite-a46f179-run01.xml').getroot();ss=suite.find('testsuite');assert ss is not None
assert [int(ss.attrib[k]) for k in ['tests','failures','errors','skipped']]==[1179,0,0,0]
old=ET.parse(E/'pc007a-integrated-suite-73f3437-run02.xml').getroot()
identity=lambda t:Counter((x.attrib.get('classname'),x.attrib['name']) for x in t.iter('testcase'))
removed=list((identity(old)-identity(suite)).elements());added=list((identity(suite)-identity(old)).elements())
assert removed==[('tests.authoring.test_loft_curve_compaction','test_v2_cache_stales_on_load_preserving_raw_file_source_layout_and_frame')]
assert any('preserving_raw_file_source_layout_frame[ANALYTIC_SIGNED_CREASES_INTRINSIC_AREA_EXACT_COLLINEAR_CUT_V2]' in name for _,name in added)
report['full_suite']={'actual':dict(ss.attrib),'historical_V2_test_renamed_and_parametrized_with_V3_not_omitted':True,'renamed':removed,'added_including_rename':added,'prior_access_violation_cause':'UNRESOLVED; summary only, full stderr absent; later PASS does not diagnose cause'}
changed=git('diff','--name-only',CODE,META).decode().splitlines();missing=[];links=0
for rel in changed:
    if not rel.endswith('.md'):continue
    text=blob(Path(rel)).decode('utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if target.startswith(('http:','https:','mailto:','#')):continue
        dest=(ROOT/rel).parent/target.split('#')[0];links+=1
        if not dest.exists():missing.append((rel,target))
assert not missing,missing
q=json.loads(blob(Path('05_WORK_QUEUE.json')));assert q['product_gate']['accepted_by_owner'] and q['product_gate']['status']=='PO_ACCEPTED'
assert q['current_delivery']['status']=='IN_PROGRESS' and q['cross_cutting_usability']['participants_observed']==0
t=next(t for t in q['tickets'] if t['id']=='PC-007A');assert t['status']=='IN_PROGRESS' and 'whole AC not closed' in t['acceptance_state']['AC-AU09']
report['metadata_audit']={'sha':META,'changed_paths':len(changed),'all_changed_markdown_local_links_exist':links,'product_gate_accepted_contract_only':True,'whole_ticket_and_P2_not_closed':True,'novice_count':0,'release_readiness':q['release_readiness'],'SK012':'matches own narrow V4 transfer verdict; further PC008/general/human effectiveness pending'}
report['verdict']='PASS_IN_B1_B2_BEZIER_TECHNICAL_INTEGRATION_SCOPE_NOT_WHOLE_PC007A_P2_NOVICE_PHYSICAL'
(E/'pc007a-loft-integration-review-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'verdict':report['verdict'],'native':len(report['native']),'editor':len(report['editor']),'vectors':report['vectors'],'metadata':report['metadata_audit']},ensure_ascii=False,indent=2))
