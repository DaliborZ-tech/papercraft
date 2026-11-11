# PC-007A — nezávislá revize asynchronního exportu

11.11.2026. Reviewer `/root/commands_review` není autorem posuzované produkce ani driveru. Přesný source **`e1948cfd11c095fd2aaf5643edd2403630ea4747`**; scope root změny `753abc47c0c606d12c6d0a288fcd5bfedbff6259` (worker/dialog/host a writer checkpoints), `e1948cf` (read-only native progress observer) a dříve samostatně nerevidovaný `acb675099909f12651bf4dfd40e51c9225a94443` (vedení autora při neprokázaném loftu). Výkonové a D změny jiných autorů nejsou tímto reportem revidované.

**APPROVED_IN_ASYNC_VECTOR_PUBLICATION_AND_HOST_SCOPE,0 otevřených BLOCKER / MAJOR.** Jde o komponentové schválení exportního jobu a jeho host napojení, nikoli celé B, finálního nativního průchodu, plné odezvy pracovního postupu, PC-007A/P2 nebo release. Novice0 a P3 NOT_RUN. Nový skutečný Windows/vektorový/editorový důkaz výsledného sjednoceného zdroje zůstává nutný.

## Připnutí a provedené ověření

[Runner](evidence/pc007a-export-job-review-archive.py) použil fresh `git archive` přesného source do Temp, fresh subprocess s explicitním `PYTHONPATH` do jeho `src`/fixtures a `QT_QPA_PLATFORM=offscreen`. [Raw manifest](evidence/pc007a-export-job-review-archive-e1948cf.json) obsahuje hash archivu, skutečné importované cesty `author_window`, `author_export_job`, `author_export` a shodu jejich LF-normalizovaného text SHA-256 s Git bloby. Živý pracovní strom ani desktop ownera se nepoužil jako testovací zdroj.

- **88 původních PASS /6.62s**, [JUnit](evidence/pc007a-export-job-review-original-e1948cf.xml): všechny export job, exporter a workspace testy v tomto připnutém zdroji. To zahrnuje existující C05 pending-input/stale-snapshot a autorův heartbeat/worker-thread test.
- **13 vlastních PASS /3.01s**, [vlastní oracles](evidence/pc007a-export-job-review-own.py), [JUnit](evidence/pc007a-export-job-review-own-e1948cf.xml). Všechny vlastní případy jsou technické unit/offscreen kontroly, nikoli nový uživatel, native desktop, skutečný Inkscape nebo opakování matematického review loftu.

## Worker, dialog a zdrojový stav

`_ExportJob` dostává hlubokou kopii snapshotu při konstrukci; worker nedrží mutable doménu/controller ani Qt kresbu. Úloha běží v QThreadPool, stavové zprávy a výsledek/chyba se vracejí signály do GUI. Host před pořízením snapshotu nadále dokončuje rozepsaný vstup, kontroluje rozpracovaný obrys a vyžaduje validní snapshot. Během vlastního jobu je skutečný dialog ApplicationModal; běžná editace parent workflow zůstává zablokovaná do dokončení.

Hostův lokální `progress` a Qt parent drží dialog po celou synchronní `exec()` sekvenci; běžný Esc/X není dokončení ani destrukce jobu. `reject`/`closeEvent` pouze požádají o zrušení a ponechají dialog, dokud worker nevrátí ACK. Vlastní oba skutečné vstupy Esc a window-close ověřily, že dialog zůstává viditelný/modal, cancel tlačítko je vypnuté a starý bundle nedotčený; teprve následný actual writer checkpoint vrátil `ExportCancelledError` a ukončil dialog. Před startem queued jobu má požadavek stejnou bezpečnou sémantiku.

Vlastní test změnil původní snapshot v době již existujícího workeru (project ID a celý CUT); worker stále vyexportoval původní odpojenou kopii. Výstup je pojmenovaná verze snapshotu, ne čtení průběžně měněné živé domény. `progress.exec()` je záměrná lokální modal event loop, která ponechá Qt zpracovávat události; není to volání writeru v GUI vlákně ani skrytá synchronní náhrada threadu. Testy neprokazují externí násilné ukončení procesu/OS ani jim nepřidělují bezpečný rollback claim.

## Zrušení a transakce

Nové checkpoints nezměnily font, numeric, topology, material/area ani loft output validace. Přidávají možnost bezpečně skončit před přípravou, ve staged vektorech, před actual geometry kontrolou a před první publikací. Stávající filesystem transakce a její rollback/recovery zůstávají vlastněné writerem, pod jeho zámkem.

