# AU13 — měřené dělení křivek

## Aktuální komponentové předání nad skutečným schema9 jádrem

**Source freeze `7ef51beddeb86b1ba5d31be8277803458bd4a9fb`**, vlastní UI příprava `411d137f54187e1ff5bd9d53ee8449f949e42ce6` a připnuté jádro `4f43a6427c7fbd25a87309ab31ad676ddd7794e1` / jeho evidence `7c61c7ee54233dc662420b5199e3a5d914da4441`, integrováno bez konfliktu commitem `95a1f1f`. Samostatná větev `revival/p2-curved-profile-ui`; produkční doménu/schema/exporter autor UI neměnil. Jejich nezávislé review má samostatný rozsah.

[Závěrečný připnutý JUnit](evidence/pc008-curved-subdivision-ui-core9-final.xml): **111 PASS / 0 SKIP / 138,41 s**. Jde o 18 vlastních AU13 UI případů (7 skutečných core průchodů a 11 UI negativů/context), 59 existujících C/LINE/curve/loft/segmentation workspace regresí a 34 doménových provenance regresí. [Source/import/hash vazba a reprodukční příkaz](evidence/pc008-curved-subdivision-ui-core9-binding.json) patří tomuto konkrétnímu zdroji, běh má vlastní `PYTHONPATH` a `QT_QPA_PLATFORM=offscreen`. Ruff a diff-check PASS. Počty se nesčítají s překrývajícími předchozími běhy.

Čtyři původně čekající skutečné průchody nyní proběhly: oba typy ARC/CUBIC používají skutečnou délku a inverzi vzdálenosti přes public API, a oba projdou hlavním dialogem → jediný controller Undo/Redo → výslovný přepočet → zachovaný rámec, ruční rozmístění a zámky → save/open → inverzní merge. Analytické orákulum kubiky zůstává nezávislým integrálem rychlosti `L(t)=8t³−12t²+12t`; podíl vzdálenost/celková délka by dal chybný parametr. Skutečný Cancel běžícího nového náhledu prošel pro oba typy. Nesousední potomci stejné historie se odmítnou v UI bez fitu, změny dokumentu či povoleného potvrzení.

Těchto sedm skutečných public-core případů nepoužívá dependency callback. Ostatních 11 vlastních případů cíleně zkouší scheduler, vadnou odpověď, typed chybu a C05/kontext; callbacky u těchto negativů nepředstírají úspěšné dělení. Potvrzení náhledu skutečného core také ponechává původní živý dokument beze změny, dokud hlavní controller příkaz opravdu neprovede.

První [actual běh 3 PASS / 1 FAIL](evidence/pc008-curved-subdivision-ui-core9-first.xml) měl chybu harnessu: desetinná tečka v česky lokalizovaném spinboxu znamenala jiný vstup než zamýšlených 10,471976. Test nyní píše číslo přes konkrétní `QLocale`. [Další 14 PASS / 1 FAIL](evidence/pc008-curved-subdivision-ui-core9-run02.xml) zachytil další chybu harnessu, celočíselný argument nesprávného overloadu PySide `toString`; opraven explicitním float argumentem. Obě raw zůstávají zachované a nejsou nálezem produktu. [Opravený průběžný běh](evidence/pc008-curved-subdivision-ui-core9-run03.xml) má 15 PASS před doplněním dalších tří skutečných Cancel/invalid-merge případů.

Nezávislé review tohoto UI source je **PENDING**. Důkaz je offscreen widget/controller komponenta, nikoli rootův celý nativní AU13 průchod od vlastního kreslení přes export a editor. Dokumentové a nativní důkazy C8 se tím zpětně nepřeznačují na C9. AC-US08 nový uživatel **0 / NOT_RUN**, fyzické P3 **NOT_RUN**. Následující WIP stav je výslovně historický.

## Historický checkpoint před integrací nového jádra

**WIP_SOURCE: `411d137f54187e1ff5bd9d53ee8449f949e42ce6`** ve větvi `revival/p2-curved-profile-ui`, WT `papercraft-curved-profile-ui`, základ `8f1ec6382d527c719133958e7eb6f78a724ef5d5` (C+LINE/schema8). Toto není hotový ani nezávisle schválený křivkový balík. Doménový schema9 runtime není v tomto checkpointu integrován.

