# ArchPapercraft Studio — epiky a produktová roadmapa

Verze 1.0 · Všechny epiky patří do cílové vize. Stav při přípravě: PLANNED, nikoli implementováno nebo přijato. První mandát je P0/P1. Odhady vzniknou až z discovery.

## Etapy a závislosti

| Etapa | Ucelený výsledek | Epiky / podmínky |
|---|---|---|
| P0 | Clone do otevřeného VS Code rootu, runtime baseline a reprodukce vad | E01, diagnostické části E02–E08 |
| P1 | Rozhodnutí o obnově, UX a připravený P2 kontrakt | E01, návrhy všech epic, nezávislé review, přijetí PO |
| P2 | Domeček se skutečnou 3D/2D editací, ručními spoji a stránkami, SVG/PDF | Základ E02–E09, E12, E13; fyzický proof čeká P3 |
| P3 | Výtisk a sestavení; odstranění praktických vad první verze | E14 a opravy souvisejících epic, PO fyzické přijetí |
| P4 | Stabilní autorský editor a výrobní komfort | Rozšíření E03–E09, E12, E13, materiál E06 |
| P5 | Architektonické detaily a ověřené rotační tvary | E10, E11, související materiálové kontroly |
| P6 | Výtvarná a návodová nadstavba | E15, E16; závislé na stabilní identitě a konstrukci |

Uvnitř etapy dodávej vertikální řezy. E12 a E13 nejsou práce odložená celá na konec: jejich minimum je nutné už v P2. P4 zlepšuje editor, ale neodkládá základní ovladatelnost P2. Fyzické čekání nesmí být zaměněno za dokončení P3; lze mezitím nezávisle připravovat návrhy P4/P5.

**Závislosti níže znamenají potřebné capability konkrétního řezu, nikoli dokončení celého epiku.** E05 potřebuje jen základní jednotkový/materiálový kontrakt E06, ne jeho pozdější kompenzace. Pokročilé E06 naopak používá již existující spoje E05. E14 je průběžná verifikace a fyzický výstup řezu, nikoli vstupní požadavek na hotový celý E14 před začátkem implementace. V queue musí být konkrétní acyklický ticket DAG, ne cyklus celých epic.

## E01 — Obnova, diagnostika a ADLC

**Přínos:** vědět, co skutečně funguje, a řídit další práci nad jedinou evidencí.

IN: bezpečný bootstrap do otevřeného workspace, runtime/test baseline, analytické experimenty, keep/fix/replace mapa, architektonické rozhodnutí, UX, backlog a evidence. OUT: univerzální orchestrátor, automatický rewrite, produkční P2 před přijetím kontraktu.

AC: kořen Git je otevřený adresář; žádná data vlastníka nepřepsána; každý statický nález má reprodukci nebo pravdivé NOT_VERIFIED; plán rozlišuje core/GUI/Windows/externí editor/fyzickou stavbu; celý balík má nezávislé review. Závislosti: žádné.

## E02 — Konstrukční model a geometrický základ

**Přínos:** rozměry a spoje jsou správné a model má stejný význam ve 3D i na papíře.

P2 IN: panelové těleso jednoduchého domečku, sedlová střecha, významové plochy, hrany, přehyby a spoje, jednotky, měřítko, konečné validované parametry. Později: obecnější architektonické konstrukce. OUT P2: univerzální CSG/CAD, volný mesh editor a obecný import.

AC: známé rozměry referenčního domu sedí; vnitřní triangulace netvoří řez; transformace včetně rodičů odpovídají exportu; chybná/degenerovaná geometrie končí konkrétní validací; nepodporované CSG nedává úspěch; core se testuje bez Qt. Závislost: E01 rozhodnutí. Důkazy: analytická geometrie a metamorfní transformace, AC-G01–G05.

## E03 — Propojené 3D a 2D pracovní prostředí

**Přínos:** autor rozumí vztahu konstrukce a dílů bez hledání podle indexů.

P2 IN: orbit/pan/zoom/focus, výběr kliknutím ve 3D i 2D, společné zvýraznění, strom, číselná editace rozměrů a umístění, přední/zadní strana a směry přehybů. Později: více pohledů, dočasné barvy dílů, izolace, měření, gizma a výběr více prvků, kde mají užitek.

