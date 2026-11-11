"""Own D writer oracles use author planes and actual output bytes."""
import copy,hashlib,json,math,re,xml.etree.ElementTree as ET
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
import pytest
from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter import author_export
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.segmented_output_validation import validate_segmented_snapshot


def source(*,large=False,tab=False):
    p=AuthorProject.new(scale=1)
    x,y,z=(400,.02,1200) if large else (16,8,12)
    a=p.add_profile([[0,0],[x,0],*([[2*x,0]] if large else [])],closed=False)
    b=p.add_profile([[0,0],[x,0],[2*x,y]] if large else [[0,0],[x,y]],closed=False,plane=dict(origin=[0,0,z],u=[1,0,0],v=[0,1,0]))
    s=p.add_loft(a,b,correspondences=[dict(first_segment_id=first.id,
        second_segment_id=second.id,first_interval=[0,1],second_interval=[0,1])
        for first,second in zip(p.profiles[a].segments,p.profiles[b].segments)])
    limit=.25 if large else .26
    preview=p.preview_segmented_variant(s,max_deviation_mm=limit)
    assert preview['can_confirm'],preview['message']
    v=p.add_segmented_variant(s,max_deviation_mm=limit,preview_digest=preview['preview_digest'])
    rows=p.segmented_variants[v].triangle_bindings
    p.pages[0].width_mm=8000 if large else 210
    p.pages[0].height_mm=8000 if large else 297
    p.set_placements({r['part_id']:dict(page_id=p.pages[0].id,x_mm=2000+(i%2)*3000 if large else 25+(i%4)*35,
        y_mm=2000+(i//2)*3000 if large else 25+(i//4)*35) for i,r in enumerate(rows)})
    owner=None
    if tab:
        p.set_material_profile(crease_zone_mm=.05);p.recompute()
        if large:
            r=rows[0];edge=p.profiles[r['profile_id']].segments[0].id
            receiver=p.add_profile([[0,0],[x,0],[x,20],[0,20]])
            target=p.add_surface(receiver)
            joint=p.place_and_connect_edges(r['surface_id'],edge,target,p.profiles[receiver].segments[0].id,angle_deg=90)
            p.set_placement(p.surfaces[target].part_id,p.pages[0].id,7000,1000)
        else:
            uses=p.segmented_variants[v].paired_seams[0]['uses'];byid={r['id']:r for r in rows}
            r,t=(byid[u['triangle_id']] for u in uses)
            joint=p.connect_edges(r['surface_id'],uses[0]['edge_id'],t['surface_id'],uses[1]['edge_id'])
        p.set_tab(joint,owner=r['surface_id'],width_mm=.3,shape='triangle');owner=r['part_id']
    issues=p.validate_layout()
    assert all(i.severity=='warning' for i in issues),[(i.severity,i.code) for i in issues]
    for issue in issues:p.acknowledge(issue.id)
    return p,s,v,owner


def triangle_area(points):
    p=[tuple(map(Fraction,row)) for row in points]
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1])))/2


@pytest.fixture(scope='module')
def small_bundle(tmp_path_factory):
    p,s,v,_=source();snapshot=p.snapshot();out=tmp_path_factory.mktemp('own-D')/'bundle'
    author_export.export_all(snapshot,out)
    return p,s,v,snapshot,out


def test_direct_plane_oracle_against_actual_svg_tokens_and_pdf(small_bundle):
    from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions
    p,s,v,snapshot,out=small_bundle
    manifest=json.loads((out/'.author-export.json').read_text(encoding='utf8'))
    records=manifest['actual_curve_output_checks']['segmented_variants']['parts']
    actual_pdf=read_pdf_cut_regions(out/'model.pdf')['parts']
    ns='{http://www.w3.org/2000/svg}'
    actual_svg={}
    for path in out.glob('*.svg'):
        root=ET.parse(path).getroot()
        for group in root.findall(f'{ns}g[@data-part-id]'):
            cut=group.find(f"{ns}g[@data-role='CUT']")
            if cut is None:
                cut=next(g for g in group if g.get('id','').endswith('-CUT'))
            paths=cut.findall(f'{ns}path');assert len(paths)==1
            tokens=re.findall(r'[MLZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',paths[0].get('d'))
            points=[];i=0
            while i<len(tokens):
                op=tokens[i];i+=1
                if op=='Z':continue
                assert op in ('M','L')
                points.append([Fraction(tokens[i]),Fraction(tokens[i+1])]);i+=2
            actual_svg[group.get('data-part-id')]=triangle_area(points)
    assert set(actual_svg)==set(actual_pdf)==p.material_part_ids()
    for row in p.segmented_variants[v].triangle_bindings:
        pid=row['part_id'];profile=p.profiles[row['profile_id']]
        u,w=(tuple(map(Fraction,getattr(profile.plane,k))) for k in ('u','v'))
        points=[tuple(map(Fraction,vert.point)) for vert in profile.vertices]
        vectors=[tuple((q[0]-points[0][0])*x+(q[1]-points[0][1])*y for x,y in zip(u,w)) for q in points[1:]]
        a,b=vectors;cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        sq=sum(c*c for c in cross)
        with localcontext() as context:
            context.prec=80
            expected=(Decimal(sq.numerator)/Decimal(sq.denominator)).sqrt()/2
            observed=Decimal(actual_svg[pid].numerator)/Decimal(actual_svg[pid].denominator)
            assert abs(expected-observed)<Decimal('.01')
            low,high=map(Fraction,records[pid]['source_plane_body_area_exact'])
            # Squaring positive rational endpoints proves sqrt containment
            # exactly; a rounded Decimal oracle can lie outside an 84-digit box.
            assert low>0 and 4*low*low<=sq<=4*high*high
        pdf_points=[c[1:] for c in actual_pdf[pid]['loops'][0] if c[0] in ('M','L')]
        assert abs(triangle_area(pdf_points)-actual_svg[pid])<Fraction(1,100)
    # The retained target is never upgraded to EXACT by successful vectors.
    assert p.loft_status(s)['status']!='EXACT'


