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

## Desktop Workspace — implementační předání 17. 11.

Nový frontend `a9dc877`, následná oprava navigace `b15d25a`, používá čtyři
volně přístupné kontexty **Modelování / Spoje a rozvin / Stránky / Export**.
Výchozí velké 3D uvolňuje skicu kreslení nebo výslovnému přepínači. Stránky
upřednostňují papír s volitelným 3D; Export ponechává náhled a společnou
připravenost. Kontexty drží jeden dokument, výběr, historii a ruční rozmístění.
Menu a zkratky zůstávají dostupné; Ctrl+1–4 mění kontext, F8 otevře problémy.
Převzatý `AuthorProblemsPanel` má původní kanonické issue/ack digesty,
seskupení a jednotlivé cíle; navigace nepřesouvá ani nepotvrzuje materiál.

Přepnutí nejdřív dokončí viditelný vstup. Syntakticky i geometricky odmítnuté
číslo zachová přesný raw text a původní viditelný kontext. Stejně se ověřuje
inline název vybrané plochy. Inspektor filtruje sekce, zalamuje celé popisky
a ovladače; test při šířce 300 px včetně rozbalených pokročilých spojů nemá
horizontální scroll. Základní logical velikost 1366×768 je ověřena komponentově;
nenahrazuje nativní DPI/client měření. Běžný refresh zachovává kameru,
Open a první zviditelnění papíru rámují po změně rozměru viewportu. F/Home
pracují s aktivním pohledem. Potvrzený problém návratu UNPLACED nyní rámuje
společně skutečný stash díl a existující cílovou stránku; běžné F nadále
zaměřuje samotný díl.

Na připnutém `a9dc877` prošlo **168 komponentových testů / 82,48 s**,
na následné navigaci `b15d25a` **52 testů / 9,34 s**. V běžícím pytest je
ověřen skutečný import z vlastní izolace, vlastní PYTHONPATH a sdílený Python.
Celý widgetový průchod zahrnuje dvě vlastní stěny, editaci a Undo/Redo,
dialog spoje, 3mm chlopeň, přepočet, ruční dvě A4, Save/New/Open a skutečný
SVG/PDF writer. Nezávislé čtení SVG ověřuje plochy 4800 a 6744 mm² a 60mm
přehyb; PDF má dvě A4. Změny produkčního zdroje se omezují na UI.
[JUnit](../p2/implementation/evidence/desktop-workspace-components.xml),
[source identity](../p2/implementation/evidence/desktop-workspace-components.json)
a [navigační regrese](../p2/implementation/evidence/desktop-workspace-navigation-followup.xml).
Použity projektové UI/delivery/verification skills na skutečných odmítnutích,
průchodu a zdrojově vázaném důkazu; konstrukční/doménový kontrakt nezměněn.
Nativní nezávislé UX review, společný recovery hook a integrační ověření
následují u ostatních vlastníků. Nový lidský uživatel a fyzické sestavení
zůstávají **NOT_RUN**; autorův komponentový průchod je nenahrazuje.
