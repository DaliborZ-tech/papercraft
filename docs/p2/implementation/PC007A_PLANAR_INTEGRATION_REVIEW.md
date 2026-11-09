# PC-007A — finální nezávislá revize rovinného autorského podbalíku

9.11.2026. Reviewer `/root/commands_review` je jiný agent než autoři posuzované produkce a driveru; v tomto balíku neimplementoval žádnou produkci. Přesný **SOURCE `63ab275a5fe9b92bdb370a5ec3dedf1c5f70a65e`**.

**APPROVED_IN_BOUNDED_PLANAR_AUTHORING_SLICE_SCOPE. 0 otevřených BLOCKER / MAJOR pro tento technický podbalík. V02 CLOSED na skutečném nativním exportu tohoto zdroje.** Schválení zahrnuje implementované ruční rovinné line/arc/cubic profily a jejich editaci, plochy/otvory, vymezené spoje a chlopně, materiálové/topologické/layout guardy, save/reopen, navázané3D/2D a aktuální SVG/PDF writer. Neznamená dokončení celé PC-007A, loft B1/B2/B3, C/D, AU19, celého P2, produktovou akceptaci vlastníkem nebo release. Test s novým člověkem má0 účastníků; fyzický P3 zůstává NOT_RUN.

## Přesně auditovaný důkaz

[Spustitelný nezávislý audit](evidence/pc007a-planar-final-artifact-review.py) vytvořil fresh `git archive` SOURCE63 do izolovaného Temp adresáře. [Raw výsledek](evidence/pc007a-planar-final-artifact-review-63ab275.json) zaznamenává skutečný import raw PDF readeru z tohoto archivu. Source `src/` i `pyproject.toml` se proti nezávisle schválenému `3252544` **vůbec nezměnily**; jediné delta je pozorování skutečných QAction/focus v desktop driveru.

Audit nečetl jen `status=PASS`. S původními Git bloby porovnal všech **100 zaznamenaných source SHA-256**; výslovně rozlišuje Git LF a Windows CRLF fyzické hashe. Zkontroloval všech **17 nativních artifact hashů**, skutečnou cestu importované aplikace do `papercraft-profiles`, identitu projektu `3bba971b-35a8-44bc-85c2-e2813d1ce450`, canonical snapshot digest `7b5b06d53ba1e95f05432f32a6a9b3056e4dac85c1a3b8a3035488a41030803b`, UUID všech3 dílů a3 ploch a shodné přiřazení na2 stránky v projektu/snapshotu/SVG/PDF. Nevytvářel náhradní artefakty místo nativního exportu.

## Skutečné UI a oprava observability

[Nativní run04](evidence/pc007a-desktop-63ab275-run04/results.json) skutečně dokončil prázdný projekt → vlastní stěnu s kruhovým otvorem → vlastní Bézier panel → spoj/chlopeň → ruční stránky → uložení/otevření → SVG/PDF, **63.406s**. Dokládá NVIDIA OpenGL4.6,3 nativní OS dialogy s pozorovaným přijetím, skutečný export confirmation a následné dokončení. Reference jsou [uložený projekt](evidence/pc007a-desktop-63ab275-run04/curves-planar/curves-planar.apcraft), [snapshot](evidence/pc007a-desktop-63ab275-run04/curves-planar/snapshot.json) a [výsledný manifest](evidence/pc007a-desktop-63ab275-run04/curves-planar/export/.author-export.json).

V `inputs` jsou pozorované signály QAction: rectangle2, hole1, draw1, edit_curve2, undo1, attach_inside1, recompute2, save1, new1, open1, export1. Před zkratkami driver zaznamenal aktivní okno a očekávanou akci a poté ověřil skutečné zvýšení počtu signálů. Změna driveru aktivuje/zdvihne již skutečné okno; nesahá do geometrie, controlleru nebo výsledků příkazů. Příčina předchozího run03 se **neoznačuje jako prokázaný focus bug**: starý běh nezaznamenal dostatečný QAction důkaz. Jeho [FAIL](evidence/pc007a-desktop-3252544-run03/results.json) zůstává zachovaný a není dodatečně změněn na PASS.

