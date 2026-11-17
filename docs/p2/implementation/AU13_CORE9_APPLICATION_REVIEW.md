# CORE9 aplikační review — přerušený stav pro navázání

Reviewer `commands_review`, jiný agent než autor `authoring_domain`. Zdroj `4f43a6427c7fbd25a87309ab31ad676ddd7794e1`, evidence/HEAD `7c61c7ee54233dc662420b5199e3a5d914da4441`. Vlastní izolovaný WT `C:/Users/dalib/projects/papercraft-core9-review`, větev `review/core9-7c61c7e`. Práce přerušena 11. 11. 2026 na výslovnou žádost vlastníka; nejde o dokončené review.

Verdikt: **CHANGES_REQUIRED / CORE9-R01 OPEN; další revize PENDING**. Není uděleno schválení celého CORE9, UI, AU13, C ani P2. Helper matematika má oddělené nezávislé review `48522778`; nepřebírám jeho autorství ani z něj neodvozuji schválení aplikace. Nový uživatel 0 / NOT_RUN; fyzický proof P3 NOT_RUN. Žádná produkce, desktop, integrace ani push od reviewera.

## Potvrzený nález CORE9-R01

Závažný nedostatek current9 validačního kontraktu: aktivní nenulový `source_reference` může patřit zaniklému dílu historie. Reprodukce na přesném 7c61: vytvořit ARC nebo CUBIC → split 1/3 → inverzní merge; v serializovaném aktuálním merged segmentu nahradit `id` a `source_reference.piece_id` retired root/left/right ID. Ostatní projekce i zdrojový descriptor zůstanou beze změny. `AuthorProject.from_dict` podvržený dokument přijme; následné sémantické rozlišení původního rootu nemá aktivní zdroj. Aktivní descriptor tedy není kvalifikován skutečným aktivním replay piece.

Příčina v `profile_subdivision.py::_validate_profile_subdivisions`: equality descriptoru se kontroluje pouze při iteraci `history.pieces`, pokud příslušný segment v profilu existuje. Chybějící piece legitimně přeskočí kvůli explicitní náhradě obrysu. Závěrečná kontrola ostatních descriptorů ovšem testuje jen členství segment ID v `seen_edges`, zahrnujícím i retired ID. Tento union nenahrazuje mapu aktivních kvalifikovaných vlastníků.

[Vlastní reprodukce](evidence/au13-core9-review-own.py) má šest konkrétních negativů, ARC/CUBIC × root/left/right. Všechny **6 FAIL**, protože očekávaný `ProjectFormatError` nebyl vyvolán. [JUnit původního běhu](evidence/au13-core9-review-7c61-own-run01.xml) zůstává historicky nezměněný. Root nález převzal; opravný pin dosud nebyl revidován.

Oprava musí každý aktivní nenulový descriptor porovnat s přesnou aktivní piece/profile/root/generation/span/source replay mapou. Nemá zakazovat archivní orphan historii po explicitním nahrazení obrysu; takový legitimní stav se starými UNRESOLVED referencemi musí zůstat uložitelný. Nesmí se zavést nearest/first-child fallback.

## Co již bylo ověřeno

- Původní nový aplikační soubor: **34 PASS / 64,11 s**, [JUnit](evidence/au13-core9-review-7c61-original.xml). Počty se nesčítají s autorovým 419 coupled během.
- Zbývajících **10 vlastních PASS / celý vlastní běh 9,82 s**: chybějící historie při původních aktivních child ID odmítnuta; foreign profile/history/piece/generation/span descriptor odmítnut; nezávislé kubické očekávání `L(u)=8u³−12u²+12u` při nerovnoměrné partition 0,2/7,5/7,1 a měřená inverze; nerovnoměrné jednostranné split/merge ARC i CUBIC zachová původní loft CUT, params, rámec, layout 67/83/30° a oba locks přes save/reopen.
- Vlastní proces připnul `project.__file__` k vlastnímu `src` a porovnal LF bytes pěti relevantních modulů proti přesnému Git blobu 7c61 před testy. Prostředí `PYTHONPATH=<own WT>/src`, `QT_QPA_PLATFORM=offscreen`, sdílený `.venv/Scripts/python.exe`. Nativní GUI se nespouštělo.
- Přečtena skutečná produkční delta model/project/profile_curves/profile_subdivision, relevantní loft binding/frame/semantic consumers, circular consumers, hash-only D None normalizace a exporter binding. Tato průběžná analýza není závěrečné schválení všech cest.

