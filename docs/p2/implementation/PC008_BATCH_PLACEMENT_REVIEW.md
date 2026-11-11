# PC-008 — nezávislá revize explicitního dávkového rozmístění

Aktuální následný verdikt: **APPROVED_IN_EXPLICIT_BATCH_PLACEMENT_COMPONENT_SCOPE, BP01 CLOSED** na úzké opravě`65159f82e6ac9809c5552a2a08ef77240f863556`. Původní otevřený stav a FAIL níže zůstávají historickým důkazem0210118; finální přezkoušení je v závěrečném dodatku.

11.11.2026. Reviewer `/root/commands_review` není autorem API/testů. Původní přesný source **`0210118e02dd7f65dc6161b5f86cfda2b2dbdf29`** proti doméně95fa2c7. Scope pouze sdílený `_apply_placement`, veřejné `set_placements`, zachování starého `set_placement` a související testy. Souběžná curved-bridge ani UI práce nejsou součástí tohoto pinu/revize.

**Předběžný stav: BP01 MINOR OPEN, transakční/lock meze bez zásadního nálezu.** Konkrétní no-op dirty chyba byla předána integračnímu ownerovi a autorovi opravy. Finální delta verdikt bude uveden samostatně níže; tento odstavec se nezpětně přepisuje na původní PASS.

## Připnutí a původní výsledky

Skutečně načtené4 projektové skills vedly k zachování autorských voleb, vratnosti, stejných guardů a přesného source. [Runner](evidence/pc008-batch-review-archive.py) použil fresh exact `git archive`, explicitní `PYTHONPATH` a skutečný import/hash `project.py`, s výslovnou LF/CRLF normalizací. [Manifest](evidence/pc008-batch-review-archive-0210118.json). Živý worktree se do výsledku neimportoval.

- **42 původních PASS /1.94s**, [JUnit](evidence/pc008-batch-review-original-0210118.xml): batch/controller/domain regrese.
- **14 vlastních PASS /1 FAIL /1.14s**, [vlastní případy](evidence/pc008-batch-review-own.py), [JUnit](evidence/pc008-batch-review-own-0210118.xml). Jediný FAIL je níže popsané BP01, nikoli problém harnessu nebo uvolněný očekávaný výsledek.

## BP01 — no-op načtených integer souřadnic vytváří dirty bez undo

Platný načtený v5 JSON má `placement.x_mm=1`, `y_mm=2`, `rotation_deg=3` jako integer čísla. Pořízení saved digestu a následný controller příkaz `set_placements({pid:{x_mm:1,y_mm:2,rotation_deg:3}})` převede scalars na1.0/2.0/3.0. Numerická dict equality považuje before/after za stejné: revision se nezmění a undo nevznikne. JSON digest ale rozlišuje integer/float zápis, proto se `controller.dirty` změní naTrue.

Přesná reprodukce je `test_noop_loaded_integer_coordinates_do_not_make_a_dirty_unrecorded_change` ve vlastním souboru. Jde o **MINOR** pravdivosti no-op/dirty/history; geometrie se nepohne a není doložena ztráta autorské práce. Oprava má po stávající finite/bool validaci zachovat původní raw numeric value, je-li numericky shodná. Nesmí kvůli rovnosti1==True přeskočit boolean guard. Root i autor byli informováni okamžitě a dostali přesnou cestu k reprodukci.

## Co již vlastní negativy a analytika ověřily

API přijímá jen plain unique dict a plain per-part dict s uzavřenými klíči; UserDict/MappingProxyType se odmítají i jako pozdní row. Neznámý part/page, bool, NaN/Inf, neplatné zámky a extra pole mají typed failure. Pro stejné guardy se samostatným setterem se shodují příčiny chyby; předchozí správná změna jiného dílu v dávce přitom nezůstane.

Pozice/zámky se vyhodnocují před jejich změnou: odemknout-a-přesunout v jedné row neobchází původní zámek. Samostatné explicitní odemknutí a následný přesun jsou možné, zámek natočení zůstává samostatný. Vlastní vynucená chyba až při závěrečné doménové validaci obnovila všechny placements, revision i mutable privátní state. Jediný controller příkaz má jeden undo; neúspěšná větev po undo zachovala redo a následné redo obnovilo všechny skutečné volby. Vstupní update dict se nemutuje.

Nevzniká packing, výběr stránky, zmenšení, skrytá normalizace úhlu nebo odemykání. Explicitně zadané−20mm a720° zůstaly uchované; layout správně hlásil PHYSICAL_OVERFLOW, místo aby autora tajně přesunul. Vynechaný díl a prázdná row nezměnily jeho autorské hodnoty. Atomická dávka sníží počet plných validací; tento report z toho neodvozuje native UI odezvu nebo benchmark celého pracovního postupu.

Reviewer vytvořil pouze tuto zprávu/raw. Žádná produkční mutace, staging/commit nebo desktop. Celé D/P2, nový UI workflow, novice a P3 nejsou schválené tímto API komponentovým review.

## Cílené přezkoušení BP01 — 65159f82

Přesná oprava **`65159f82e6ac9809c5552a2a08ef77240f863556`** mění pouze6 řádků sdíleného helperu a přidává regresi do batch testu. Všechny tři příchozí numeric hodnoty nejprve projdou původní `number` finite/bool validací; teprve potom se pro numericky shodnou hodnotu ponechá původní scalar. Zámky, neznámé díly/stránky, finální validace, atomická hranice a `_touch` zůstávají stejné. Rovnost1==True proto neobchází bool guard.

Reviewer použil další fresh archive tohoto pinu se skutečným import/hash guardem. [Manifest](evidence/pc008-batch-review-archive-65159f8.json), [JUnit](evidence/pc008-batch-review-own-65159f8.xml): **15 vlastních PASS /1.15s**. Původní BP01 repro byl přehrán beze změny expected, vedle stejných14 guard/rollback/history případů. Loaded-int no-op má nyní původní JSON digest, dirty=false, žádnou revision ani undo. Původní42 PASS na021 nebyly bezdůvodně opakovány; tato cílená sada pokrývá změněné chování i bool/NaN/Inf a související staré guardy.

**BP01 CLOSED / VERIFIED. Finální verdict APPROVED_IN_EXPLICIT_BATCH_PLACEMENT_COMPONENT_SCOPE,0 otevřených BLOCKER / MAJOR / MINOR pro tento úzký API přírůstek.** Schválení se týká021 dávkového API a uvedené opravy; nepřenáší se na paralelně slučované curved-domain změny, UI, auto packing, actual Windows výkon, writer nebo celé D/P2. Benchmarky autora nejsou vydány za vlastní native/human důkaz. Žádná produkce, staging ani commit reviewera.
