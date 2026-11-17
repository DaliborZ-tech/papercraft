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

Regrese obrácených kuželových oblouků je opravena `09b6811` a nezávisle ověřena.
Finální úplná sada `4f110d9`: **1916 PASS, 0 FAIL/ERROR/SKIP, 710,39 s**.
Původní neúspěšné běhy zůstávají zachované. Archivní D fixtures nyní výslovně
ověřují odmítnutí staré cache před přepočtem a zachování autorské práce po něm;
jejich původní numerické a negativní přejímky se nemění. Nové current9 D
projekty prošly save/reopen i skutečnými SVG/PDF.

Na stejném produkčním zdroji `a5eedc9` prošel znovu válec Qt150 (101,125 s),
kužel (169,063 s), near (146,5 s) a všech šest jejich skutečných SVG stránek
editací a uložením v Inkscape. Tyto nové výsledky mají vlastní source binding;
nezávislé integrační review je níže.

PC-009 konsolidace a změny po reopen jsou rozpracované. V odděleném kandidátu
prošel skutečný A se dvěma stránkami a oběma zámky, včetně druhé změny po
reopen; dosavadní C9 integrační scope tento novější frontendový přírůstek
nezahrnuje. PC-010 má připravený scénář, skutečný historický model je NOT_RUN.
AC-US08 má stále 0 skutečných nových účastníků / NOT_RUN. Fyzické P3 je NOT_RUN.

## Aktuální produktová priorita vlastníka

Následný audit a konkrétní PO rozhodnutí nad screenshotem odmítají současné
UI jako cílovou podobu. Nejbližší výstup je fungující desktop se čtyřmi volnými
kontexty **Modelování / Spoje a rozvin / Stránky / Export**, kontextovým
inspektorem, dominantním pracovním pohledem, dohledatelným výběrem a seskupenými
opravitelnými problémy. Rozpracovanou práci má chránit oddělený autosave draft
a recovery. Geometrické a datové kontrakty se neoslabují.

Vlastník výslovně požádal nezávislého agenta o zkušenosti a vzory z místních
i internetových zdrojů a praktické hodnocení GUI. Jde o expertní agentní
ověření, nikoli provedený test nového člověka. Implementace workspace a recovery
probíhá v oddělených větvích; historický model nepředbíhá tuto nápravu.

C9 technický přírůstek byl integrován a pushnut jako `6efa881`; lokální master,
origin/master i přímý ls-remote měly shodné SHA. [Záznam publikace](evidence/p2-c9-publication-6efa881.json).
Nový workspace a recovery jsou samostatný probíhající přírůstek.

## Nezávislé integrační review C9 — f5f06b2

Reviewer `editor_review` není autorem produkční delty. Posouzen přesný
`f5f06b2014d5a576d4eb7bdbd4182668cacbb4cd` proti baseline
`00db953cd8d936fb7d99d0503c7bd2ecd04bf369`. Vlastní připravovaný PC009
after-reopen driver v tomto kandidátu není a toto review jej neschvaluje.

**APPROVED_IN_C9_TECHNICAL_INTEGRATION_SCOPE**, bez otevřeného technického
nálezu. Finální předávací metadata po nové změně produktových priorit a
publikace mají ještě svůj konkrétní následný pin; toto není přijetí P2 ani release.

- Celé `src` odpovídá již nezávisle posouzeným komponentám: 115 souborů z
  `3e6fbb6`, dva UI soubory z `5415e2`, `loft_surface.py` z `09b6811`.
  Tools jsou shodné s posouzeným `42dca62`; žádná skrytá integrační změna
  producentu, identity, tolerance nebo GUI handleru nepřibyla.
- [Úplná sada na 4f110d9](../p2/implementation/evidence/p2-candidate-4f110d9-full/binding.json):
  **1916 PASS / 0 failures, errors, skips / 710,39 s**. Ověřeno 255 skutečných
  source/test/tool hashů vůči f5 a všech 106 in-process importů z vlastního
  `quarter-arc-fix/src`. `src` i `tests` Git trees jsou mezi 4f a f5 shodné.
  Ruff dotčených souborů PASS; původních 47 selhání a5 se zachovává jako FAIL.
