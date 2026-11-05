"""Prepare the single authorized queue and read-only AC mapping for P1 review."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
queue_path = ROOT/'05_WORK_QUEUE.json'
queue = json.loads(queue_path.read_text(encoding='utf-8-sig'))
if any(t['stage'] in ['P0','P1'] and t['status'] not in ['PLANNED','IN_REVIEW','IN_PROGRESS'] for t in queue['tickets']):
    raise SystemExit('Refusing to regress reviewed or accepted queue state; this is a one-time P1 preparation helper')
queue['updated_on'] = '2026-11-05'
queue['baseline_sha'] = 'd689af67e059512fdc99e85e9eb0b8d432f4c5d4'
queue['working_branch'] = 'revival/p0-p1-contract'
queue['product_gate']['status'] = 'PO_PENDING_AFTER_INDEPENDENT_REVIEW'
queue['product_gate']['contract'] = 'docs/revival/P2_IMPLEMENTATION_CONTRACT.md'
queue['release_readiness'] = 'NOT_READY: product defects open; P2 and physical acceptance pending'
queue['evidence_index'] = 'docs/revival/BASELINE_REPORT.md'
outputs = {
'PC-000':['docs/revival/evidence/bootstrap.json','docs/revival/BASELINE_REPORT.md'],
'PC-001':['docs/revival/BASELINE_REPORT.md','docs/revival/CURRENT_PROJECT_STATE.md','docs/revival/WINDOWS_REPRO.md'],
'PC-002':['docs/revival/FINDINGS.md','docs/revival/GEOMETRY_SPIKE.md','tools/revival/geometry_probe.py','tools/revival/integration_probe.py','tools/revival/test_diagnostic_contracts.py'],
'PC-003':['docs/revival/ARCHITECTURE_DECISION.md'],
'PC-004':['docs/revival/UX_CONTRACT.md','docs/revival/ux-prototype.html','docs/revival/P2_IMPLEMENTATION_CONTRACT.md','docs/revival/TRACEABILITY.md','05_WORK_QUEUE.json'],
'PC-005':['docs/revival/REVIEW_REPORT.md','docs/revival/PO_DECISION_CARD.md'],
}
for ticket in queue['tickets']:
    if ticket['stage'] in ['P0','P1']:
        ticket['status'] = 'IN_PROGRESS' if ticket['id']=='PC-005' else 'IN_REVIEW'
        ticket['evidence'] = outputs[ticket['id']]
        ticket['technical_verdict'] = 'PENDING_INDEPENDENT_REVIEW'
        ticket['product_acceptance'] = 'PO_PENDING'
        ticket['review'] = 'PC-005; distinct reviewer; exact CODE SHA and evidence in REVIEW_REPORT.md'
    else:
        ticket['acceptance_state'] = {ac:'NOT_RUN' for ac in ticket['acceptance'] if ac.startswith('AC-')}
        ticket['implementation_contract'] = 'docs/revival/P2_IMPLEMENTATION_CONTRACT.md' if ticket['stage']=='P2' else '04_ACCEPTANCE_AND_VERIFICATION.md#5-fyzická-akceptace-p3'
        ticket['review'] = 'Independent reviewer required after implementation, not implementer self-approval'
        ticket['product_acceptance'] = 'NOT_RUN'
queue_path.write_text(json.dumps(queue,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

epics = [
('E01','Obnova a ADLC','P0/P1','—','PC-000–005','AC-B01–B05; evidence a nezávislé review','baseline, bootstrap, review'),
('E02','Konstrukční panely','P2, rozšíření P5','E01 rozhodnutí','PC-006','AC-G01–G05/G07','numerika/domény/world transform'),
('E03','Propojené pracovní prostředí','P2 minimum; P4 měření/gizma/sekce','E02/E12','PC-007','AC-C01/C02','Windows 3D↔2D picking; DPI'),
('E04','Švy a rozvin','P2 tree; P4 paint/locks/auto','E02/E12','PC-007','AC-C03/C04/C07; AC-G07','split/join, negative cycles, undo'),
('E05','Chlopně/spoje','P2 tapered A/B/off; P4 pásky','E04 + jednotky E06 + E12','PC-007','AC-C05/C06/C08/C09/C10','owner, winding, convex/concave'),
('E06','Papír/materiál','P2 varování; P4/P5 kompenzace/vlákna','E02/E05 + fyzický proof konkrétního řezu','PC-008 + budoucí','AC-I04; epic materiál AC','detail<0.5mm/tab<2mm warning; později analytika+stavba'),
('E07','Ruční stránky','P2 A4/snap/oba locks; P4 ostatní formáty a skupiny','E02/E05/E12/E13 minimum','PC-008','AC-L01–L03/L06/L09','drag, numeric, rotation, delete/undo, save'),
('E08','Validace/volitelná automatika','P2 validace; P4 packing; později tiled','E05/E07/E12','PC-008','AC-L04–L10','full envelopes, locks v automatice až P4'),
('E09','Vektorový export','P2 SVG/PDF; P4 varianty; později DXF/PNG','E07/E08/E12','PC-009','AC-X01–X10','XML/PDF reader, Inkscape, font, calibration'),
('E10','Architektonické detaily/knihovna','P5 otvory/ostění/výztuhy/presety','E02–E06/E12 + fyzický proof','budoucí','AC-G06; epic otvor/instance AC','holes/winding/triangulation + editor + stavba'),
('E11','Rotační tvary','P5 válec→kužel→báně; import později zvlášť','E02/E04–E06 + fyzický proof','budoucí','AC-R01–R05','analytic profiles/arcs, near-cylinder, curvature'),
('E12','Identita a autorská práce','P2 revision/lineage minimum; P4 varianty/diff','E02, průřez','PC-006/008','AC-I01–I04/I08','střecha zachová stěny; split bez index reassignment'),
('E13','Persistence/undo/recovery','P2 safe save; P4 recovery/snapshot/bundle','E01/E02/E12','PC-006/008','AC-I05–I07; epic dirty/close AC','fault injection, schema, cancel close, keyboard/DPI'),
('E14','Kvalita a stavba','P0 geometrie; P2 digitální; P3 fyzický','ověřovaný řez, nikoli hotový celý E14','PC-002/005/010/011','vše relevantní + P3 protokol','independent review, measured calibration/build'),
('E15','Grafika','P2 SVG roles; P6 editor/textury; round-trip později','E09/E12/E13','PC-009 + budoucí','AC-X10/A01–A03/L07','part grouping nyní, přenosné assets a round-trip conflicts později'),
('E16','Návod/podsestavy','P2 díly/spoje legenda; P6 kroky/obrazový návod/animace','E03/E05/E12/E15 dle scope','PC-009 + budoucí','AC-N01–N03; epic legenda','paired joints/pages nyní; revision/cycles/access model později'),
]
lines = ['# Traceability: epiky → požadavky → AC → ověření','',
'Toto je pohled nad jedinou frontou `05_WORK_QUEUE.json`, nikoli druhý tracker. Normativní text kritérií zůstává v `04_ACCEPTANCE_AND_VERIFICATION.md`. P2/P3/future stav NOT_RUN znamená, že návrh a experiment nejsou implementační PASS. Původní legacy vady jsou doložené ve FINDINGS; tabulka níže hodnotí přejímku budoucího podporovaného produktu.','',
'## Zachování celé vize','', '| Epic | Požadavek / IN a pozdější scope | Etapa | Capability závislosti | Ticket | AC | Test/demo |','|---|---|---|---|---|---|---|']
lines += ['| '+' | '.join(row)+' |' for row in epics]
lines += ['','Žádný capability vztah nevyžaduje dokončení celého E14 před implementací. Ticket DAG PC-000→001→002→003→004/005→006→007→008→009→010→011 je acyklický; PC-004 má navíc PC-001 a PC-005 čeká PC-003+004. P4–P6 dostanou konkrétní tickety při přípravě etapy, nikoli fiktivní implementační stav.','',
'## Úplná matice explicitních AC','', '| AC | Normativní požadavek | Etapa / owner | Test nebo demo / důkaz | Stav přejímky |','|---|---|---|---|---|']
criteria=[]
for line in (ROOT/'04_ACCEPTANCE_AND_VERIFICATION.md').read_text(encoding='utf-8').splitlines():
    if not line.startswith('| AC-'):
        continue
    cells=[c.strip() for c in line.split('|')[1:-1]]
    ac,requirement,proof=cells
    criteria.append(ac)
    owners=[t['id'] for t in queue['tickets'] if ac in t['acceptance']]
    stage='P2 / '+', '.join(owners) if owners and not ac.startswith('AC-B') else 'P0 / PC-000–001' if ac.startswith('AC-B') else 'Pozdější capability / viz epic'
    state='NOT_RUN'
    if ac=='AC-B02': state='PASS: bootstrap hashes/root'
    elif ac=='AC-B04': state='PASS: přesně evidovaná instalace a výsledky'
    elif ac=='AC-B01': state='NOT_APPLICABLE: root nebyl prázdný; B02 ověřeno'
    elif ac=='AC-B03': state='NOT_APPLICABLE: žádná rozdílná kolize/jiný Git; preflight před zápisem PASS'
    elif ac=='AC-B05': state='NOT_APPLICABLE: Windows/OpenGL dostupné; core/desktop odděleny, repro pack hotový'
    if ac=='AC-I08': stage='Při zavedení workeru / PC-006–009 nebo později'
    if ac=='AC-C02': proof += '; PC-007 příprava, finální přes2stránky až PC-009 po008'
    lines.append(f'| {ac} | {requirement} | {stage} | {proof} | {state} |')
assert len(criteria)==len(set(criteria))==61
lines += ['','Doplňky z epic bez číslovaného AC jsou výslovně v P2 kontraktu: malý detail/chlopeň, snap/alignment, samostatné locks, díly/spoje legenda, dirty při větvení undo a Windows DPI/klávesnice. Tyto demo položky jsou NOT_RUN; nejsou zrušeny absencí číselného ID.','',
'AC-I07: P1 rozhodnutí a dnešní sample round-trip prozkoumány; P2 legacy read-only/refusal bez ztráty se musí implementovat a ověřit, proto zde NOT_RUN. AC-G05: P0 reprodukce vady hotová, P2 odmítnutí unsupported zatím NOT_RUN. AC-L06 v P2 ověří odmítnutí/zachování velikosti a odkládací plochu bez packingu. AC-X10 P2 ověří skupinu všech implementovaných part složek; interní artwork přibývá v E15, struktura a prázdná role už v P2.','']
(ROOT/'docs/revival/TRACEABILITY.md').write_text('\n'.join(lines),encoding='utf-8')
print(f'Prepared queue {len(queue["tickets"])} tickets; mapped {len(epics)} epics and {len(criteria)} AC')
