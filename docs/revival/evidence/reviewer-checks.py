"""Independent P0/P1 review probes; uses fresh analytical fixtures and no integrator oracle."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
CODE='5b01bb26e6b4c3da8d75afdca19cad5d6b43d576'
sys.path.insert(0,str(ROOT/'src'))
from archpapercraft.core_geometry.primitives import MeshData,make_box_mesh
from archpapercraft.core_geometry.backend import MeshBackend
from archpapercraft.unfolder.exact_unfold import unfold_part,_compute_dihedral
from archpapercraft.unfolder.strategies import generate_rings
from archpapercraft.tabs_generator.tabs import TabSettings,generate_tab
from archpapercraft.seam_editor.seam_graph import SeamGraph
from archpapercraft.unfolder.approx_unfold import unfold_all_parts
from pypdf import PdfReader

results={}
start=time.perf_counter()
# Positive: a 3-4-5 triangle with a rigid transform must preserve all edge lengths
# and area=6. Independent pairwise distances/Heron, not the integrator's helper.
v=np.array([[0.,0,0],[3,0,0],[0,4,0]])
rotation=np.array([[0.,-1,0],[0,0,-1],[1,0,0]])
v=v@rotation.T+[31.,-27.,100.]
tri=MeshData(v,np.array([[0,1,2]]))
p=unfold_part(tri,[0])
lengths=sorted(float(np.linalg.norm(p.vertices_2d[a]-p.vertices_2d[b])) for a,b in [(0,1),(1,2),(2,0)])
s=sum(lengths)/2
area=math.sqrt(s*math.prod(s-d for d in lengths))
assert np.allclose(lengths,[3,4,5],atol=1e-12) and abs(area-6)<1e-12
results['positive_rigid_triangle']=dict(lengths=lengths,area=area,pass_numerics=True,boundary_cuts=len(p.cut_edges))

# Negative: a closed tetrahedron has positive curvature. A flat triangular face
# is valid, but at least one seam must be declared or the input explicitly rejected.
tet=MeshData(np.array([[0.,0,0],[4,0,0],[2,2*math.sqrt(3),0],[2,2/math.sqrt(3),4*math.sqrt(2/3)]]),np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]]))
tp=unfold_part(tet,list(range(4)))
occ={}
for ids in tp.faces:
    for k in range(3):
        i,j=int(ids[k]),int(ids[(k+1)%3]); a,b=int(tp.vert_map_3d[i]),int(tp.vert_map_3d[j])
        key=tuple(sorted((a,b)))
        occ.setdefault(key,[]).append({a:tp.vertices_2d[i],b:tp.vertices_2d[j]})
gaps=[max(float(np.linalg.norm(values[0][i]-values[1][i])) for i in edge) for edge,values in occ.items() if len(values)==2]
assert len(tp.faces)==4 and len(tp.cut_edges)==0 and max(gaps)>.01
results['negative_closed_tetrahedron']=dict(faces=len(tp.faces),cuts=len(tp.cut_edges),max_unreported_gap=max(gaps),defect_reproduced=True)

# A different cone fixture: r1=3, r2=8, slant=13, axial height=12.
# Cone apex similarity yields radii7.8/20.8; radial seam must remain13.
ring=generate_rings(np.array([[3.,0.],[8.,12.]]),num_rings=1)[0]
side=float(np.linalg.norm(ring[2]-ring[1]))
area_ring=abs(float(np.dot(ring[:,0],np.roll(ring[:,1],-1))-np.dot(ring[:,1],np.roll(ring[:,0],-1))))/2
assert abs(area_ring-math.pi*11*13)<1e-10 and abs(side-13)>.01
results['negative_cone_lengths_vs_area']=dict(expected_radial_seam=13,actual_radial_seam=side,expected_area=math.pi*143,actual_area=area_ring,defect_reproduced=True)

# Boundary cylinder limit: no claimed global E11 PASS; just finite values and
# matching local rectangle for this direct analytic profile.
near=generate_rings(np.array([[10.,0.],[10.+1e-10,30.]]),num_rings=1)[0]
near_side=float(np.linalg.norm(near[2]-near[1]))
assert np.isfinite(near).all() and abs(near_side-30)<.01
results['boundary_near_cylinder']=dict(finite=True,joining_side=near_side,pass_this_fixture_only=True)

ridge=MeshData(np.array([[0.,0,0],[0,7,0],[-4,0,-3],[4,0,-3]]),np.array([[0,1,2],[0,3,1]]))
swap=np.array([1,0,2,3]); ridge2=MeshData(ridge.vertices[swap],swap[ridge.faces])
angle=_compute_dihedral(ridge,0,1,(0,1)); angle2=_compute_dihedral(ridge2,0,1,(0,1))
assert angle>0 and angle2<0 and abs(angle+angle2)<1e-12
results['negative_index_permutation']=dict(angle=angle,reindexed=angle2,expected_same_semantic_polarity=True,defect_reproduced=True)

# Exact rectangular material clipping for tab against rectangle, independent of
# the integrator's general polygon clipping routine. This tab is entirely inside.
tab=generate_tab(np.array([0.,0.]),np.array([12.,0.]),TabSettings())
tab_poly=tab.polygon
inside=bool(((tab_poly[:,0]>=0)&(tab_poly[:,0]<=12)&(tab_poly[:,1]>=0)&(tab_poly[:,1]<=10)).all())
tab_area=abs(float(np.dot(tab_poly[:,0],np.roll(tab_poly[:,1],-1))-np.dot(tab_poly[:,1],np.roll(tab_poly[:,0],-1))))/2
assert inside and tab_area>0
results['negative_tab_in_material']=dict(entire_tab_inside_rect=inside,overlap_mm2=tab_area,defect_reproduced=True)

# Disjoint CSG intersection is an unambiguous negative, unlike A intersect A.
a=make_box_mesh(2,2,2); b=MeshData(a.vertices+[100,0,0],a.faces.copy())
intersect=MeshBackend().boolean_intersect(a,b)
assert intersect.num_faces!=0
results['negative_disjoint_intersection']=dict(expected='empty or explicit unsupported',actual_faces=intersect.num_faces,defect_reproduced=True)

# Nonmanifold edge with three incident right triangles. Two unfolded children
# coincide exactly, so their positive area is overlap without a clipping helper.
nm=MeshData(np.array([[0.,0,0],[6,0,0],[0,8,0],[0,0,8],[0,-8,0]]),np.array([[0,1,2],[1,0,3],[0,1,4]]))
nmp=unfold_part(nm,[0,1,2])
triangle_keys=[sorted(tuple(np.round(point,10)) for point in nmp.vertices_2d[face]) for face in nmp.faces]
duplicate=any(triangle_keys[i]==triangle_keys[j] for i in range(len(triangle_keys)) for j in range(i))
assert duplicate
results['negative_nonmanifold']=dict(accepted_faces=len(nmp.faces),two_children_coincident=duplicate,overlap_mm2=24,defect_reproduced=True)

# Read the saved outputs independently. No rerender or rewrite of integrator evidence.
pdf=PdfReader(ROOT/'docs/revival/evidence/diagnostic-landscape.pdf')
page=pdf.pages[0]
svg=ET.parse(ROOT/'docs/revival/evidence/diagnostic-landscape.svg').getroot()
assert abs(float(page.mediabox.width)*25.4/72-297)<.01
assert svg.attrib['width']=='210.0mm'
results['export_landscape_mismatch']=dict(pdf_width_mm=float(page.mediabox.width)*25.4/72,svg_width=svg.attrib['width'],defect_reproduced=True)

boot=json.loads((ROOT/'docs/revival/evidence/bootstrap.json').read_text(encoding='utf-8-sig'))
preserved=[]
for item in boot['original_files']:
    path=ROOT/item['path']
    if path.name=='05_WORK_QUEUE.json':continue # deliberately current queue, documented mutation
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==item['sha256'].upper(),path.name
    preserved.append(path.name)
for rel in ['docs/revival/evidence/diagnostic-landscape.pdf','docs/revival/evidence/desktop-export.pdf']:
    blob=subprocess.check_output(['git','show',CODE+':'+rel],cwd=ROOT)
    assert blob==(ROOT/rel).read_bytes(),rel
results['bootstrap_and_binary_proof']=dict(original_files_still_byte_equal=preserved,pdf_blobs_byte_equal=True)
changed=subprocess.check_output(['git','diff','--name-only','d689af67e059512fdc99e85e9eb0b8d432f4c5d4..'+CODE,'--','src','tests','pyproject.toml'],cwd=ROOT,text=True)
assert not changed
results['production_unchanged']=True
report=dict(base_sha='d689af67e059512fdc99e85e9eb0b8d432f4c5d4',code_sha=CODE,command=subprocess.list2cmdline([sys.executable,*sys.argv]),exit_code=0,python=sys.version,seconds=time.perf_counter()-start,results=results)
(ROOT/'docs/revival/evidence/reviewer-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
