"""Independent rational D source, full-registry and persistence negative oracles."""
import copy
import hashlib
import json
import math
from fractions import Fraction as F

import pytest

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject,ProjectFormatError,ValidationError,load_project
from archpapercraft.authoring import segmented_surface as domain


def target():
    p=AuthorProject.new(scale=1)
    a=p.add_profile([[0,0],[16,0]],closed=False)
    b=p.add_profile([[0,0],[16,8]],closed=False,plane={'origin':[0,0,12],'u':[1,0,0],'v':[0,1,0]})
    sid=p.add_loft(a,b,correspondences=[{'first_segment_id':p.profiles[a].segments[0].id,'second_segment_id':p.profiles[b].segments[0].id,'first_interval':[0,1],'second_interval':[0,1]}])
    return p,sid,a,b


@pytest.fixture(scope='module')
def state():
    p,sid,a,b=target();preview=p.preview_segmented_variant(sid,max_deviation_mm=.26)
    assert preview['can_confirm'],preview
    vid=p.add_segmented_variant(sid,preview_digest=preview['preview_digest'],max_deviation_mm=.26)
    return p.to_dict(),sid,a,b,vid


def restored(state):
    data,sid,a,b,vid=state
    return AuthorProject.from_dict(copy.deepcopy(data)),sid,a,b,vid