AC: výběr dílu funguje oběma směry; part tvořený více povrchy zvýrazní správnou množinu; výběr spoje ukáže oba protikusy a jejich stránky; skrytý/uzamčený objekt má konzistentní chování; chybějící protikus má vysvětlení; kontext výběru přežije změnu režimu. Reálný desktop proof. Závislosti: E02 a identita E12.

## E04 — Autorské švy, rozvin a dělení dílů

**Přínos:** autor zvolí viditelnost spojů, velikost dílů a obtížnost sestavení.

P2 IN: ruční označení způsobilé hrany jako cut/fold, omezený split/join sousedních rovinných panelů, přepočet a validace, undo. P1 přesně určí podporovanou topologii; UI ostatní případy vysvětlí. Později: malování švů, zámky, automatické návrhy podle architektury/velikosti, složitější díly s dírami.

AC: automatika nepřepíše ručně zamčený šev; split/join zachová pokrytí povrchů a aktualizuje původ/ID; hrany mají platné protikusy a orientaci; překryv nebo nemožné uzavření nezíská nálepku přesného rozvinu; nepodporovaný merge je odmítnut bez částečné změny. Závislost: E02/E12; důkazy AC-G a AC-C.

## E05 — Spoje, chlopně a lepicí pásky

**Přínos:** každý spoj má vhodnou konstrukci a dá se k němu při stavbě dostat.

P2 IN: generovaná zkosená chlopeň, ruční změna šířky/tvaru v podporovaném rozsahu, přesun na protikus, vypnutí, párování hran. Později: rovné/zubaté chlopně, relief cuts, samostatné lepicí pásky, značky lepení bez chlopní, lepený/volný/nasazovací spoj, odnímatelná střecha.

AC: chlopeň leží vně správného obrysu; přesun odstraní původní a vytvoří novou atomicky; nikdy tichá dvojitá chlopeň na stejném spoji; nezpůsobilá hrana nabídne důvod; rozměr se ukládá v definovaných paper mm; kolize chlopně je viditelná před exportem. Samostatný pásek má vlastní part ID a odkazy na spoj. Závislosti: E04/E06/E12.

## E06 — Papír, tolerance a vyrobitelnost

**Přínos:** model respektuje fyzický materiál a míru detailu.

P2 minimum: upozornění na příliš malé detaily/chlopně a oddělení model scale od fyzických tiskových rozměrů. P4/P5 IN: tloušťka odděleně od gramáže, materiálové profily, směr vláken, konstrukční vůle, vybrané kompenzace tloušťky, křehké můstky, návrhy výztuh. OUT: univerzální fyzikální simulace a zaručená přesnost každé tiskárny.

AC: gramáž neurčuje bez explicitního profilu jedinou tloušťku; každá kompenzace má definovaný spoj, analytické očekávání a fyzické ověření; změna materiálu nezničí ruční chlopně, ale označí dopad; směr vláken omezuje automatiku dle nastavení, ruční porušení vysvětlí. Readiness procento nenahrazuje seznam konkrétních problémů. Závislosti: E02/E05/E14.

## E07 — Ruční stránky a rozmístění

**Přínos:** tvůrce řídí vzhled a výrobní organizaci vystřihovánky.

P2 IN: A4, více stránek, odkládací plocha, přesun/rotace dílů myší i číselně, přesun mezi stránkami, přidání/odebrání stránky, základní snap/zarovnání, zámky, undo/save/reopen. Automatika není podmínka ruční editace. P4: A3/Letter/custom, multi-select, hromadné přesuny, skupiny podsestav, samostatné zámky pozice/rotace, rezervované oblasti pro text/legendu a přehled materiálů. Pokud plné nezávislé zámky nebudou už P2, jejich minimum a vývoj musí být výslovné v kontraktu.

AC: smazání neprázdné stránky neztratí díly, vrátí je na odkládací plochu nebo vyžádá konkrétní přesun; export neobsahuje neumístěné díly bez explicitního označení částečného výstupu; přesun zamčeného dílu nemění nic; save/reopen zachová transformace a pořadí stránek; tiskové měřítko je nezávislé na zoomu. Závislosti: E02/E05/E12/E13.

## E08 — Volitelné automatické rozmístění a validace

**Přínos:** automatika šetří práci, autor si zachová kontrolu.

P2 minimum: kolize, přesahy tiskové oblasti, duplicity/missing placements a kontrola všech chlopní. Automatické rozmístění lze dodat později; pokud je dostupné, musí dodržet kontrakt. P4 IN: pouze vybrané/neumístěné díly, dodržení zámků a směru vláken, minimální mezera, náhled a potvrzení jako jediný undo příkaz. Později dlaždicový tisk.