## Konkrétní další postup

1. Převzít nový autorův R01 fix pin do nového archivu/izolovaného stavu; beze změny expected přehrát šest negativů. Přidat strip nonNone→None na aktivním ARC/CUBIC, konzistentně přepsaný descriptor i canonical cache a legitimní orphan replacement/mixed-generation UNRESOLVED save/reopen.
2. Dokončit rozpracovaný samostatný spotcheck exporter/source context: `_source_context` a `_bound_source_native` při odebrané celé `profile_subdivisions` přijaly validní current merged descriptor. Důvod: prázdný registry obejde `if context.profile_subdivisions` validaci a sémantický helper umí self-contained fallback. **NEEDS_INVESTIGATION**, nikoli potvrzená kompletní exportní false-SAFE reprodukce; změnu deklarovaných digestů a skutečný `validate_loft_snapshot`/writer negativ jsem do přerušení neprovedl. Případná oprava má vázat required historii i v detached consumeru, bez oslabování schváleného matematického helperu.
3. Přidat nezávislé current9 stale/poison, source binding omissions, actual archivní A/B/D/C/LINE a C8 copy/export/hash kontroly; autorovy backendové výsledky nejsou nové nativní UI/editor důkazy.
4. Zvlášť revidovat následný UI pin, až bude hotový. Native Windows/editor vlastní root. Dokončit source review před technickou integrací; žádné schválení či push neověřeného CORE9.

Načteny AGENTS a všechny čtyři projektové skills, normativní přesnost a AC-AU13/14/15/16/17 + AC-US. Construction: historie není první child ani nový radius z projekce. Verification: samostatné negativy, původní length polynomial a skutečný import pin; FAIL se uchovává. UI: budoucí widget/native scope výslovně oddělen. Delivery: nezávislá otevřená revize a konkrétní navázání, bez přijetí nedokončeného balíku. Normativní AC a tolerance nebyly změněny.

## Nezávislé uzavření opravy R01 — 17.11.2026

Reviewer `core9_review` je jiný agent než původní autor i nynější integrační
autor. Vlastní izolace mimo projekty:
`C:/Users/dalib/.codex/workspaces/papercraft-20261117/core9-review`.
Posuzovaný fix **72f7a168b0ecbc58ecd0f014cb1555f11d6339ba**, testovaný checkout
**6064f222dfa87f6c46837f11ed9da5c04a6523cb** má shodnou produkci.
Historický report výše, původní negativy a původní FAIL se zachovávají.

**Verdikt: R01 CLOSED / APPROVED_IN_SCOPE pro tento doménový fix.** Každý
aktuální descriptor se nyní porovnává s přesným aktivním replay piece daného
profilu; členství v unii historických UUID už nestačí. Guard odmítá i retired
ID bez descriptoru. Mapa přitom nevyžaduje přítomnost orphan piece po explicitní
náhradě celého obrysu. Kontrola skutečné aktivní projekce a incidence zůstává
v původním replay průchodu, bez nearest/first-child nebo radius-fit fallbacku.

| Běh | Přesný zdroj a výsledek | Důkaz |
|---|---|---|
| Původní nezměněné orákulum |7c61c7ee: **6 FAIL +10 PASS**,32,65s; očekávané znovupotvrzení původní chyby | [JUnit](evidence/au13-core9-r01-baseline-7c61-replay.xml), [log](evidence/au13-core9-r01-baseline-7c61-replay.log) |
| Totéž orákulum po opravě |6064f222/src72f7a168: **16 PASS**,32,47s | [kopie](evidence/au13-core9-r01-unchanged-own.py), [JUnit](evidence/au13-core9-r01-fixed-6064-replay.xml) |
| Nová nezávislá matice |6064f222: **33 PASS**,62,19s | [orákulum](evidence/au13-core9-r01-matrix-own.py), [JUnit](evidence/au13-core9-r01-matrix-6064.xml) |
| Původní autorské regrese |6064f222: **42 PASS**,54,06s; doplňková regrese, nikoli nezávislé autorství testů | [JUnit](evidence/au13-core9-r01-author42-6064.xml) |

