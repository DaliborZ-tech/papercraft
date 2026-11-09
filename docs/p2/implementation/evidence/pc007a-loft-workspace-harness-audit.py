"""Pinned read-only harness audit and differently derived numerical expectations."""
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[4];E=ROOT/'docs/p2/implementation/evidence'
archive=json.loads((E/'pc007a-loft-workspace-review-archive-10a21ac.json').read_text(encoding='utf8'))
path=Path(archive['isolated_directory'])/'tools/authoring/loft_desktop_steps.py'
tree=ast.parse(path.read_text(encoding='utf8'));calls=[]
for node in ast.walk(tree):
    if isinstance(node,ast.Call):
        name=ast.unparse(node.func);calls.append(name)
        assert not any(term in name for term in ('controller.execute','setattr','monkeypatch','project.add_','project.set_','project.update_'))
    if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
        assert not any('self.w.project' in ast.unparse(target) for target in targets)
spec=importlib.util.spec_from_file_location('reviewed_loft_native_steps',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
nodes,weights=np.polynomial.legendre.leggauss(48)
def integrate(function,low,high):return sum(w*function((high+low)/2+(high-low)*x/2)*(high-low)/2 for x,w in zip(nodes,weights))
R=32.5;c=12.5
def strip_jacobian(theta,v):
    point=np.array([c+R*math.cos(theta),R*math.sin(theta),0])
    du=(1+.2*v)*np.array([-R*math.sin(theta),R*math.cos(theta),0])
    dv=.2*point+np.array([0,0,10])
    return np.linalg.norm(np.cross(du,dv))
gothic=440+2*integrate(lambda theta:integrate(lambda v:strip_jacobian(theta,v),0,1),math.atan2(30,-12.5),math.pi)
controls=np.array([[0,0,0],[20,30,0],[60,30,0],[80,0,0]])
def bezier_jacobian(u):
    derivative=3*((1-u)**2*(controls[1]-controls[0])+2*u*(1-u)*(controls[2]-controls[1])+u*u*(controls[3]-controls[2]))
    return np.linalg.norm(np.cross(derivative,[0,0,10]))
bezier=integrate(bezier_jacobian,0,1)
observed={'gothic':module.expected_gothic_area(),'bezier':module.expected_bezier_area()}
assert abs(gothic-observed['gothic'])<1e-8 and abs(bezier-observed['bezier'])<1e-8
result={'source_sha':archive['source_sha'],'harness_path':str(path),'harness_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'no_direct_project_or_controller_mutation_in_new_steps':True,'distinct_calls':sorted(set(calls)),
        'own_method':'48-node Gauss tensor integral of independently formed world partial derivative cross products',
        'claim':'NUMERICAL_CONSISTENCY_ONLY; NOT_A_RIGOROUS_CERTIFICATE_OR_NATIVE_B_PASS',
        'gothic':{'own':float(gothic),'harness_simpson':observed['gothic'],'difference':float(abs(gothic-observed['gothic']))},
        'bezier':{'own':float(bezier),'harness_simpson':observed['bezier'],'difference':float(abs(bezier-observed['bezier']))}}
(E/'pc007a-loft-workspace-harness-audit-10a21ac.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='distinct_calls'},indent=2))
