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

### Nezávislé DATA01 peer review společného pinu `bea8020`

Reviewer není autor RecoveryStore/controller API/adapteru; vlastní workspace
tímto review neschvaluje. Izolace `recovery-peer-review`, vlastní PYTHONPATH,
Qt offscreen a shared Python; import adapteru ověřen uvnitř pytest. Původních
**33 recovery testů PASS / 9,14 s** zahrnuje skutečné přerušení procesu,
dead-lock převzetí, původní soubor, dirty kopii, C/D data i disk-full a mazání.
Vlastní fsync negativ navíc zachová přesné bytes posledního konceptu a
původního souboru a uklidí nedokončený temporary soubor.

Dvě konkrétní mezery v adapteru vyžadují opravu DATA01:

- **DATA01-R01-01:** skutečná akce Otvor + dva body do existující stěny nese
  `draft_plane` jako `SketchPlane`. `capture_ui` jej vloží přímo do JSON,
  checkpoint vrátí False s `Object of type SketchPlane is not JSON serializable`.
  Poslední dobrý koncept zůstane zachován, nové body otvoru se však neukládají.
  Budoucí oprava musí přesně obnovit rovinu vlastníka otvoru, bez odhadu XY.
- **DATA01-R01-02:** potvrzena již avizovaná integrační mezera inline názvu:
  čistý model + rozepsaný `selection_name` (platný text nebo prázdný neplatný
  název) nejsou `sketch` ani `pending_number`, takže checkpoint vrátí False
  a koncept nevytvoří. Po přerušení práce tento raw vstup chybí.

[Vlastní frozen testy](../../tests/authoring/test_recovery_peer_review.py)
mají na `bea8020` **2 PASS / 3 FAIL / 1,07 s**, dvě parametrizace odpovídají
stejné druhé příčině. [Původní JUnit](../p2/implementation/evidence/data01-peer-existing.xml),
[vlastní JUnit s oběma nálezy](../p2/implementation/evidence/data01-peer-own.xml).
Zdroj se v této revizi neopravuje; autor adapteru i root dostali přesné
reprodukce. Následuje nezávislý replay stejných očekávání na opravném pinu.

### Celá integrační regrese workspace/recovery `d94f9b3`

Na neměnném `d94f9b329c1e1e73241e8b66b76924a72bfac214` prošlo
**1978 testů, 0 FAIL/ERROR/SKIP / 596,44 s**. Běžící proces ověřil skutečné
importy z integračního worktree a shodné LF Git SHA256 všech sledovaných
Python souborů v `src`, `tests`, `tools` před a po běhu.
[JUnit](../p2/implementation/evidence/workspace-final-d94f9b3-full.xml),
[source binding](../p2/implementation/evidence/workspace-final-d94f9b3-full.json).
Jediné pytest upozornění se týká formátu `record_property`/JUnit, nikoli
neúspěšného nebo přeskočeného testu. Tento běh nezahrnuje následující opravy
pojmenování a skutečně sbalených profilových ovladačů nalezené v GUI.
Nativní expertní průchod, produktové UX přijetí, nový člověk a fyzický model
mají vlastní stav; počet automatických testů je nenahrazuje.

### Nezavisle uzavreni recovery nalezu

**Opravný pin `07025ed282b187c6454a8ae08abeb626c4833217`: oba DATA01 nálezy
uzavřeny nezávislým replay.** Adapter serializuje skutečnou SketchPlane a před
obnovou ji validuje i porovnává s přesnou rovinou původního vlastníka otvoru.
Nenahrazuje ji pojmenovanou či nejbližší rovinou. Samostatný `pending_name`
zachovává rozepsaný text včetně prázdného, váže jej na přesné surface ID a
obnovuje jej po pracovním kontextu bez přepsání platného doménového názvu.
Změna nezasahuje Window/controller ani geometrii. Původní assertions vlastních
negativů zůstaly zachovány; navíc přibylo skutečné dokončení obnoveného otvoru
dalšími dvěma QTest clicky a Enterem, s přesnou rovinou vzniklého hole profilu.

Finální cílený běh **48 PASS / 0 FAIL**, včetně vlastních pěti případů a
původních storage/controller/adapter regresí: [JUnit po opravě](../p2/implementation/evidence/data01-peer-fixed.xml),
[source/hash binding](../p2/implementation/evidence/data01-peer-binding.json).
Původní FAIL evidence výše zůstala zachována. Tento scoped peer verdict přijímá
technický recovery přírůstek na uvedeném pinu; není review vlastního workspace,
nativní použitelnostní akceptace, nový člověk ani fyzický proof.
### DATA01 — integrace nového názvu a přesné roviny otvoru

