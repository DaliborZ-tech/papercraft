"""Independent negative/analytic qualification of diagnostic SVG area oracle."""
import ast,math,os,re,xml.etree.ElementTree as ET
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
import pytest
from circular_svg_oracle import svg_signed_area

# Reuse ONLY this reviewer's earlier independent Decimal110 derivation,
# with Machin pi and different arcsine reduction; never the new helper's math.
source=Path(__file__).with_name('pc007b-c8-review-near-area.py').read_text(encoding='utf8')
names={'D','atan','pi','asin','theta_minus_sin','commands','svg_green'}
exec(compile(ast.Module(body=[node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name in names],type_ignores=[]),'<own-independent-Green-reference>','exec'))

@pytest.mark.parametrize('radius,shift',[('30000000','0'),('30000000','1e20'),('1e29','1e29')])
def test_parallel_arc_region_and_qualified_small_area_mutation(radius,shift):
 with localcontext() as ctx:
  ctx.prec=120;x=Decimal(shift)
  def shape(width):return f'M {x} 0 A {radius} {radius} 0 0 1 {x+width} 0 L {x+width} 30 A {radius} {radius} 0 0 0 {x} 30 Z'
  good=shape(Decimal(10));bad=shape(Decimal('10.001'))
  assert abs(svg_signed_area(good)-300)<Decimal('1e-55')
  # Both closed paths are geometrically simple equal-radius parallel bows;
  # two signed segment terms cancel exactly, leaving width*30, not a parser fault.
  expected=Decimal('300.03');actual=svg_signed_area(bad)
  assert abs(actual-expected)<Decimal('1e-55') and abs(actual-300)>Decimal('.01')

@pytest.mark.parametrize('sweep,large',[(0,0),(1,0),(0,1),(1,1)])
def test_quarter_and_major_sector_have_independent_pi_and_orientation(sweep,large):
 text=f'M 0 0 L 2 0 A 2 2 0 {large} {sweep} 0 2 L 0 0 Z'
 with localcontext() as ctx:
  ctx.prec=110;actual=svg_signed_area(text);reference=svg_green(commands(text))
  assert abs(abs(actual)-reference)<Decimal('1e-95')
  if not large:
   expected=pi() if sweep else Decimal(4)-pi()
  else:expected=Decimal(4)+3*pi() if sweep else -3*pi()
  assert abs(actual-expected)<Decimal('1e-95'),(text,actual,expected)

def test_current_decimal_context_cannot_change_result_or_global_context():
 shape='M 0 0 A 30000000 30000000 0 0 1 10 0 Z';expected=svg_signed_area(shape)
 with localcontext() as ctx:
  ctx.prec=12;actual=svg_signed_area(shape);assert actual==expected and ctx.prec==12

@pytest.mark.parametrize('number',['1e-201','1e31','0.'+'123456789'*9])
def test_arithmetic_budget_refusals_are_explicit(number):
 with pytest.raises(ValueError,match='arithmetic budget'):svg_signed_area(f'M 0 0 L {number} 0 Z')

def test_input_and_token_work_limits_refuse_instead_of_returning_false_area():
 with pytest.raises(ValueError):svg_signed_area('M 0 0 Z'+' '*(4*1024*1024))
 with pytest.raises(ValueError):svg_signed_area('M 0 0 '+'L 0 0 '*135000+'Z')

def test_actual_preserved_near_svg_matches_independent_endpoint_green():
 folder=Path(os.environ['PC8_NEAR_FAIL_EVIDENCE'])/'C-near/export';count=0
 with localcontext() as ctx:
  ctx.prec=110
  for path in folder.glob('*.svg'):
   for group in ET.parse(path).getroot().findall('{http://www.w3.org/2000/svg}g[@data-part-id]'):
    cut=next(g for g in group if g.get('data-role')=='CUT')
    for p in cut:
     text=p.get('d');assert abs(abs(svg_signed_area(text))-svg_green(commands(text)))<Decimal('1e-90');count+=1
 assert count==2
