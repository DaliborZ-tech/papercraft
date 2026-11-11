# Nezávislé review C autorského UI

Reviewer `commands_review`, 11.11.2026, není autorem UI (`curve_ui`). Source **62cb8bc3d84c5c3edf0c7faf08965ea5eef4b625**, handoff **9e1c7ed95690080a008edd101c45eeb6e006d9df**. Vlastní izolovaný worktree `papercraft-curved-authoring-ui-review`, branch `review/c-curved-ui-62cb8bc`. Žádná produkční změna; root vlastní nativní desktop a integraci C+LINE/schema8.

**Finální verdikt: APPROVED_IN_C_UI_COMPONENT_SCOPE** pro přesný opravný CODE **e1c06f5b068880ac22b28516ce69c66aee32603d**, s dokumentačním handoffem **694004e040ac1bcbb1337c3c86ab0cd01b0a9ef0**. CUI01–CUI04 jsou CLOSED / VERIFIED; zbývající doložené zásadní UI nálezy0. Nenahrazuji samostatné backend review geometry_analysis v df6dd20f1988cf98879a3987696e6f27c611a113. Schválení se nevztahuje na nový root C+LINE/schema8 merge, jeho nativní průchod, vektory/editor, nového uživatele nebo fyzické P3.

## Skutečné provedené ověření

[Runner](evidence/pc007b-curved-ui-review-run.py) používá explicitní PYTHONPATH na vlastní source/tests, Qt offscreen, skutečné import paths a LF Git-blob hash guards. Další opravné piny se spouštějí z oddělených exact archivů. Žádný editable-install jiného worktree ani native GUI.

- Původní UI a curve/loft/segmentation workspace regrese: **47 PASS48.01s**, [JUnit](evidence/pc007b-curved-ui-review-original-run01.xml), [raw](evidence/pc007b-curved-ui-review-original-run01.json).
- [Vlastní testy](evidence/pc007b-curved-ui-review-own.py): cílené failures a positive rollback/concurrency pokusy jsou samostatně připnuté v následujících odkazech. Běhy se nesčítají jako jedinečná fullsuite.
- [Expanded-run03](evidence/pc007b-curved-ui-review-own-expanded-run03.xml):3 PASS/3 FAIL6.91s — dvě varianty CUI01 a kvalifikovaný CUI02.
- [Ownerdeleted-run04](evidence/pc007b-curved-ui-review-own-ownerdeleted-run04.xml):1 FAIL1.49s, CUI03.
- [Inactive-slot-run06](evidence/pc007b-curved-ui-review-own-inactive-slot-run06.xml):2 FAIL3.80s, obě varianty CUI04.

## Nálezy

**CUI01 MINOR — CLOSED / VERIFIED na e1c06f5; původní nález: rejected C05 nechá jiné viditelné ovládání než skutečný autorský stav.** Ve skutečném hlavním vertex_x je prázdný rozepsaný input a hasAcceptableInput=False. Změna comboboxu na jinou sadu je správně odmítnuta, dokument a current_id zůstanou původní, ale combobox dále ukazuje novou sadu. Druhá varianta: odškrtnutí celé sady při stejném rejected preflight ponechá checkboxFalse, přestože record.enabled=True. Nejde o požadavek obejít chybu čísla: oprava má vrátit viditelný kontext a ponechat raw input opravitelný. První dva vlastní testy mají skutečné Qt/domain fixture, bez stubování _commit_pending_input. Raw prvnírepro [run01](evidence/pc007b-curved-ui-review-own-run01.json).

**CUI02 MINOR — CLOSED / VERIFIED na e1c06f5; původní nález: hlavní guidance popírá aktuální doložený C spoj.** Kvalifikovaný single-set producer fixture má explicitně CERTIFIED_APPROXIMATE. Zvolen je tento plášť/sada, ale hlavní hint stále říká, že připojení této prostorové plochy zatím nemá ověřený spoj. Obecný loft text nepokrývá novou C možnost/status a odporuje panelu. Oprava má rozlišit podporovaný circular shell od obecného loftu a zachovat APPROXIMATE/physical omezení. [Kvalifikovaný samostatný repro](evidence/pc007b-curved-ui-review-own-guidance-run02.json).

