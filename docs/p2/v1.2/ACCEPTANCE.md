# P2 v1.2 — přejímky autorské tvorby

Tyto nové přejímky rozšiřují `04_ACCEPTANCE_AND_VERIFICATION.md`. Původní jednotky, přesnost, 3D↔2D, změny, oba locks, dirty/save/undo, výstupy, skutečný editor a DPI zůstávají. Dům je regresní fixture. **Všechny nové produktové AC jsou NOT_RUN** do implementace a skutečných průchodů; matematický spike není UI proof. Rozhodný CODE SHA a typ důkazu musí být u každého PASS. Fyzický stav je samostatný P3.

## Společný end-to-end protokol

Každý podporovaný řez se provede v reálné aplikaci Windows z prázdného projektu: kreslení/editace → konstrukce a připojení → šev/chlopně → explicitní rozvin → ruční přesun/rotace mezi dvěma listy → uložit → zavřít → otevřít → SVG/PDF. Klikání nelze nahradit vložením připraveného JSON přes interní controller. Automatizace skutečných widgetů je přípustná, musí popsat, co stiskla. Souborový dialog a 3D/2D výběr ověřit skutečně. U pokusu, který selže, zůstane log a stav FAIL/BLOCKED, ne zmizelý záznam.

V balíku: zdrojový projekt, analytický oracle nezávislý na implementaci, snapshot, všechny SVG a PDF, SHA256, runtime/build/editor verze, screenshoty kroků, příkazy/test counts a seznam omezení. Zapsat, zda je rozvin EXACT nebo APPROXIMATE a jakou chybu reprezentuje. A/B/C se mají zachovat jako editovatelné projekty, nikoli exporty sestavené mimo aplikaci.

## A — ruční budova bez dna s přesahy a základnou

Bez tlačítka „hotový dům“. Autor nakreslí obdélníkové stěny a štíty, sestaví otevřený obal délky 10000, šířky 6000 a výšky stěn 4000mm, hřeben 7000mm. Při 1:100 numerický základ odpovídá starému domu; přidá však horizontální okapový přesah 500mm na obě strany a štítový přesah 400mm na obou koncích. Střecha má tedy délku 108mm a poloviční sklonovou délku `sqrt(35²+35²)=49.497474683mm` na papíře. Původní wall-top trace zůstane 5mm půdorysně / 7.071067812mm po ploše od okraje. Základna je samostatný obdélník 130×100 paper mm s vnitřní půdorysnou lepicí oblastí. Dno budovy se nevytváří. Přidá se vlastní výztuha s otvorem, jeden autorský lepicí pásek a samostatný spodní díl/podhled střechy pro ukázku printed side.

Povinně změnit jen jeden přesah, zachovat vnitřní připojovací stopu, uložit/otevřít a ověřit délky i umístění. Negativní případ: stopa nebo chlopeň míří mimo cílovou plochu či do otvoru → konkrétní chyba lepicí plochy, žádné oříznutí střechy. Samostatná otevřená stěna musí být validní. Původní povinný společný díl stěna–střecha má vlastní skutečný fold fixture bez přesahu: kotva [60,60], rotace30°, stránka2, oba locks, rise3000→3500, stale celého dílu a po přepočtu všechny body kořenové stěny beze změny. To není nahrazeno testem oddělených dílů nebo lepeným attachmentem A.

## B — ostění mezi dvěma různými obloukovými/gotickými profily

V UI nakreslit profil otvoru z úseček a dvou kruhových oblouků s ostrým gotickým vrcholem, vytvořit druhý **rozměrově jiný** profil v jiné rovině a zvolit korespondenci rohových bodů. Případ B1: druhý profil je homotetický faktor1.2 kolem stejné osy při nenulové hloubce; spikem doložená kuželová rodina po jednotlivých pravidelných intervalech může mít EXACT. Ověřit původní obloukové délky/rohy a hloubku, vrchol profilu se nevyhladí. Otvor ve stěně musí zůstat dírou v obou vektorových výstupech. Rozvin otvor nezalepí fan triangles.

