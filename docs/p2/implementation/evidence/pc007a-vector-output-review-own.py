"""Independent actual serialized PDF/SVG review, not source-surrogate tests."""
from fractions import Fraction
import hashlib
import json
import xml.etree.ElementTree as ET

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from archpapercraft.exporter.curve_output_validation import CurveOutputError, read_pdf_cut_regions, validate_pdf_curve_geometry
from archpapercraft.exporter.svg_curve_validation import validate_svg_curve_geometry

UNIT=Fraction(127,360)


def pdf(tmp_path,commands,name='own.pdf'):
    path=tmp_path/name
    writer=PdfWriter()
    page=writer.add_blank_page(width=360,height=360)
    stream=DecodedStreamObject()
    stream.set_data(commands.encode('ascii'))
    page[NameObject('/Contents')]=writer._add_object(stream)
    with path.open('wb') as f: writer.write(f)
    return path


def part(pid,path,role='CUT'):
    return f'/APPart_{pid} BMC /APRole_{role} BMC {path} EMC EMC '


def rect(x,y,w,h):
    return f'{x} {y} m {x+w} {y} l {x+w} {y+h} l {x} {y+h} l h S '


def expected(pid,count=1):
    return {pid:{'page_index':0,'loop_count':count,'name':'Own '+pid}}


def exact_page_pdf(tmp_path,page_fields):
    content=part('a',rect(10,10,10,10)).encode('ascii')
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
             b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
             ('<< /Type /Page /Parent 2 0 R '+page_fields+' /Resources << >> /Contents 4 0 R >>').encode('ascii'),
             b'<< /Length '+str(len(content)).encode('ascii')+b' >>\nstream\n'+content+b'\nendstream']
    raw=b'%PDF-1.4\n'
    offsets=[0]
    for index,obj in enumerate(objects,1):
        offsets.append(len(raw))
        raw+=str(index).encode('ascii')+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(raw)
    raw+=b'xref\n0 5\n0000000000 65535 f \n'
    raw+=b''.join(f'{offset:010d} 00000 n \n'.encode('ascii') for offset in offsets[1:])
    raw+=f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('ascii')
    path=tmp_path/'exact-page.pdf'
    path.write_bytes(raw)
    return path


def test_V01_original_pdf_numeric_lexeme_must_be_exact_or_refused(tmp_path):
    token='1.00000000000000001'
    path=pdf(tmp_path,part('a',f'{token} 1 m 10 1 l 10 10 l {token} 10 l h S'))
    try:
        actual=read_pdf_cut_regions(path)
    except CurveOutputError:
        return  # A truthful unsupported precision rejection is permitted.
    assert actual['parts']['a']['loops'][0][0][1]==Fraction(token)*UNIT


@pytest.mark.parametrize('field',['MediaBox','CropBox','Rotate','UserUnit'])
def test_V01_page_dictionary_numeric_lexemes_must_not_silently_round(tmp_path,field):
    options={
        'MediaBox':'/MediaBox [0 0 360.00000000000000001 360]',
        'CropBox':'/MediaBox [0 0 360 360] /CropBox [0 0 359.99999999999999999 360]',
        'Rotate':'/MediaBox [0 0 360 360] /Rotate 360.00000000000000001',
        'UserUnit':'/MediaBox [0 0 360 360] /UserUnit 1.00000000000000001',
    }
    path=exact_page_pdf(tmp_path,options[field])
    try:
        actual=read_pdf_cut_regions(path)
    except CurveOutputError:
        return
    if field=='MediaBox':
        assert actual['pages'][0]['width_mm']==Fraction('360.00000000000000001')*UNIT
    else:
        pytest.fail('Nonstandard exact '+field+' silently rounded into accepted page geometry')


def test_own_pdf_composite_ctm_and_y_reflection_use_actual_order_and_units(tmp_path):
    path=pdf(tmp_path,'q 1 0 0 1 10 20 cm 2 0 1 3 4 5 cm '+part('a','2 3 m 12 3 l 12 13 l 2 13 l h S')+'Q')
    loop=read_pdf_cut_regions(path)['parts']['a']['loops'][0]
    assert loop[0]==['M',21*UNIT,326*UNIT]
    assert loop[1]==['L',41*UNIT,326*UNIT]
    assert loop[2]==['L',51*UNIT,296*UNIT]


def test_own_graphics_restore_prevents_ctm_leaking_to_next_part(tmp_path):
    path=pdf(tmp_path,'q 2 0 0 2 10 10 cm '+part('a',rect(5,5,10,10))+'Q '+part('b',rect(5,5,10,10)))
    actual=read_pdf_cut_regions(path)
    assert actual['parts']['a']['loops'][0][0]==['M',20*UNIT,340*UNIT]
    assert actual['parts']['b']['loops'][0][0]==['M',5*UNIT,355*UNIT]


