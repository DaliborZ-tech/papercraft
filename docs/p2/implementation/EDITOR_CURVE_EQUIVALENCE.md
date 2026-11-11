# Celokřivkové ověření SVG po editoru

Zdrojový pin `a799072`, autorský přírůstek nad
`52836321810f7a8a0c6a8d43b801f98ed875bbde`.
Přesný měřený obsah zdroje připínají SHA-256 v
[replay raw](evidence/editor-equivalence-recorded-replay.json); samotný parent SHA
není tvrzení o přesném necommitovaném zdroji. Nezávislá revize: **PENDING**.
Nový skutečný průchod Inkscape na tomto přírůstku: **NOT_RUN**, provede integrátor.
Původní skutečný neúspěch zůstává v [nezměněném raw](evidence/editor-near-original-failure.json).

Použité skills: verification — analytická očekávání, negativní případy a rozlišení
recorded replay / native UI; construction — zachování oblouků, skutečné oblasti
a děr; authoring-ui — editor může přepsat transformaci do ekvivalentní rotace
kolem bodu; delivery — úzký izolovaný přírůstek a předání jinému reviewerovi.
Produkční geometrie ani aplikace se nemění. Helper nemá produkční geometrické
importy. Nedává nové schválení původnímu exportu ani fyzické výrobě.

## Co se prokazuje

`certify_path_equivalence` dostává již normalizované přesné racionální M/L/C/A/Z.
Nezvyšuje tolerance: celý bodový průběh nejvýše **0.00002 mm**, součet absolutních
mezí změny délek celého path nejvýše **0.01 mm**, přímá změna čisté plochy nejvýše
**0.01 mm²**. Driver navíc sčítá délku a plochu přes všechny path každého dílu/role;
plošný rozpočet se nezvětšuje o chlopně. Pevná podlaha může být přísnější než
relativní mez velkého těla. Příkazy, orientace/flags oblouků, uzavření, role a ID
zůstávají zachovány. Není použit fallback na blízkost operandů, bbox či vzorkování.

L/C: rozdíl odpovídajících Bernsteinových kontrolních bodů omezuje celou polohu
konvexním obalem. Z nerovnosti `|length(P)-length(Q)| <= integral |P'-Q'|`
plyne délková mez součtem norem sousedních rozdílů kontrolních bodů rozdílové
křivky. Integrál Bernsteinova členu derivace má váhu `1/n`, která ruší faktor n.
Plocha C je přesný racionální integrál `(x*y'-y*x')/2` v mocninném základu.

Menší kruhový A: graf nad orientovanou tětivou délky c má výšku
`h(r,c,t)=sqrt(r²-(t-.5)²*c²)-sqrt(r²-c²/4)`. V celém sousedství s
`q=sqrt(r_min²-c_max²/4)>0` platí

* `|dh/dr| <= c_max²/[4*q*(r_min+q)]`;
* `|dh/dc| <= c_max/(4*q)`;
* sagitta nejvýše `c_max²/[4*(r_min+q)]`.

Je-li každý endpoint posunut o L1 nejvýše e, změna tětivy je nejvýše `2e` a změna
jednotkové normály nejvýše `4e/c_min`. Součet endpoint, normálové a obou grafových
mezí tedy pokrývá **celou** odpovídající křivku. Pro délku
`l=2r*asin(c/(2r))`, `x=c_max/(2r_min)`, `cos_min=q/r_min` platí
`|dl/dc|<=1/cos_min` a `|dl/dr|<=2*x³/(3*cos_min³)`: poslední mez plyne
integrací `t²/(1-t²)^(3/2)` od 0 do x. Součet přes všechny A/L/C je globální.
Změněná půlkružnice, velký A, elipsa, radius correction nebo ztracená regularita
jsou **UNRESOLVED**. Geometricky zcela nezměněný path smí pouze zachovat dříve
ověřený zdroj. Neprokazuje tím novou platnost jeho materiálu.

Plocha A se počítá přímo jako chord Green plus podepsaná kruhová úseč:
`cross(start,end)/2 ± (r²*theta-c*q)/2`. Velký oblouk má příslušné znaménko
sinusového členu. Úhly jsou uzavřeny nezávislou Machinovou identitou pro π a
alternující řadou atan s prokázaným zbytkem a konečným limitem. Odmocniny používají
integer square root. Intervaly a výsledné skalární meze se zaokrouhlují ven na
racionální mřížku `10^-80`; float nezaokrouhluje certifikát. Plošné absolutní
rozdíly se sčítají po uzavřených subpath, čímž omezují libovolné zachované
přiřazení tělo minus díry a nemohou se falešně vyrušit mezi dírami.

