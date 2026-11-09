# PC-007A — nezávislá revize loft hostu a vazby snapshotu na zdroj

9.11.2026. Reviewer `/root/commands_review` není autorem hostu, bindingu, driveru ani oprav. Původní přesný pin **`a9d155a1861edebfe9581bbd44fde11a56a5394c`**: root změny `6f7defe` (detached source binding), `7971141` (nezávisle deklarované expected loft coverage), `4605302` (workspace create/edit) a `a9d155a` (skutečné vstupy driveru). Následně úzce zkontrolován přesný **`10a21ac7effeb0a7aa6b928b1312e2aeb243fe3e`** s opravou zde nalezeného LW01 a novou numeric focus observability `f84b849`.

**APPROVED_IN_HOST_AND_SOURCE_BINDING_COMPONENT_SCOPE,0 otevřených BLOCKER / MAJOR pro posouzené API/binding změny. LW01 MINOR CLOSED v10a21ac.** Tento závěr **neschvaluje celé B, nativní loft předání, finální writer/source→výstup důkaz, výkon pracovního průchodu ani celou PC-007A/P2**. Nativní B1 na a9 skončil FAIL, přetrvává požadavek vyřešit dlouhé výpočty a dokončit skutečné B1/B2/B3/Bézier UI→save/reopen→layout→výstupy→editor. Novice0 a P3 NOT_RUN.

## Připnutí a provedené testy

Vše spuštěno z fresh `git archive`, s explicitním `PYTHONPATH` do archivovaného `src` a test fixtures a `QT_QPA_PLATFORM=offscreen`. [Runner](evidence/pc007a-loft-workspace-review-archive.py) kontroluje skutečné importované cesty `author_window` a `loft_surface` a jejich Git text SHA-256, s explicitní Windows LF/CRLF konverzí. Živý paralelně měněný worktree se netestoval jako připnutý zdroj. Reviewer nevstupoval do nativního desktopu a neměnil produkci.

- Původní a9 workspace/domain/editing testy: **77 PASS /72.80s**, [JUnit](evidence/pc007a-loft-workspace-review-original-a9d155a.xml), [source manifest](evidence/pc007a-loft-workspace-review-archive-a9d155a.json).
- Vlastní a9: **10 PASS /1 FAIL**, [JUnit](evidence/pc007a-loft-workspace-review-own-a9d155a.xml); jediný skutečný FAIL je LW01 níže. Předchozí test setup chyby byly odděleně zachované: PySide `findData` nad Python tuple nevybral položku a reviewer dosadil do JSON digestu int1 místo actual float1.0. [Původní raw](evidence/pc007a-loft-workspace-review-harness-initial-a9d155a.json) se nezaměňuje za dvě produktové chyby.
- Úzký replay opravy na10a21ac a rozšíření binding/revision: **12 vlastních PASS /2.89s**, [JUnit](evidence/pc007a-loft-workspace-review-own-10a21ac.xml), [manifest/imports](evidence/pc007a-loft-workspace-review-archive-10a21ac.json), [vlastní zdroj](evidence/pc007a-loft-workspace-review-own.py). Jedna mezilehlá reviewer chyba při vkládání nového testu je zvlášť v [harness-insertion raw](evidence/pc007a-loft-workspace-review-harness-insertion-10a21ac.json); opravena bez změny expected nebo produkce.

## Host, aktuální zdroje a autorská práce

Akce create/edit používají veřejné `LoftProfilesDialog` a controller. Preview se provádí nad klonem, create volá `dialog.apply` v jediném undo příkazu, edit před `update_loft` kontroluje `check_source`. Host při editaci nepropouští jiný first profile nebo nové `end_ruling_id`; zdrojové identity a params jsou vlastněné doménou. Widget identity/atomic malformed-response opravy mají [vlastní nezávislé review](PC007A_LOFT_UI_REVIEW.md), core a1 má [samostatné review](PC007A_LOFT_DOMAIN_REVIEW.md). Zde se neuděluje jejich autorům vlastní schválení ani neotvírá již uzavřený LUI02 znovu jako host nález.

