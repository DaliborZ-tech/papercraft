"""Independent high precision endpoint Green audit of preserved failed near run.

No actual application/controller/geometry mutation, no GUI, no changed norm.
This is a numerical oracle, not a new rigorous production certificate.
"""
import hashlib,json,math,re,sys,xml.etree.ElementTree as ET
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'src'))
from archpapercraft.exporter.curve_output_validation import read_pdf_cut_regions
E=ROOT/'docs/p2/implementation/evidence';NATIVE=Path(sys.argv[1]).resolve()
def D(x):
 q=F(x);return Decimal(q.numerator)/Decimal(q.denominator)
def atan(x):return sum(((-1)**k*x**(2*k+1)/Decimal(2*k+1) for k in range(160)),Decimal(0))
def pi():return 16*atan(Decimal(1)/5)-4*atan(Decimal(1)/239)
def asin(x):
 if x*x>Decimal('.5'):return pi()/2-asin((1-x*x).sqrt())
 term=total=x
 for n in range(1,360):term=term*x*x*Decimal((2*n-1)**2)/Decimal((2*n)*(2*n+1));total+=term
 return total
def theta_minus_sin(theta):
 term=theta**3/6;total=term
 for n in range(2,100):term=-term*theta*theta/Decimal((2*n)*(2*n+1));total+=term
 return total
def commands(text):
 tokens=re.findall(r'[MLAZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',text);out=[];i=0
 while i<len(tokens):
  op=tokens[i];i+=1;n={'M':2,'L':2,'A':7,'Z':0}[op];values=tuple(map(F,tokens[i:i+n]));assert len(values)==n;i+=n;out.append((op,*values))
 return out
def svg_green(cmds):
 total=Decimal(0);current=start=None
 for c in cmds:
  if c[0]=='M':current=tuple(c[1:]);start=current
  elif c[0] in ('L','A','Z'):
   end=start if c[0]=='Z' else tuple(c[-2:]);total+=D(current[0]*end[1]-current[1]*end[0])/2
   if c[0]=='A':
    _,rx,ry,rotation,large,sweep,_x,_y=c;assert rx==ry and rx>0 and rotation==0 and large in (0,1) and sweep in (0,1)
    chord2=(current[0]-end[0])**2+(current[1]-end[1])**2;radius=D(rx);ratio=D(chord2).sqrt()/(2*radius);assert ratio<=1
    theta=2*asin(ratio)
    if large:theta=2*pi()-theta
    segment=radius*radius*theta_minus_sin(theta)/2
    total+=segment if sweep else -segment
   current=end
  else:raise AssertionError(c[0])
 return abs(total)
def pdf_green(cmds):
 total=F(0);current=start=None
 def line(a,b):return (a[0]*b[1]-a[1]*b[0])/2
 for c in cmds:
  if c[0]=='M':current=tuple(c[1:]);start=current
  elif c[0]=='L':end=tuple(c[1:]);total+=line(current,end);current=end
  elif c[0]=='Z':total+=line(current,start);current=start
  elif c[0]=='C':
   a,b,c1,d=[current,*[tuple(c[i:i+2]) for i in (1,3,5)]]
   coeff=[a,tuple(3*(y-x) for x,y in zip(a,b)),tuple(3*(z-2*y+x) for x,y,z in zip(a,b,c1)),tuple(w-3*z+3*y-x for x,y,z,w in zip(a,b,c1,d))]
   total+=sum((x[0]*j*y[1]-x[1]*j*y[0])/F(i+j) for i,x in enumerate(coeff) for j,y in enumerate(coeff) if j)/2;current=d
  else:raise AssertionError(c[0])
 return abs(total)
def triangle_tab(r,s):
 w=Decimal('.24');depth=Decimal('9.5');q=s*w/(4*r);half=w/(2*(1+q*q));sag=-s*w*w/(8*r*(1+q*q))
 if not s:return half*depth
 theta=4*atan(q)
 return half*(depth-sag)-(r/s)**2*theta_minus_sin(theta)/2
r=json.loads((NATIVE/'results.json').read_text(encoding='utf8'));assert r['source_sha']=='8f1ec6382d527c719133958e7eb6f78a724ef5d5' and r['status']=='FAIL'
assert 'Independent oracle C source/SVG material area' in r['error']
folder=NATIVE/'C-near';model=json.loads((folder/'C-near.apcraft').read_text(encoding='utf8'));snapshot=json.loads((folder/'snapshot.json').read_text(encoding='utf8'))
with localcontext() as context:
 context.prec=110
 r0,r1,h=Decimal(10),Decimal('10.00001'),Decimal(30);slant=((r1-r0)**2+h*h).sqrt();body=pi()*(r0+r1)*slant;expected=body+11*triangle_tab(r0,(r0-r1)/slant)
 record=next(iter(model['curved_connectors'].values()));owner=model['surfaces'][record['owner_surface_id']]['part_id'];receiver=model['surfaces'][record['receiver_surface_id']]['part_id']
 wants={owner:expected,receiver:100*pi()};svg={};svg_files=[]
 for path in (folder/'export').glob('*.svg'):
  svg_files.append(dict(name=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  root=ET.parse(path).getroot();assert root.get('width')=='210mm' and root.get('height')=='297mm'
  for group in root.findall('{http://www.w3.org/2000/svg}g[@data-part-id]'):
   assert not re.search(r'(scale|matrix|skew)',group.get('transform',''))
   cut=next(g for g in group if g.get('data-role')=='CUT');pid=group.get('data-part-id');svg[pid]=sum(svg_green(commands(x.get('d'))) for x in cut)
 pdf_path=folder/'export/model.pdf';pdf=read_pdf_cut_regions(pdf_path)['parts'];assert set(pdf)==set(svg)==set(wants)
 results=[]
 for pid,want in wants.items():
  actual_pdf=sum(pdf_green(loop) for loop in pdf[pid]['loops']);svg_error=abs(svg[pid]-want);pdf_error=abs(D(actual_pdf)-want)
  assert svg_error<Decimal('.01') and pdf_error<Decimal('.01')
  results.append(dict(part_id=pid,expected=str(want),actual_svg=str(svg[pid]),actual_pdf=str(D(actual_pdf)),svg_error=str(svg_error),pdf_error=str(pdf_error),actual_pdf_exact=str(actual_pdf)))
 out=dict(status='PASS_HIGH_PRECISION_AREA_AUDIT_OF_PRESERVED_FAILED_NATIVE_NOT_FINAL_NATIVE_PASS',source_sha=r['source_sha'],native_status_preserved='FAIL',cause='Old float circle-center Green cancellation, independently replaced here only for audit by endpoint rational chord + Decimal110 analytic circular segment',scope='Numerical independent oracle, not rigorous interval production proof, native UI/editor/fullC not approved here',precision=110,svg_files=svg_files,pdf_sha256=hashlib.sha256(pdf_path.read_bytes()).hexdigest(),results=results)
(E/'pc007b-c8-review-near-area-8f1ec63.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print(json.dumps(out,indent=2))
