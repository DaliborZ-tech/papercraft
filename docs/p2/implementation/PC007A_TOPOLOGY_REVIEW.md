# PC-007A — nezávislá revize topologie skutečných křivkových hranic

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; autor komponenty je jiný agent. Požadovaný zdroj **`55c4443d40beb36c83d26f8ae940b987c4facf9c`**, `authoring/curve_topology.py`, větev `revival/p2-curve-numerics`.

**Verdikt: CHANGES_REQUESTED — T01 MAJOR OPEN.** Byla nalezena konkrétní falešná tvrdá INVALID klasifikace nativní tiskové hranice. Deklarovaná assumption o endpoint constraints uvnitř floating rezervy tento problém neřeší. Následná oprava skutečné emitované geometrie se připravuje; není zatím tímto reportem schválená.

## T01 — nominal center witness není důkaz průniku skutečného SVG

Nezávislý reprodukční vstup má `delta=1e-14` a `x=1+delta/2`:

```python
arc = Curve((0,1), (1,0), "arc", {
    "center": (delta,0), "sweep_deg": -90
}, "native-quarter")
outer = (
    arc,
    Curve((1,0), (x,0)),
    Curve((x,0), (x,2)),
    Curve((x,2), (0,2)),
    Curve((0,2), (0,1)),
)
```

Writer vydá přesně `M 0 1 A 1 1 0 0 0 1 0`, tedy nativní jednotkový čtvrtoblouk se středem `(0,0)` a `x<=1`. Malá spojnice na vnější stranu a svislice na `x=1.000000000000005` tento oblouk neprotínají; zbytek hranice vede přes horní obdélníkový obvod. Jde o jednoduchou uzavřenou nativní hranici. Její podlimitní vzdálenost může vyžadovat UNRESOLVED, ale není analytickým důkazem neplatnosti.

Přesto `55c4443` vrací **INVALID**, witness `ANALYTIC_CIRCLE_LINE_ROOT_IN_ARC_INTERVAL`, bod přibližně `[1.000000000000005,9.892395146499475e-08]`, segmenty arc a vertical. Důvod: průnik se počítá s nominálním zdrojovým středem `(delta,0)` a poloměrem od startu, zatímco SVG endpoint reprezentace má skutečný střed `(0,0)`. To jsou odlišné kružnice. Rozdíl v endpoint constraint je menší než globální floating guard, ale povolený malý numerický rozdíl nedovoluje použít tvrdý topologický witness pro jinou křivku.

Druhý hraniční podklad: nominální oblouk `(-1,0)→(1,0)` se středem 0 a sweep `180+1e-12°` plus zavírací úsečka dostal VALID v pouhých třech uzlech. Nominální center+sweep křivka však dosáhne `(1,0)` již před koncem a následně má vynucený koncový skok; skutečný writer ji kanonizuje jinak. Tento druhý případ sám není důkaz neplatnosti výsledného SVG. Ukazuje potřebu přesně pojmenovat, **které** hranici topologický certifikát patří. Hlavním prokázaným produkčním protikladem je výše uvedený T01 false INVALID.

Doporučení: buď důsledně a prokazatelně validovat skutečnou kanonickou výrobní hranici všech emitovaných A úseků s přesnými společnými endpointy a intervaly jejích parametrů, nebo při neprokázané ekvivalenci vrátit UNRESOLVED. Samotný polohový/délkový bound z R01 neurčuje topologickou ekvivalenci u dotyku či téměř společného vrcholu. Nelze jen rozšířit seznam assumptions nebo endpoint považovat za přesný středový constraint kvůli malé odchylce.

## Důkazy a zdrojové připnutí

Nejprve byl pracovní strom na `55c4443` čistý a přímý subprocess reprodukoval konkrétní false INVALID. Během pozdějšího běhu sad začal jiný agent přepisovat `curve_topology.py` na novou reprezentaci. Tento nepřipnutý mezistav skončil TypeError v rozpracované homogeneous větvi. Jde o **WIP běh bez platné atribuce**, nikoli regresi původního commitu nebo výsledek review nové opravy. Raw je zachovaný jako `pc007a-topology-review-original-unpinned-wip.xml` a `pc007a-topology-review-own-unpinned-wip.xml`.

