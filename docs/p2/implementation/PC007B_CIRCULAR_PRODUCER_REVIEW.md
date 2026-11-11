# Nezávislé review C consumer/composer/domain/publisher

Reviewer: `geometry_analysis`. Produkční source **80493e6e9e48cb22548b9a55c2116d850e8e73f3**,
izolovaný worktree `papercraft-circular-producer-review`, branch
`review/p2-circular-producer`. `src/tests/tools` jsou podle skutečně spuštěného
`git diff` totožné s `e3413e56b33043754a4e6b54a91b35d9f9f03e24`. Produkci jsem neměnil.

**Verdikt: APPROVED_IN_CONSUMER_COMPOSER_DOMAIN_PUBLICATION_COMPONENT_SCOPE.**
Zásadní otevřené nálezy: **0**. Jeden MINOR test-evidence nález CY01 je uzavřen
test-only opravou **84117c484aee8049f339cc602ba19d70e1e3ccba** a nezávislým replayem.
Před integračním tvrzením o opravě musí být tento testový pin převzat; jeho
`src` diff je prázdný. Evidence/addendum autora: `fd81d9bd713882d8846988a8897d6df1d1a46504`.

## Nejde o schválení vlastních matematických tvrzení

Jsem autorem source-transfer dependency `f10fa26`, **nikoli autorem nového C
consumeru, composeru, source binderu či publisheru**. V tomto review výslovně
vylučuji nové nezávislé schválení vlastních `curved_tabs_transfer.py`,
`curved_tabs_chart.py`, dřívější `loft_area.py` a ostatních vlastních pure math
prací. Transfer má cizí nezávislé schválení `0023902` v
[samostatném review](PC007B_SOURCE_TRANSFER_REVIEW.md); proti tomuto dependency
pinu se transfer source Git blob v 804 nezměnil. Posuzuji jeho správné volání,
pravdivé current source/boundary podmínky a oddělení následného vector scope.
Source/rim foundation již má samostatné cizí review `2bdbf2f`/`c04e43b`.

Tento verdikt není celé C/P2, nativní Windows/UI/editor, nový uživatel, fyzická
elasticita, lepidlo ani P3. UI zde není; vše běželo s `QT_QPA_PLATFORM=offscreen`
a lokálním `PYTHONPATH=.../src`. Skutečné importy, source SHA/Git bloby a hash
vlastních důkazů jsou v [manifestu](evidence/pc007b-circular-producer-review-source.json).

## Skutečné ověření

- Relevantní author consumer/composer/persistence/scene/output selection:
  **95 PASS /134,05 s**, [JUnit](evidence/c-producer-review-author.xml). Šest původních
  SVG mutation případů mělo slabinu CY01; jejich důkaz nahradil replay opravy níže.
- Vlastní [zdroj testů/orákel](evidence/pc007b-circular-producer-review-own.py):
  **29 PASS /38,63 s**, [finální JUnit](evidence/c-producer-review-own-complete.xml).
  Expected source plochy/identity nejsou výsledkem stejného generátoru nebo
  produkčního area/PDF reader helperu. Zahrnují skutečné zdroje/registry i výstupy.
- Samostatný replay **přesného opraveného Git blobu** testu 84117c4 proti aplikaci
  804: **6 PASS /20,97 s**, [JUnit](evidence/c-producer-review-fixed-delta.xml).
  Vlastní odlišné valid-XML SVG fault případy: **6 PASS /2,22 s**; jsou i ve finální sadě.
- Samostatný původní real-writer cancellation checkpoint: **1 PASS /0,72 s**,
  [JUnit](evidence/c-producer-review-cancel.xml); zachoval owned i foreign bytes.
