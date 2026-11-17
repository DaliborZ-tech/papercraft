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