Případ B2: profily ve stejné rovině → rovinný pás; obě hranice zůstávají vstupem, nevznikne falešný prostorový objem. Případ B3: druhý profil změněn nezávisle nebo otočen tak, že plocha není rozvinutelná → přesný režim se odmítne nebo zůstane UNRESOLVED; nabídne se segmentace s vyčíslením chyby podle D. Neomezovat editor jen na homotetická tlačítka: nezávislé kreslení druhého profilu a jeho validace patří do podporované práce. Samostatně nakreslit a upravit kubický Bézierův segment, extrudovat jej jako rozvinutelný pás a ověřit mez chyby numerické obloukové délky. Negativní korespondence křížících se generátorů, nulový poloměr, nulová plocha a záměna směru musí být vysvětlené bez částečné mutace.

## C — stočený plášť a dělené trojúhelníkové chlopně

V UI vlastní profil/parametry, nikoli pouze načtený hotový export: válec r=10, h=30 paper mm. Autor určí periodický šev, stranu potisku a 12 trojúhelníkových záložek podél kruhového okraje se zadanou roztečí/gap, jednu vypne, jinou ručně upraví. Přesný rozvin pláště má šířku `20π=62.8318530718mm` a výšku30mm. Každá chlopeň má vlastní ID a odkaz na příjemce; export nemá dvojité řezy v base hinge, spojovací šev se nezdvojí jako nadbytečný materiál. Samotný kruhový průběh záložek může mít segmentační odchylku; musí být doložena, ne označena jako přesný hladký lem.

Druhý případ: kuželový pás r1=10,r2=20,s=30mm: rozvin mezikruhová výseč R1=30,R2=60,úhel2π/3, oblouky20π a40π. Test válcového limitu r1≈r2 a změny směru. Příjemce je navržený samostatný díl s oblastí lepení. Ověřit skutečnou plochu záložky v regionu po ohnutí, kolizi sousedních záložek, mezeru pro ohyb a zásah do otvoru. Překryv záložek lze reprodukovat nevhodným počtem/šířkou; očekávání se nesmí odvozovat ze stejného generátoru.

## D — prokazatelně nerozvinutelná plocha

Vlastní dvojice profilů s nenulovým developability determinantem nebo kulový segment s nenulovou dvojitou křivostí. Zachovat původní cíl. UI musí odmítnout EXACT a ukázat důvod i dotčenou oblast; výsledek není schován pouze v logu. Není-li solver schopen důkaz rozhodnout, řekne UNRESOLVED, nikoli „přesně rozvinutelné“.

Nabídnout změnu geometrie, přidání skutečných švů nebo vytvoření segmentované odvozené varianty. Pro povinný průchod autor zvolí poslední cestu, zadá max odchylku0.25 paper mm a schválí konkrétní náhled. Report uvádí konzervativní mez odchylky uvnitř ploch, délkové rozdíly, normal-angle a počet dílů/švů. Vzorkované maximum se označí jako vzorkované a nesplňuje samo hard budget. Přísnější nesplnitelný limit musí blokovat „ověřenou“ variantu, ne měnit původní cílový model. Schválená segmentovaná varianta projde uložením/otevřením, ručním layoutem a oběma výstupy s metadaty APPROXIMATE vůči původnímu cíli. Rovinné segmenty mohou být přesně rozvinuté, původní hladká plocha tím EXACT není.

## Nové normativní AC