V původním orákulu se změnil pouze literal PIN pro nový checkout; AST všech
funkcí včetně dekorátorů zůstává shodné. Baseline běžel v druhé nové izolaci
na skutečném7c61. Každý pytest proces měl vlastní explicitní `PYTHONPATH` a
import assertion. [Binding](evidence/au13-core9-r01-binding.json) dokládá
`project.__file__`, Python, normalizované blob hashe šesti modulů, hashe JUnit
a sedmi původních projektů. Pomocný sběrač metadat se při prvním spuštění bez
`PYTHONPATH` správně zastavil import assertion před zápisem; poté byl spuštěn
s vlastním zdrojem. Tento odmítnutý sběrač není žádný testovací PASS.

Nová matice zahrnuje retired ROOT/left/right×ARC/CUBIC také s None, prázdným
či boolean descriptorem; chybějící/None aktivní autoritu a konzistentně cizí
analytický zdroj společně se všemi nativními cache body a daty. Nestačí tedy
jen samostatné poškození jednoho pole. Pozitivní whole-outline orphan i
mixed-generation úprava zachovají starou korespondenci, retired kotvu,
odvozené cesty, stránky67/83/30° a oba locks, nedotčený profil a uložitelný
UNRESOLVED stav; snapshot ho odmítne bez mutace práce.

Skutečné archivní A, B1, D-gothic, LINE a všechny tři poslední C8 projekty
(válec/kužel/near) prošly read-only načtením, odmítnutím přepisu originálu,
SaveAs9/reopen, explicitním přepočtem a skutečným zápisem SVG/PDF. Všechna
původní zdrojová UUID, body, data, plochy, spoje, generace, kotvy a ruční
placementy kontroluje samostatné čtení původního JSON; původní byte hashe
zůstávají stejné. Jde o **backendový replay existujících artefaktů**, nikoli
nový průchod v desktopu nebo Inkscape.

Uplatnění skills je konkrétní: construction zachovává celý historický zdroj
a retired kotvu; verification reprodukuje původní FAIL na správném checkoutu,
zkouší konzistentní counterfeit a původní artefakty; delivery připíná nezávislý
verdikt ke konkrétnímu fixu a nepřenáší ho na UI; authoring-ui chrání bezpečný
návrat k uložené práci, skutečné widget/native pokrytí ale tímto neběželo.
Pravidlo importu bylo skutečně použito i při odmítnutém pomocném sběrači.

LINE hypotéza byla mezitím nezávisle potvrzena a v opravě uzavřena: stejný
[samostatný Python skript](evidence/au13-core9-r01-line-process-own.py) bez
pytest/conftest načte na [původním7c61](evidence/au13-core9-r01-line-7c61-process.json)
všechna tři retired LINE root/left/right UUID s None, ale na
[opravě72f7](evidence/au13-core9-r01-line-72f7-process.json) všechny tři odmítne.
Každý proces uvnitř ověřuje import i byte shodu tří modulů s deklarovaným pinem.
Tento důkaz platí pro původní7c61; nepředstírá zpětné zjištění na jiném masteru.

**Otevřený rozsah:** samostatná hypotéza prázdné historie v detached exporteru,
následné UI a jeho skutečný
ARC/CUBIC desktop, finální integrační snapshot a metadata ještě vyžadují vlastní
kontrolu. Toto schválení samo nepovoluje vydávat celý CORE9/C/P2 za hotový.
Nový lidský uživatel0/NOT_RUN; fyzické P3 NOT_RUN.

## Detached exporter — nezávislé uzavření 3e6fbb63