@pytest.mark.parametrize('mutation',['omit_all','equal_area_cut','extra_tab','reference_mask','source_plane','status','deep','nan','uuid'])
def test_closed_source_binding_negatives(small_bundle,mutation):
    _,_,_,snapshot,_=small_bundle;data=copy.deepcopy(snapshot)
    page=data['pages'][0];part=page['parts'][0];checks=data['construction_checks']
    if mutation=='omit_all':
        checks.pop('segmented_source_project');checks['segmented_variants']={}
        data['coverage']['expected_segmented_variant_ids']=[]
    elif mutation=='equal_area_cut':
        for q in part['paths']['CUT'][0]['points']:q[0]+=1
    elif mutation=='extra_tab':part['paths']['TABS'].append(copy.deepcopy(part['paths']['CUT'][0]))
    elif mutation=='reference_mask':data['coverage']['reference_surface_ids'].extend(part['surface_ids'])
    elif mutation=='source_plane':
        row=next(iter(checks['segmented_variants'].values()))['triangle_bindings'][0]
        checks['segmented_source_project']['profiles'][row['profile_id']]['plane']['u'][0]*=1.001
    elif mutation=='status':next(iter(checks['segmented_variants'].values()))['status']='EXACT'
    elif mutation=='deep':
        node=[];checks['segmented_source_project']['unexpected']=node
        for _ in range(65):child=[];node.append(child);node=child
    elif mutation=='nan':checks['segmented_source_project']['scale']=float('nan')
    else:part['flattening']['target_surface_id']=part['id']
    with pytest.raises(CurveOutputError):validate_segmented_snapshot(data)


def test_cache_is_immutable_and_snapshot_source_is_detached(small_bundle):
    p,_,_,snapshot,_=small_bundle;old=copy.deepcopy(snapshot);working=copy.deepcopy(snapshot)
    before=p.to_dict();bindings=validate_segmented_snapshot(working)
    p.name='live changed after snapshot'
    assert snapshot==old
    first=next(iter(bindings));bindings[first]['report']['mode']='EXACT'
    # Returned binding aliases its caller, but immutable cache must not change.
    assert next(iter(validate_segmented_snapshot(old).values()))['report']['mode']=='APPROXIMATE'
    p.name=before['name']


def test_actual_malformed_transform_fails_atomically(small_bundle,monkeypatch,tmp_path):
    import shutil
    _,_,_,snapshot,existing=small_bundle;out=tmp_path/'old';shutil.copytree(existing,out)
    (out/'foreign.txt').write_bytes(b'foreign\x00bytes')
    before={x.name:x.read_bytes() for x in out.iterdir()};writer=author_export._svg
    def poison(*args,**kwargs):
        result=writer(*args,**kwargs);path=args[4]
        text=path.read_text(encoding='utf8')
        # Unsupported three-operand translation must be rejected as serialized.
        text=text.replace('translate(', 'translate(1.00000000000000001 ',1)
        path.write_text(text,encoding='utf8');return result
    monkeypatch.setattr(author_export,'_svg',poison)
    with pytest.raises(CurveOutputError):author_export.export_all(snapshot,out)
    assert {x.name:x.read_bytes() for x in out.iterdir()}==before


def test_precise_actual_svg_translation_retains_lexeme(small_bundle,tmp_path):
    from archpapercraft.exporter.svg_curve_validation import read_svg_cut_regions
    _,_,_,snapshot,out=small_bundle
    original=next(out.glob('*.svg'));root=ET.parse(original).getroot()
    group=root.find('{http://www.w3.org/2000/svg}g[@data-part-id]')
    group.set('transform',re.sub(r'translate\([^ ]+', 'translate(25.00000000000000001',group.get('transform')))
    changed=tmp_path/'precise.svg';ET.ElementTree(root).write(changed,encoding='utf-8',xml_declaration=True)
    result=read_svg_cut_regions(changed,author_export._curve_output_expectations(snapshot))
    actual=result['parts'][group.get('data-part-id')]['placement'][0]
    assert actual==Fraction('25.00000000000000001') and actual!=Fraction(25)


