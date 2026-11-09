"""Independent exact-token artifact readback and negative source/output probes."""
import copy
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter import author_export
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.loft_output_validation import validate_loft_snapshot

HERE=Path(__file__).parent
ROOT=HERE.parents[3]
SOURCE='3f4ece8e54081164a1f5731518056712930ac14b'
EVIDENCE='18fad42ea7dc61f730576d540578aa46d277197a'
ART=HERE/'pc007a-loft-output-3f4ece8'
assert Path(author_export.__file__).resolve().is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve())
NS='{http://www.w3.org/2000/svg}'
PI=Q('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def hashes(directory):return {str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file()}


def parse_svg_cut(path):
    root=ET.parse(path).getroot();assert root.tag==NS+'svg'
    groups=[g for g in root.findall(NS+'g') if g.get('data-part-id')]
    assert len(groups)==1
    group=groups[0];cuts=group.findall(NS+"g[@data-role='CUT']/"+NS+'path');assert len(cuts)==1
    tokens=re.findall(r'[MLCZ]|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',cuts[0].get('d'))
    result=[];i=0
    while i<len(tokens):
        op=tokens[i];n={'M':2,'L':2,'C':6,'Z':0}[op]
        result.append([op,*map(Q,tokens[i+1:i+n+1])]);i+=n+1
    assert i==len(tokens) and result[-1]==['Z']
    return result,{'part_id':group.get('data-part-id'),'roles':[g.get('data-role') for g in group.findall(NS+'g')],'width_mm':str(Q(root.get('width')[:-2])),'height_mm':str(Q(root.get('height')[:-2])),'placement':group.get('transform')}


def parse_pdf_cut(path):
    """Independent restricted own-writer reader, raw decompressed bytes only.

    These archived probes have one page/part. pypdf only decompresses streams;
    original decimal operands are parsed directly to Fraction before decoding.
    Exact Green area transforms by actual serialized CTM determinant, so its
    translation/MediaBox top-origin choice cannot cancel missing precision.
    """
    reader=PdfReader(path);assert len(reader.pages)==1
    raw=reader.pages[0].get_contents().get_data()
    assert len(re.findall(rb'/APPart_[^\s]+ BMC',raw))==1
    prefix=raw.split(b'/APPart_',1)[0]
    number=rb'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
    mats=re.findall(rb'('+number+rb'(?:\s+'+number+rb'){5})\s+cm',prefix)
    assert len(mats)==3 # identity, page mm/flip, part placement; no hidden q.
    determinant=Q(1)
    for matrix in mats:
        a,b,c,d,e,f=map(lambda t:Q(t.decode('ascii')),matrix.split());determinant*=a*d-b*c
    block=re.search(rb'/APRole_CUT BMC(.*?)EMC',raw,re.S)[1]
    body=re.search(rb'\bn\s+(.+?)\s+S\s*$',block,re.S)[1]
    tokens=body.split();result=[];operands=[]
    for token in tokens:
        if token in (b'm',b'l',b'c',b'h'):
            n={b'm':2,b'l':2,b'c':6,b'h':0}[token];assert len(operands)==n
            result.append([{b'm':'M',b'l':'L',b'c':'C',b'h':'Z'}[token],*operands]);operands=[]
        else:
            assert re.fullmatch(number,token);operands.append(Q(token.decode('ascii')))
    assert not operands and result[-1]==['Z']
    media=re.findall(rb'/MediaBox\s*\[([^]]+)\]',path.read_bytes());assert len(media)==1
    box=list(map(lambda t:Q(t.decode('ascii')),media[0].split()))
    return result,abs(determinant)*Q(127,360)**2,{'ctm_tokens':[m.decode('ascii') for m in mats],'media_box_exact':list(map(str,box)),'page_size_mm':[str((box[i+2]-box[i])*Q(127,360)) for i in (0,1)]}


def native_green(commands):
    """Own scalar power-polynomial Green integral, not production area helper."""
    total=Q(0);current=start=None
    for cmd in commands:
        op=cmd[0]
        if op=='M':current=start=tuple(cmd[1:]);continue
        end=start if op=='Z' else tuple(cmd[-2:])
        if op in ('L','Z'):total+=(current[0]*end[1]-current[1]*end[0])/2
        elif op=='C':
            controls=[current,tuple(cmd[1:3]),tuple(cmd[3:5]),end]
            polys=[]
            for axis in (0,1):
                a,b,c,d=[p[axis] for p in controls]
                polys.append([a,3*(b-a),3*(a-2*b+c),d-3*c+3*b-a])
            x,y=polys
            total+=sum(Q(j,2*(i+j))*(x[i]*y[j]-y[i]*x[j]) for i in range(4) for j in range(1,4))
        else:raise AssertionError('Unsupported independent readback op')
        current=end
    return abs(total)


def gothic_oracle():
    # Independent half-angle integral; intrinsic H10/R32.5/c12.5/k6/5.
    # P=116+272t²+181t⁴ on[0,2/3], f=65sqrt(P)/(1+t²)².
    # Scalar chain-rule bounds with sqrt(P)>10, |P'|<600, |P''|<1600,
    # |P'''|<3000, |P''''|<4400 and reciprocal bounds[1,4,28,264,3144]
    # give |f''''|<1e8. Simpson remainder covers the WHOLE arc.
    n=4096
    with localcontext() as c:
        c.prec=80;end=Decimal(2)/3;step=end/n
        def f(t):return 65*(116+272*t*t+181*t**4).sqrt()/(1+t*t)**2
        total=f(Decimal(0))+f(end)
        for i in range(1,n):total+=(4 if i%2 else 2)*f(i*step)
        integral=Q(total*step/3)
        remainder=Q(end)*Q(step)**4*10**8/180+Q(1,10**55)
        # Bound actual binary source sweep against the rational terminal angle.
        report=json.loads((ART/'B1'/'.author-export.json').read_text(encoding='utf8'))
        source=next(iter(report['construction_checks']['lofts'].values()))['source_binding']['profiles'][0]
        sweep=source['segments'][0]['data']['sweep_deg']
        z=Q(2,3);atan=sum((-1 if i%2 else 1)*z**(2*i+1)/Q(2*i+1) for i in range(300));ae=z**601/601
        angle_error=abs(abs(Q(sweep))*PI/180-2*atan)+2*ae+Q(1,10**90)
        # Angular area density per arc <=500, including actual source endpoint.
        remainder+=500*angle_error
        return Q(11,5)*(integral-remainder)+440,Q(11,5)*(integral+remainder)+440


def test_exact_pinned_source_imports_and_committed_artifact_bytes():
    result=json.loads((ART/'results.json').read_text(encoding='utf8'));record={}
    for name,expected in result['artifact_sha256'].items():
        path=ART/name;assert sha(path)==expected
        git=subprocess.check_output(['git','show',EVIDENCE+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
        assert hashlib.sha256(git).hexdigest()==expected;record[name]=expected
    mods=['archpapercraft.exporter.author_export','archpapercraft.exporter.loft_output_validation','archpapercraft.exporter.curve_output_validation','archpapercraft.exporter.svg_curve_validation','archpapercraft.authoring.project','archpapercraft.authoring.loft_surface']
    imports={}
    for name in mods:
        mod=__import__(name,fromlist=['x']);p=Path(mod.__file__).resolve();assert p.is_relative_to(Path(os.environ['PC_REVIEW_SOURCE']).resolve());imports[name]={'path':str(p),'sha256':sha(p)}
    (HERE/'pc007a-loft-output-review-imports-and-hashes.json').write_text(json.dumps({'source_sha':SOURCE,'evidence_sha':EVIDENCE,'actual_imports':imports,'verified_git_artifacts':record},indent=2),encoding='utf8')


@pytest.mark.parametrize('model',['B1','LD02'])
def test_actual_stored_svg_pdf_against_independent_green_and_source_oracles(model):
    svg=next((ART/model).glob('*.svg'));pdf=ART/model/'model.pdf'
    svg_commands,sm=parse_svg_cut(svg);pdf_commands,pf,pm=parse_pdf_cut(pdf)
    assert [c[0] for c in svg_commands]==[c[0] for c in pdf_commands]
    assert set(sm['roles'])=={'CUT','TABS','ARTWORK','LABELS','GUIDES','FOLD_MOUNTAIN','FOLD_VALLEY'}
    assert sm['width_mm']=='210' and sm['height_mm']=='297'
    areas={'svg':native_green(svg_commands),'pdf':native_green(pdf_commands)*pf}
    ol,oh=gothic_oracle() if model=='B1' else (4000*PI,4000*(PI+Q(1,10**100)))
    budget=max(Q(1,100),ol/1000000)
    for area in areas.values():assert max(abs(area-ol),abs(area-oh))<=budget
    manifest=json.loads((ART/model/'.author-export.json').read_text(encoding='utf8'));sid=next(iter(manifest['construction_checks']['lofts']))
    proofs=manifest['actual_curve_output_checks']['lofts']['lofts'][sid]['outputs']
    for kind,area in areas.items():
        lower,upper=map(Q,proofs[kind]['area_exact']);assert lower<=area<=upper
    out={'source_sha':SOURCE,'model':model,'independent_source_interval':list(map(str,(ol,oh))),'norm_area_budget':str(budget),'actual_green_areas':{k:str(a) for k,a in areas.items()},'actual_area_float':{k:float(a) for k,a in areas.items()},'svg':sm,'pdf':pm,'svg_sha256':sha(svg),'pdf_sha256':sha(pdf),'native_command_counts':{k:sum(c[0]==k for c in svg_commands) for k in ('M','L','C','Z')}}
    (HERE/f'pc007a-loft-output-review-artifact-{model}.json').write_text(json.dumps(out,indent=2),encoding='utf8')


def project():
    p=AuthorProject.new(scale=1);a=p.add_profile([[0,0],[14,0],[14,2]],closed=False);b=p.copy_profile(a,plane={'origin':[0,0,7],'u':[1,0,0],'v':[0,1,0]})
    rows=[dict(first_segment_id=x.id,second_segment_id=y.id,first_interval=[0,1],second_interval=[0,1]) for x,y in zip(p.profiles[a].segments,p.profiles[b].segments)]
    sid=p.add_loft(a,b,correspondences=rows);pid=p.part_for_surface(sid);p.set_placement(pid,p.pages[0].id,30,30);return p,sid,pid


def test_same_area_cached_cut_swap_cannot_rebind_to_current_source():
    p,sid,pid=project();snap=p.snapshot();part=snap['pages'][0]['parts'][0];commands=part['paths']['CUT'][0]['commands'];old=native_green(commands)
    for c in commands:
        for i in range(1,len(c),2):c[i]+=.125
    assert native_green(commands)==old
    with pytest.raises(CurveOutputError):validate_loft_snapshot(snap)


@pytest.mark.parametrize('damage',['missing_registry','reverse_profiles','revision','frame','representation'])
def test_source_binding_and_empty_planar_registry_cannot_hide_actual_loft(damage):
    p,sid,pid=project();snap=p.snapshot();assert snap['construction_checks']['curve_profiles']=={}
    report=snap['construction_checks']['lofts'][sid]
    if damage=='missing_registry':snap['construction_checks']['lofts']={}
    elif damage=='reverse_profiles':report['source_binding']['profiles'].reverse()
    elif damage=='revision':report['feature_revision']+=1
    elif damage=='frame':report['paper_frame']['anchor_vertex_id']=p.profiles[next(iter(p.profiles))].vertices[-1].id
    else:report['representation']['position_error_bound_paper_mm']=0
    with pytest.raises(CurveOutputError):validate_loft_snapshot(snap)


def test_pure_loft_rotated_second_page_still_has_actual_output_guards(tmp_path):
    p,sid,pid=project();page=p.add_page();p.set_placement(pid,page,80,80,31)
    before=copy.deepcopy(p.to_dict());snap=p.snapshot();author_export.export_all(snap,tmp_path/'bundle')
    manifest=json.loads((tmp_path/'bundle'/'.author-export.json').read_text(encoding='utf8'))
    check=manifest['actual_curve_output_checks'];assert check['lofts']['status']=='VERIFIED'
    assert len(check['svg'])==2 and check['pdf']['parts'][pid]['page_index']==1
    assert p.to_dict()==before


def test_whole_source_budget_no_fresh_allowance_for_each_conversion(tmp_path,monkeypatch):
    # Independent fixture: 112 ->112.008 SVG ->112.016 PDF, .01 final budget.
    p,sid,pid=project();snap=p.snapshot();directory=tmp_path/'bundle';author_export.export_all(snap,directory);(directory/'foreign.dat').write_bytes(b'owner data\x00\xff');before=hashes(directory)
    svg0,pdf0=author_export._svg,author_export._pdf
    def svg(*args,**kwargs):
        svg0(*args,**kwargs);path=args[4];tree=ET.parse(path);cut=tree.find(f'.//{NS}g[@data-role="CUT"]/{NS}path');d=cut.get('d');cut.set('d',re.sub(r'(?<![\d.])7(?![\d.])','7.0005',d));tree.write(path,encoding='utf-8',xml_declaration=True)
    def pdf(*args,**kwargs):
        out=pdf0(*args,**kwargs);path=args[3];reader=PdfReader(path);writer=PdfWriter()
        for page in reader.pages:
            raw=page.get_contents().get_data();match=re.search(rb'/APRole_CUT BMC(.*?)EMC',raw,re.S);block=match[1];changed,n=re.subn(rb'(?<![\d.])7(?![\d.])',b'7.001',block);assert n>=2;raw=raw[:match.start(1)]+changed+raw[match.end(1):];stream=DecodedStreamObject();stream.set_data(raw);page[NameObject('/Contents')]=stream;writer.add_page(page)
        with path.open('wb') as f:writer.write(f)
        return out
    monkeypatch.setattr(author_export,'_svg',svg);monkeypatch.setattr(author_export,'_pdf',pdf)
    with pytest.raises(CurveOutputError) as caught:author_export.export_all(snap,directory)
    assert caught.value.report is not None,str(caught.value)
    outs=caught.value.report['lofts'][sid]['outputs']
    assert abs(float(Q(outs['svg']['source_to_actual_area_error_bound_exact']))-.008)<1e-9
    assert abs(float(Q(outs['pdf']['source_to_actual_area_error_bound_exact']))-.016)<1e-9
    assert hashes(directory)==before


def test_unavailable_actual_topology_budget_preserves_bundle_and_foreign_bytes(tmp_path,monkeypatch):
    from archpapercraft.exporter import loft_output_validation as validation
    p,sid,pid=project();snap=p.snapshot();d=tmp_path/'bundle';author_export.export_all(snap,d);(d/'foreign.dat').write_bytes(b'original');before=hashes(d)
    monkeypatch.setattr(validation,'LOFT_OUTPUT_MAX_NODES',0)
    with pytest.raises(CurveOutputError):author_export.export_all(snap,d)
    assert hashes(d)==before


def test_cold_binding_validation_can_recompute_approved_source_without_mutation(monkeypatch):
    # Record actual cold-cache behavior; this is not a human/latency acceptance.
    from archpapercraft.authoring import loft_surface
    from archpapercraft.exporter import loft_output_validation as validation
    p,sid,pid=project();snap=p.snapshot();before=copy.deepcopy(snap)
    validation._bound_source_native.cache_clear();loft_surface._analyze.cache_clear();loft_surface._bound_analysis.cache_clear()
    calls=[];original=loft_surface.flatten_loft
    def counted(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(loft_surface,'flatten_loft',counted)
    assert sid in validate_loft_snapshot(snap)
    assert len(calls)>=1 and snap==before
    (HERE/'pc007a-loft-output-review-cold-cache.json').write_text(json.dumps({'source_sha':SOURCE,'cold_flatten_calls':len(calls),'snapshot_unchanged':snap==before,'scope':'Cold source-binding recomputation is real; no OS/UI latency claim.'},indent=2),encoding='utf8')