Původní hypotéza je nyní **potvrzená chyba před opravou a CLOSED po opravě**.
Reviewer nepsal produkční fix
**3e6fbb636f57d394ca0e5433553dc394e1b9379e**. Diff proti6064 mění pouze
podmíněné zavolání existujícího projektového replay validatoru v
`loft_surface._source_context` na nepodmíněné. Schválená matematika
self-contained source-view se nemění; připojení projektu vyžaduje autoritu
také tehdy, když je dodaný registr prázdný.

[Nezávislý subprocess](evidence/au13-core9-detached-process-own.py) vytvořil
vlastní kubickou extruzi, oba profily rozdělil2/7 a sloučil, potom ve snapshotu
vyprázdnil nebo úplně vynechal historii a přepočítal vlastní SHA256 deklarace
i interně konzistentní representation. Původní [6064 replay](evidence/au13-core9-detached-6064-process.json)
oběma podvrhům skutečně vydal SVG/PDF a nahradil manifest. Nešlo tedy už jen
o přijetí pomocným `_source_context` nebo o hypotézu z četby kódu.

Na [opravě3e6f](evidence/au13-core9-detached-3e6f-process.json) tentýž skript
oba vstupy odmítá kvůli chybějícímu přesnému aktivnímu vlastníkovi historie.
Předchozí vydaný bundle a nesouvisející soubor zůstávají byte/hash shodné;
zdrojový projekt se nemění. Na obou pinech současně projdou skutečným
SVG/PDF writerem tři legitimní pozitivy: native legacy/None bez historie,
platný qualified zdroj a nový LINE loft nad profilem se zachovanou orphan
historií dřívější kubiky. `__file__` i zdrojové blob hashe se kontrolují uvnitř
každého samostatného procesu bez pytest/conftest.

**Verdikt: APPROVED_IN_SCOPE pro3e6f source-context opravu.** Opakování celé
vlastní33případové matice včetně původních A/B/D/LINE/C8 projektů spolu se
7 autorovými guard regresními případy: **40 PASS /61,20s**, [JUnit](evidence/au13-core9-detached-matrix-3e6f.xml).
Překryv s předchozími běhy se nesčítá. Review checkout má byte shodnou celou
produkční `src` s3e6f; nové UI a společný finální snapshot se kontrolují níže
samostatně. Desktop/Inkscape tímto během neproběhly, nový člověk a P3 zůstávají
NOT_RUN.

## Společný frozen zdroj 5415e2bc — doména a křivkové UI

**APPROVED_IN_SCOPE**, bez nového blokujícího nálezu pro produkční source
**5415e2bc45f0a073d202144f1281557377afbc61** v rozsahu CORE9/R01, detached
authority a měřeného subdivision UI. [Vazba](evidence/au13-core9-final-5415-binding.json)
ověřuje všech118 souborů `src` proti skutečným Git blobům kandidáta a importy
uvnitř reviewerova procesu. Produkční strom je
`76883ed59a115d877e8456d35a742116828a5699`.

Delta proti posouzenému3e6f obsahuje pouze `ui/author_subdivision.py` a
`ui/author_window.py`, přesně odpovídající dřívějšímu UI406fa6f. Merge nemění
již zkontrolované doménové guardy. Četba ověřila oddělený snapshot workeru,
latest-only token/queue, Cancel/close bez aplikace pozdního výsledku,
opětovný source fingerprint před příkazem, vstup po skutečné obloukové délce
a předání pouze parametrů do atomického controlleru. Main-window kontext
nejprve vyhodnotí rozepsaný vstup, po odmítnutí vrátí viditelnou volbu bez
smazání raw textu a po přijetí sjednotí podvýběr s požadovaným zdrojem.