Nativní kroky dále dokládají drag odemčeného dílu a zachování kotvy zamčeného dílu, pick sestaveného3D s vazbou na papír, cancel/edit/apply/undo zdroje, zobrazitelnost materiálu po otevření a zachování uživatelského zoom/pan při běžném recompute. Automatizované skutečné Qt/Windows ověření není pozorování začátečníka ani důkaz plné použitelnosti pro člověka. Jediné přijaté varování je `MATERIAL_CLEARANCE_UNVERIFIED` s explicitním digitálním/fyzickým rozlišením.

## V02 — skutečná plocha finálního exportu

Nezávislý očekávaný výsledek je stěna120×100 s dírou R20, tedy `12000−400π`. Audit načetl skutečné původní PDF lexémy přes již samostatně revidovaný raw reader a provedl **vlastní přesný Fraction Green integrál skutečných C/L/Z polynomů**. Expected nepřebírá produkční helper ani produkční toleranční obálku.

| Actual PDF část | Plocha mm² | Absolutní chyba vůči analytice | Normativní mez mm² |
|---|---:|---:|---:|
| Vnější stěna |12000.000000000002|1.82e−12|.012|
| Otvor R20 |1256.6338136850402|.003247750877|.01|
| Stěna bez otvoru |10743.366186314961|.003247750878|.010743362939|
| Bézier2060 +tab128 |2188.0000000000005|4.55e−13|.01|
| Příjemce80×10 |800.0000000000001|1.14e−13|.01|

Původní V02 actual net chyba `.036339134183` překračovala `.010743362939`. Nový skutečný nativní artefakt splňuje tutéž přejímku; ta nebyla změkčena. Samostatný otvor a outer byly také ověřeny, takže úspěch nevznikl kompenzací těchto dvou chyb. Manifest má doložené actual native topology a area intervals a samostatný source flattening/position scope. Nezávislé [source/negative/rollback review opravy](PC007A_AREA_INTEGRATION_REVIEW.md) ověřilo81 původních +10 vlastních testů, včetně přesně4 neúspěšných coarse pokusů, automatického úspěchu po2 zpřesněních, 1 pokusu při jiné chybě a zachování původních i cizích souborů.

## Skutečné Inkscape roundtripy obou stránek

[Bézier stránka](evidence/pc007a-inkscape-63ab275-page1-run03/editor-results.json), **14.500s**, a [stránka s kruhovým otvorem](evidence/pc007a-inkscape-63ab275-page2-run04/editor-results.json), **14.093s**, jsou nové skutečné Inkscape1.4.4 běhy nad kopiemi právě tohoto nativního bundle. Oba mají doložené native Inkscape actions pro posun dílu10/15px a barvu, skutečné GUI Unicode psaní/uložení s kontrolou foreground před každým vstupem a editorové screenshoty/render. Reviewer do GUI nezasahoval; nezávisle četl zapsané soubory a vizuálně prohlédl oba finální rendery.

Vlastní přesný Fraction parser normalizoval relativní/absolutní M/L/H/V/C/A/Z a skutečnou přímou closure. Předchozí vadný harness se nepoužil jako expected. V původních ID bylo beze změny **6 výrobních/guide cest**, včetně1 native C a4 native A, vnějšího obrysu i samostatného otvoru. Žádná křivka nebyla nahrazena tětivovým mesh. U obou stránek zůstaly stejné fyzické rozměry210×297mm a viewBox, exact100mm calibration i při editorovém přidělení ID dříve anonymní čáře. Při hole stránce jsou zachovány2 CUT smyčky (outer a circle); jde o skutečné řezy otvoru, nikoli slib fyzického vyříznutí.