Rozhodné inicializační běhy byly proto bezpečně zopakovány v čerstvém subprocessu z **přesného Git blobu `55c4443`**, bez přepnutí větve nebo změny cizího zdroje. [Runner](evidence/pc007a-topology-review-pin.py) a [pin/hash záznam](evidence/pc007a-topology-review-pin.json) dokládají zdroj načteného topology modulu. Závislé `curves.py` bylo shodné s pinen (prázdný git diff); skutečný import pochází z tohoto worktree.

```powershell
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe docs/p2/implementation/evidence/pc007a-topology-review-pin.py tests/authoring/test_curve_topology.py tests/authoring/test_curves.py -q --junitxml=docs/p2/implementation/evidence/pc007a-topology-review-original-55c4443.xml
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe docs/p2/implementation/evidence/pc007a-topology-review-pin.py docs/p2/implementation/evidence/pc007a-topology-review-own.py -q --junitxml=docs/p2/implementation/evidence/pc007a-topology-review-own-55c4443.xml
```

- Původní testy: **60 PASS / 1,66 s**, [JUnit](evidence/pc007a-topology-review-original-55c4443.xml).
- Vlastní analytika: **15 PASS, 1 FAIL / 0,23 s**, [zdroj](evidence/pc007a-topology-review-own.py), [JUnit](evidence/pc007a-topology-review-own-55c4443.xml). FAIL je T01. Dvě další sub-ULP varianty výslovně pracují s opravdu zaokrouhlenými endpointy a nezkoušejí vytvořit nulovou úsečku.

Vlastní pozitivní/negativní očekávání zahrnuje skrytý kubický crossing při epsilon 1e-6, 1e-9, 1e-12, druhý průnik sousední kubiky poblíž společného konce, oddělené a vnořené kruhové díry, díru mimo obvod, coincident/crossing circles, obě orientace, tečný otvor a tři vyčerpané globální rozpočty. Šestnáct případů neuděluje nový globální důkaz algoritmu: analytická kontrola zkoumala právě platnost výše uvedeného společného endpoint předpokladu a našla jeho konkrétní porušení.

## Skills a rozsah

Před prací skutečně načteny čtyři projektové skills a příslušné AU08/09, včetně původní akceptace topologických děr. Konstrukční význam je skutečný vystřihovaný materiál, ne vizuálně podobný sampled polygon. UI musí rozlišit doloženou neplatnost od neprokázané přesnosti; T01 je problém produktu a důkazu, nikoli příležitost překrýt chybu nápovědou. Verification skill vyžadoval nezávislé nativní geometrické očekávání, raw FAIL a opravu atribuce souběžného WIP běhu. Delivery skill zakazuje vydat tuto komponentu za schválenou jen proto, že prošla původní sada.

Pure topology komponenta nenahrazuje zdrojovou numerickou toleranci ani mez developability, pravidelnost loftu, rozvin/UI/save/reopen/layout/export, skutečný editor, nového člověka nebo fyzické P3. Navazující nový topologický pin potřebuje vlastní review skutečné emitované hranice; tento report nesmí být přenesen na něj bez kontroly.

## Úplná izolace přes Git archive stejného zdroje

Na požadavek integračního ownera byl `55c4443` zopakován ještě jednou i s izolací **všech** aplikačních zdrojů, autorových testů a pyproject z přesného `git archive`. Čerstvé subprocessy měly `PYTHONPATH` i pytest config pouze v čerstvé dočasné kopii. Žádný produkční soubor sdíleného worktree nebyl spuštěn nebo přepsán.

[Archive runner](evidence/pc007a-topology-review-archive.py), [zdrojový pin, hash archivu a raw výstupy](evidence/pc007a-topology-review-archive-55c4443.json): **60 původních PASS / 2,25 s**, [JUnit](evidence/pc007a-topology-review-original-55c4443-archive.xml); **15 vlastních PASS, T01 FAIL / 0,73 s**, [JUnit](evidence/pc007a-topology-review-own-55c4443-archive.xml). Výsledek se shoduje s přesným module-blob během. T01 MAJOR zůstává OPEN do nového opravného pinu. Archive kopie byla ponechána v dočasném umístění pro dohledání; nic se nemaže z cizí práce.
