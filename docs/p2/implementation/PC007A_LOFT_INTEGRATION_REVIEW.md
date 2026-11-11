# Nezávislá integrační revize B1/B2/Bézier

11.11.2026. Reviewer: samostatný agent `authoring_independent_review`; autor integračního/UI/exportního balíku je jiný agent. Reviewer neměnil produkci, testy produktu, stage ani desktop.

**Verdikt: APPROVED_IN_B1_B2_BEZIER_TECHNICAL_INTEGRATION_SCOPE.** Posuzovaný CODE je **`a46f179331a5ab94fec7b68ba52b2f9431ac699b`**, evidence/metadata **`053abda0f6baa2b9be39394745e2c2491163c0d7`** s úzkou opravou MI-01 **`382a364d81e7975cb9c76f4a8eb1dfd72abc0c79`**. Otevřené zásadní nálezy tohoto vymezeného přírůstku: **0**. Technický přírůstek lze integrovat podle platného mandátu; celé PC-007A/P2 zůstává IN_PROGRESS. Tento verdikt není nový uživatel, fyzická stavba ani produktové přijetí celé implementace.

## Zdroj a rozsah nezávislosti

Reviewer skutečně načetl AGENTS a všechny čtyři projektové skills, dotčené AC-AU09/AU13/AU15 a AC-US a původní numerické meze. Pro vlastní runtime kontrolu použil úplný `git archive` přesného CODE do izolovaného dočasného adresáře. [Záznam zdroje](evidence/pc007a-loft-integration-review-source.json) a [vlastní audit](evidence/pc007a-loft-integration-review-audit.json) obsahují skutečné importované cesty, hashe, výsledky a meze.

Delta `src/tests/tools/pyproject.toml` mezi schváleným V4 `7ee42b3` a CODE a mezi CODE a konečnými metadata je prázdná. Nejde o novou nezkontrolovanou větev numeriky. Použitelné jsou předchozí oddělené revize [domény/LD01–04](PC007A_LOFT_DOMAIN_REVIEW.md), [intrinsic plochy](PC007A_LOFT_INTRINSIC_AREA_REVIEW.md), [UI widgetu](PC007A_LOFT_UI_REVIEW.md), [workspace](PC007A_LOFT_WORKSPACE_REVIEW.md), [source→skutečný výstup](PC007A_LOFT_OUTPUT_REVIEW.md), [výkonu/PF-01](PC007A_LOFT_PERFORMANCE_REVIEW.md), [asynchronní publikace](PC007A_EXPORT_JOB_REVIEW.md), [coalescingu](PC007A_LOFT_COALESCING_REVIEW.md) a [V4 rezervy](PC007A_LOFT_COALESCING_V4_REVIEW.md). Jejich omezení zůstávají platná.

Vlastní cílené opakování na tomto přesném izolovaném CODE: **39 PASS /18,36s**, [JUnit](evidence/pc007a-loft-integration-review-targeted-a46-final.xml). Zahrnuje předchozích 13 nezávislých async/export negativů a relevantní loft/export-job regrese: rušení před publikací v jednotlivých fázích, pozdní Cancel, skutečný rollback po zápisu, oddělený snapshot, ukončení dialogu, source binding a přímou plošnou kontrolu. Jde o opakované případy, nikoli 39 nových unikátních testů navíc k1179. První reviewerův sběr chyběl import testového helperu `test_workspace`; [původní collection error](evidence/pc007a-loft-integration-review-targeted-a46.xml) je zachován a není produktovou regresí.

## Skutečné Windows a výrobní artefakty

Reviewer nezávisle četl uložené důkazy, nikoli znovu řídil Windows. Všechny tři native výsledky připínají CODE, skutečnou importovanou cestu, 108 zdrojových stop, NVIDIA OpenGL4.6 a vlastní aplikační proces. Obsahují tři skutečně přijaté nativní souborové dialogy a dva skutečné QMessageBox. B1/B2/Bézier prošly od prázdného projektu vlastními Qt vstupy přes profily, preview/edit/Cancel, propojený výběr, ruční stránky, drag/locks a native Save/New/Open až po obě vektorové reprezentace. Status je pravdivě PASS_REQUESTED_FIXTURE, nikoli celé A/B/C/D.

