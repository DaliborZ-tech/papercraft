# AU13 — měřené dělení křivek, rozpracovaná UI příprava

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
