# PC-008 — nezávislá komponentová revize UI D a ruční mřížky

Aktuální následný verdikt: **APPROVED_IN_D_PREVIEW_GENERATION_SELECTION_AND_MANUAL_LAYOUT_UI_COMPONENT_SCOPE**, source **`1f677efbb38d7c586146990f0d8c3ad112515bc9`**, **DU01 CLOSED,0 otevřených nálezů** v tomto scope. Závěrečný dodatek uvádí přezkoušení; původní otevřený stav a FAIL níže zůstávají historické.

11.11.2026. Reviewer `/root/commands_review`, autor změny `/root`. Původní přesný source **`ea03025cba5245acdaa83ae4a2575dd1b0e6a2e6`**; šest UI/test paths. Doména95 a batch021 byly revidovány zvlášť. Oprava známého BP01 na65159f82 patří do finální integrace; není novým nálezem UI. Souběžné curved-domain, D writer ani native harness7887e30 zde nejsou schváleny.

**Průběžný verdikt: DU01 MINOR OPEN. Žádný doložený BLOCKER/MAJOR v tomto UI přírůstku.** Po opravě bude následovat přesně připnutý dodatek, původní FAIL se zachová.

## Zdroj a skutečně provedené zkoušky

[Runner](evidence/pc008-ui-review-archive.py) vytváří fresh exact `git archive`, čtyři skutečné importy UI modulů i LF-normalizované SHA porovnává s Git blobs; v subprocessu je explicitní `PYTHONPATH` a `QT_QPA_PLATFORM=offscreen`. Živý worktree nefiguruje v testovaném runtime. [Prvotní manifest](evidence/pc008-ui-review-archive-ea03025-initial.json), [17-PASS manifest](evidence/pc008-ui-review-archive-ea03025-baseline.json), [samostatný DU01 manifest](evidence/pc008-ui-review-archive-selection-ea03025.json).

- **42 původních PASS /22.79s**: nové dialog/workspace testy a starší A/loft host regrese, [JUnit](evidence/pc008-ui-review-original-ea03025.xml). Autorových77 výsledků nejsou vydávány za vlastní nové spuštění.
- **17 vlastních PASS /4.65s**, [vlastní oracles](evidence/pc008-ui-review-own.py), [JUnit](evidence/pc008-ui-review-own-ea03025-baseline.xml).
- **DU01 1 cílený FAIL /1.65s**, [JUnit](evidence/pc008-ui-review-own-selection-ea03025.xml). Jde o osmnáctý odlišný vlastní případ, nikoli o změkčený předchozí expected.

Vlastní skutečný target má analyticky `S(u,v)=(16u,8uv,12v)`. Dialog přes reálný domain worker vytvořil16 trojúhelníků; pozice vrcholů splňují `y=xz/24`, prokázaná mez leží mezi1/4 a0.26mm. Nejde o podvržený příznivý solver. Source→fine matematický certifikát je samostatná doménová revize, tento regresní výpočet ji nenahrazuje.

Zkoušky potvrdily zdrojový fence během výpočtu, po přijetí před aplikací a v mřížce; chybný target/status/confirmation token/parameters nemůže aktivovat potvrzení. Překročená odchylka, záporná délková mez, neplatná normála, NaN vrchol, neexistující vertex index a nesouhlas počtu trojúhelníků jsou blokované. Display mesh se nepřijímá jako produkční geometrie; doména znovu ověřuje konkrétní preview digest.

Jediný běžící worker plus poslední čekající request zahazuje prostřední požadavek a starý výsledek. Vlastní kontrolované zdržení volalo stále původní skutečný solver; timer běžel ve vlákně GUI a solver v jiném. Close/Cancel nepublikuje ani nemutuje původní projekt. Toto je důkaz komponentové responzivity při čekání, nikoli Windows výkon celého workflow či okamžité zastavení výpočtu.

Ruční mřížka zachová jednotlivé úhly, všechny vynechané díly a zámky. Pozdní zamčený úhel blokuje celý návrh, rozepsané44 bez Enter nemůže potvrdit starý preview; po novém náhledu jde celá dávka jedním Undo/Redo. Změna projektu po potvrzení zastaví apply před první mutací. Aktivní tiskové díly a netisková reference se odlišují ve stromu, paperu i3D; inactive child lze prohlížet bez skrytého výběru pro tisk, původní target lze obnovit a Undo obnoví předchozí aktuální generaci.

## DU01 — combobox tvrdí jinou generaci než zvýrazněný díl

Přesný opakovatelný případ `test_generation_combo_cannot_claim_a_different_generation_than_selected_child`: vytvořit dvě reálné generace téhož cíle, vybrat child první neaktivní generace, pak v `generation_choice` zvolit druhou. `choose_generation()` mění pouze `selected_generation` a volá `_sync_selection()`. `selected_surface` i viewport nadále patří první generaci, zatímco combobox/status popisují druhou. Invariant vlastníka vybraného childu vůči uvedené generaci selže s dvěma různými UUID.