def test_failure_after_first_owned_publication_restores_all_and_foreign(small_bundle,tmp_path,monkeypatch):
    import shutil
    from archpapercraft.exporter.author_export import ExportWriteError
    _,_,_,snapshot,existing=small_bundle;out=tmp_path/'old';shutil.copytree(existing,out)
    (out/'foreign.bin').write_bytes(b'\x00untouched foreign\xff')
    before={x.name:x.read_bytes() for x in out.iterdir()}
    original=author_export.os.replace;published=[]
    def fail_second(a,b):
        if Path(a).parent.name=='new' and Path(b).parent==out:
            if published:raise OSError('own review second owned publication fault')
            published.append(str(b))
        return original(a,b)
    monkeypatch.setattr(author_export.os,'replace',fail_second)
    with pytest.raises(ExportWriteError):author_export.export_all(snapshot,out)
    assert len(published)==1
    assert {x.name:x.read_bytes() for x in out.iterdir()}==before


def test_tab_does_not_relax_source_body_area_budget(monkeypatch,tmp_path):
    p,s,v,pid=source(large=True,tab=True)
    snapshot=p.snapshot();binding=next(r for r in p.segmented_variants[v].triangle_bindings if r['part_id']==pid)
    part=next(x for page in snapshot['pages'] for x in page['parts'] if x['id']==pid)
    body=p.parts[pid].polygons[binding['surface_id']][0]
    base=triangle_area(body);union=triangle_area(part['paths']['CUT'][0]['points'])
    assert base>10000 and union>base
    # Keep the hinge and the entire tab fixed. Move only the opposite BODY
    # vertex: exact body and CUT area both increase by the same small amount.
    cut=part['paths']['CUT'][0]['points']
    candidates=[point for point in body if any(point==q for q in cut)]
    hinge=part['paths']['TABS'][0]['points']
    moving=next(point for point in candidates if not any(point==q for q in hinge))
    index=next(i for i,point in enumerate(cut) if point==moving)
    # The midpoint falls strictly between the body-only and union-derived
    # relative budgets. The body itself violates the normative budget.
    delta=float((base+union)/2000000)
    before=triangle_area(cut)
    previous,following=cut[index-1],cut[(index+1)%len(cut)]
    derivative_x=Fraction(str(following[1]))-Fraction(str(previous[1]))
    derivative_y=Fraction(str(previous[0]))-Fraction(str(following[0]))
    signed=sum(Fraction(a[0])*Fraction(b[1])-Fraction(a[1])*Fraction(b[0]) for a,b in zip(cut,cut[1:]+cut[:1]))
    derivative_x=derivative_x/2*(1 if signed>0 else -1)
    derivative_y=derivative_y/2*(1 if signed>0 else -1)
    coordinate=0 if abs(derivative_x)>=abs(derivative_y) else 1
    derivative=derivative_x if coordinate==0 else derivative_y
    replacement=list(moving);replacement[coordinate]+=delta/float(derivative)
    changed=copy.deepcopy(cut);changed[index]=replacement
    actual_delta=triangle_area(changed)-before
    assert base/1000000<actual_delta<union/1000000
    original_svg,original_pdf=author_export._svg,author_export._pdf
    def changed_value(value):
        value=copy.deepcopy(value)
        for page in value['pages'] if 'pages' in value else [value]:
            for x in page['parts']:
                if x['id']==pid:x['paths']['CUT'][0]['points'][index]=replacement
        return value
    def svg(page,*args,**kwargs):return original_svg(changed_value(page),*args,**kwargs)
    def pdf(data,*args,**kwargs):return original_pdf(changed_value(data),*args,**kwargs)
    monkeypatch.setattr(author_export,'_svg',svg);monkeypatch.setattr(author_export,'_pdf',pdf)
    out=tmp_path/'body-area-poison'
    try:author_export.export_all(snapshot,out)
    except CurveOutputError:return # Required safe refusal of this actual body change.
    manifest=json.loads((out/'.author-export.json').read_text(encoding='utf8'))
    record=manifest['actual_curve_output_checks']['segmented_variants']['parts'][pid]
    witness=dict(part_id=pid,source_body_area_exact=str(base),source_union_area_exact=str(union),
        body_only_budget_exact=str(base/1000000),changed_body_and_union_delta_exact=str(actual_delta),
        published_record=record,artifacts={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir()})
    (Path(__file__).parent/'pc008-output-review-tab-area-witness.json').write_text(json.dumps(witness,indent=2)+'\n',encoding='utf8')
    pytest.fail('Actual body area exceeds body-only normative budget, but bundle was VERIFIED')