- Oprava tří legacy D fixture v `4f110d9` požaduje stale a odmítnutý snapshot,
  potom explicitní recompute a invariant profilů, generací, kotev, layoutu a
  originálních bytů. Původní poison/output očekávání nebyla změněna. Vlastní
  replay všech tří souborů: [57 PASS / 166,37 s](../p2/implementation/evidence/c9-integration-review-f5-D-tests.xml),
  včetně dvou nových fresh schema9 LINE/CURVED save/reopen/SVG/PDF/poison případů.
- [Vlastní audit skutečných výstupů](../p2/implementation/evidence/c9-integration-review-f5-artifacts.json)
  znovu ověřil všechny tři finální C projekty na a5: každý 132 runtime hashů a
  22 artifact hashů, přesný snapshot/manifest/SVG/PDF digest, aktuální schema9,
  příjemce, zachovaný vypnutý slot a upravený vrchol, dvě stránky a oba locks.
  Nezávislé analytické plochy proti skutečnému SVG/PDF splňují původní 0,01 mm².
  Všech šest finálních Inkscape stránek má 24 shodných artifact hashů, zachovaný
  originální bundle, opakovanou celokřivkovou/frame kontrolu a přesně uložený
  víceslovný Unicode label. Screenshoty skutečného C náhledu, layoutu a editoru
  byly zkontrolovány; žádný nový desktopový vstup reviewer nevyslal.
- Oba původní native ARC/CUBIC saved projekty se ve f5 načetly a daly přesně
  původní JSON snapshot; ověřeno dalších 48 output hashů. Přenos není novým
  native během. Qt150 má oddělené již posouzené skutečné viewport/own-HWND
  události, samostatný zoom/pan a zachování po refreshi.

[Vazba integračního review](../p2/implementation/evidence/c9-integration-review-f5-binding.json)
a [opakovatelný čtenář artefaktů](../p2/implementation/evidence/c9-integration-review-own.py).
SK008/013/016 odpovídají doložené příčině a vymezenému technickému přenosu.
Nové odstavce a záznamy SK017/018 jsou **APPROVED_IN_SKILL_TEXT_SCOPE**: oddělují
orientovanou zdrojovou topologii od korespondence a CSS frame od operandů/bbox.
Účinnost SK008 follow-up a SK016/017/018 správně zůstává PENDING_NEXT_USE;
SK013 má pouze prokázaný technický přenos valid/rejected context, ne člověka.
Konstrukční, UI, verification a delivery skills jsou doloženy konkrétními
source-bound negativy, zachováním práce, skutečnými soubory a jiným reviewerem.
Bezpečná první verze a navazující DATA01/UX práce zůstávají otevřené; AC-US08
0/NOT_RUN, PC010/AC-AU19 a fyzické P3 se tímto schválením neuzavírají.
### Exact final metadata review — C9 `4c43094`, 17. 11. 2026

Nezávislý reviewer `editor_review`: **APPROVED_IN_C9_TECHNICAL_INTEGRATION_SCOPE**
pro přesný kandidát `4c43094b088a58f3009f731d9401d72cf0a81e2d`, bez otevřeného
zásadního nálezu. Proti již přezkoumanému `f5f06b2` nemění `src`, `tests`
ani `tools`; všechny tři Git tree identity odpovídají úplnému běhu `4f110d9`.
Převzaté full-suite artefakty jsou totožné s důkazem `aeb8ec7`, jehož JUnit,
255 source/test/tool hashes a 106 skutečných finish importů jsem ověřil výše:
1916 PASS, žádný FAIL/ERROR/SKIP. Nový report zachovává původní neúspěšný a5
výsledek a nepřičítá cílené podmnožiny k úplné sadě.

Zkontroloval jsem celý metadata delta od svého review `90257e3`: queue, aktuální
úvod tohoto reportu, nový full-suite oddíl a stav review SK017/018 odpovídají
doloženému rozsahu; účinnost obou poučení zůstává `PENDING_NEXT_USE`. Nová
priorita workspace/recovery a expertního agentního GUI hodnocení neprohlašuje
hotovou implementaci ani produktové přijetí. AC-US08 stále 0 skutečných nových
účastníků / NOT_RUN, PC010 actual a fyzické P3 NOT_RUN. Moje následné PC009
tools a DATA01 změny v tomto kandidátu nejsou a toto schválení se na ně
nevztahuje. Předchozí věcná omezení C9 review zůstávají platná; desktop jsem
neaktivoval. Integrace/push a remote identity jsou samostatný následující krok.

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