Na obou stránkách byl z uloženého XML přečten přesný nový text **„Žluťoučký – vlastní díl“**, nová barva, nezměněné ostatní texty a nezměněná lokální geometrie. Hashe `editor-original.svg` odpovídají skutečnému origin source; všechny `origin_bundle_sha256` i finální native hashe stále odpovídají. Editor pracoval s kopií a origin projekt/bundle zůstal byte-for-byte zachovaný. Jde o ověření těchto skutečných stránek v Inkscape, nikoli všech editorů, všech DPI, AU17 v plném rozsahu nebo uživatele.

## Regrese a uzavření historických nálezů

Reviewer přímo načetl [uložený JUnit](evidence/pc007a-suite-63ab275-run03.xml): **908 testů,0 failures,0 errors,0 skipped,76.465s**. Sadu znovu nespouštěl, protože zdroj se od plošně revidovaného pinu nezměnil a aktuální artefakt audit pokrývá finální delta. Jde o přímý audit uloženého ownerova běhu, nikoli nový běh sady. Vlastní dřívější analytické a komponentové oracles jsou dohledatelné v navazujících zprávách.

| Nález | Přesný současný závěr a důkaz |
|---|---|
| P01/P02 — native topology/proxy layout | CLOSED v [planar review](PC007A_PLANAR_REVIEW.md), raw původní e3a FAIL zachovaný |
| T01/R01 — native arc topology/serialization | CLOSED v [topology](PC007A_TOPOLOGY_REVIEW.md) a [curves](PC007A_CURVES_REVIEW.md), component scope zachován |
| V01 — PDF raw numeric lexémy | CLOSED v [vector output review](PC007A_VECTOR_OUTPUT_REVIEW.md), původních5 FAIL zachováno |
| Materiálové proxy/contact/bend nejistoty | Bounded scope APPROVED v [material integration](PC007A_MATERIAL_INTEGRATION_REVIEW.md), guaranteed/possible a známé negativní priority zůstávají |
| Preview `'points'` | Komponentově opravený2944; source63 skutečné Bézier+tab dialog/export potvrzují finální integraci. Původní611 native FAIL zachován |
| V02 — PDF plocha | **CLOSED na finálním native SOURCE63**, nezměněné normativní meze, nezávislý actual Green audit výše |
| Editor explicit L vs Z | Opravený source325; původní2944 editor FAIL zachován, oba SOURCE63 editor roundtripy nově prošly |
| Native325 run03 | Historický FAIL zachován, příčina zůstává nedoložená; nová observability a native63 skutečný PASS jej nenazývají zpětným PASS |

## Skills, integrace a neuzavřený produkt

Načtené čtyři projektové skills se uplatnily na skutečném výsledku: materiál/otvor/chlopeň a otevřené plochy; viditelný výsledek, vratný experiment a volba kontextu; nezávislé expected a rozlišení digitálního/human/fyzického důkazu; okamžité předání V02, oprava, nový source pin a actual re-review. SK009/010 mají dřívější úzké review v material reportu; jejich širší účinnost se tímto jedním přírůstkem automaticky neuzavírá. Nový tolerance lesson SK011 a finální queue/delivery metadata jsou samostatný ještě nepřipnutý dokumentační delta a čekají na kontrolu konkrétního metadata commitu. Tento source/artifact verdict je neinterpretuje předem jako schválené.

Integrační owner může po kontrole finálního metadata pinu integrovat a publikovat tento ucelený technický podbalík podle mandátu. Nesmí označit celou PC-007A nebo P2 za hotovou. Loft UI, B1/B2/B3, C/D a navazující řezy zůstávají v jejich pravdivém rozpracovaném stavu; tento reviewer nepřijímá souběžné loft změny z jiných worktrees. AC-US08 má0 účastníků, AU19 není nahrazeno touto malou fixture a P3 zůstává NOT_RUN.

Reviewer neprovedl produkční změnu, staging, commit, merge nebo push; tyto review/evidence soubory čekají mimo zmrazený HEAD na integračního ownera.