**MINOR**, AC-US02/US03: rozporný kontext při prohlížení a další úpravě. Samotné přepnutí nic neukládá, nepřepíná materiál pro tisk a neztrácí práci; netvrdím nedoložený závažnější dopad. Nález byl neprodleně předán rootovi. Doporučený fix při explicitní změně generace přejde na zachovaný target, vyčistí závislý výběr hrany/vertexu/spoje a obnoví sketch/3D/strom konzistentně. Nesmí přitom implicitně zvolit generaci pro tisk.

## Poctivé hranice důkazů a uplatnění skills

Čtyři skills byly skutečně načteny: konstrukce vedla k nezaměnění cíle, tiskového materiálu a referencí; UI k vlastnímu výběrovému invariantu a C-05 zkoušce; verification k analytickému targetu, fresh archive/import guardům a negativům; delivery k otevřenému DU01 a oddělení tohoto komponentového stavu od předání D. Tím není prokázána účinnost širších pending poučení ani AC-US08.

První vlastní příprava vynechala required `preview_digest`; druhá předpokládala, že přesně0.5mm raw geometrický budget dovolí také nenulovou floating-frame rezervu. Doména správně vrátila UNRESOLVED. Opravená příprava používá výslovně potvrzený digest a0.51mm, očekávaný výběrový invariant nemění. [První raw](evidence/pc008-ui-review-own-ea03025-initial.xml) a [hraniční raw](evidence/pc008-ui-review-own-ea03025-boundary.xml) zůstávají. První běh nového výběrového testu musel být přerušen kvůli vlastnímu dirty-close cleanupu; [pravdivý záznam](evidence/pc008-ui-review-selection-interrupted.json). Nový samostatný DU01 FAIL již doběhl standardně.

Toto review neprovádí skutečný Windows D, save/reopen→ruční layout→SVG/PDF celého D, reálný editor, nového modeláře ani P3. Výsledky offscreen OpenGL nejsou nativním grafickým důkazem. Reviewer mění pouze report/raw, žádnou produkci, staging, commit či desktop.

## Přezkoušení opravy DU01 — 1f677ef

Přesný opravný pin **`1f677efbb38d7c586146990f0d8c3ad112515bc9`** mění10 řádků hostu a související test/cleanup. `choose_generation()` si před změnou zapamatuje vlastníka cíle, výslovně nastaví zvolenou generaci, vyčistí závislý podvýběr a použije již existující `select_surface(target)`. Tato cesta obnoví sketch,3D a strom v kontextu původního cíle. Panel může legitimně vybrat první vertex target profilu, nesmí ale podržet vertex childu jiné generace. Produkční projekt, undo, print_selected, source/certifikát, worker, writer ani mřížka se touto navigací nemění.

Fresh exact archive opět doložil všechny čtyři skutečné importy a jejich SHA: [manifest](evidence/pc008-ui-review-archive-1f677ef.json).

- **11 současných původních dialog/workspace PASS /14.47s**, [JUnit](evidence/pc008-ui-review-original-1f677ef.xml), včetně nové skutečné dvougenerační regrese autora. Ta navíc ověřuje target-owned vertex, přesný nested group stromu, pouze referenční target ve viewportu, přepnutí na „Nová generace“ a invariant původního dokumentu/print výběru.
- **18 vlastních PASS /4.32s**, [JUnit](evidence/pc008-ui-review-own-1f677ef.xml). Původní DU01 invariant je přehrán beze změny expected; zbylých17 případů chrání reálný solver, source fence, hard meze, async/Cancel, locks/C-05 a bezpečný návrat. Prvotních42 A/loft regresí není započteno znovu a bezdůvodně se neopakovalo: opravný runtime diff je pouze v novém přepínači generací.

**DU01 CLOSED / VERIFIED. APPROVED_IN_D_PREVIEW_GENERATION_SELECTION_AND_MANUAL_LAYOUT_UI_COMPONENT_SCOPE.** Pro uvedený zdroj a vymezený komponentový přírůstek je0 otevřených BLOCKER/MAJOR/MINOR. Užití UI skillu se zde projevilo opravou samotné interakce a vlastnictví výběru, nikoli přidáním další nápovědy. Přenos tohoto principu na jiné přepínače se tím automaticky neprokazuje.

Tento verdikt zahrnuje původníea03025 a úzkou opravu1f677ef. Known BP01 v základním batch021 má samostatnou ověřenou opravu65159f82, kterou finální integrační owner musí zahrnout. Verdikt se nepřenáší na curved-domain bridge, nový D writer/harness, výsledný budoucí integrační commit, skutečný native průchod, celý AC-AU12/D, nové uživatele, C nebo celé P2. Žádný vlastní staging/commit ani produkční změna.
