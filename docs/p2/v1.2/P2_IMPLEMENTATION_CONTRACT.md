# P2 v1.2 — autorský papírový model, návrhový kontrakt

6. 11. 2026. Tento návrh vzniká na výslovný [opravný pokyn vlastníka](OWNER_CLARIFICATION.txt). Nahrazuje omezení v1.1 na preset domu. Dřívější přijetí v1.1 zůstává historickou skutečností; není přijetím tohoto nového návrhu ani hotového editoru. Stav implementace v1.2: **NOT_RUN**. Technické review a integrace návrhu nejsou produktová akceptace. Aktuální stav určuje `05_WORK_QUEUE.json`.

## Výsledek pro autora

Offline Python/Qt editor umožní začít prázdným projektem, nakreslit vlastní obrys nebo profil z úseček, kruhových oblouků a kubických Bézierových křivek, vytvořit rovinnou plochu s výřezy, lomený nebo stočený plášť a plochu mezi dvěma profily. Autor je umístí, připojí, zvolí přehyby/lepení a upraví chlopně, rozvine, ručně rozmístí na stránky a vydá editovatelné SVG i vektorové PDF. Hotové prvky využívají stejný konstrukční graf a lze je rozložit na editovatelné entity. Numerický domeček je jedna regrese.

První skutečně použitelná autorská verze je dokončené **PC-006A + PC-006B**: vlastní rovinné polygonové díly s otvory, umístění do 3D, základna a výztuhy, skutečné přesahy střechy, spoj hrana–hrana i hrana–vnitřní čára a lepicí oblast, autorské rovné/zúžené/trojúhelníkové chlopně, ruční švy, 3D↔2D výběr, undo/save/reopen, ruční více stránkový layout a oba výstupy. Musí projít model A. Nejde o vydání presetového domu s příslibem pozdější vlastní tvorby.

Úplné digitální P2 navíc zahrnuje oblouky/Bézierovy profily a ostění B, válcové/kuželové pláště C s dělenými chlopněmi a pravdivý postup D pro nerozvinutelnou plochu. Každý další řez zachovává předchozí end-to-end workflow. Ani první autorská verze, ani celé P2 nedokazují fyzickou sestavitelnost.

## Závazný rozsah

| Schopnost | První autorská verze A | Dokončené P2 v1.2 |
|---|---|---|
| Prázdný projekt, vlastní konstrukce | Úsečky, otevřené profily a uzavřené obrysy, vnější smyčka + díry; rovinná plocha, lomené pásy, umístění | Navíc kruhové oblouky, kubické Bézierovy segmenty, jejich editace, extruze a plochy mezi profily |
| Papírová stavba | Otevřená budova bez dna, samostatná základna, výztuha, přesah každé hrany střechy, výřez | Obloukové/gotické ostění, plynulé stočení, dělené spojovací prvky |
| Spojení | EdgePair, SurfaceTrace a GlueRegion oddělené od fold/cut grafu | Totéž na podporovaných zakřivených plochách s mapováním do materiálu |
| Chlopně | Autorský obrys, šířka, zkosení, trojúhelník, počet/mezery/owner/off, samostatný pásek | Dělení kolem zakřivené hrany, kontrola příjemce po ohnutí, relief a kolize |
| Rozvin | Rovinné díly a validované stromové přehyby | Přesný válec, kuželový pás, extruze a doložené kuželové/homotetické loft rodiny; ostatní profily vyžadují klasifikaci, případně řízenou segmentaci |
| Ruční práce a výstup | Plné původní minimum v1.1, stabilní kotvy, obě stránky A4, oba locks, SVG/PDF | Zachováno pro A/B/C i odsouhlasenou aproximovanou variantu D |

Otevřenost není chyba a netvoří se automatická spodní stěna. Samostatná plocha, otevřená skořepina i několik nespojených dílů jsou platná konstrukce. Neumístěný díl, rozbitý odkaz a stale rozvin stále blokují kompletní export. Uzavřenost tělesa je volitelná informace o sestavě, nikoli globální validita.

V P2 nebudou obecné CSG, libovolné NURBS/BREP, automatická oprava importovaného meshe, přesné zploštění dvojité křivosti, univerzální fyzikální simulace, automatický packing, SVG round-trip, grafický editor ani obrazový návod. Pokročilý tvarovaný terén a automatický návrh výztuh zůstávají později; **rovinná základna s půdorysnými lepicími oblastmi, vlastní rovinná výztuha a jednoduché výškové stupně už patří do P2**. Všechny původní epiky zůstávají v roadmapě.

## Konstrukční a výrobní kontrakty

Normativní návrh entit a invariantů: [architektura](ARCHITECTURE.md). Produktové situace: [analýza](PRODUCT_ANALYSIS.md). Skutečné experimenty a jejich omezení: [spiky](GEOMETRY_SPIKES.md). Obrazovky a průchody: [UX](AUTHORING_UX.md). Hodnocení zachovávaného kódu: [dispozice](CODE_DISPOSITION.md).

