"""Independent integration oracles: actual serialized cubic Green integral."""
import copy
import hashlib
import importlib.util
import json
import math
from fractions import Fraction as F
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject
from archpapercraft.exporter import author_export as writer
from archpapercraft.exporter import curve_output_validation as pdfcheck
from archpapercraft.exporter.curve_output_validation import CurveOutputError,read_pdf_cut_regions


def integral(points):
    if len(points)==2:return (points[0][0]*points[1][1]-points[1][0]*points[0][1])/2
    xy=[]
    for axis in (0,1):
        a,b,c,d=(point[axis] for point in points)
        xy.append([a,3*(b-a),3*(c-2*b+a),d-3*c+3*b-a])
    x,y=xy
    return sum((x[i]*j*y[j]-y[i]*j*x[j])/F(2*(i+j)) for i in range(4) for j in range(1,4))


def loop_area(commands):
    total=F(0);current=start=None
    for command in commands:
        if command[0]=='M':current=start=tuple(command[1:])
        elif command[0]=='L':
            end=tuple(command[1:]);total+=integral([current,end]);current=end
        elif command[0]=='C':
            end=tuple(command[5:7]);total+=integral([current,tuple(command[1:3]),tuple(command[3:5]),end]);current=end
        elif command[0]=='Z':total+=integral([current,start]);current=start
        else:raise ValueError(command[0])
    return abs(total)


def wall():
    project=AuthorProject.new(scale=1)
    outer=project.add_profile([[0,0],[120,0],[120,100],[0,100]])
    hole=project.add_profile(segments=[
        {'kind':'arc','start':[80,50],'end':[40,50],'data':{'center':[60,50],'sweep_deg':180}},
        {'kind':'arc','start':[40,50],'end':[80,50],'data':{'center':[60,50],'sweep_deg':180}}])
    sid=project.add_surface(outer,[hole]);pid=project.part_for_surface(sid)
    project.set_placement(pid,project.pages[0].id,25,30)
    return project,pid


def hashes(directory):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}


def test_original_v02_actual_polynomial_hole_and_net_area_now_meet_norm(tmp_path):
    project,pid=wall();snapshot=project.snapshot();before=copy.deepcopy(snapshot)
    writer.export_all(snapshot,tmp_path/'bundle')
    record=read_pdf_cut_regions(tmp_path/'bundle/model.pdf')['parts'][pid]
    outer,hole=sorted((loop_area(loop) for loop in record['loops']),reverse=True)
    assert abs(float(outer)-12000)<1e-8
    assert abs(float(hole)-400*math.pi)<.01
    assert abs(float(outer-hole)-(12000-400*math.pi))<max(.01,1e-6*(12000-400*math.pi))
    assert snapshot==before


def test_rotated_actual_raw_ctm_and_green_integral_with_different_dimensions(tmp_path):
    project,pid=wall()
    project.set_placement(pid,project.pages[0].id,75,25,29)
    writer.export_all(project.snapshot(),tmp_path/'bundle')
    actual=read_pdf_cut_regions(tmp_path/'bundle/model.pdf')
    outer,hole=sorted((loop_area(loop) for loop in actual['parts'][pid]['loops']),reverse=True)
    assert abs(float(outer)-12000)<1e-8
    assert abs(float(outer-hole)-(12000-400*math.pi))<.010744
    from pypdf import PdfReader
    raw=PdfReader(tmp_path/'bundle/model.pdf').pages[0].get_contents().get_data()
    rotation=math.cos(math.radians(29))
    # Exact decimal tokens are read as emitted, not their pypdf float image.
    token=format(rotation,'.17f').rstrip('0').rstrip('.')
    assert token.encode()+b' ' in raw
    assert any(isinstance(v,F) for loop in actual['parts'][pid]['loops'] for cmd in loop for v in cmd[1:])


