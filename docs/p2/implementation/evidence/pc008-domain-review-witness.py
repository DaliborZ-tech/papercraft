"""Raw facts for the independently constructed S=(16u,8uv,12v) witness."""
import hashlib,importlib.util,json,sys
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
a=json.loads((E/'pc008-domain-review-archive-95fa2c7.json').read_text(encoding='utf8'))
sys.path.insert(0,str(Path(a['isolated_directory'])/'src'))
spec=importlib.util.spec_from_file_location('own_D_oracles',E/'pc008-domain-review-own.py')
own=importlib.util.module_from_spec(spec);spec.loader.exec_module(own)
p,sid,first,second=own.target();before=p.to_dict()
preview=p.preview_segmented_variant(sid,max_deviation_mm=.26)
assert preview['status']=='APPROXIMATE' and p.to_dict()==before
vid=p.add_segmented_variant(sid,preview_digest=preview['preview_digest'],max_deviation_mm=.26)
variant=p.segmented_variants[vid];own.layout(p,vid);snapshot=p.snapshot()
frame=variant.certificate['material_frame'];math=variant.certificate['math']
result={'source_sha':a['source_sha'],'actual_source_import':sys.modules['archpapercraft.authoring.segmented_surface'].__file__,
        'independent_source_formula':'S(u,v)=(16u,8uv,12v); S_u cross S_v=(96v,-192,128u)',
        'analytic_nonzero_determinant':-1536,'actual_determinant':math['patches'][0]['developability_determinant_exact'],
        'input_limit_paper_mm':.26,'raw_math_deviation_exact':math['max_surface_deviation_paper_mm_exact'],
        'actual_material_deviation_bound_exact':frame['max_target_to_material_deviation_paper_mm_exact'],
        'actual_material_normal_angle_bound_deg_exact':frame['max_material_normal_angle_deg_exact'],
        'actual_flat_length_difference_bound_exact':frame['max_source_edge_to_flat_length_difference_bound_paper_mm_exact'],
        'embedding':variant.certificate['embedding'],'counts':math['counts'],
        'target_status_after_confirmation':p.loft_status(sid)['status'],
        'material_mode':snapshot['construction_checks']['segmented_variants'][vid]['mode'],
        'material_part_count':len(snapshot['coverage']['expected_part_ids']),
        'construction_surface_count':len(snapshot['coverage']['all_construction_surface_ids']),
        'reference_surface_ids':snapshot['coverage']['reference_surface_ids'],
        'two_page_part_counts':[len(page['parts']) for page in snapshot['pages']],
        'schema_version':p.to_dict()['schema_version'],'scope':'COMPONENT_BACKEND_ONLY; UI_EXPORT_EDITOR_NOVICE_PHYSICAL_NOT_RUN'}
assert result['actual_determinant']=='-1536' and result['target_status_after_confirmation']!='EXACT'
assert F(result['actual_material_deviation_bound_exact'])<=F(.26)
(E/'pc008-domain-review-witness-95fa2c7.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,indent=2))