Reviewer ověřil všech **17/18/17** zaznamenaných souborových hashů, jejich přesné uložené Git bytes a všechny zdrojové stopy. Jeden helper má v `git archive` CRLF, zatímco nativní stopa přesně odpovídá Git LF; rozdíl je pouze koncovka řádku a je explicitně zapsán. Výrobní artefakty se nenormalizovaly. Všechny tři skutečné `.apcraft` reviewer znovu načetl přes izolovaný CODE: `to_dict` odpovídá uloženému JSON, layout je bez chyb a nové snapshoty jsou platné.

Vlastní matematický reader nepoužívá writer ani produkční geometrický helper pro expected. Původní PDF numerické tokeny čte z dekomprimovaného streamu před převodem do float, L/C integruje přesnou racionální Greenovou formulí a násobí přesným determinantem skutečných PDF CTM. SVG kruhové A řeší samostatně s 80místnou Decimal aritmetikou; π a atan používají vlastní konvergentní řady. Zdrojové očekávání je odvozené z vlastních parametrů: gotické ostění přes substituci polovičního úhlu a Simpsonovu globální rezervu, stěna s odečteným gotickým otvorem, kruh400π, mezikruží176π a Bézierova extruze přes explicitní polynom rychlosti s globální rezervou čtvrté derivace. Binary hodnota měřítka je zachována.

| Skutečná strana | CUT smyčky | Horní vlastní chyba source→SVG mm² | Horní vlastní chyba source→PDF mm² | Původní mez mm² |
|---|---:|---:|---:|---:|
| B1 stěna/otvor | 2 | 0,000000101 | 0,002800 | 0,01113284 |
| B1 gotické ostění | 1 | 0,000596 | 0,000596 | 0,01 |
| B2 disk | 1 | <0,000000001 | 0,003235 | 0,01 |
| B2 mezikruží/otvor | 2 | <0,000000001 | 0,001437 | 0,01 |
| Bézierova extruze | 1 | 0,001668 | 0,001668 | 0,01 |

Všechny vyhovují původnímu `max(0.01 mm²,1e−6×A)` přímo od zdroje do skutečného souboru. Vlastní orákulum nepřiděluje každé mezifázi novou toleranci. B1 ostění má skutečných **16C**, obě rovinné kruhové strany a gotický otvor skutečné **A**; rozvin normální Bézierovy extruze má správně přímé okraje, není mu uměle připsána C. Všech pět PDF stran nemá obrazový XObject, SVG nemá raster image. Ve stěně i mezikruží zůstávají dvě skutečné CUT smyčky, otvor se odečítá. Oddělený původní disk B2 je nadále samostatný díl; jeho existence nevydává odvozený prstenec za plný disk.

## Editor a uzavření LX-01

Všech **pět aktuálních Inkscape1.4.4** běhů má PASS, přesný zdroj a odpovídající helper hash. Reviewer porovnal všechny čtyři výstupní hashe každého běhu, původní SVG proti skutečnému native exportu a nezměněný celý původní bundle. Záznamy vážou skutečné Unicode psaní/uložení na vlastní PID/HWND a kontrolu popředí před klávesami. Přesný text „Žluťoučký – vlastní díl“ je skutečně přečten z editovaného SVG. Připnutý strict harness zachovává původní IDs/geometrii/role, dovoluje jen nový ID již existující anonymní kalibrace a přesun vlastního dílu10/15CSSpx. Vstup se neopravoval XML zásahem.

Reviewer navíc samostatně přečetl relativní i absolutní L/C/A cesty editovaných SVG a znovu spočítal jejich čistou plochu a otvory: [nezávislý editorový readback](evidence/pc007a-loft-integration-review-editor-independent.json). Gotické ostění má změnu **0,0000216451463562mm²**, Bézierův rozvin **0,000004434254mm²**, ostatní tři strany nulovou změnu v použitém readeru. Skutečné rendery stěny, gotického ostění, mezikruží a Bézierova pásu byly také vizuálně prohlédnuty. Pozitivní výsledek jednoho editoru necertifikuje jiné editory ani nový uživatelský test.