1. Konstrukční pravda jsou analytické křivky, orientované smyčky, plochy a reference v lokálních souřadnicích. Triangle mesh je pouze cache pro obraz/picking. Průmět ani triangulace nesmějí vymazat díru nebo vytvořit konstrukční řez.
2. Rozlišují se rovinný pás v jedné rovině, prostorový ruled loft a jeho rozvinutelnost. Spojení dvou křivek přímkami samo nedokazuje přesný rozvin. U obecného loftu numerické vzorkování může vyvrátit rozvinutelnost; bez důkazu nedává certifikát EXACT.
3. Spoj stěna–střecha s přesahem míří na vnitřní stopu střechy. Střecha se nepřistřihne ke stěně, neduplikuje a vnitřní stopa se neprohlásí za vnější hranu. Připojení k základně má stejnou zásadu. Spoj při sestavení není automaticky přehyb jednoho papírového dílu.
4. Chlopeň je identifikovaný autorský spojovací prvek s geometrií a příjemcem, nikoli pouze šířka na seam. Kontroly rozlišují plochý layout, prostor po ohnutí, ohybovou mezeru a skutečný průnik s povolenou lepicí oblastí. Kontrola geometrie není důkaz pevnosti lepidla nebo přístupu ruky.
5. Změna rozměru/profilu invaliduje všechny závislé plochy, spoje, chlopně a celý dotčený papírový díl. Nic se nepřepočítá a nepřemístí potichu. Nezměněný kotvený povrch společného dílu zachová všechny své body na stránce; ztracená kotva vyžaduje explicitní opravu. Povinný [smíšený fixture v1.1](../../revival/MIXED_PART_LAYOUT_CONTRACT.md) zůstává beze změny a doplní se volně kreslenými prvky.
6. Přesnost přesného režimu zůstává `max(0.01 paper mm, 1e-6 L)` a plocha `max(0.01 paper mm², 1e-6 A)`. Jiná veličina je chyba aproximace cílové 3D plochy. Tu nelze schovat do tolerance přesného rozvinu. Konkrétní meze a přejímky určuje [akceptace](ACCEPTANCE.md).
7. Příkaz je atomický, undo/redo obnovuje konstrukci i autorská data. Save je atomický a nesmí přepsat originál při chybě. Nový formát není stabilizován tímto návrhem; po prvním reálném průchodu A a serializačních kontraktech se verzují generické entity. Návrh nesmí vydat house-only schema za dlouhodobou smlouvu.

## Vertikální řezy a výstup každého

| Ticket | Co jde skutečně udělat | Povinný důkaz |
|---|---|---|
| PC-012 | Tento návrh + spiky, zhodnocení prototypu | Připnuté nezávislé review; žádné tvrzení hotového UI A–D |
| PC-006A | Prázdný projekt → vlastní úsečkový obrys s otvorem → plocha → 3D → základní papírový díl | Reálné UI, save/reopen, ruční šev, layout, SVG/PDF; invarianty identity, jednotek, děr, žádná podmínka closed volume |
| PC-006B | Sestavit ručně dům A s přesahy a základnou/výztuhou, vnitřní připojení a vlastní chlopně | Celý model A přes skutečné UI; první autorská verze; smíšené kotvy a negativní plocha příjemce |
| PC-007A | Oblouky/Bézier + dvojice různých profilů → ostění B, včetně děr | B přes UI; rovinný pás vs prostorový loft; EXACT pouze pro certifikovanou rodinu; nerovné neslučitelné profily nesmějí tiše získat EXACT |
| PC-007B | Válec/kužel → explicitní šev → souvislé či dělené trojúhelníkové chlopně C | C přes UI a oba exporty; poloměry/obloukové délky a vlastní počty/mezerování; prostorová lepicí plocha |
| PC-008 | D + robustní změny konstrukce napříč A–C | Reálné odmítnutí EXACT, náhled segmentace s chybou/rozpočtem, explicitně potvrzená odvozená varianta až do exportu; všechny povinné mixed-part testy |
| PC-009 | Výrobní konsolidace a skutečná interoperabilita | A/B/C a segmentovaná varianta D, stejný snapshot SVG/PDF, nezávislé čtení, skutečný externí editor, 100/150/200% DPI a klávesnice |
| PC-010 | Nezávislá revize celého digitálního P2, opravy, předání | Konkrétní CODE SHA, každý AC a jeho důkaz, projekty/exporty/hash/verze, tisk 100%; P3 fyzicky pending |

PC-006 až PC-010 zůstávají původními rodičovskými ID. Jejich staré definice a důkazy jsou zachovány, nové podřezy jsou v jediné queue. Každý implementační řez zahrnuje relevantní ověření, nezávislou revizi, opravy a bezpečnou integraci, nemusí čekat na PC-010, aby měl skutečné UI a výstupy. Review autorovi provádí jiný agent. Po PC-006A a PC-006B se přepočítá [odhad](ESTIMATE_AND_RISKS.md); ztracená přesnost nebo nejasná geometrie není důvod zúžit A/B/C/D na preset.

## Stav a autorizace

Aktuální úkol vlastníka autorizuje návrh, experimenty, nezávislé review a integraci tohoto návrhového balíku. Nezakládáme další rutinní souhlasy mezi technickými řezy. Rozsah v1.2 je zásadně širší než dříve přijatá v1.1: jeho produktové přijetí evidujeme odděleně a bez výslovného přijetí nevydáváme technické schválení/push za `PO_ACCEPTED`. Stabilizace nové domény a persistence čeká na vyřešení návrhových nálezů; implementace užšího domu se nezamění za celé P2. Fyzická akceptace A/B/C a každého nového konstrukčního principu vyžaduje skutečný výtisk v P3.
