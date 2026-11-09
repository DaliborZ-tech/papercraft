# PC-007A — nezávislá revize opravy V02 a editorové closure

Následný aktuální verdikt: [finální source/artifact revize63ab275](PC007A_PLANAR_INTEGRATION_REVIEW.md) ověřila nový skutečný nativní export i oba editor roundtripy a uzavřela V02. Níže uvedený pending stav325 je zachován jako stav při předání této zdrojové revize.

9.11.2026. Reviewer `/root/commands_review` není autorem posuzovaných změn. Přesný source **`3252544850c0d4a9c4465de8f359ec2a5350af27`**; archivovaný delta rozsah od `2944c0fc7bb899355d45fe1f16e49253c90560c4`: skutečné SVG/PDF area guards, přesnější serializované PDF CTM, omezené zpřesnění oblouků v transakci a přesná normalizace přímého uzavření SVG při editorovém auditu. Numerický helper `60d60d1` má [samostatnou nezávislou revizi](PC007A_AREA_REVIEW.md); tu tento integrační audit nenahrazuje.

**APPROVED_IN_SOURCE_AREA_GUARD_AND_EDITOR_CLOSURE_SCOPE, 0 nových BLOCKER / MAJOR.** Zdrojová oprava V02 i její negativní a rollback guard jsou ověřeny. **Finální nativní potvrzení V02 a schválení celého planar podbalíku zatím PENDING:** nativní `3252544-run03` skončil FAIL v sekvenci exportních potvrzení a nevytvořil finální bundle. Níže uvedený úspěšný nezávislý offline export jeho uloženého snapshotu se nesmí vydávat za nativní UI export. Původní V02 FAIL na `2944c0f` v [předchozí revizi](PC007A_MATERIAL_INTEGRATION_REVIEW.md) a raw důkazy zůstávají zachované.

## Připnutí a ověření

[Archiv a čtyři skutečné importy](evidence/pc007a-area-integration-review-archive-3252544.json) dokládají fresh `git archive` zdroje/testů/tools, fresh subprocess a skutečné cesty `author_export`, `curve_output_validation`, `svg_curve_validation`, `curve_area` do izolovaného Temp adresáře. Každý LF-normalizovaný importovaný text odpovídá připnutému Git blobu; deklarována je jen běžná Windows LF/CRLF konverze.

- **81 původních PASS /2.98s**, [JUnit](evidence/pc007a-area-integration-review-original-3252544.xml): původní area, export guard, raw PDF a editor closure regrese.
- **10 vlastních PASS /2.50s**, [vlastní oracles](evidence/pc007a-area-integration-review-own.py), [JUnit](evidence/pc007a-area-integration-review-own-3252544.xml). Očekávání plochy používá nezávislý analytický `400π`, line/cubic Green integrál actual PDF příkazů a ručně zadané rozdíly/budgety; nevolá produkční area helper jako expected.
- Dvě chyby prvního reviewer harnessu jsou zvlášť zachované: [SyntaxError v novém vlastním testu](evidence/pc007a-area-integration-review-harness-syntax-3252544.json) a [umístění v doporučeném okraji](evidence/pc007a-area-integration-review-harness-margin-3252544.json). Po opravě testu a posunu Y8→25 vznikl výše uvedený PASS; nejde o produktové vady nebo odstranění negativních testů.

## Důvody schválení zdroje

Area se počítá až po prokázání skutečné nativní topologie, z dodaných přesných L/C a kruhových A čísel. Produkční guard porovnává nejhorší krajní rozdíl obou outward intervalů, nikoli jejich midpoint. Samostatný normativní rozpočet `max(.01,1e−6×base_lower)` nepřebírá poziční/perimeter tube. `base_lower=max(0,CUT_lower−ΣTAB_upper)` je konzervativní dolní mez základního materiálu, pokud cache dodržuje `CUT=base∪tabs`; překryvy chlopní mohou rozpočet pouze zpřísnit. Rozpočet se proto nezvětšuje plochou chlopní. Zdrojový flattening a source→native position bound zůstávají oddělené důkazy; aktuální porovnání má pravdivý scope `ACTUAL_NET_CUT_AREA_AGREEMENT`.