## Připravené ovládání

Výběr úseku nabídne dělení pro skutečné LINE/ARC/CUBIC; autor zadává vzdálenost **po obrysu**, nikoli procento parametru nebo podíl tětivy. Křivkový dialog volá pouze veřejná `profile_segment_length` a `profile_segment_parameter_at_length`, potom skutečný split/merge a přepočet na odděleném projektu workeru. Mez chyby vzdálenosti je nejvýše 0,001 paper mm převedená jednou přes měřítko; nepřidává se epsilon. Počáteční půlka délky se zaokrouhlí na zobrazitelné jednotky ještě před inverzním měřením. LINE zachovává původní přímý průchod.

Náhled používá skutečné nativní úsečky, oblouky a kubiky, začátek měření a nový bod; rozměry ukazují doložené meze délky a u oblouku poloměr. Zobrazení není geometrický certifikát. Potvrzení zapisuje pouze autorský parametr příkazem hlavního controlleru; preview projekt ani cache se do dokumentu nepřenášejí. Rozvin vyžaduje výslovný přepočet, změna má zůstat jedním Undo.

Výpočet křivek používá oddělený snapshot, jeden aktivní a nejvýše jeden poslední čekající požadavek. Zdroj, rozepsaný vstup, nové zadání, Cancel nebo zavření zneplatní starý výsledek. Zrušení nečeká na worker. Chyba výpočtu zůstává opravovatelná číslem či volbou jiného úseku.

Přepnutí zdrojového úseku nejprve vyhodnotí viditelný pending numeric input (C05). Odmítnutí vrátí také viditelnou volbu; přijetí zachová požadovaný nový úsek i po refreshi a podvýběr se převede na jeho začátek. Vlastní regrese odhalila, že Qt `findData` nemusí po obnově seznamu ztotožnit obsahově stejnou novou Python tuple; výběr proto vyhledáváme hodnotovou shodou. Nejde o vizuální redesign ani změnu geometrického kontraktu.

## Ověření a pokračování

[Připnutý WIP JUnit](evidence/pc008-curved-subdivision-ui-wip.xml): **70 PASS / 4 deselected / 52,33 s**, offscreen s vlastním `PYTHONPATH`; [source/import vazba](evidence/pc008-curved-subdivision-ui-wip-binding.json). Zahrnuje 11 nových UI negativních/context případů a 59 existujících C/LINE/curve/loft/segmentation workspace regresí. Ruff a diff-check PASS. Žádná z těchto 70 zkoušek nedokazuje nové křivkové split/merge na skutečném schema9 jádře.

Čtyři připravené skutečné pozitivní případy **PENDING / nezahrnuty do WIP běhu**: měřený ARC a CUBIC split přes public core, a oba typy přes hlavní dialog → jeden Undo/Redo → přepočet → zachovaný rámec/layout/zámky → save/open → inverzní merge. Po integraci připnutého doménového runtime musí opravdu projít; callback je nenahrazuje. Kubický orákulum nezávisle integruje rychlost konkrétního zdroje jako `L(t)=8t³−12t²+12t`, takže záměna délky za parametr neprojde.

Dosavadní nové negativní komponenty používají výslovné dependency callbacky pro scheduler, chybné odpovědi a typed UNRESOLVED; **nejsou důkazem úspěšného křivkového dělení**. Pokrývají responsivitu event loopu, rychlý Cancel/late discard, latest-only queue, změnu zdroje, raw invalid číslo/focus-out, vadný packet, C05 rollback a platný pending vstup při změně kontextu. Existující C/LINE/curve/loft/segmentation workspace testy zůstávají regresní kontrolou starého runtime.

Předchozí [69 PASS / 4 deselected / 51,90 s](evidence/pc008-curved-subdivision-ui-before-core.xml) je průběžný nepřipnutý běh před doplněním valid-context regrese a její opravou; nedokazuje finální WIP source.