Vlastní **skutečný writer** s kruhovým otvorem byl zrušen samostatně v prepare/vectors/verify/publish. Všechny vlastněné SVG/PDF/manifest i cizí binární `foreign.txt` zůstaly byte-for-byte zachované; staged adresář nezůstal. Nešlo o simulaci zrušení bez skutečného publisheru. Samostatný dialogový test zrušil job ještě před queued startem a ověřil stejné soubory.

Checkpoint před `publish` je poslední příležitost potvrdit cancellation, dokud jsou původní výstupy nedotčené. Po vstupu do publikace se dokončí celá transakce nebo rollback; požadavek zrušení nesmí ponechat poloviční sadu. Vlastní test pozastavil **actual `os.replace` po první výměně**, vyvolal Cancel a pak nechal skutečnou publikaci doběhnout. Výstup existoval kompletní, foreign soubor zůstal, `finished_during_cancel=true`, `cancelled=false`. Dialog/host pravdivě oznamují již dokončené uložení.

Další vlastní test po stejném prvním actual replace a late Cancel vynutil OSError při další výměně. Vrácena byla skutečná `ExportWriteError`, nikoli falešné potvrzení zrušení; rollback obnovil všechny původní bytes. Pozdní Cancel tedy nezakrývá chybu publikace. Fronta phase signálů nemění tuto autoritu: i když GUI dostane publish fázi o něco později, worker již neukončuje rozběhlou transakci uprostřed.

## Chyba, oprava v UI a host návrat

Worker vrací původní exception objekt. Vlastní host průchod přes skutečnou modal event loop předal `CurveOutputError` s jiným part ID, ověřil identitu téhož objektu a vlastnosti chyby, zvolení správného dílu v hostu a návrat přes stávající `run()`/focus mechanismus. Zpráva zůstala dostupná pro opravu, nevzniklo hlášení o úspěchu. Samostatná cancellation skončila jen status zprávou, bez warning/success dialogu, s nezměněným parent dokumentem a viditelným hlavním oknem.

`acb6750` bylo ověřeno vlastním skutečným host fixture se17° pootočeným druhým profilem: source byl neEXACT, hint nabídl změnu tvaru/hloubky/dvojic a vysvětlil, že samotný recompute nerozvinutelnost nezmění. Tato větev předchází obecnému stale-recompute textu. Neoznačuje D nebo segmentovaný postup za implementovaný a nenahrazuje opravitelný source pouhou další nápovědou.

## Native driver a hranice měření

Read-only delta `e1948cf` v existujícím100ms GUI timeru pouze rozpozná skutečný aktivní `ExportProgressDialog`, přečte description, počítá vzorky/gapy a pořizuje skutečný screenshot. Nevolá `_phase`, `_done`, cancel, completion signal nebo controller a nepodvrhuje progress. Import je součást stejného explicitně připnutého runtime; existující HEAD/source hash guard před a po nativním průchodu zůstává. Žádná taková nativní data se tímto offscreen reportem nevyráběla.

**Důležitý scope:** timer měří pouze interval, v němž je progress dialog aktivní. Hostovo `project.snapshot()` a počáteční detached kopie se dějí před vlastním workerem; celkovou počáteční odezvu ani nejdelší main-thread pauzu celé exportní cesty nelze vyvodit jen z tohoto observeru. Nativní proof musí ponechat tyto úseky a celkovou odezvu pravdivě viditelné. Naměřené B1 publisher/verification náklady jsou konkrétní důvod přesunu writeru do workeru; tento report neprohlašuje celý výkonový problém za vyřešený.

Numeric focus guard `f84b849` nadále vyžaduje skutečné active window a vlastnictví fokusu, čte viditelný text i interpretovanou hodnotu po Tab; nevkládá `.setValue` místo vstupu. Jeho dřívější vlastní focused44→40 replay a [host review](PC007A_LOFT_WORKSPACE_REVIEW.md) zůstávají komponentovým důkazem. Původní B1 numeric cause stále není prokázaná a zde se zpětně neuzavírá.

## Skills a další ověření

Čtyři dotčené skills byly načtené: UI se uplatnil v bezpečném návratu z modalu, pravdivé late-cancel a opravě podle part ID; verification v actual writer bytes, negativním rollbacku, import pinu a oddělení heartbeat od celého workflow; construction v zachování snapshotu materiálu/otvoru a beze změny geometrických AC; delivery v omezeném review scope a pokračující potřebě skutečného finálního digitálního důkazu. Autorův/automatizovaný průchod není novice test. Účinnost nového poučení se zde neprohlašuje za obecně ověřenou.

Reviewer nevytvořil produkční změnu ani nový skill, nic nestagoval/necommitoval a nepoužil native desktop. Report a vlastní raw jsou předané integračnímu ownerovi. Budoucí věcná změna jobu/hostu/publisheru a sjednocený native source vyžadují odpovídající navazující ověření; toto schválení není finálním předáním B/P2.