def layout(p,vid):
    p.add_page()
    for index,r in enumerate(p.segmented_variants[vid].triangle_bindings):
        p.set_placement(r['part_id'],p.pages[index%2].id,25+(index//2%4)*35,25+(index//8)*40,0,
                        position_locked=index==0,rotation_locked=index==0)


def source(u,v):return (16*u,8*u*v,12*v)


def actual_vertices(profile):
    plane=profile.plane
    return [tuple(F(plane.origin[i])+F(plane.u[i])*F(point[0])+F(plane.v[i])*F(point[1]) for i in range(3)) for point in profile.points]


def test_own_rational_bilinear_midpoints_have_true_nonzero_error_and_finite_frame_reserve(state):
    p,sid,a,b,vid=restored(state);variant=p.segmented_variants[vid]
    assert p.loft_status(sid)['status']!='EXACT'
    report=variant.certificate['math'];frame=variant.certificate['material_frame']
    assert report['patches'][0]['developability_determinant_exact']=='-1536'
    total=F(frame['max_target_to_material_deviation_paper_mm_exact'])
    raw_bound=F(report['max_surface_deviation_paper_mm_exact'])
    assert 0<raw_bound<=total<=F(.26)
    observed=F(0)
    for record in variant.triangle_bindings:
        uv=[tuple(map(F,point)) for point in record['parameter_vertices_exact']]
        actual=actual_vertices(p.profiles[record['profile_id']])
        # Convex barycentric points use the actual finite plane, not its ideal source triangle.
        for weights in ((F(1,3),)*3,(F(1,2),F(0),F(1,2))):
            u,v=(sum(w*point[i] for w,point in zip(weights,uv)) for i in (0,1))
            point=tuple(sum(w*x[i] for w,x in zip(weights,actual)) for i in range(3))
            delta=tuple(x-y for x,y in zip(point,source(u,v)))
            assert sum(d*d for d in delta)<=total*total
            observed=max(observed,abs(delta[1]))
    assert observed>F(1,20)  # Actual approximation must not be mislabeled exact.
    assert frame['normal_scope'].startswith('SOURCE_NORMAL_FIELD_TO_ACTUAL_MATERIAL_PLANE')


def test_complete_seam_edges_bind_real_triangle_uv_in_opposite_directions(state):
    p,sid,a,b,vid=restored(state);variant=p.segmented_variants[vid]
    by_id={r['id']:r for r in variant.triangle_bindings}
    for seam in variant.paired_seams:
        left,right=seam['uses'];pairs=[]
        for use in (left,right):
            record=by_id[use['triangle_id']];profile=p.profiles[record['profile_id']]
            segment=profile.segment(use['edge_id']);index=record['edge_ids'].index(segment.id)
            pair=[record['parameter_vertices_exact'][index],record['parameter_vertices_exact'][(index+1)%3]]
            assert pair==use['parameter_endpoints_exact'];pairs.append(pair)
        assert pairs[0]==list(reversed(pairs[1]))


def test_material_normals_cover_independent_rational_source_normal_field(state):
    p,sid,a,b,vid=restored(state);variant=p.segmented_variants[vid]
    bound=float(F(variant.certificate['material_frame']['max_material_normal_angle_deg_exact']))
    assert 0<bound<180
    largest=0
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    for record in variant.triangle_bindings:
        actual=actual_vertices(p.profiles[record['profile_id']])
        edges=[tuple(point[i]-actual[0][i] for i in range(3)) for point in actual[1:]]
        normal=cross(*edges)
        uv=[tuple(map(F,point)) for point in record['parameter_vertices_exact']]
        uv.append(tuple(sum(point[i] for point in uv)/3 for i in (0,1)))
        for u,v in uv:
            # S_u cross S_v for S=(16u,8uv,12v), independent of product helpers.
            source_normal=(96*v,F(-192),128*u)
            dot=sum(x*y for x,y in zip(normal,source_normal));assert dot>0
            turn=cross(normal,source_normal)
            angle=math.degrees(math.atan2(math.sqrt(float(sum(x*x for x in turn))),float(dot)))
            largest=max(largest,angle);assert angle<=bound
    assert largest>1


def test_layout_snapshot_reference_coverage_and_save_reopen_are_separate(state,tmp_path):
    p,sid,a,b,vid=restored(state);layout(p,vid)
    assert not p.validate_layout()
    snapshot=p.snapshot();coverage=snapshot['coverage']
    expected={r['part_id'] for r in p.segmented_variants[vid].triangle_bindings}
    assert set(coverage['expected_part_ids'])==expected
    assert coverage['reference_surface_ids']==[sid] and sid not in coverage['expected_surface_ids']
    assert len(coverage['all_construction_surface_ids'])==len(expected)+1
    assert snapshot['construction_checks']['reference_targets'][sid]['status']!='EXACT'
    assert all(part['flattening']['mode']=='APPROXIMATE' for pg in snapshot['pages'] for part in pg['parts'])
    before=copy.deepcopy(p.to_dict());path=tmp_path/'derived.apcraft';p.save(path)
    assert load_project(path).to_dict()==before


def test_source_revision_name_changes_vs_real_source_mutation(state):
    p,sid,a,b,vid=restored(state)
    p.profiles[a].name='Author name';p.profiles[a].revision+=1
    p.surfaces[sid].name='Target name';p.surfaces[sid].revision+=1
    assert p.segmented_variant_status(vid)['status']=='APPROXIMATE'
    p.profiles[a].vertices[1].point[0]+=F(1,2)
    assert p.segmented_variant_status(vid)['status']=='STALE'


def test_changed_material_remains_unresolved_even_after_recompute(state):
    p,sid,a,b,vid=restored(state);layout(p,vid)
    record=p.segmented_variants[vid].triangle_bindings[0];profile=p.profiles[record['profile_id']]
    p.move_vertex(profile.id,profile.vertices[-1].id,[profile.points[-1][0],profile.points[-1][1]+.5])
    p.recompute([record['part_id']])
    assert p.segmented_variant_status(vid)['status']=='UNRESOLVED'
    with pytest.raises(ValidationError):p.snapshot()


@pytest.mark.parametrize('damage',['certificate','fake_child_hash','seam_edge','generation_cycle','duplicate_uuid','unknown_record'])
def test_closed_registry_rejects_forgery_even_after_attacker_rehashes_payload(state,damage):
    p,sid,a,b,vid=restored(state);v=p.segmented_variants[vid]
    if damage=='certificate':v.certificate['material_frame']['max_target_to_material_deviation_paper_mm_exact']='0'
    elif damage=='fake_child_hash':
        r=v.triangle_bindings[0];profile=p.profiles[r['profile_id']];child=p.surfaces[r['surface_id']]
        profile.vertices[-1].point[0]+=.25;r['material_input_digest']=domain._geometry_binding(profile,child)
    elif damage=='seam_edge':v.paired_seams[0]['uses'][0]['edge_id']=v.triangle_bindings[0]['vertex_ids'][0]
    elif damage=='generation_cycle':v.previous_variant_id=vid
    elif damage=='duplicate_uuid':v.paired_seams[0]['id']=v.triangle_bindings[0]['id']
    else:v.triangle_bindings[0]['ignored_extra']='not permitted'
    v.generation_digest=domain._digest(domain._generation_payload(v))
    with pytest.raises(ProjectFormatError):AuthorProject.from_dict(p.to_dict(validate=False))


def test_unrelated_loft_error_cannot_be_filtered_by_confirmed_generation(state):
    p,sid,a,b,vid=restored(state);layout(p,vid)
    c=p.add_profile([[0,0],[16,0]],closed=False)
    d=p.add_profile([[0,0],[16,7]],closed=False,plane={'origin':[40,0,12],'u':[1,0,0],'v':[0,1,0]})
    other=p.add_loft(c,d,correspondences=[{'first_segment_id':p.profiles[c].segments[0].id,'second_segment_id':p.profiles[d].segments[0].id}])
    p.set_placement(p.part_for_surface(other),p.pages[0].id,160,160)
    assert p.loft_status(other)['status']!='EXACT'
    with pytest.raises(ValidationError):p.snapshot()


def test_controller_failed_confirmation_preserves_redo_and_original_target(state,tmp_path):
    p,sid,a,b,vid=restored(state);c=AuthorController();c.project=p
    c.execute('return to source',lambda project:project.restore_segmented_target(sid));before=c.project.to_dict()
    c.execute('select confirmed variant',lambda project:project.select_segmented_variant(vid));after=c.project.to_dict()
    c.undo();assert c.project.to_dict()==before and c.can_redo
    with pytest.raises(ValidationError):c.execute('invalid token',lambda project:project.add_segmented_variant(sid,preview_digest='bad',max_cells=1))
    assert c.project.to_dict()==before and c.can_redo
    c.redo();assert c.project.to_dict()==after


def embedding_report(a,b,*,shared=False):
    first=[['0','0'],['1','0'],['0','1']]
    second=[['2','0'],['3','0'],['2','1']]
    if shared:second=[['1','0'],['1','1'],['0','1']]
    return {'patches':[{}],'source':{'first_closed':False},'triangles':[
        {'world_vertices_model_mm':a,'parameter_vertices_exact':first,'patch_index':0},
        {'world_vertices_model_mm':b,'parameter_vertices_exact':second,'patch_index':0}]}


@pytest.mark.parametrize('b',[[(0,0,0),(4,0,0),(0,4,0)],[(4,0,0),(8,0,0),(4,4,0)]])
def test_projected_duplicate_or_unintended_touch_never_gets_free_certificate(b):
    report=embedding_report([(0,0,0),(4,0,0),(0,4,0)],b)
    with pytest.raises(domain.SegmentationError):domain._embedding(report)


def test_projected_shared_uv_edge_is_allowed_but_work_cap_is_not_success(monkeypatch):
    report=embedding_report([(0,0,0),(4,0,0),(0,4,0)],[(4,0,0),(4,4,0),(0,4,0)],shared=True)
    assert domain._embedding(report)['status']=='CERTIFIED'
    monkeypatch.setattr(domain,'MAX_EMBEDDING_PAIRS',0)
    with pytest.raises(domain.SegmentationError) as caught:domain._embedding(report)
    assert caught.value.report['status']=='UNRESOLVED'


@pytest.mark.parametrize('damage',['unknown_top','unknown_derived','unknown_capability'])
def test_schema4_safe_copy_rejects_unknown_current_capability_and_preserves_original(state,tmp_path,damage):
    p,sid,a,b,vid=restored(state)
    # Construct a genuine supported v4 envelope from the retained original only.
    p,sid,a,b=target();data=p.to_dict();data.pop('segmented_variants')
    data.update(schema_version=4,writer_version='0.3.0-pc007a-profiles-experimental')
    path=tmp_path/'old.apcraft';path.write_text(json.dumps(data),encoding='utf8');before=path.read_bytes()
    c=AuthorController();c.open(path)
    c.execute('rename old copy',lambda project:setattr(project,'name','Edited copy'));c.undo()
    with pytest.raises(ValueError):c.save(path)
    assert path.read_bytes()==before
    forged=copy.deepcopy(data)
    if damage=='unknown_top':forged['unrecognized_registry']={}
    elif damage=='unknown_derived':forged['segmented_variants']={}
    else:forged['surfaces'][sid]['params']['triangle_id']='unsupported old field'
    with pytest.raises(ProjectFormatError):AuthorProject.from_dict(forged)
