# PC-007A — nezávislá revize přesných nativních příkazů a oddělení materiálu

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; autor matematické komponenty je jiný agent. Přesný revidovaný pin **`4c0194feab7cc49e6fd2ac91b7ae210694a28ce7`**, změny `3136efb` a `4c0194f` v `authoring/curve_topology.py` a jeho testech nad dříve posouzeným `ded92ec`.

**Verdikt: APPROVED_IN_EXACT_NATIVE_COMMAND_TOPOLOGY_AND_SEPARATION_COMPONENT_SCOPE.** V deklarovaném konzervativním rozsahu nebyl nalezen blocker ani major. Toto je schválení čisté matematické komponenty přijímající přesně dodané příkazy; není to schválení čteček skutečného SVG/PDF, aplikovaných transformací, celého exportního balíku, UI, PC-007A nebo P2.

## Co bylo ověřeno

Nový vstup `certify_native_region_topology` zpracuje absolutní M/L/C/A/Z záznamy bez převodu přes `Curve`, přepočtu nominálního středu nebo zpětné serializace. Decimal a řetězce zachovávají skutečné racionální hodnoty; float zachová přesnou dodanou binární hodnotu. Zavírací Z vytváří skutečnou implicitní přímou hranu, nulové L jsou prázdná operace. Vstup je jedna výslovně uzavřená podcesta na smyčku; nepodporované elipsy/major arcs/rotace či neúplná data bezpečně vracejí UNRESOLVED.

Racionální kubické kontrolní body a kladné intervalové homogeneous kontroly skutečných minor kruhových A navazují na již přezkoušenou reprezentaci `ded92ec`. Rozhodnutí stojí na celých konvexních obalech/intervalech, nikoli na konečném souboru vzorků. Winding je dovoleno spočítat na chordech až po důkazu, že homotopie celých intervalů query bod nezasáhne. Report výslovně uvádí `EXACTLY_SUPPLIED_NATIVE_PATH_GEOMETRY` a přesný native-command vstup.

Nový vstup `certify_native_region_separation` nejdřív vyžaduje platnou topologii obou samostatných materiálových oblastí včetně otvorů. Používá jediný společný konečný rozpočet, který se během kroků neobnovuje. Potom rozlišuje:

- **OVERLAP:** prokázaný skutečný průchod vnitřky materiálových hranic, přísné materiálové containment při již oddělených hranicích, nebo ověřený bod ve společném otevřeném materiálovém vnitřku.
- **DISJOINT:** oddělené všechny hranice a symetrické materiálové winding ověření, že materiál jednoho není uvnitř druhého. Otvor je prázdný prostor a nesmí vyvolat falešný overlap.
- **UNRESOLVED:** nedoložený kontakt, unsupported případ, neplatný vstupní region nebo vyčerpaný rozpočet. Dotyk nebo překrytá hraniční čára samy nejsou důkazem kladné společné plochy.

Pro tvrdé tvrzení o průchodu úseček jsou parametry v přísných vnitřcích; Bernsteinův sign-change witness musí ležet přísně uvnitř konečné přijímací úsečky. Intervalový circle-line root vyžaduje kladný diskriminant a přísnou vnitřní polohu; circle-circle root vyžaduje doložené netečné dva průsečíky a vnitřek obou skutečných arc úseků. Předchozí endpoint-only dotyk proto není automaticky povýšen na plochu. U platných Jordanových materiálových hranic takový skutečný průchod zakládá otevřenou společnou oblast i při hole hranici.

Mřížka devíti kandidátů v `_strict_common_interior` je pouze hledání pozitivního svědka. Každý nalezený bod musí projít certifikovaným materiálovým winding v obou regionech. Nenalezený bod nedává důkaz prázdného průniku; výsledek zůstává UNRESOLVED. Ani malé vzorkované maximum není v tomto kódu použito jako globální DISJOINT důkaz.

## Izolované ověření a vlastní orákula

Všechny rozhodné běhy použily **přesný Git archive** aplikace, testů a pyproject na revidovaném pinu. Fresh subprocess měl PYTHONPATH i pytest config výslovně na této kopii. Souběžné živé worktrees nejsou vydávány za připnutý zdroj.

[Runner](evidence/pc007a-native-output-topology-review-archive.py), [raw výstup, source pin a SHA256 archivu](evidence/pc007a-native-output-topology-review-archive-4c0194f.json):

```powershell
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe docs/p2/implementation/evidence/pc007a-native-output-topology-review-archive.py 4c0194feab7cc49e6fd2ac91b7ae210694a28ce7
```

- Původní topology + curves: **86 PASS / 2,54 s**, [JUnit](evidence/pc007a-native-output-topology-review-original-4c0194f.xml).
- Vlastní analytické/negativní případy: **21 PASS / 0,60 s**, [zdroj](evidence/pc007a-native-output-topology-review-own.py), [JUnit](evidence/pc007a-native-output-topology-review-own-4c0194f.xml).

Vlastní tvrzení vycházejí z předem určených osově orientovaných obdélníků, jejich přesných otvorů a známých kruhových oblastí. Neodvozují expected stejným produkčním helperem. Zahrnují:

- skrytý racionální cubic crossing o velikosti `1e-150` u souřadnice 1 i po posunu o milion, který by float roundtrip vymazal; witness uchovává opačná znaménka jako přesné racionální texty;
- Decimal/string/Fraction směsi v topologii a winding otvoru, bez záměny orientace za materiál;
- oddělený materiál uvnitř cizího otvoru v obou směrech, skutečný materiál uvnitř okraje prstence a dvě vnořené prstencové oblasti;
- přidání vzdáleného otvoru, které nesmí smazat jinou již prokázanou kolizi;
- kladnou mezeru i kladný překryvový proužek o velikosti `1e-40`: mezera se nestane OVERLAP a proužek se nestane DISJOINT; nedoložená podlimitní varianta smí zůstat UNRESOLVED;
- čistý dotyk hranou a rohem, který nesmí být označen za kladnou plochu;
- skutečný kruhový overlap a disjoint, kruhový díl uvnitř kruhového otvoru;
- neplatnou nebo neuzavřenou vstupní oblast, implicitní Z crossing, nepodporovanou elipsu a tři malé globální rozpočty.

## Uplatnění skills a integrační meze

Před revizí skutečně načteny **Papercraft konstrukce** a **Ověřování geometrie a výroby**. Konstrukční hledisko vyžaduje materiál s odečtenými otvory a skutečnou lepicí/společnou plochu; hraniční dotyk není plocha. Verification hledisko vedlo k přesnému archivnímu zdroji, racionálnímu sub-float protikladu, oddělení pozitivního svědka od důkazu absence a ověření, že další neznámá/vzdálená struktura nemaže jistý negativní výsledek.

Schválená API kontrolují právě dodané příkazy. Neprokazují, že nějaký externí SVG/PDF reader tyto příkazy načetl správně, zahrnul všechny podcesty, zachoval desetinné souřadnice, správně složil transformace a jednotky, vybral skutečné CUT/material role nebo odeslal kompletní díly včetně chlopní. Takové vazby musí přezkoušet integrační owner na konkrétním výstupu a pinu. Pokud publisher pouze předá dřívější zdrojový surrogate, tento komponentový verdikt na skutečné výstupy neplatí.

Native topology ani separation nejsou důkaz developability, numerické délky, kvality lepicí plochy po ohnutí nebo fyzické sestavitelnosti. Žádné změny normativních AC ani tolerancí, nové produktové přijetí, nativní UI/editor průchod, novice test či fyzické P3 touto revizí neproběhly. Produkci reviewer neměnil.