def test_four_coarse_attempts_only_and_every_old_or_foreign_byte_preserved(tmp_path,monkeypatch):
    project,pid=wall();snapshot=project.snapshot();directory=tmp_path/'bundle'
    writer.export_all(snapshot,directory)
    (directory/'author-note.txt').write_bytes(b'foreign author data\x00')
    before=hashes(directory);calls=[];original_pdf=writer._pdf;original_cubics=writer._arc_cubics
    def coarse(arc,*,tolerance_mm=None):return original_cubics(arc,tolerance_mm=.001)
    def counted(*args,**kwargs):calls.append(kwargs['arc_tolerance_mm']);return original_pdf(*args,**kwargs)
    monkeypatch.setattr(writer,'_arc_cubics',coarse);monkeypatch.setattr(writer,'_pdf',counted)
    with pytest.raises(CurveOutputError,match='plo') as caught:writer.export_all(snapshot,directory)
    assert caught.value.part_id==pid
    assert len(calls)==4 and all(math.isclose(v,1e-4*10**(-i),rel_tol=1e-14) for i,v in enumerate(calls))
    assert hashes(directory)==before
    assert not list(tmp_path.glob('.author-export-*'))


def test_actual_coarse_writer_recovers_with_exactly_two_attempts(tmp_path,monkeypatch):
    project,_=wall();monkeypatch.setattr(writer,'PDF_ARC_TOLERANCE_MM',.001)
    writer.export_all(project.snapshot(),tmp_path/'bundle')
    manifest=json.loads((tmp_path/'bundle/.author-export.json').read_text(encoding='utf8'))
    attempts=manifest['pdf_arc_approximation']['precision_attempts']
    assert len(attempts)==2
    assert attempts[0]['status']=='AREA_BUDGET_NOT_MET'
    assert attempts[1]['status']=='ACTUAL_GEOMETRY_AND_AREA_VERIFIED'


def test_other_geometry_failure_is_never_retried_and_preserves_bundle(tmp_path,monkeypatch):
    project,_=wall();directory=tmp_path/'bundle';writer.export_all(project.snapshot(),directory)
    before=hashes(directory);calls=[]
    def hard_failure(*args,**kwargs):calls.append(True);raise CurveOutputError('independent unsupported geometry')
    monkeypatch.setattr(pdfcheck,'validate_pdf_curve_geometry',hard_failure)
    with pytest.raises(CurveOutputError,match='independent'):writer.export_all(project.snapshot(),directory)
    assert len(calls)==1 and hashes(directory)==before


def checks(svglo,svghi,pdflo,pdfhi,base):
    return {'svg':[{'parts':{'p':{'material_area_bounds_mm2':{'lower':str(svglo),'upper':str(svghi)},'base_area_lower_bound_mm2':str(base)}}}],
            'pdf':{'parts':{'p':{'material_area_bounds_mm2':{'lower':str(pdflo),'upper':str(pdfhi)}}}}}


def test_relative_budget_uses_base_excluding_large_tabs():
    expected={'p':{'name':'base plus tabs','page_index':0}}
    # CUT area 1000000, but only 1000 is base: full CUT would wrongly allow 1mm2.
    with pytest.raises(CurveOutputError):writer._validate_vector_area_agreement(checks(1000000,1000000,F('1000000.1'),F('1000000.1'),1000),expected)
    result=writer._validate_vector_area_agreement(checks(1000000,1000000,F('1000000.009'),F('1000000.009'),1000),expected)
    assert F(result['comparisons']['p']['allowed_area_error_mm2'])==F('.01')


def test_interval_midpoint_agreement_does_not_hide_large_possible_area_error():
    expected={'p':{'name':'uncertain','page_index':0}}
    with pytest.raises(CurveOutputError):writer._validate_vector_area_agreement(checks(100,101,100,101,100),expected)
    result=writer._validate_vector_area_agreement(checks(100,100,100,100,0),expected)
    assert F(result['comparisons']['p']['allowed_area_error_mm2'])==F('.01')


def editor():
    spec=importlib.util.spec_from_file_location('review_editor_probe',Path(writer.__file__).resolve().parents[3]/'tools/authoring/editor_probe.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_editor_exact_decimal_relative_closure_is_canonical_but_nearby_is_not():
    probe=editor()
    assert probe._path_signature('M .1 .2 L .3 .4 l -.2 -.2 Z')==probe._path_signature('M .1 .2 L .3 .4 Z')
    assert probe._path_signature('M .1 .2 L .3 .4 L .10000000000000001 .2 Z')!=probe._path_signature('M .1 .2 L .3 .4 Z')


@pytest.mark.parametrize('segment',['C 1 2 3 4 0 0','A 1 1 0 1 1 0 0'])
def test_editor_closing_curve_cannot_be_replaced_by_z(segment):
    probe=editor()
    assert probe._path_signature('M 0 0 '+segment+' Z')!=probe._path_signature('M 0 0 Z')