AC: packing pracuje s kompletní obálkou; neexistující řešení nezmenší model; grafické pozadí není konstrukční kolize; autor může vědomě přijmout konkrétní fyzický překryv/overflow s důvodem pro daný snapshot; změna dotčených dílů invaliduje takové přijetí. Tiled print musí mít clipping, návaznost a kalibraci, jinak není podporovaný. Závislosti: E05/E07/E12.

Přijaté varování nepřebíjí integritu: mimo doporučený tiskový okraj uvnitř stránky je autorská volba s upozorněním; mimo fyzický formát nelze tvrdit kompletní tisknutelnost bez dlaždicování/jiného formátu. Rozbité odkazy nebo stale geometrie nejsou prominutelná varování. Detaily jsou v exportním kontraktu a AC-L10.

## E09 — Vektorové exporty a tisk

**Přínos:** přesný tisk a další úpravy v grafickém editoru.

P2 IN: SVG po stránkách, vektorové PDF, logické skupiny a stabilní ID, fyzické jednotky, české texty, kalibrační úsečka, exportní souhrn a známé fontové závislosti. P4: dávkový balík, barevná/pracovní/čistá varianta, exportní presety. Později DXF s výrobními vrstvami a PNG náhled.

AC: SVG lze otevřít a upravit v reálném grafickém editoru; PDF obsahuje vektorové cesty; fyzické rozměry a rozmístění SVG/PDF se shodují; export nereorganizuje stránky; neúspěch nezanechá falešně kompletní výstup; pracovní čísla lze skrýt bez skrytí konstrukce. DXF tolerance a jednotky se ověří před tvrzením podpory plotru. Závislosti: E07/E08/E12, AC-X.

## E10 — Architektura, knihovna a konstrukční detaily

**Přínos:** rychlá tvorba budov a jejich modelářských variant.

P5 IN: zdi, obdélníkové/obloukové/gotické otvory, ostění, rámy, základny, podlahy, výztuhy, věže a více střech. Okno může být potisk, řez, zapuštěné ostění nebo samostatný rám. Knihovna podporuje parametrické presety, vlastní prvky a opakování; změna instance nesmí bez příkazu změnit všechny ostatní.

AC: otvor je skutečná díra dle režimu, nikoli zobrazený cutter; vnější obrys i vnitřní otvor mají správný winding a triangulaci; opakovaný prvek má rozlišenou identitu instance; profil a rozměry odpovídají UI; výztuha patří k sestavě a má návodové reference. Závislosti: E02–E06/E12/E14; gotika před fyzickým proof není hotová pouze názvem presetu.

## E11 — Válce, kužely, báně a aproximace

**Přínos:** architektonické rotační tvary s pravdivě uvedenou přesností.

P5 IN po jednotlivých řezech: analytický válec, kužel/komolý kužel, ověřené pásy, facety a góry pro báně. Autor volí segmentaci a vidí kompromis detail/počet dílů/sestavitelnost. Zachovat původní profil, ne ho zbytečně odhadovat z již triangulovaného a transformovaného meshe.

AC: válec má správný obvod a výšku, kuželový pás je výseč se správnými oblouky a délkou tvořící; limit shodných poloměrů má stabilní válcovou větev; koule nemá označení přesný rozvin; aproximace reportuje definovanou chybu, ne libovolné procento; posun/rotace tělesa nemění jeho místní rozvin. Závislosti: E02/E04/E05/E06/E14, AC-R.

## E12 — Stabilní identita, revize a zachování autorské práce

**Přínos:** konstrukční úprava nezničí grafiku, rozvržení ani číslování bez upozornění.

P2 IN: stabilní element/surface/edge/part/page ID, revision a dependency invalidace, zachování nezměněných placements a explicitní stale stav. P4: přehled dopadů, split/merge lineage, porovnání verzí, jednoduché/detailní varianty a kontrola změn mezi exporty. Základní změna ID není migrační strategie.

AC: změna střechy nepřesune nedotčené stěny; změna počtu dílů nezpůsobí přiřazení staré grafiky jinému dílu podle indexu; starý export není prezentován jako aktuální; názvy/čísla lze měnit odděleně od identity; split/merge nejednoznačné reference vyžadují kontrolu. Závislost: E02, průřez všemi epiky.