**CUI03 MINOR — CLOSED / VERIFIED na e1c06f5; původní nález: missing-owner source change uniká z timer handleru jako KeyError.** Ve veřejně platném projektu bez existující C sady otevřený dialog drží owner; delete_material_part odstraní tento owner. Stejný _source_changed handler jako QTimer zavolá invalidate→_refresh_labels→part_for_surface a dereferencuje zaniklý surface. Vlastní deterministický test timer zastaví před ručním vyvoláním stejného handleru a bezpečně uklidí dialog. Modal běžnému ručnímu souběžnému delete brání; nejde o tvrzení pozorovaného native crash. Po souběžné změně má být obsolete preview neaktivní se srozumitelnou cestou zavřít/znovuotevřít, pozdní výsledek se nemá použít.

**CUI04 MINOR — CLOSED / VERIFIED na e1c06f5; původní nález: effective enabled není totéž co autorský slot override.** Slot11 z uchovaného12-poolu při count8 nebo slot ve vypnuté celé sadě má effective row.enabledFalse. Tlačítko proto říká Zapnout, ale toggle_tab čte latentní override defaultTrue a zapíšeFalse. Činnost tedy změní autorský stav opačně než svůj popisek. Count i global enabled správně zůstávají stejné. Oprava může label/action odvozovat z autorského override s explicitním outside-count/disabled vysvětlením, nebo akci zakázat. Nesmí automaticky rozšířit count či zapnout tisk.

## Pozitivní ověřené vlastnosti

Čtení produkčního kódu potvrzuje oddělený worker-owned projekt z úplného serialized source a kopii requestu, jeden běžící worker a nejvýše poslední pending request. Draft/source fingerprint a token brání přijetí zastaralého výsledku; Accept a Apply mají oddělený source fence. Do živého dokumentu se ukládá intent přes veřejné příkazy, nikoli preview certifikát/projekt či hotová geometrie. Staré sloty jsou vázané UUID prefixem, index adresuje jen čerstvě vytvářený pool.

Vlastní positive/fault cases dokazují: Cancel vymaže i queued latest request a pozdní callback nemění živý projekt; mutace worker clone zůstane oddělená; skutečný late set_curved_tab fault po změně papíru a vytvoření slotů vrátí celý dokument a Undo depth; skutečný producer packet s podvrženým receiver ID nepublikuje certified display ani nepovolí Apply. Callback stubs slouží concurrency/response faultům, nikoli pozitivní C geometrii.

Původní skutečné producer/widget testy navíc pokrývají oba rims válce/kužele/near-cylinder, off/custom-tip, staged paper repair, explicitní stale/recompute, Undo/Redo a save/open. Jsou to backend fixtures následované skutečným dialogem, nikoli kompletní kreslení C od prázdna přes native Windows a editor.

## Kvalifikace vlastního harnessu

První guidance pokus používal dvě současné sady, které nebyly CERTIFIED; tento třetí failure run01 proto **není** CUI02 důkaz. Následný kvalifikovaný single-set test prokazuje status před vlastním guidance očekáváním.

První mouseClick inactive-slot run05 neaktivoval skrytý scroll control a dal slabé2 PASS beze změny stavu. Tento běh je **DISQUALIFIED**, nenahrazuje run06. Opravený offscreen test aktivuje skutečný QPushButton.click a jeho připojený UI handler. Pozitivní native scroll/mouse důkaz zůstává rootovi. [Přesné harness poznámky](evidence/pc007b-curved-ui-review-harness-notes.json). Původní raw se nemažou.

## Skills a integrační meze

AGENTS a všechny4 skills skutečně načteny. Construction vede k oddělení pláště/příjemce, celého source a konkrétního slotu; UI k C05 kontextu, pravdivému statusu a opravě stejného workflow; verification kvalifikuje fixture/aktivaci a nepřiznává matematiku či native za stuby; delivery předává konkrétní nálezy jinému autorovi, zachovává rawFAIL a čeká na přesný fix pin.

Při C+LINE integraci zachovat surface/variant priority v _sync_selection, LINE action enablement/_update_edit_actions, C _current_issues v refresh/focus/ack, a nové C guidance před obecným loft fallbackem. Schema8, known C6/LINE7 adaptéry a nová canonical source vazba jsou samostatný integrační scope, nikoli automaticky získané schválení tohoto staršího UI pinu.

Native UI→save/reopen→unfold→manual layout→SVG/PDF/editor pro celé C je PENDING. Novice0/NOT_RUN, physical P3/NOT_RUN. Tento report není dokončené C/P2 ani jeho produktové přijetí.


## Nezávislé přezkoušení oprav e1c06f5

Opravný pin mění pouze dva produkční UI soubory a jejich testy; žádný geometrický producer, persistence schema, source binder, writer ani normativní AC nebyly změněny. Runner pořídil fresh exact archive e1c06f5 a samostatný subprocess má skutečné importy/hash shodné s Git bloby, nikoli sdílený editable checkout.

