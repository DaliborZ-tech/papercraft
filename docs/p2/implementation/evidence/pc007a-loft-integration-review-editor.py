"""Read current saved Inkscape CUT paths independently, without GUI or writer."""
import ast
import json
import re
from pathlib import Path
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
import xml.etree.ElementTree as ET

E=Path(__file__).resolve().parent
getcontext().prec=80
helper=E/'pc007a-loft-integration-review-audit.py'
for node in ast.parse(helper.read_text('utf-8')).body:
    if isinstance(node,ast.FunctionDef) and node.name in ['dec','atan','green_curve','loop_areas','svg_commands','net']:
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(helper),'exec'))
NUM=r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
PI=16*atan(D(1)/5)-4*atan(D(1)/239)
ns={'s':'http://www.w3.org/2000/svg'}
results=[]
for p in sorted(E.glob('pc007a-loft-*-inkscape-a46*-run01/editor-results.json')):
    areas=[];counts=[]
    for name in ['editor-original.svg','editor-edited.svg']:
        root=ET.parse(p.parent/name).getroot()
        group=root.find('.//s:g[@data-role="CUT"]',ns)
        commands=[]
        for path in group.findall('.//s:path',ns):
            commands.extend(svg_commands(path.attrib['d']))
        a=loop_areas(commands);areas.append(net(a));counts.append(len(a))
    assert counts[0]==counts[1] and abs(areas[1]-areas[0])<D('.01')
    results.append({'run':p.parent.name,'cut_loops':counts,'original_area':str(areas[0]),'edited_area':str(areas[1]),'independently_read_area_delta_mm2':str(abs(areas[1]-areas[0]))})
(E/'pc007a-loft-integration-review-editor-independent.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('PASS independent saved editor CUT loops and Green areas:',len(results))