**LX-01 CLOSED_VERIFIED_IN_CURRENT_a46_ARTIFACT_SCOPE:** nové ostění má21 příkazů/16C; aktuální přísná serializační kontrola2e−5mm prošla a uložený přesný rozbor dává maximum2,2575571e−6mm. Původní9049příkazový FAIL s porušením normativní plochy a pozdější69příkazový FAIL pouze přísnější serializace zůstaly uchované. Normy, harness ani preference editoru se neoslabily. Samotný malý roundtrip rozdíl nenahrazuje výše uvedený přímý source→výstup důkaz.

## Metadata, skills a přetrvávající meze

[Přesný metadata audit](evidence/pc007a-loft-integration-review-metadata.json) kontroluje Git tree konečného pinu, všechny měněné dokumentové odkazy a byte shodu nových raw důkazů. Mandát, normativní AC/kontrakt, přijetí produktové brány a její historie jsou beze změny. Queue ponechává PC-007A/P2 IN_PROGRESS, AC-AU09 pouze částečně technicky ověřené, AC-AU13 nedokončené; nový člověk má0/NOT_RUN, AC-AU19 i fyzické P3 NOT_RUN. Branch-local C/D práce není vydávána za publikovanou hotovou implementaci.

**MI-01 CLOSED_VERIFIED** na382a: původní vrchní `release_readiness` stále uváděl chybějící performance review a kompletní B1. Oprava mění pouze zastaralý důvod na skutečně zbývající B3/D/C, provenance/mixed, PC009, AC-US08, historický model a celkovou revizi; NOT_READY správně zůstává.

Skills byly uplatněny na výsledku: konstrukce zachovává vlastní otevřenou stěnu/otvor, skutečné ostění a zdrojové profily; UI má skutečný staged/reverzibilní průchod, propojený výběr a locks; verification odděluje matematiku, skutečné PDF/SVG a editor od člověka/fyziky a zachovává původní meze; delivery spojuje review komponent, opravy, skutečnou evidenci a omezené technické předání. SK-012 ledger přesně odpovídá předchozí vlastní revizi V4: úzký technický přenos kontraktu cache V3→V4 je doložený, širší efektivita a nové použití v PC008 zůstávají pending. Nevyplývá z něj lidská ani fyzická účinnost.

Full-suite1179PASS/220,34s je běh autora, jeho JUnit reviewer skutečně přečetl:0 failures/errors/skips. Předchozích1175 případů nebylo účelově vypuštěno: jeden V2 stale test byl při zachování assertions přejmenován a parametrizován V2/V3; další případy doplnily clipping rezerv a přesnou diagnostiku. Vlastní reviewerova39testová sada není tvrzení o opakování všech1179.

**Zbytková rizika se nezamlčují.** Historický full-suite73f3437 run01 skončil Windows access violation při GC, dostupný je pouze shrnutý záznam bez úplného stderr; příčina je UNRESOLVED. Následné celé1175/1179PASS ani native úspěchy ji nevysvětlují. První B1 preview87,078s a edit preview30,422s jsou citelné čekání, nikoli hotová výkonnostní/uživatelská akceptace. Aktuální B1 raw nezaznamenává celé heartbeat měření exportu; B2/Bézier mají pouze jeden vzorek. Starších214 vzorků se nesmí připsat tomuto běhu a worker necertifikuje odezvu předchozí tvorby snapshotu. Uživatelský pozorovatel je nedostupný; automat ani tento reviewer jej nenahrazuje.

K dalšímu dokončení zůstává B3/D/C, povinné změny společného dílu a plná split/merge provenance, další výrobní/UI konsolidace PC009, AC-US08, historická architektura AC-AU19 a celková P2 revize/předání. Fyzická sestavitelnost vyžaduje následný skutečný výtisk vP3. Tato omezení nevyžadují novou rutinní produktovou bránu pro autorizovaný technický přírůstek.