PDF přesný transform je emitován pouze po vlastním čerstvém `q`. Zavolání skutečného `canvas.transform` zachová backend tracking a ověří očekávaný lokální `cm`; nahradí se právě tento token17místným fixed decimal zápisem bez nepřípustného PDF exponentu. Actual raw reader stále čte původní lexémy a numeric guard posuzuje skutečná CTM a controls. Vlastní29° případ ověřil přímo token `cos29°` v decompressed streamu, zachované Fraction coordinates a nezávislý integrál otočené díry/stěny. Nejde o důkaz z pypdf float roundtripu.

Zpřesnění je omezené na4 kompletní staged pokusy, s desetinovým arc budgetem po každém skutečném area mismatch. Chyba PDF topologie/parseru se nerecykluje jako plošný problém. Vlastní vynucený coarse backend ignoroval requested precision a po přesně4 pokusech export skončil chybou se zachováním všech původních vlastněných souborů, manifestu i cizího `author-note.txt` byte-for-byte; stage byl uklizen. Jiná vynucená geometry chyba vyvolala právě1 pokus. Skutečný počáteční coarse `.001` writer se automaticky dostal k úspěchu právě2 pokusy. To řeší přesnost za uživatele bez požadavku na znalost interní geometrie.

Relativní TAB budget byl zkoušen také negativně: CUT1,000,000mm² s base1000mm² nesmí přijmout rozdíl.1mm², přestože rozpočet z celé CUT plochy by jej přijal; správně se odmítne a rozdíl.009 projde absolutní.01 mezí. Shodné midpointy širokých intervalů[100,101] se odmítnou; zero conservative base zachová absolutní.01 minimum.

Editor normalizace odstraňuje jen skutečný poslední přímý L do **přesně stejného** počátku před Z; Fraction brání falešnému rozdílu `.1+.2`. Každý subpath má vlastní začátek. Vlastní negativní případy zachovávají blízký endpoint `.10000000000000001`, C a A končící ve startu. Tím je opravena konkrétní příčina původního Bézier Inkscape harness FAIL, nikoli povolena ztráta křivky či malé hrany. Skutečný nový Inkscape roundtrip tímto unit testem prokázán není.

## Nezávislý actual PDF výpočet původní V02 geometrie

[Spustitelný audit](evidence/pc007a-area-integration-artifact-review.py) z přesného archivu vyexportoval snapshot uložený skutečným run03 do nového Temp adresáře. [Raw výsledek](evidence/pc007a-area-integration-artifact-review-3252544.json) má SHA-256 všech vytvořených souborů i vstupu a explicitní označení **OFFLINE**, nikoli náhradní nativní PASS. Přesný racionální Green integrál actual raw PDF C/L/Z dal:

| Část | Actual mm² | Analytické expected | Absolutní chyba | Mez mm² |
|---|---:|---:|---:|---:|
| Vnější stěna |12000.000000000002|12000|1.82e−12|.012|
| Kruhový otvor R20 |1256.6338136850402|400π|.003247750877|.01|
| Stěna minus otvor |10743.366186314961|12000−400π|.003247750878|.010743362939|
| Bézier materiál s tabem |2188.0000000000005|2060+128|4.55e−13|.01|
| Příjemce |800.0000000000001|800|1.14e−13|.01|

Outer a otvor byly zkoušeny i samostatně, takže jejich chyby se v tomto svědkovi neschovávají vzájemným odečtením. Bézier `2060+128` je kontrola celé skutečné CUT geometrie; není tvrzením fyzické lepicí plochy ani náhradou base-only definice tolerančního rozpočtu.

## Skills a hranice

Skutečně načtené čtyři projektové skills se projevily nezávislým očekáváním a source pinem, oddělením plochy materiálu/chlopní/otvorů, bezpečným autonomním zpřesněním bez geometrického navádění uživatele, zachováním starých FAIL a požadavkem na nový skutečný UI/editor výsledek. Nešlo o obecnou dokumentační fázi ani změnu AC. Autor harnessu není nový uživatel; novice count zůstává0. Fyzická sestavitelnost a P3 zůstávají NOT_RUN, PC-007A jako celek včetně loft UI není schválená. Žádná produkce, staging nebo Git commit tímto reviewerem nebyly změněny; dokumenty čekají na konec rootova source freeze.
