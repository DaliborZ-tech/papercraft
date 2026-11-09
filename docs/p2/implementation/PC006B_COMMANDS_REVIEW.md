# PC-006B — nezávislá revize pojmenování a odstranění dílu

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; není autorem komponenty.

**Zdroj:** `60c7889c827ea33bc309d299319ee2e63c538556`, větev `revival/p2-author-commands`. Před spuštěním byl pracovní strom čistý a HEAD odpovídal tomuto pinu. Revize nemění produkční kód ani testy autora.

**Verdikt: APPROVED_IN_COMPONENT_SCOPE.** Nebyl nalezen blocker ani major v revidované komponentě. Jeden doložený minor UI textu je otevřený. Toto není nezávislé schválení následného zapojení do hlavního okna, PC-006B jako celku ani P2.

## Rozsah a důkazy

Přečteny `authoring/editing.py`, `ui/author_editing.py`, autorovy testy a závislé mechanismy controlleru, atomických příkazů, cache a persistence. Základem jsou platné AGENTS ze skutečného rootu, kontrakt v1.2, relevantní AC-AU / AC-US a autorské UX; produktové přijetí v1.2 zůstává v platnosti.

Spuštění z worktree `C:\Users\dalib\projects\papercraft-author-commands`:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_editing.py tests/authoring/test_controller.py tests/authoring/test_persistence.py -q --junitxml=docs/p2/implementation/evidence/pc006b-commands-review-existing.xml
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest docs/p2/implementation/evidence/pc006b-commands-review-own.py -q --junitxml=docs/p2/implementation/evidence/pc006b-commands-review-own.xml
```

- Původní cílené testy: **41 PASS / 20,70 s**. [JUnit](evidence/pc006b-commands-review-existing.xml).
- Vlastní nezávislé případy: **16 PASS / 1,19 s**. [Zdroj](evidence/pc006b-commands-review-own.py), [JUnit](evidence/pc006b-commands-review-own.xml). Poslední případ pravdivě reprodukuje minor níže; jeho zelený výsledek neoznačuje chybný text za správný.

Vlastní očekávání vychází z předem určených tří nespojených čtvercových dílů, přesných uložených slovníků a přímého textu dialogů; nejde o přepočítání očekávaného dopadu stejným produkčním helperem. Kontrolováno samostatné odstranění prostředního dílu při zachování dvou zbývajících dílů, umístění, zdrojových profilů a čítačů. Autorovy případy navíc pokrývají fold komponentu, přímé i nepřímé závislosti, pásek a nezávislý rozbitý spoj bez globálního přepočtu.

Vlastní negativní případy ověřují změnu projektu po náhledu odstranění, cizí projekt, odstraněný cíl přejmenování a atomické odmítnutí devíti neplatných vstupů. Zrušení a potvrzení dialogu, no-op bez dirty/undo, undo/redo a save/open jsou pokryté cílenými autorovými testy i vlastními případy. Doslovný název obsahující HTML podobné značky, ampersand, uvozovky a Unicode zůstává textem v dialogu a po IO.

Vlastní schema-1 projekt byl otevřen přes controller jako kopie. Přejmenování i odstranění, undo/redo a následný neúspěšný příkaz neumožnily přepsat původní cestu; původní bajty zůstaly stejné a uložení pod novou cestou se po otevření přesně shodovalo se stavem controlleru. To ověřuje konkrétní schema-1 adaptér tohoto pinu, nikoli budoucí schema-3 integraci.

## C-EDIT01 — minor, počet spojů je označen jako počet chlopní

**OPEN.** `DeletePartDialog` uvádí `Odstraněné chlopně: {len(connectors)}`. Jeden connector může obsahovat čtyři samostatné chlopně; vlastní obdélníkový fixture s `count=4` zobrazil počet 1. Údaj je tedy počet definic/spojovacích prvků, nikoli počet jednotlivých aktivních chlopní. Vypnuté individuální chlopně rozdíl dále mění.

Doporučení při zapojení: buď přesně pojmenovat počet spojovacích prvků, nebo uvést počet prvků i aktivních jednotlivých chlopní z konkrétního náhledu. Neměnit geometrii ani odstraňovací dopad pouze kvůli tomuto textu. Ověřit při rozděleném patternu a po vypnutí jedné chlopně. Nález nezpochybňuje atomické odstranění jednoho connectoru a všech jeho override dat.

## Uplatnění projektových skills

- **Papercraft konstrukce:** mazání je omezené na celý skutečný papírový díl a přímo navázané spoje; zachovává zdrojové skici, protikusy, jejich kotvy a layout. Ověření zahrnuje skutečný dvouplošný pásek a fold komponentu z autorových testů. C-EDIT01 rozlišuje connector od jednotlivého materiálu chlopně.
- **Srozumitelné autorské UI:** náhled uvádí modelářské názvy a čísla, zachované skici a protikusy; nepodmiňuje základní rozhodnutí UUID. PlainText brání interpretaci vlastních názvů jako značek. Cancel a jeden vratný příkaz byly technicky ověřené. Přesnost počtu v náhledu má minor výše. C05 preflight musí zajistit hlavní okno; samostatný dialog jej nemůže certifikovat.
- **Ověřování geometrie a výroby:** vlastní očekávání zachování dat je určeno nezávislým fixturem a přesnou rovností před/po, včetně negativních případů a původních bajtů starého projektu. Důkaz je numerický/controller a offscreen Qt, nikoli nativní OS/editor/nový uživatel/fyzická stavba.
- **ADLC delivery a poučení:** verdikt je připnut na zdroj a oddělen od následné integrace. Nález byl předán integračnímu ownerovi; produktovou opravu ani účinnost dosud neprovedeného poučení tento report netvrdí.

## Co ještě neověřeno

Zapojení příkazů do kontextu skutečného výběru, hlavní menu a klávesnice; C05 rozeditované vstupy před dialogem; chování společného finálního commitu se schema 3; skutečný nativní průchod včetně přepočtu značení a obou exportů. Tyto body čekají ověření v integračním balíku. AC-US08 s novým člověkem je NOT_RUN; offscreen testy jej nenahrazují. Fyzický důkaz zůstává P3.

## Navazující revize zapojení `ccc2d7e` — 9. 11. 2026

**UI integrační zdroj:** `ccc2d7e98b8d2d4e302de3f9c578a657a614ccb3`. Přečten konkrétní diff: menu Úpravy, F2, dvě kontextová tlačítka, dostupnost podle výběru a preflight před konstrukcí obou dialogů. `delete_part` úmyslně nemá globální Delete zkratku, která by mohla odstraňovat díl při psaní v poli. Změny odpovídají zachování názvů a bezpečnému experimentu v platném workflow; nevytvářejí novou produktovou bránu.

**APPROVED_IN_COMPONENT_SCOPE pro tento UI delta. C-EDIT01 CLOSED:** text nyní přesně uvádí počet spojovacích prvků s chlopněmi. Náhled stále nelže, že jde o počet jednotlivých chlopní. Vlastní test přímo čte opravený text dialogu.

- Přezkoušené stávající workspace + editing: **54 PASS / 6,05 s**, [JUnit](evidence/pc006b-commands-review-integrated-existing.xml).
- Vlastní integrační případy: **4 PASS / 1,17 s**, [zdroj](evidence/pc006b-commands-review-integration.py), [JUnit](evidence/pc006b-commands-review-integration.xml).
- Vlastní skutečně zaslaná klávesa F2 při rozepsané souřadnici potvrdila 12 m → 12000 model mm před dialogem; jeho zrušení zachovalo právě potvrzenou číselnou změnu.
- Skutečný klik na postranní tlačítko odstranil právě vybraný druhý díl, zachoval první díl i jeho placement a jediné undo obnovilo přesný stav.
- Zrušení výběru vypnulo oba vstupy odstranění, ale ponechalo přejmenování modelu; otevřený dialog neměl pole nevybraných entit.

Vlastní test byl spuštěn s `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH` explicitně na `papercraft-bend-integration/src` a `tests/authoring`, s `-c` na tamní `pyproject.toml`; první test ověřil skutečnou cestu importovaného modulu. Příkaz má stejný tvar jako výše, ale vstup je `pc006b-commands-review-integration.py` a JUnit `pc006b-commands-review-integration.xml`.

**Přesná mez pinu:** během běhů byl HEAD integračního worktree `ccc2d7e`, avšak jiný agent souběžně měnil `authoring/bend.py` a jeho testy. `git diff ccc2d7e -- author_window.py author_editing.py editing.py test_workspace.py` byl prázdný. Tato revize proto schvaluje uvedené přesné UI/editing soubory a jejich integrační delta; neuděluje schválení celému znečištěnému pracovnímu stromu ani rozpracovanému adaptéru ohybu. Finální sjednocený commit potřebuje samostatné připnuté ověření/review. Testy zde neobsahovaly nové konektorové ohyby a neposuzují jejich správnost.

Nativní OS průchod s novými příkazy, finální schema-3 balík, výrobní exporty, nový člověk a fyzické sestavení nadále nebyly tímto doplňkem provedeny. Historické evidence ani jejich zdrojové piny nebyly přepsány.

## Nativní driver a poučení — nezávislá úzká revize 9. 11. 2026

Revidované změny driveru: `bae88e2dfdd71dbf0c10aafb6b5d06042c8de2f6` (vlastní pojmenování/mazání/materiál), `1108361ac625d59939a53ef7045a1743555deacf` (vazba importu na worktree), doplněk `d2a3b735ce2fcffcddbea6ca32d7449a1609b0c5` (odmítnutí necommitovaných zdrojů). Revidovaná změna skillu a ledgeru: `d072aa8d83af1fa19df7ed93ab733909549582e2`.

**APPROVED_IN_HARNESS_AND_LESSON_SCOPE.** Driver má skutečné menu/toolbar vstupy, textové psaní QTest, nativní potvrzení/zrušení dialogu a klávesové undo/redo. Konstrukční data se nevkládají controllerem ani přímou změnou geometrie. Volání světové geometrie, snapshotu a `to_dict` slouží k pozorování. Jediná náhrada `AuthorMainWindow` factory přidá izolované settings a časovač, vytvoří původní třídu a poté volá skutečné `app.main()`; nedodává dokument ani náhradní controller. Potvrzování varování používá skutečný výběr a tlačítko a omezuje se na explicitní známý kód fyzické nejistoty; tvrdé chyby nesmějí projít.

`1108361` vkládá vlastní `src` před import aplikačních modulů. Skutečné `author_window.__file__` musí odpovídat tomuto worktree před vytvořením evidence adresáře a spuštěním GUI; cesta se ukládá do reportu. V již cachovaném cizím modulu je místo falešného přepnutí bezpečné odmítnutí. Na konci úspěšného běhu se musí shodovat aktuální HEAD i kompletní SHA256 pokrytých souborů se stavem na začátku. SHA256 pokrývá všechny Python zdroje aplikace, driver, native-dialog helper a pyproject. Vlastní review nepouštělo desktop ani QApplication.

Při revizi byl upozorněn rozdíl mezi shodou hashů po dobu běhu a shodou se zdrojovým commitem. Owner jej uzavřel `d2a3b735`: ještě před `output.mkdir` a GUI se odmítá diff HEAD v aplikaci/harnessu/pyproject i nepřidaný pokrytý zdrojový soubor. Nezávislé důkazy mimo tyto zdrojové cesty přitom mohou vznikat souběžně. Diff kontroluje index i pracovní kopii proti HEAD. Revize nejde tak daleko, aby certifikovala případné externí import hooky nebo měnící se instalované třetí knihovny; runtime verze se evidují odděleně.

Vlastní [zdroj orákula](evidence/pc006b-commands-review-import-binding.py) a [raw JSON](evidence/pc006b-commands-review-import-binding.json): **3 fresh subprocess případy PASS**, navíc **5 rozhodovacích případů guardu PASS**. Skript provedl bez desktopu skutečný importní prefix vytažený pomocí AST z revidovaného driveru, nikoli pouze ručně opsanou domněnku o Python path:

- Bez opravy sdílený venv načetl `papercraft/src/.../author_window.py`.
- S prefixem skutečného driveru načetl `papercraft-bend-integration/src/.../author_window.py`; všech 26 právě načtených aplikačních modulů pocházelo z integračního `src`.
- S již načteným cizím modulem guard skončil požadovaným `ValueError` ještě před GUI a výstupy.
- Extrahovaný blok kontroly commitovaných zdrojů přijal čisté zdroje i nepokrytou dokumentaci a odmítl pracovní změnu, staged změnu a nový nepřidaný pokrytý zdroj. Jde o test rozhodovacího bloku s explicitními vstupy, nikoli předstírání úpravy živého checkoutu během nativního běhu.

Soubor driveru při této zkoušce odpovídal `d2a3b735` (prázdný `git diff` proti tomuto pinu); raw JSON obsahuje jeho hash `31d7ed628b0b7bff84c0f46d7d4cc97ecc0380db6dbd9c75084991c8aa52b65d`. Původní run04 zůstává FAIL s `KeyError: rename`; nové importní orákulum potvrzuje doloženou příčinu, ale nepřepisuje historickou evidenci na produktový FAIL ani PASS cílového zdroje.

SK-007/SK-008 jsou úzké postupy navázané na K01 a skutečné selhání importu. Nesnižují normativní AC, nevytvářejí nové oprávnění a nenahrazují výrobní ani lidský důkaz. SK-007 explicitně požaduje uchovat jistou negativní dvojici po přidání nezávislé nejistoty; konkrétní integrovanou fyzickou interpretaci vrstev stále musí schválit review adaptéru. SK-008 vyžaduje skutečnou cestu importu, nikoli pouze deklarovaný Git pin. Ledger pravdivě drží účinnost obou **PENDING_NEXT_USE** a další použití NOT_RUN. Vlastní importní subprocess je přiměřené dílčí ověření opravy harnessu; sám neuzavírá další nativní použití ani účinnost u lidí. Záznam technického review lze doplnit odkazem na tento oddíl, ale stav účinnosti není důvod automaticky změnit.

Meze: tento dodatek schvaluje uvedené změny harnessu a poučení, nikoli neproběhlý celý nativní model A/společný díl, geometrický adaptér, AC-US08, Inkscape nebo P3. Nativní desktop zůstal po celou revizi vyhrazen integračnímu ownerovi.
