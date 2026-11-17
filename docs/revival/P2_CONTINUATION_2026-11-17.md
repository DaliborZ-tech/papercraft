# Pokračování P2 — 17. 11. 2026

Práce obnovena výslovným PO CONTINUATION. Výchozí čistý master i načtený
origin/master: `00db953cd8d936fb7d99d0503c7bd2ecd04bf369`. Nová izolace je mimo
`projects`; původní worktrees a důkazy zůstávají zachované. Git historie tohoto
baseline již obsahuje C+LINE runtime `8f1ec638`; nové CORE9/UI a comparator se
přebírají a ověřují zvlášť. Tento záznam není produktová akceptace ani release.

## Dokončené technické ověření

- CORE9-R01: původních šest negativů znovu selhalo na původním zdroji, stejná
  očekávání s opravou prošla. Rozšířená nezávislá matice zahrnuje retired ID,
  None/counterfeit, orphan/UNRESOLVED, starší skutečné projekty a ruční layout.
  [Nezávislá revize](../p2/implementation/AU13_CORE9_APPLICATION_REVIEW.md).
- Potvrzen samostatný detached CUBIC export bypass bez historie. Oprava
  `3e6fbb6` vyžaduje replay také v prázdném kontextu; nezávislý skutečný writer
  po odmítnutí zachová předchozí bundle. LINE ROOT/left/right resurrection je
  potvrzen na původním zdroji a již opraven `72f7a16`.
- Skutečná Windows aplikace, source `6969069`: vlastní ARC i CUBIC → loft →
  měřené dělení/sloučení → Undo/Redo → ruční dvě stránky a oba zámky →
  Save/New/Open → SVG/PDF. [ARC](../p2/implementation/evidence/au13-arc-native-6969069-run02/results.json)
  29,75 s; [CUBIC](../p2/implementation/evidence/au13-cubic-native-6969069-run01/results.json)
  91,64 s. Původní FAIL `5415e2` zůstává; šlo o chybné čtení atributu v harnessu.
- [Válec při Qt150](../p2/implementation/evidence/c-cylinder-qt150-42dca62-run01/results.json),
  source `42dca62`, 80,046 s PASS: skutečný recipient, upravené/vypnuté chlopně,
  chybný vstup a oprava, dvě stránky, soubory a nezávisle pozorovaný zoom i pan.
  PID/HWND/foreground/hit-test pojistky zůstaly. Jde o škálování procesu 1,5,
  nikoli certifikaci nastavení DPI operačního systému.
- [Původní near plášť v Inkscape](../p2/implementation/evidence/c-near-original-inkscape-42dca62-run01/editor-results.json),
  27,485 s PASS: stejný skutečný export `5283632`, přesun dílu, Unicode text,
  uložení, 23 celokřivkových porovnání a zachování původního bundle. Comparator
  nezaměňuje zaokrouhlení poloměru za změnu materiálu; původní meze zůstávají.
  Nezávislý EDITOR-R01 odhalil CSS frame bypass; oprava jej bezpečně odmítá.
  [Review comparatoru](../p2/implementation/EDITOR_CURVE_EQUIVALENCE.md).

## Otevřený rozsah

Široký běh na `6969069` odhalil dva false-INVALID případy obráceného kuželového
oblouku. Oprava, její nezávislé review a finální úplná regrese právě probíhají;
dosavadní dílčí PASS tento nález nezakrývá. Nový finální zdroj vyžaduje vhodný
opakovaný průchod C a source-bound výstupy před technickou integrací.

PC-009 konsolidace a změny po reopen, PC-010 vlastní historický model a jejich
finální nezávislé digitální ověření zůstávají rozpracované. AC-US08 má stále
0 skutečných nových účastníků / NOT_RUN. Fyzické P3 je NOT_RUN.

Integrace tohoto pokračování na master a ověření remote SHA zatím PENDING.
### DATA01 — oddělené koncepty a obnova, první autorský kandidát

Zdroj `7edf31431de0a3aa4a0b20636e57c09ba3b405d2` (autor `editor_review`,
izolace `data01-recovery`, základ `f5f06b2`) přidává samostatný atomic recovery
store, 30s timer a obnovu v aktivním AuthorController/AuthorMainWindow přes
malý [Window hook patch](../p2/implementation/evidence/data01-window-hooks.patch).
Window layout/actions nepřepisuji: tento přesný patch byl při ověření aplikován
navíc ke zdrojovému commitu, poté vrácen; vlastník nového workspace jej přebírá
se společným modulem. Feature bez těchto hooků není v aplikaci zapojená.

Koncept nikdy nepíše uživatelský projekt. Uchovává potvrzenou doménu a odděleně
rozepsané číslo hlavního inspektoru či nedokončený obrys, bez interpretace textu,
přepočtu, změny fokusu, savepointu nebo undo. Obnova je neuložená kopie s novým
jménem při Save As a ochranou původního souboru. Dialog rozlišuje obnovení,
odložení a výslovné zahození; QLockFile vylučuje koncept jiného živého okna.
Při nemožnosti smazat vlastní koncept se New/Open/close zastaví. Testovací INI
settings izolují také vyhledávání konceptů, takže offscreen testy nečtou AppData.

Finální cílený běh se source/import guardem uvnitř procesu:
**82 PASS / 0 FAIL/ERROR/SKIP, 29,66 s** = 12 storage/controller + 21 recovery UI
+ 49 původních regresí. [JUnit](../p2/implementation/evidence/data01-recovery-final.xml),
[raw](../p2/implementation/evidence/data01-recovery-final.log),
[binding](../p2/implementation/evidence/data01-recovery-binding.json).
Ověřeny jsou disk-full/NaN/corrupt negativy, original/foreign bytes,
skutečné os._exit aktivního AuthorWindow a následné převzetí dead lock s obnovou
modelu i syrového `-`, všechny tři dialogové volby, exact druhý zdrojový bod
loftu, kubické pending úchopy s Backspace, celé aktuální C a D generace/layout.
Původní komponentové mezikroky jsou zachovány; binding také uvádí jediný
pozdější neúspěšný testovací setup s chybným názvem public API, opravený před
finálním během. Ruff dotčených souborů a diff check PASS.

Neobnovuje nepotvrzené ovladače uvnitř samostatných modálních konstrukčních
náhledů. Zápis je synchronní lokální atomic operace; není doložená výkonnost na
libovolně velkém projektu. Native desktop tohoto přírůstku, společný nový
workspace a nezávislé review feature jsou PENDING; autor je sám neschvaluje.
Nový člověk AC-US08 i fyzické P3 zůstávají NOT_RUN.