- Ruff vlastního testu a whitespace diff: PASS. Původní raw výsledky včetně
  chybných/disqualified vlastních harness pokusů zůstávají zachované; nejsou
  vydávány za produktové chyby ani za geometrické důkazy.

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
python -m pytest tests/authoring/test_curved_connector_sources.py tests/authoring/test_curved_connector_scene.py tests/authoring/test_curved_connector_persistence.py tests/authoring/test_curved_connector_geometry.py tests/authoring/test_circular_material.py tests/authoring/test_circular_material_integration.py tests/authoring/test_circular_guide_output.py tests/authoring/test_pdf_page_precision.py -q --junitxml=Temp/c-producer-review-author.xml
python -m pytest docs/p2/implementation/evidence/pc007b-circular-producer-review-own.py -q --junitxml=Temp/c-producer-review-own-complete.xml
```

Použit je root `.venv/Scripts/python.exe` 3.12.15. Delta replay používá dočasnou
kopii `git show 84117c4:tests/authoring/test_circular_guide_output.py`, nikoli edit
souboru z 804; aplikace i fixture imports zůstávají v tomto review checkoutu.

## Source, identita, cache a uzavřená scéna

`curved_connector_inputs` zahrnuje source surface/profile/frame, měřítko, skutečný
material profile, všechny vybrané cizí material faces, staré straight connectors
a další aktivní C sady. Layout do sestavené geometrie nepřidává nepravdivou
závislost. Source hash je z obsahu, nikoli jen UUID/revision. Vlastní testy mění
source sweep, skutečný receiver pose a hole, current certificate i equal-area
CUT bez změny IDs/revision: žádná změna nezíská current positive publication.
Shrink poolu 12→6→12 a off/custom slot po save/reopen zachová původní IDs/override;
neplatný count command má bezeztrátový rollback. Globální UUID validation navíc
zahrnuje connector i celý uchovaný slot pool.

Omezený source context se přestaví z authored záznamů, ne current mesh/cache.
Kontrolují se zdvojené body/receiver vazby, profile coverage, part membership a
frame. Kontext je označen jako source-only a nelze jej publikovat jako celý
projekt. Oddělený `curved_source_project` fence znovu vytvoří úplný canonical
snapshot včetně všech tiskových dílů, layoutu a běžných chyb. Vlastní odmítnuté
forgeries: odstraněný úplný zdroj, přesunutý nepřipojený foreign surface a
equal-area translated CUT. Exportní validator se při této rekonstrukci nevolá
zpět; source LRU je omezená a ukládá immutable JSON, návraty jsou detached.

Foreign continuous material používá všechny cubic Bernstein controls nebo celý
arc circle box, ne pouze endpoints/render mesh. Vlastní cubic má endpoints x200,
controls x−100 a skutečný x(1/2)=−25; jeho whole hull blízko C správně způsobí
UNRESOLVED a změna source zneplatní předchozí packet. Conservative AABB overlap
není přejmenován na COLLISION ani CLEAR. Whole-phase straight tab hull zahrnuje
šířku i celý custom outline; jiné C sady mají samostatný whole-motion box.

Opačný legacy bend consumer nepoužije stale CLEAR při přiblížení C; podporovaný
rovinný zbytek scény stále hledá prokázaný B02/K01 negative. Opakovaná coupled
sada ověřila COLLISION i po přidání neznámé tloušťky/blízké C nejistoty. Vlastní
actual receiver void má radius9,8, zatímco veškerý final glue je mezi r0,5 a
r<9,401; native receiver negative zůstává v reportu i při unknown thickness,
publication je zablokovaná. Důkaz nedostává physical claim.

## Actual materiál, source/native rozdíl a vektorový výstup

Vlastní čerstvé zdroje zahrnují quarter-arc kruhy, r10/h30, oba směry výšky,
reverse correspondence, r10→20/H=Float(√800), near r10,000001 a společný posed
frame. Native body zůstává A/L, bez fiktivních fold/score čar pro stočení.
Source R/κ interval a nominal native κ nejsou ztotožněny. Každý enabled slot
používá své actual A/L+apex data a explicitní whole-chart producer, nikoli
`RIM_TANGENT_ONLY` či scalar center delta za whole-collar derivaci.

Vlastní boundary check vyžaduje přesně jeden CUT side a→apex a jeden apex→b
pro každý skutečný shared GUIDE a/b, bez stejného a↔b CUT. Actual filled loop
sdílí endpoints a apex; composer znovu váže registry, source direction/intervals,
native chart digest a pure source area. Source trim endpoints se neberou jako
midpoint nejistých úhlů: intervaly řídí coverage/order, actual coordinates pocházejí
z actual shared base. Full native topology a area jsou nutné před current cache.
Otvory přijímače nebyly nahrazeny nominálním diskem a source plane se nepromítá.

Composer a publisher používají plochu tělo+legitimní chlopně; **relativní mez
normalizují pouze tělem**. Vlastní kvalifikovaný skutečný cylinder r100/h100
má body `20000π`, tabs13,68. Validní SVG fault přidá plochu0,0628386931 mm² mezi
správnou mezí0,0628318531 a chybnou union mezí0,0628455331. Endpoints se posunou
jen o0,0001000109 mm, tab CUT/GUIDE zůstane stejný. Skutečný AREA guard odmítne
publikaci a zachová všechny předchozí bundle bytes/staging cleanup. Jde o
skutečný podporovaný C source→snapshot→writer comparator, ne jen mocked status.

První skutečné čtyři bundle artefakty producer67 a doménový bundle511 byly
znovu hashově ověřeny. Vlastní PDF reader čte původní decompressed decimal
operands přes `Fraction`, skládá raw `cm` determinanty a nezávisle integruje
L/C Green polynomy; nepoužívá production PDF reader ani native area helper.
Analytické source očekávání je cylinder/frustum area plus triangle mínus/plus
pravý circular segment base. [Vlastní numerické výsledky](evidence/pc007b-circular-producer-review-areas.json):

| Artefakt | Own source→actual PDF area chyba mm² | Mez mm² |
|---|---:|---:|
| cylinder-first | 2,28e−13 | 0,01 |
| cone-first | 0,001753194917 | 0,01 |
| cone-second | 0,000227531794 | 0,01 |
| near-cylinder-first | 0,000002503893 | 0,01 |
| off/custom/far/3pages | 2,28e−13 | 0,01 |

Analytické float π očekávání je zde numerické orákulum s rezervou řádově11
desetinných míst proti rozhodné mezi, nikoli nový rigorous interval certificate.
Skutečný PDF Green integral je přitom uchován celý racionálně. Raw MediaBox
origin/rozměry všech artefaktů mají nezávislou token kontrolu <1e−11mm vůči A4.
Fix je lokální PDFPage objekt, bez změny globálního ReportLab formatteru.

CUT/GUIDE/TABS jsou z téhož snapshotu; role reader dál odmítá neuzavřený CUT,
neznámou roli i open TABS. Actual A→PDF C se pro GUIDE/fill zpřesňuje na vlastní
reserve/16. Regionální Hermite/control-hull position a globální numerical length
bound zahrnují celé kubiky, ne jen endpoints; vlastní fresh804 cone PDF má
změněný jediný vnitřní GUIDE C control o0,001, endpoints zůstávají byte-exact.
Raw role reader přijme validní cestu, až celý GUIDE metric guard ji odmítne.
Canonical metadata producer67 zůstávají historická: nepředstírám, že starý
snapshot je current canonical report novější domény; tento nový fault proto
používá fresh804 source/bundle. Původní soubory se nepřepsaly.

Reporty výslovně oddělují `SOURCE_NATIVE_STRAIN_CERTIFIED` od actual
`CUT_GUIDE_FILL_POSITION_GLOBAL_LENGTH_AND_AREA_ONLY`. Není zde actual PDF C
derivative/collar-strain ani fyzický fold proof. Pozice není použita jako náhradní
strain ani jako plošná tolerance. Actual vector metrics neprohlašují nový
deformační model PDF; jde o doloženou výrobní reprezentaci téhož source modelu.

## CY01 MINOR — nekvalifikované původní SVG mutanty — CLOSED

`test_circular_guide_output.py` v 804 používal `ET.write(encoding='utf8')`.
U skutečných Unicode metadata Expat takový dokument odmítl jako not well-formed
ještě před GUIDE guardem. Šest starých green cases proto samo neprokazovalo
požadované geometric rejection. Produkce již psala správné `utf-8`.

Autor (jiný agent) opravil pouze test pin84117c4: `utf-8`, explicitní ET.parse
a root SVG assertion každého mutantu, specific guard reason pro každou vadu.
Zdrojové chyby neobcházel, toleranci neměnil. Vlastní oddělené validné mutanty
omitted/extra/reversed/moved/CTM/cross-role všech6 skutečně odmítly role/metric
guards, nikoli XML parse. Přesný fix blob replay prošel dalším6cases. MINOR je
tím uzavřen bez produkční změny; původní203raw se nemažou, těchto6cases nahrazuje
přesnější evidence. Dva první own area pokusy použily chybnou add_loft/add_page
signaturu; třetí vlastní ET mutator měl tutéž encoding slabinu. Zachované FAIL
raw jsou harness qualification historie a nepřipisují se produktu.

## Skills a zbývající přejímky

Načteny AGENTS a všechny čtyři projektové skills, AU07/AU10–11/AU15–17,
numerické G/C/X a source-transfer/producer proofy. Konstrukce je doložena
skutečným příjemcem, collar a material roles. Verification přeneslo DR01,
P01/P02, SO01, V01/V02, K01 a PF01 do whole controls, raw lexemů, body-only
komparatoru, negative+unknown a current-cache poison. CY01 ukazuje nutnost
kvalifikovat samotný mutant před připsáním PASS; uzavření doložil jiný autor
a vlastní replay. Delivery zachovalo přesné source/evidence piny. UI skill
v tomto backend scope vede k readonly repair/status packets a zachování author
intent/undo; neuděluji na jeho základě splnění UX či nového člověka.

Aktuální C native desktop/editor, usability s novým uživatelem, celé all-C
package/harness review jiným reviewerem a P3 zůstávají **NOT_RUN / PENDING**.
Toto komponentní review je nepřepisuje a neuděluje vlastníkovo přijetí.