| ID | Kritérium a negativní/hraniční doplněk | Řez | Stav produktu |
|---|---|---|---|
| AC-AU01 | Prázdný projekt, vlastní úsečky, rozměry, editace; presety rozbalené do stejné domény; nulová délka odmítnuta | 006A | NOT_RUN |
| AC-AU02 | Rovinná konkávní plocha s otvory, výřez v UI/3D/2D/SVG/PDF; dotyk nebo crossing smyček odmítnut | 006A | NOT_RUN |
| AC-AU03 | Otevřená plocha/budova bez dna platná; žádné automatické uzavření | 006A/B | NOT_RUN |
| AC-AU04 | Celý A a nesymetrická změna přesahu; vysvětlená jednotka/režim přesahu | 006B | NOT_RUN |
| AC-AU05 | EdgePair, SurfaceTrace, GlueRegion; místní UV a orientace, uvnitř i mimo/skrze otvor | 006B | NOT_RUN |
| AC-AU06 | Vlastní trojúhelník/zkosení/autorský obrys, pásek, gap/owner/off, undo a příjemce | 006B | NOT_RUN |
| AC-AU07 | Kontrola ploché kolize oddělená od ohnuté lepicí plochy/clearance; neznámý materiál neslibuje physical PASS | 006B/007B | NOT_RUN |
| AC-AU08 | Vlastní kruhový oblouk i kubická křivka, numerická editace, rohy/tangence bez nechtěného vyhlazení | 007A | NOT_RUN |
| AC-AU09 | B1/B2/B3 a extruze Bézier; explicitní korespondence a seam; neznámý obecný loft nemá EXACT | 007A | NOT_RUN |
| AC-AU10 | C válec/kužel i válcový limit, stočení odlišné od score/fold | 007B | NOT_RUN |
| AC-AU11 | Dělené záložky na zakřivené hraně, míra segmentační odchylky, kontakt a relief; negative collision | 007B | NOT_RUN |
| AC-AU12 | D skutečné odmítnutí a editovatelná odvozená aproximační varianta včetně konzervativního error budget a exportu | 008 | NOT_RUN |
| AC-AU13 | Feature/segment split/merge provenance, trim IDs a jednoznačné přemapování; unresolved bez nearest fallback | všechny | NOT_RUN |
| AC-AU14 | Společný díl starého fixture: všechny wall coordinates invariant; nově též po editaci zdrojového profilu a interior attachment | 008 | NOT_RUN |
| AC-AU15 | Každý řez skutečné UI→save/reopen→rozvin→ruční layout→SVG/PDF, complete coverage a správný režim | všechny | NOT_RUN |
| AC-AU16 | Read-only staré soubory, prototypový PanelProject jen rozpoznaný copy/SaveAs adapter, nevratný přepis zakázán | 006A/008 | NOT_RUN |
| AC-AU17 | SVG native curves/compound paths a otvory; PDF vector approximation má doloženou mez; oba ze stejného snapshotu, reálný editor | 009 | NOT_RUN |
| AC-AU18 | Fyzický výtisk A/B/C + varianty D, skutečná kalibrace a sestavení; geometrická změna invaliduje dotčený proof | P3 | NOT_RUN |

Tabulka se doplňuje původními AC: G01–G07 (G06 přesunuto do P2), C01–C10 dle výslovného rozsahu (C08 pásek už v P2), L01–L04/L06/L08–L10, I01–I07, X01–X07/X10 a R01–R05 digitální částí (R01/R02 fyzický proof P3). AC-I08 platí při zavedení asynchronních workerů. Automatický packing, grafika a obrazový návod se neprohlašují hotové; jejich původní AC zůstávají v pozdějších epicích.

## Oddělení review od přijetí

Review návrhu kontroluje úplnost, proveditelnost a reprodukci spikeů. Review implementace ověří konkrétní CODE SHA, vlastní negativní a hraniční případy a skutečné UI důkazy. Vlastník přijímá produkt; agent si toto přijetí neuděluje. Digitální předání lze prohlásit za AGENT_VERIFIED až po úplném P2 digitálním rozsahu, nikoli po samotném A. P3 fyzická akceptace čeká na člověka a skutečný výtisk.
