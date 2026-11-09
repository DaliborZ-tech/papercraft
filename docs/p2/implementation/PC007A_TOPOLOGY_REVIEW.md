# PC-007A — nezávislá revize topologie skutečných křivkových hranic

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; autor komponenty je jiný agent. Požadovaný zdroj **`55c4443d40beb36c83d26f8ae940b987c4facf9c`**, `authoring/curve_topology.py`, větev `revival/p2-curve-numerics`.

**Verdikt: CHANGES_REQUESTED — T01 MAJOR OPEN.** Byla nalezena konkrétní falešná tvrdá INVALID klasifikace nativní tiskové hranice. Deklarovaná assumption o endpoint constraints uvnitř floating rezervy tento problém neřeší. Následná oprava skutečné emitované geometrie se připravuje; není zatím tímto reportem schválená.

**Aktuální následný verdikt:** oprava **`ded92eca90225a52df50346516a6d99bb8e30c83`** níže má APPROVED_IN_NATIVE_SVG_TOPOLOGY_COMPONENT_SCOPE; T01 CLOSED. Původní zdroj a FAIL výše zůstávají historickým důkazem.

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

## Následná revize skutečných SVG endpoint oblouků — `ded92ec`

Přesný zdroj **`ded92eca90225a52df50346516a6d99bb8e30c83`**, 9. 11. 2026. Spuštěn kompletní izolovaný `git archive` zdrojů/testů/pyproject, fresh subprocess a importy pouze z této kopie. Žádný živý produkční soubor sdíleného checkoutu nebyl při přezkoušení použit. [Pin, hash archivu a raw](evidence/pc007a-topology-review-archive-ded92ec.json).

**T01 CLOSED; APPROVED_IN_NATIVE_SVG_TOPOLOGY_COMPONENT_SCOPE.** Tato omezená formulace se vztahuje přesně na nové `geometry_scope = MANUFACTURING_NATIVE_SVG_ENDPOINT_ARCS_AND_AUTHORED_LINES_CUBICS`. Není to schválení přesné topologické ekvivalence původního nominal center+sweep pole ani libovolného PDF/tessellovaného výstupu.

- Původní topology + curves sada: **62 PASS / 2,66 s**, [JUnit](evidence/pc007a-topology-review-original-ded92ec-archive.xml).
- Vlastní samostatné případy: **19 PASS / 2,35 s**, [JUnit](evidence/pc007a-topology-review-own-ded92ec-archive.xml). Původní T01 orákulum významově nezměněné prošlo; staré FAIL XML se nepřepisovalo.

Přečtena nová numerická reprezentace i rozhodovací větve. Každý skutečně emitovaný minor endpoint A úsek má přesné binární endpointy a poloměr; střed a kladná racionální kvadratická váha jsou uzavřené intervaly z vnějšího sqrt. Homogeneous řídicí intervaly ohraničují celou skutečnou kruhovou část. Dělení je racionální intervalové de Casteljau, nikoli rozdělení sampled polygonu. Kladné váhy dovolují použití kartézského control hull pro celou křivku. Halfplane endpoint-only test požaduje kontrolu celých intervalů a dovolí výjimku pouze skutečně pevnému společnému konci; nejistý midpoint intervalu se nestává novým přesným sdíleným vrcholem.

Analytické kružnice pro tvrdé INVALID nyní vycházejí z intervalů skutečných SVG středů. Existence průniku a jeho pobyt uvnitř skutečných minor arc intervalů musí být přísně doložené; tečnost nebo neurčená diskriminanta není důvod k falešnému witnessu. Tvrdé překrytí totožného nebo obráceného A je založeno na shodě pevných endpointů, radius a sweep, nikoli domnělé shodě nominálních kružnic. Subdividované nejisté nativní části nevydávají analytický root pro původní celý interval.

T01 s tenkým vnějším přemostěním správně končí UNRESOLVED bez falešného průniku. Dvě další sub-ULP varianty nezkonstruovaly nulovou úsečku ani nevydaly falešnou tvrdou neplatnost. Samostatný vlastní skutečný průnik nativního jednotkového čtvrtoblouku s vertikálou `x=0.9` zůstal INVALID s intervalovým witness a kořenem poblíž `(0.9,sqrt(1-0.9²))`. Přesně obrácené dva nativní čtvrtoblouky zůstaly INVALID kvůli doloženému překrytí. Nominal `180+1e-12°` skok již nepoužívá starou endpoint assumption jako důkaz: výsledek výslovně patří emitované hranici, zatímco odchylku od nominálního tvaru dokládá oddělený curve certifikát R01.

Winding stále stojí na k query bodu disjunktních celých control boxech: homotopie na chordy je dovolena až po tomto důkazu. Intervaly na sdílených dělicích bodech se nenahrazují důkazem náhodných vzorků. Původní skryté cubic crossing případy, sousední návrat, otvory, nesting, coincident/crossing kružnice a vyčerpané rozpočty zůstaly v nezávislé sadě zachované.

### Povinná integrační mez tohoto verdiktu

Topologie skutečného SVG a metrická odchylka nominal→SVG jsou dva různé certifikáty. Samotná malá vzdálenost dvou hranic neprokazuje zachování otvoru nebo absenci dotyku. Pokud jiný výrobní writer používá jinou aproximaci (například PDF kubiky nebo chordy), musí integrace doložit topologii té konkrétní publikované hranice nebo bezpečný přenos se striktními mezemi separace; tento report jej automaticky neuděluje. Stejně tak intervaly pomocné racionální výrobní parametrizace nejsou bez další mapy prohlášené za přesnou zdrojovou center+sweep parametrizaci.

Finální doménová validace, nativní UI, skutečný SVG editor, oba kompletní exporty, lidská přejímka a P3 musí být posouzeny samostatně. Doplněk nemění AC ani žádnou výrobní toleranci.