def test_own_actual_pdf_hole_void_allows_separate_insert(tmp_path):
    path=pdf(tmp_path,part('wall',rect(10,10,100,100)+rect(30,30,40,40))+part('insert',rect(40,40,10,10)))
    report=validate_pdf_curve_geometry(path,{**expected('wall',2),**expected('insert')})
    assert report['status']=='VALID' and report['separations'][0]['status']=='DISJOINT'
    assert report['pdf_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    json.dumps(report,allow_nan=False)


def test_own_cut_role_and_unclosed_curve_cannot_disappear_from_coverage(tmp_path):
    path=pdf(tmp_path,part('a',rect(10,10,10,10),'ARTWORK'))
    with pytest.raises(CurveOutputError): validate_pdf_curve_geometry(path,expected('a'))
    path=pdf(tmp_path,part('a','10 10 m 20 10 l 20 20 l 10 20 l S'))
    with pytest.raises(CurveOutputError): read_pdf_cut_regions(path)


def test_own_actual_cubic_hidden_crossing_blocks_geometrical_publication(tmp_path):
    content='0 100.0005 m 3 99.999 l 7 99.999 l 10 100.0005 l 10 100 l 0 100 l h S'
    content=content.replace('3 99.999 l 7 99.999 l 10 100.0005 l','3 99.999 7 99.999 10 100.0005 c')
    path=pdf(tmp_path,part('a',content))
    with pytest.raises(CurveOutputError): validate_pdf_curve_geometry(path,expected('a'))


@pytest.mark.parametrize('op',['W n','0 0 0 1 0 0 cm','Q'])
def test_own_unsupported_clipping_singularity_and_stack_never_pass(tmp_path,op):
    path=pdf(tmp_path,op+' '+part('a',rect(10,10,10,10)))
    with pytest.raises(CurveOutputError): read_pdf_cut_regions(path)


def test_own_svg_exact_decimal_not_source_curve_or_float_surrogate(tmp_path):
    roles=['CUT','FOLD_MOUNTAIN','FOLD_VALLEY','TABS','LABELS','ARTWORK','GUIDES']
    d='M 0 1.00000000000000000001 C 3 .99999999999999999999 7 .99999999999999999999 10 1.00000000000000000001 L 10 1 L 0 1 Z'
    body=''.join(f'<g data-role="{role}">'+(f'<path d="{d}"/>' if role=='CUT' else '')+'</g>' for role in roles)
    path=tmp_path/'actual.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100"><g data-part-id="a" transform="translate(10 10) rotate(0)">'+body+'</g></svg>',encoding='utf8')
    with pytest.raises(CurveOutputError): validate_svg_curve_geometry(path,expected('a'))


def test_own_real_arc_writer_has_actual_cubic_pdf_topology_and_distinct_svg_scope(tmp_path):
    from archpapercraft.authoring import AuthorProject
    from archpapercraft.exporter.author_export import export_all
    p=AuthorProject.new(scale=1)
    profile=p.add_profile([[0,0],[40,0],[40,40],[0,40]])
    hole=p.add_profile(segments=[{'kind':'arc','start':[25,20],'end':[15,20],'data':{'center':[20,20],'sweep_deg':180}},
                                 {'kind':'arc','start':[15,20],'end':[25,20],'data':{'center':[20,20],'sweep_deg':180}}])
    sid=p.add_surface(profile,[hole])
    pid=p.part_for_surface(sid)
    p.set_placement(pid,p.pages[0].id,60,60,23)
    target=tmp_path/'bundle'
    export_all(p.snapshot(),target)
    actual=read_pdf_cut_regions(target/'model.pdf')
    assert len(actual['parts'][pid]['loops'])==2
    assert any(c[0]=='C' for loop in actual['parts'][pid]['loops'] for c in loop)
    manifest=json.loads((target/'.author-export.json').read_text(encoding='utf8'))
    checks=manifest['actual_curve_output_checks']
    assert checks['pdf']['status']=='VALID'
    assert checks['pdf']['proof_scope']['physical_page_bounds']=='CERTIFIED_ACTUAL_COMMANDS'
    assert checks['svg'][0]['proof_scope']['same_page_part_separation']=='NOT_CHECKED_LOCAL_COORDINATES'
    bounds=manifest['pdf_geometry_precision']
    assert bounds['combined_position_error_bound_mm']<=bounds['required_digital_budget_mm']
