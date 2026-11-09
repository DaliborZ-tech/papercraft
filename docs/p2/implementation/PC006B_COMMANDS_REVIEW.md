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