Společný frontend/recovery kandidát `bea8020` přidal `selection_name`; jeho
rozepsaný text v čistém uloženém modelu dosavadní numeric-only capture nechránil.
Nezávisle potvrdil identity reviewer a core9 peer; vlastní reprodukce mají
[2 FAIL](../p2/implementation/evidence/data01-inline-name-bea8020-original-fail.xml).
Core9 současně doložil neserializovatelný SketchPlane rozpracovaného otvoru;
vlastní XZ/custom-plane reprodukce mají
[2 FAIL](../p2/implementation/evidence/data01-hole-plane-9f8ed54-original-fail.xml).

Opravy `9f8ed54` a finální CODE `07025ed282b187c6454a8ae08abeb626c4833217`
mění pouze recovery adapter, bez zásahu do Window/controlleru: raw název
včetně prázdného je oddělený od posledního platného názvu a vázaný na přesnou
vybranou plochu; časovač jej nepotvrzuje. Rovinu otvoru zapisuje jako origin/u/v,
ověří její platnost a přesnou shodu s profilem vlastníka a obnoví ji bez volby
náhradní roviny. Actual hole action → QTest body → restore → další body/Enter
vytvořilo otvor v přesně stejné XZ i vlastní posunuté rovině. Odlišná platná
rovina, vadné osy a cizí platný vlastník raw názvu se odmítnou před výměnou práce.

Připnutý in-process source/blob/import-bound běh na `07025ed`:
**106 PASS / 0 FAIL/ERROR/SKIP, 31,08 s** (43 recovery + 63 existujících
controller/workspace/curve/profile/segmentation/problems regresí).
[JUnit](../p2/implementation/evidence/data01-07025ed-regression.xml),
[raw](../p2/implementation/evidence/data01-07025ed-regression.log),
[binding](../p2/implementation/evidence/data01-07025ed-regression-binding.json).
Ruff/diff check PASS. Core9 neautor samostatně oznámil 48 PASS na tomto CODE
(43 původních + 5 vlastních); jeho připnutý review report přebírá integrátor.
Autor nepřiděluje vlastní feature schválení. Společný native GUI průchod ještě
PENDING; původní meze DATA01 a NOT_RUN člověka/P3 zůstávají platné.
### Nezávislý skutečný průchod workspace + recovery, 17. 11. 2026

Verdikt pro runtime `d94f9b329c1e1e73241e8b66b76924a72bfac214`:
**CHANGES_REQUIRED pro UI; DATA01 APPROVED v níže ověřeném rozsahu.**
Neautorský expert použil skutečnou Windows aplikaci 1366 × 768, DPR 1,
Qt widget input s ověřenou Win32 aktivací vlastního PID/HWND a skutečné
nativní filepickery. Není to naivní objevování ovládání ani nový člověk;
AC-US08 zůstává NOT_RUN. Zdroje a přenosné pracovní vzory jsou v předchozím
[doplňku USABILITY_TEST](../p2/v1.2/USABILITY_TEST.md).

Od prázdného projektu vznikly pouze UI čtyři pojmenované obdélníky,
stěna připojená nakreslenou vnitřní čarou k podložce a trojúhelníková
chlopeň 4 mm. Dva listy A4 byly rozmístěny ručně, stěna otočena o 15°
a oba skutečné domain locks zaškrtnuty TRUE. Zpět/Znovu vrátilo/obnovilo
posun 40→45 mm. Záporná kotva vyvolala viditelný přesah listu; oprava
ve stejném UI chybu odstranila. Primární UNPLACED přechod při prvním
i opakovaném vstupu rámoval současně díl i A4; všechny čtyři členy skupiny
šlo projít bez automatického umístění. Primární review varování odkrylo
jeho text a explicitní přijetí; acknowledgement zůstal prázdný do vlastního
kliknutí. Nejde o fyzické ověření papíru.