Na tomto přesném zdroji: **21 PASS /20,92s**, [JUnit](evidence/au13-core9-ui-5415.xml):
18 původních skutečných-core/widget regresí a
[3 nové nezávislé UI případy](evidence/au13-core9-ui-own.py). Vlastní kubika
má jiný rozměr a nezávislý integrál `L(u)=24u³−36u²+36u`; zadání57/8 po délce
musí dát parametr1/4, nikoli poměr19/64. První běžící skutečný výpočet byl
záměrně zpožděn, nové zadání ho zneplatnilo a přijal se pouze nový skutečný
výpočet. Další případy ověřily raw neplatný vstup po platném náhledu a skutečnou
úpravu řídicího bodu živého projektu za běhu workeru. Pozdní Apply neprojde;
původní nebo nově autorem změněná práce zůstává zachovaná. Zpoždění je pouze
plánovací dependency; geometrie se stále počítá skutečnými veřejnými příkazy.

Zpřesněný odstavec SK013 ve skillu authoring-ui odpovídá doloženému CUI01 a
je **APPROVED_IN_SCOPE jako úzká pracovní rada**. Viditelný rollback s raw
vstupem byl nyní znovu spuštěn i v jiném přepínači křivky; není to nový lidský
uživatel ani plošně prokázaná účinnost dalších přenosů.

Tento verdikt není kontrolou rootova dosud běžícího nativního Windows/editor
průchodu, nového comparator guardu, škálování, celé regresní sady ani pozdějších
předávacích metadat. Tyto výstupy mají samostatné source-bound důkazy a review.
Celý P2, AC-US08 a fyzické P3 tímto nejsou přijaty ani dokončeny.

## Skutečný native ARC/CUBIC průchod — evidence6969069 na42dca627

**APPROVED_IN_SCOPE pro oba doložené nativní subdivision průchody a jejich
soubory.** Produkce6969069/42dca627 zůstává byte shodná s posouzeným5415.
[Nezávislý audit](evidence/au13-native-artifact-review-own.py) a jeho
[výsledek](evidence/au13-native-artifact-review-42dca.json) ověřily48/48
původních output hashů a každý ze132 runtime/source hashů obou běhů proti
Git6969069. ARC run02 trval29,75s, CUBIC run01 91,64s; import ukazuje skutečný
integrační checkout, vlastní PID, nativní OpenGL a skutečné Save/Open/Export
dialogy. Četba driveru, input/action logů a screenshotů potvrzuje vlastní
kreslení od prázdného projektu, měřený split/merge, Undo/Redo, neplatný vstup,
ruční dvě stránky/locks a3D↔2D picking. Reviewer desktop znovu neovládal.

Oba skutečné saved schema9 projekty se otevřou v aktuálním zdroji a jejich
JSON snapshot přesně odpovídá archivnímu snapshotu; původní projekt se nemění.
První pomocná audit assertion porovnávala Python tuple v topologickém proofu
s JSON listem; audit pak explicitně normalizoval jen JSON container kontrakt.
Původní root a děti zůstávají retired, aktuální merged UUID je nové, původní
root kotvy, correspondence/seam i55/90/17° na druhé stránce a oba locks drží.
SVG, PDF subject a manifest nesou stejný ručně přepočtený snapshot digest.

Samostatný Fraction lexer použil původní číselné tokeny SVG a dekomprimovaného
PDF streamu včetně skutečného CTM, bez původního float orákula. ARC má očekávání
`100π =314,1592653589793mm²`, oba výstupy314,154455352098mm²,
chyba0,004810006881mm². CUBIC má očekávání800mm², SVG799,996938547659mm²,
PDF799,9969385476588mm², chyba0,003061452341mm². Obě jsou pod původní0,01mm²
mezí. Split vzdálenosti10,47197551 a20,000093598883paper mm potvrzuje vlastní
obloukový/rychlostní integrál. Vektorový výstup obsahuje oba díly na dvou A4
stránkách a žádné raster XObjects.

Původní [FAIL5415](evidence/au13-arc-native-5415e2-run01/results.json) zůstává:
observer četl neexistující `.parameters`;696 opravuje pouze dvě čtení na
`.params`. Nejde o zametenou vadu produktu. Toto review nepřenáší native PASS
na nový camera-only nástroj42dca, Inkscape, nové jiné loft rodiny ani celý
PC009. Nový člověk0/NOT_RUN, AC-AU19 NOT_RUN, fyzické P3 NOT_RUN.