- [Všech9 vlastních případů](evidence/pc007b-curved-ui-review-own-fixed-e1c06f5-run07.xml): **9 PASS9.54s**, [raw/source binding](evidence/pc007b-curved-ui-review-own-fixed-e1c06f5-run07.json). Šest kvalifikovaných původních negativních očekávání zůstalo beze změny. Zbývající tři ověřují queued cancel/clone isolation, late atomic fault a malformed real-producer response.
- [Původní UI + author fix + curve/loft/segmentation regrese](evidence/pc007b-curved-ui-review-original-fixed-e1c06f5-run02.xml): **55 PASS57.88s**, [raw/source binding](evidence/pc007b-curved-ui-review-original-fixed-e1c06f5-run02.json). Zahrnuje původních47 a8 nových opravných případů. Žádné count agregace s dřívějšími či autorovými34cases.
- Autorův handoff694004e správně ponechává starý47 běh historicky, dokládá oddělený source e1 a cílených34/30deselected; přiznává vlastní nekvalifikovaný první CUI03 harness. Nezaměňuje deterministické stubs za pozitivní geometrii či native.

**CUI01 uzavření:** neúspěšný main numeric preflight obnoví combobox podle skutečného current_id pod QSignalBlocker a checkbox podle live record.enabled. Neprovede žádný dokumentový příkaz, nemění owner/tab/tree/viewport, zachová neplatný rozepsaný raw input k opravě. Není to automatické přijetí či zaokrouhlení vstupu.

**CUI02 uzavření:** guidance pro source-recognized circular shell rozlišuje CERTIFIED_APPROXIMATE, STALE, UNRESOLVED, vypnutou sadu a dosud nevytvořený spoj. Návazný krok je dostupný příkaz/panel/přepočet. Obecný loft nedostane nepravdivou C způsobilost. Aktuální C popisek říká digitálně doložená APROXIMACE, nikoli přesný/fyzicky doložený spoj. Rozpracované kreslení, odmítnuté tělo a profile context mají zachované předchozí priority.

**CUI03 uzavření:** _owner_available prověří surface i jeho material part před dereferencí. Source change při smazání vlastníka vymaže packet/pending, zakáže compute/apply a vysvětlí zavřít/znovuotevřít. Request preview stejného zaniklého vlastníka také bezpečně vracíFalse; late worker se nepublikuje. Oprava přidává guard, nezachovává neplatný shadow surface ani falešnou starou geometrii.

**CUI04 uzavření:** mimo count či při vypnuté sadě je tab action explicitně disabled a popisek/tooltip vysvětlují samostatnou obnovu počtu nebo sady. Latentní override se nemění. Také přímý obsolete handler call kontroluje aktuální count/global enabled/slot membership. Pro aktivní slot odvozuje label z autorské volby, ne z dočasně effective stavu; není provedeno implicitní zapnutí tisku ani přemapování identity.

Tím jsou původní kvalifikované FAIL skutečně přehrány jako PASS, nikoli odstraněny. Vlastní původní fixture/activation omyly zůstávají odlišené v harness notes. Stejně jako CY01 jiného review nelze vlastní nekvalifikovaný mutant/klik vydávat za produktový či geometrický důkaz.

## Rozsah předání integračnímu ownerovi

Tento UI přírůstek je připraven k integraci rootem spolu se schválenými backend dependency opravami. Návrhové a UI review provedl jiný agent než autor; žádné self-approval. Native Windows a skutečný C UI→save/reopen→unfold→manual layout→SVG/PDF/editor jsou stále samostatně ověřované rootem na konečném společném source pinu.

C+LINE/schema8 integrace musí ponechat C owner-first tree selection, LINE context actions, společné _current_issues a aktuální source/preview fences; known6/7→8 copy adaptéry ani root harness nejsou tímto reportem automaticky schválené. Případné věcné konflikty vyžadují kontrolu konkrétního výsledku. SK013 transfer je ověřen jen v současném validním i rejected-input rozsahu po opravě CUI01, širší next-use účinnost není garantovaná.

AGENTS/čtyři skills byly uplatněny na skutečných výsledcích a opravách; nové lessons/autorské metadata dalšího integrovaného balíku zůstávají samostatným review předmětem. Novice0/NOT_RUN a physical P3/NOT_RUN se nemění. Nejde o dokončení C, celého AU13/P2, release nebo produktové přijetí.