[Editovatelný vlastní model](../p2/implementation/evidence/workspace-recovery-native/own-four-part-model.apcraft),
[obnovená samostatná kopie](../p2/implementation/evidence/workspace-recovery-native/recovered-four-part-model.apcraft)
a [skutečné SVG/PDF](../p2/implementation/evidence/workspace-recovery-native/export/)
vznikly nativním Save/Open/Export. Po New byl model skutečně prázdný;
settled reopen zachoval celý slovník projektu včetně identit a obou locks.
Nezávislé čtení SVG cest a rozbalených PDF CUT tokenů dává shodně
300 + 600 + 2520 + 7000 = **10420 mm²**, dva A4 a společný SVG snapshot digest.
[Read-only aritmetika a vazba všech src/tools bytes](../p2/implementation/evidence/workspace-recovery-native/verify_outputs.py)
prošla proti přesnému d94; [výsledek](../p2/implementation/evidence/workspace-recovery-native/results.json)
uvádí také skutečné importy a dva PID 19920/26744. Harness byl před spuštěním
zmrazen na `57efd391e5be1c625e9e7b68b1c2a54a8aec2910`.

Skutečný 30s autosave timer zachytil nepotvrzený text „Rozepsana Stena“
v čistém uloženém projektu. Až po jeho zápisu se proces ukončil `os._exit(23)`;
checkpoint nebyl vynucen testem. Nový proces nabídl Obnovit kopii, obnovil
přesný raw vstup vlastníka a kompletní dokument jako dirty kopii bez file_path.
Po vědomém vrácení rozepsaného textu na původní „Stena“ uživatel uložil novou
kopii. Původní soubor, dokument v konceptu, reopen i nová kopie se shodují.
Raw obnova je vidět na [snímku](../p2/implementation/evidence/workspace-recovery-native/16-recovered-pending-name.png).
Původní neúspěch inline-name na bea je zachován; [stejná nezávislá reprodukce po opravě](../p2/implementation/evidence/data01-inline-name-independent-after.json)
prošla. Čtyři vlastní negativy na d94 **4 PASS / 1,09 s** pokrývají živé
dvě leases, neplatný výběr před replace, neúspěšný periodic os.replace
se zachováním posledních bytes/origin/history a corrupt/foreign ochranu;
[JUnit](../p2/implementation/evidence/workspace-recovery-native/independent-recovery.xml),
[skutečné importy uvnitř pytest procesu](../p2/implementation/evidence/workspace-recovery-native/independent-recovery-binding.json).
Původní peer očekávání otvorů a raw názvů zůstávají samostatným doplňujícím důkazem.
Mez: nezahrnuje nepotvrzené ovladače samostatných preview dialogů ani výkon
neomezeně velkých projektů.

Konkrétní přetrvávající UI nálezy pro opravu a nový nezávislý replay:

- Vlastní název „Stena“ se na papíře/problémech/SVG/PDF mění na „P2 · Plocha 2“.
  Technický provázaný výběr funguje, ale začátečník musí znovu párovat jména.
  U jednoznačné samostatné plochy má automatické part jméno následovat název;
  explicitní odlišný název a mixed-part musí zůstat zachovány.
- **Vše** po reopen a návratu do Modelování stále ořízne spodní část modelu:
  [přímý důkaz](../p2/implementation/evidence/workspace-recovery-native/13-Modelovani-fit-all.png).
  Vybraná stěna po **Výběr** je celá; okolí smí být oříznuté.
  Rozměrnější viewport sám tento problém neřeší.
- Sbalený „Profil a křivky“ současně ukazuje své rozsáhlé potomky a zatěžuje
  prostou stěnu. Jde o skutečnou nefunkční skupinu, nikoli potřebu dalšího tipu.

Tyto body brání schválení celého základního UI cíle d94; technicky úspěšný
výstup je nezakrývá. Po opravě je nutný pinned replay. Snímky
[Modelování](../p2/implementation/evidence/workspace-recovery-native/02-Modelovani-four-parts.png),
[Spoje](../p2/implementation/evidence/workspace-recovery-native/05-Spoje-tab.png),
[Stránky s cílem](../p2/implementation/evidence/workspace-recovery-native/03-Stranky-primary-part-and-page.png),
[Export po Vše](../p2/implementation/evidence/workspace-recovery-native/10-Export-all-two-A4.png)
a úplný [raw log](../p2/implementation/evidence/workspace-recovery-native/events.jsonl)
zachovávají i chyby automatizačního selectoru/modal timing; ty nejsou označeny
za produktové chyby. Žádná doménová/JSON injekce modelu, packing ani interní
UUID jako povinná znalost uživatele nebyly použity. Desktop byl po ukončení
vlastního procesu vrácen rootu.