Vlastní skutečné offscreen widget signály ověřily výběr druhého profilu ve stromu i přes combo segmentů, správný druhý source sketch, povolenou editaci jeho roviny/křivky a vypnuté planar hole/join akce. Loft se v source sketch nevydává za vyplněný polygon v první rovině; obě živé zdrojové kontury jsou přístupné a v3D zůstává sestavená plocha.

No-op edit nezdvojila profily/plochu/díl a zachovala params/frame/ruční polohu. Změna tolerance přes skutečný preview/apply je jeden controller command a Undo/Redo vrací přesně oba stavy. Přijatý preview následovaný souběžnou platnou změnou dokumentu je před aplikací odmítnut; externí změna zůstává zachovaná a host nepřepisuje params/cache. Zrušený profile-plane dialog nemutuje zdroj.

Vlastní plane průchod otočil druhý živý profil17° do nepodporovaného/neprokázaného loftu: IDs, původní frame a layout zůstaly zachované a stejný source UI profil zůstal editovatelný. Otočení zpět a Ctrl+R obnovilo EXACT. Jde o pravdivě uložený/opravitelný neprokázaný cíl, nikoli tiché přepsání modelu nebo falešný exact. Actual delete dialog odstranil jen materiál loftu a ponechal **oba** zdrojové profily; Undo obnovilo původní dokument. `part_deletion_impact` nyní správně používá úplné `source_profile_ids()`.

## Detached binding, digest a expected coverage

Snapshot obsahuje kopii obou skutečných profile dataclass záznamů v pořadí first/second, celého skutečného surface record a aktuální scale. Vlastní orákulum rekonstruovalo SHA-256 z těchto veřejných záznamů standardním JSON zápisem, nezávisle na produkčním digest helperu. Doložilo intrinsic hash `profiles+params+scale` i následný actual source hash `intrinsic_source_digest+surface`. Typ čísel se při této rekonstrukci zachovává; numerická rovnost int/float není byte identita JSON.

Mutace hluboké source_binding kopie neovlivnila projekt. Save/reopen zachovaly záznamy. Následná změna roviny druhého profilu5→9 aktualizovala aktuální source revision a digest, nový binding měl novou skutečnou rovinu; dřívější snapshot zůstal detached. Stará cache byla označena stale a po recompute se source digest znovu rekonstruoval správně.

`coverage.expected_loft_surface_ids` vychází přímo ze skutečných `surfaces.kind=='ruled_loft'`, nikoli z právě přítomného certificate registru. Vlastní mixed planar/loft snapshot měl v coverage přesně loft sid a oba expected surface IDs; vymazání vráceného registry nevymazalo expected loft coverage. Po odstranění loft dílu je expected loft seznam prázdný, zdrojové profily zůstávají. Skutečný B2 je planar region a tímto polem se nemá falešně vydávat za spatial loft. **Tento producer/binding důkaz sám neověřuje budoucího writer consumeru:** ten musí zkontrolovat úplné expected coverage, actual source binding, numeric intrinsic versus actual SVG/PDF a všechny původní normativní meze.

## Driver a nezávislé numerické očekávání

Nové `loft_desktop_steps.py` vytváří zdroje klávesami/klikáním CurveSketch, skutečnou kopií profilu a skutečným pair dialogem/preview/apply. Přímé čtení projektu a ID je observation; neprobíhá controller/project geometry injection, přiřazení dokumentu, podvržení výsledkových signálů nebo monkeypatch preview. [Vlastní AST/numerický audit](evidence/pc007a-loft-workspace-harness-audit.py), [raw](evidence/pc007a-loft-workspace-harness-audit-10a21ac.json), kontroloval nové příkazy a výrazová očekávání.