Skills: konstrukce — zachování skutečného obrysu a původního zdroje místo nového fitu; UI — měřené jednotky, viditelný bod, C05 a SK013 přímo v příkazu; verification — nezávislé analytické očekávání a oddělení callback/native/novice důkazu; delivery — izolace, WIP source freeze a návrat k pozitivům po doménovém pinu. Otevřené pozitivy ani integrace se neoznačují PASS. Nativní Windows/editor ověření patří rootovi; AC-US08 nový uživatel **0 / NOT_RUN**, fyzické P3 **NOT_RUN**.

## Nezávislá komponentová revize 17. 11. 2026

Reviewer `editor_review`, jiný agent než autor UI. Posouzeny změny
`411d137f54187e1ff5bd9d53ee8449f949e42ce6` + `7ef51beddeb86b1ba5d31be8277803458bd4a9fb`
v `author_subdivision.py`, `author_window.py` a příslušných testech proti
`8f1ec6382d527c719133958e7eb6f78a724ef5d5`. Ověřený snapshot
`1b8037a6266dcd5d849bbddf0044b8ee8d4bb963` je bezkonfliktní merge UI předání
`406fa6f` a core R01 předání `6064f222`; nejde o finální root integrační pin.
[Importy a SHA-256 skutečných zdrojů](evidence/curved-ui-review-20261117-binding.json)
ukazují vlastní izolovaný worktree mimo `projects`, explicitní `PYTHONPATH`
a Qt offscreen. Reviewer produkci, queue ani skills neměnil.

**APPROVED_IN_CURVED_SUBDIVISION_UI_COMPONENT_SCOPE, 0 otevřených nálezů v tomto rozsahu.**
Čtením zdroje ověřeno oddělení worker snapshotu od živého dokumentu, token a
fingerprint při publikaci i host apply, jediný aktivní a poslední pending request,
invalidace při rozepsaném textu, Cancel/close bez čekání na výpočet a zachování
jediného controller příkazu. Akce vychází ze skutečné LINE/ARC/CUBIC volby;
odmítnutý pending vstup vrací viditelný kontext a neschovává chybný text.

- Původních 18 curved-subdivision případů: **18 PASS / 16,71 s**,
  [JUnit](evidence/curved-ui-review-20261117-baseline.xml). Zahrnují skutečný
  public core, měřený ARC/CUBIC parametr, inverse merge, Undo/Redo, přepočet,
  frame/layout/oba locks, save/open, C05 i vadné odpovědi.
- Relevantní předchozí LINE/C/curve/loft/segmentation workspace regrese:
  **59 PASS / 50,21 s**, [JUnit](evidence/curved-ui-review-20261117-regressions.xml).
- Vlastních 7 skutečných public-core/UI případů: **7 PASS / 8,49 s**,
  [testy](../../../tests/authoring/test_curved_subdivision_review.py),
  [JUnit](evidence/curved-ui-review-20261117-own-formatted.xml). Řízené zdržení
  stále volá původní `_curve_preview`, nenahrazuje solver packetem: ARC i CUBIC
  zahodí počáteční a prostřední request při zadání 3→7 mm a Accept před dokončením;
  analytický oracle ověří skutečně potvrzených 7 mm. Oba typy zachovají GUI
  heartbeat, Cancel a dokument přes pozdní skutečný výsledek. Neplatné rozepsané
  číslo po platném náhledu nic nepotvrdí. Skutečné kreslicí circle UI rozdělí
  druhý ARC a ponechá nový vertex ve výběru i viditelných vlastnostech.
- Ruff vlastních testů a `git diff --check` PASS. Běhy se nepřičítají k historickým
  111 ani k jiným překrývajícím se sadám.

Skills se uplatnily konkrétně: konstrukce — měření po původním analytickém zdroji;
UI — pending input, viditelný výběr a bezpečný Cancel; verification — skutečný
solver pod řízeným zpožděním a nezávislá kubická délka; delivery — přesný snapshot
a omezený verdikt jiného agenta. Toto potvrzuje technické komponenty příkazu,
nikoli osvojitelnost začátečníkem. Finální integrovaný commit, nativní Windows
ARC/CUBIC workflow přes export, nový uživatel AC-US08 a fyzické P3 nejsou tímto
review schváleny a vyžadují vlastní důkazy.