## E13 — Projekty, undo/redo, recovery a použitelnost

**Přínos:** dlouhodobá bezpečná práce v offline desktopu.

P2 IN: nový/save/open, atomický zápis, validace schématu, undo/redo konstrukce i rozmístění, dirty/close, srozumitelné chyby a Windows proof. P4: autosave/recovery, pojmenované verze, sbalený projekt, klávesové zkratky, stav dlouhé operace a zrušení. Přístupnost: čitelnost při škálování Windows, stav nevyjádřený jen barvou, ovládání klíčových přesných funkcí klávesnicí.

AC: zrušení zavírání zachová práci; export neoznačí neuložený projekt jako uložený; pád během save ponechá poslední platnou verzi nebo prokazatelnou obnovu; neznámé schéma je odmítnuto bez přepsání; recovery nepřepíše originál bez rozhodnutí; input během dlouhé operace nezpůsobí aplikaci zastaralého výsledku. Závislosti: E01/E02/E12.

## E14 — Fyzické sestavení a průběžná kvalita

**Přínos:** software dodává skutečnou vystřihovánku.

IN od P2: nezávislá numerická orákula, geometrické invariance, exportní obsah, desktop průchody a review. P3: skutečný výtisk, kontrola pravítkem a sestavení domu. Opakovat pro každý nový konstrukční princip: okno/ostění, výztuha, kužel, báně. OUT: tvrzení, že screenshot nebo názor agenta nahrazuje fyzickou stavbu.

AC: evidence uvádí verzi projektu/exportu, papír a jeho tloušťku, nastavení tisku, naměřený rozměr a problémy stavby; zásadní změna geometrie invaliduje dotčený fyzický proof; uživatelské problémy se stanou konkrétními nálezy; reviewer potvrzuje konkrétní CODE SHA. Závislosti podle ověřovaného řezu.

## E15 — Grafická nadstavba a spolupráce s externím editorem

**Přínos:** autor vytvoří finální vzhled a navazující potisk.

P2 základ: oddělené konstrukční/výtvarné SVG skupiny. P6 IN: barvy, vzory, bitmapy, texty, grafika v souřadnicích dílu, náhled na 3D, návaznost přes švy, přesah potisku za řez a barevná/úsporná varianta. Později samostatně navržený round-trip externího SVG.

AC: grafická editace nemění konstrukční rozměry; textury/asset cesty se uloží přenositelně; vlastní assets nepřibývají duplicitně bez důvodu; potisk přes šev má náhled i kontrolní výtisk; změna konstrukce označí neplatné mapování. SVG round-trip musí mít whitelist podporovaných editací, validaci ID/revision a konfliktů; odmítnuté konstrukční zásahy nesmějí poškodit projekt. Závislosti: E09/E12/E13; round-trip není předpoklad P2.

## E16 — Podsestavy, obrazový návod a kontrola přístupu ke spojům

**Přínos:** tvůrce vysvětlí stavbu a zachytí špatné pořadí montáže.

P2 minimum: seznam dílů a párování spojů v pracovní dokumentaci/legendě. P6 IN: podsestavy, ruční kroky, uložené pohledy, šipky/zvýraznění, souvislý text, PDF návod, rozložený náhled a později animace. Označení „slepit před uzavřením“ může být zpočátku autorem zadaná závislost; nesmí se tvrdit automatické geometrické ověření dosažitelnosti, které neexistuje.

AC: krok odkazuje na existující díly a revision; změna dílu označí dotčený návod k revizi; automatický návrh pořadí může autor změnit; cyklické montážní závislosti mají vysvětlení; výběr spoje ukáže oba díly, stránky a krok. Pozdější automatická kontrola přístupu musí mít explicitní model nástroje/prostoru a samostatné ověření. Závislosti: E03/E05/E12/E15 podle grafiky.

## Úplnost původní vize

Sekční pohled a pokročilé měření patří do E03; knihovna, styly a opakování do E10; obecný mesh import až po E11 jako samostatný budoucí ticket; DXF a PNG do E09; dlaždice do E08; autosave, snapshoty a balík projektu do E13; materiály a směr vláken do E06; varianty a exportní diff do E12; grafický editor do E15; animace do E16. Agent nesmí nepodporované funkce prezentovat aktivním tlačítkem s prázdným handlerem nebo tichým fallbackem.