Gothic Simpson expected vychází ze skutečného Jacobianu pozitivní homotetie s normálovou hloubkou10 paper mm; rovná spodní strana přidává440mm². Bézier expected používá vlastní derivaci zadaných controls, ne výrobní mesh. Vlastní jinak sestavený48bodový Gauss tensor integrál cross-productu world partial derivatives dává gothic **1364.0463936207525mm²** proti Simpson1364.0463936207523 a Bézier **956.6509523964122mm²** proti956.6509523964114. Je to numerická konzistence s jiným orákulem, **nikoli rigorous interval certificate**. Driver to správně explicitně rozlišuje; výslednou chybu celého source→výstup řetězce musí samostatně doložit finální writer/proof. B3/C/D nejsou těmito třemi driver fixtures prohlášeny za hotové.

## LW01 — nedostupné připojení v nápovědě

Na a9 vybraná loft hrana správně vypnula planar attach/glue akce, ale hint tvrdil „Vybranou hranu můžete připojit… přehyb nebo lepení s chlopní“. Jde o **MINOR UI nekonzistenci**, doloženou vlastním původním FAIL, nikoli o LUI02 nebo chybný matematický závěr. Owner byl informován ihned.

**CLOSED v10a21ac:** loft-specific větev nyní nabízí skutečně dostupnou editaci source profilů/dvojic/švu a pravdivě uvádí neověřené připojení místo falešné přímé tětivy. Used source profil už není označen jako úplně nevyužitý. Replay původního vlastního negativu na přesném archivu opravy PASS. Nápověda neopravovala skrytou chybějící akci; odpovídá zde skutečně povolenému omezenému workflow.

## Nativní FAIL a výkon zůstávají otevřenou prací

[Actual a9 B1 run01](evidence/pc007a-loft-B1-desktop-a9d155a-run01/results.json) po327.515s skončil FAIL před exportem: po skutečném odemčeném drag měl X value44 a další pokus o číslo40 nebyl potvrzen; final screenshot ukazuje rozepsané40. Skutečný preview byl EXACT/POSITIVE_HOMOTHETIC_CONE po92.219s. Save/Open/Export nebyly provedeny a nejsou tímto komponentovým reportem schválené.

Focus jako příčina numeric FAIL je **hypotéza**, ne prokázaný produktový bug ani jeho uzavřená oprava. Vlastní lehký actual-focused Qt případ44→40 přes Ctrl+A/psaní/Tab uspěl na field i modelu a zachoval úhel17; nedokazuje příčinu nativního gothic běhu. `f84b849` správně doplňuje actual active-window/focus precondition a pozorování visible text/value po Tab; netvrdí automatický nový native PASS. Budoucí průchod musí prokázat skutečné doručení vstupu.

[Diagnostický sampling summary](evidence/pc007a-loft-B1-desktop-a9d155a-run01/diagnostic-profile-summary.json) výslovně upozorňuje, že profilování průběžný běh ovlivnilo, a není finálním latency důkazem.498 vzorků v placement průchodu a opakovaná analysis/deepcopy/validate/world_geometry jsou konkrétní vstup další opravy výkonu, nikoli důvod zamlčet dlouhé čekání nebo omezit geometrické AC. Před digitálním předáním B musí zůstat výkon a dokončený actual UI průchod vyřešené/ověřené; tento report je neuzavírá zeleným malým fixture testem.

## Skills a předání reviewerem

Čtyři projektové skills byly znovu načtené před prací: construction oddělil oba source profily, prostorovou plochu a papír; UI vedl ke konkrétnímu LW01 a opravitelnosti source editace; verification k jinému orákulu, SHA/revision a rozlišení sampled/numerical/rigorous/native; delivery zachoval původní FAIL a vedl opravu přes nový pin/replay. Žádné nové uživatelské pozorování ani fyzické sestavení nebylo provedeno. Účinnost skills mimo tuto technickou zkoušku se neprohlašuje za ověřenou.

Reviewer vlastnil pouze tuto zprávu a vlastní evidence. Žádná produkční mutace, Git staging, commit, merge/push nebo zásah do rootova nativního desktopu. Další source/performance/writer změny vyžadují odpovídající nezávislé review a nový actual důkaz.