## Oblast a frame

Malé metrické změny samy o sobě nezaručují topologii. Změněné path proto navíc
procházejí konečným pozitivním důkazem: přesné polynomiální / intervalově uzavřené
racionální kvadratické obaly A se půlí de Casteljau. Pro každý list je prokázán
společný monotónní směr obou křivek přes Bernsteinovy koeficienty `N'W-NW'`.
Tím zůstává jednoduchý i jejich lineární bodový homotopický průběh. Celé obaly
zdrojové a editované křivky dohromady pokrývají tento průběh.

Všechny páry nesousedních listů mají oddělené obaly; sousední mají prokázanou
oddělující polorovinu kolem skutečně společného endpointu. Nesdílené endpointy
musí mít také oddělené průběhy. Dvousegmentové uzavřené smyčky dovolují oba
strukturálně společné endpointy, nikoli nový kontakt. To zachovává jednoduchost,
oddělenost a nesting děr v celé homotopii. Není-li to dokázáno do `max_work`
(default 200000) / `max_depth` (24), stav je **UNRESOLVED**, ne schválený kontakt.
Command cap je 100000; chybný či bool budget se odmítá. Pouze již zcela shodná
geometrie používá identitu jako nulový důkaz.

Driver zachovává fyzické width/height/viewBox, part/role/path ID i jejich role,
odmítá nový vnořený či CSS transform a ztracený/přidaný typ vykreslené geometrie.
V part frame povoluje pouze syntakticky úplné translate/rotate a přesně stejný
výsledný úhel modulo 360. Složené rotace a translace se stejným úhlem mohou změnit
pouze translaci. Scale/skew/matrix se nezaměňují za ekvivalenci, ani když vypadají
jako identita. Původní bbox kontrola zamýšleného pohybu a nezávislá 100mm kalibrace
zůstávají dodatečnými kontrolami. Hash helperu je součást editor-results a musí
být stejný na začátku i konci měření.

## Skutečně provedené ověření

[33 targeted PASS](evidence/editor-equivalence-targeted.xml), 1.06 s:
23 zaznamenaných near path jako jeden oracle, samostatně quarter-A a skutečné C,
analytická cubic Green plocha `-3/5`, quarter-circle `25π`, nezávislý Decimal
sagitta výpočet, půlkružnice R10→10.00001 se skutečnou odchylkou >0.01413 mm,
globální délka >0.01 při jednotlivých posunech 1e-5, obdélníková plocha .011 při
procházející poloze/délce, kolaps úzkého obdélníku a únik díry přes okraj,
budgety, role/units/frame/CSS/skryté scale mutace a dosavadní editor diagnostika.

Z [přenosného recorded replay](evidence/editor-equivalence-recorded-replay.json):
všech 23 path **CERTIFIED**, včetně CUT s 19 A. CUT má prokázanou polohu
`<=5.567892e-7 mm`, globální délku `<=1.957583e-5 mm` a přímou plochu
`<=1.289767e-6 mm²`. Radius-only změna 30000000.0041217→30000000 při tětivě
15.70797898 má nezávisle ověřenou celokřivkovou mez `<1.4125e-16 mm`.
Změna `translate(55 90) rotate(17)` na
`rotate(17,-285.55688,239.84301)` prokazuje stejnou lineární část.
To není nové ověření GUI editoru ani jeho textového/pohybového průchodu.

Příkazy z kořene tohoto WT (sdílená venv, bez Qt či desktopu):

```powershell
& ../papercraft/.venv/Scripts/python.exe -m pytest tests/authoring/test_editor_curve_equivalence.py tests/authoring/test_editor_path_comparison.py tests/authoring/test_loft_editor_diagnostic.py -q --junitxml=docs/p2/implementation/evidence/editor-equivalence-targeted.xml
& ../papercraft/.venv/Scripts/python.exe docs/p2/implementation/evidence/editor-equivalence-replay.py --output docs/p2/implementation/evidence/editor-equivalence-recorded-replay.json
& ../papercraft/.venv/Scripts/ruff.exe check tools/authoring/editor_curve_equivalence.py tools/authoring/editor_probe.py tests/authoring/test_editor_curve_equivalence.py docs/p2/implementation/evidence/editor-equivalence-replay.py
git diff --check
```

První interní recorded replay měl u CUT legitimní UNRESOLVED kvůli narůstajícím
racionálním jmenovatelům a Python limitu serializace integeru. Zachován jako
[first raw](evidence/editor-equivalence-first-internal.json). Oprava používá
prokázané venkovní zaokrouhlení skalárních mezí na stejnou racionální mřížku;
žádný limit ani nepohodlný případ nebyl odstraněn.
