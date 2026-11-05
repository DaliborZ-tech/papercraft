# P2 — implementační kontrakt k přijetí vlastníkem

Verze 1.0 · 5. 11. 2026 · stav PO_PENDING po uzavření nezávislé revize P0/P1. Produkční implementace P2 zatím není autorizována. Normativní zadání: [mandát](../../02_CODEX_MANDATE.md), [akceptace](../../04_ACCEPTANCE_AND_VERIFICATION.md), [16 epic](../../03_EPICS_AND_ROADMAP.md). Traceability a aktuální fronta jsou odkázané níže.

## Co vlastník dostane

Offline desktop ve stávajícím Python/PySide6: vytvořit a rozměrově editovat panelový dům, vybrat tentýž díl ve 3D i 2D, ručně měnit způsobilé švy a chlopně, rozmístit díly na více A4 stránek, uložit a znovu otevřít a vyexportovat editovatelné SVG všech stránek i vektorové PDF z přesně tohoto rozvržení. Změna střechy zachová nedotčené stěny a autorské placements; zastaralý výsledek nesmí projít jako aktuální export.

Doporučená varianta B, srovnání nákladů/rizik a mapa modulů: [ADR-001](ARCHITECTURE_DECISION.md). Konkrétní obrazovky a chybové stavy: [UX](UX_CONTRACT.md), [klikací maketa](ux-prototype.html). Ověřená výchozí aplikace: [baseline](BASELINE_REPORT.md), vady: [findings](FINDINGS.md), nezávislá geometrie: [spike](GEOMETRY_SPIKE.md).

## Přesný rozsah a hranice

Referenční dům bez podlahy, bez přesahu a tloušťkové kompenzace: X délka 10000 mm, Y šířka 6000 mm, stěna Z=4000 mm, hřeben Z=7000 mm. Osm významových povrchů: dvě boční obdélníkové stěny, dvě čelní obdélníkové stěny, dva štítové trojúhelníky, dvě střešní roviny. Stěna/štít/střecha sdílejí matematické hrany, papír se v digitálním fixture považuje za nulově tlustý. Orientovaný seam graph určuje počet dílů; testy jej nefixují náhodným počtem triangles.

P2 podporuje jednoduché rovinné polygonové panely bez děr a jejich konstrukčně sousední hrany. Fold graf jednoho dílu je acyklický, s úplným pokrytím a bez plošného překryvu. Cut provede split tam, kde odpojí graf. Join je povolen mezi odpovídajícími sousedními panely, pokud je výsledek strom a validní; cyklus, neznámý původ hrany, non-manifold nebo nemožný rozvin jsou odmítnuty před mutací. Nejde o zákaz uzavřeného domu: fyzické uzavření probíhá přes explicitní lepené cut spoje mezi díly.

IN: orbit/pan/zoom/focus, picking povrchu a hrany, sdílený selection model, cut/fold, tab A/B/off, zkosená chlopeň se šířkou a taper ratio, paired edge čísla, papírová přední strana, A4 portrait/landscape, dvě či více stránek, odkládací plocha, drag a číselný posun/úhel, snap 1 mm a základní zarovnání, nezávislé zámky polohy/rotace, undo/redo všech autorských změn, dirty/close, validace, atomický save/open, SVG/PDF, pracovní legenda dílů/spojů.

OUT P2: obecné CSG/CAD/import meshe, otvory/gotika/ostění/výztuhy, válce a kužely a báně, automatický packing, dlaždice, interní grafický editor/round-trip SVG, generovaný obrazový návod, tloušťkové kompenzace a fyzikální simulace. Zůstávají v E03–E16/P4–P6; [traceability](TRACEABILITY.md) je zachovává. Legacy funkce s vadami nesmí v novém workflow slibovat podporu; lze je prohlížet odděleně s omezeními. Bezplatný editor Inkscape je kandidát přejímky, přesná ověřená verze se zapíše při P2, dnes interoperability PASS neexistuje.

## Data a kontrakty služeb

Závazné podrobnosti identity, jednotek, API a tolerancí jsou v ADR. Implementace musí mít domain bez Qt, application commands s atomickou validací/undo, odvozený mesh a 2D díly ze společných surface IDs a validovaný export snapshot. Významové entity mají persistované ID, obsahovou revision a samostatné uživatelské číslo. World transform obsahuje rodiče; mesh triangle index není part ID.

Změna střechy: dotčené povrchy a spoje stale, nezměněné stěny a placements zachované. Split dává nové part IDs s lineage; staré umístění se přenese jen s jednoznačnou mapou lokálních souřadnic. Při nejistotě jsou díly v explicitním stavu k rozmístění/kontrole, nikdy u jiného dílu stejného indexu. P2 nemá interní artwork, avšak neznámá data při otevření nepřepíše. Scale přepočítá konstrukci, výchozí chlopeň zůstane 5 paper mm; také font a line width mají fyzickou politiku. Každý celý dopad je undoable.

Chlopeň výchozí 5 mm, explicitně nastavitelná kladná konečná šířka, taper ratio [0,1], krátká/kolizní se nezamlčí. Jeden Joint vlastní nanejvýš jednu chlopeň, A→B se provádí atomicky. Hole winding je datově definovaný pro E10, holes nejsou v P2 podporované. Reflections v P2 odmítnout; rotace a přeznačení indexů nesmějí měnit vnější stranu ani mountain/valley. Konvenci kalibrovat na vnějším hřebeni a konkávním rohu z deklarované potištěné strany.

Exportní snapshot musí mít aktuální source revisions, každou surface právě jednou a každý díl právě na jedné stránce nebo explicitně neumístěný. Kompletní export odmítne neumístěné a chyby integrity. Odsouhlasené autorské varování se váže na příslušnou revision. Mimo doporučený okraj uvnitř papíru lze přijmout; mimo fyzický papír nelze potvrzením vytvořit úplný PDF. Částečná kopie vyžaduje explicitní označení v souhrnu i souboru, SVG uchová neviditelnou geometrii mimo viewBox a varování. Export bez autorského příkazu nikdy nerepackuje.

SVG každý page soubor, mm/viewBox, `part-<stable-id>` s placement transform a vnořenými CUT/FOLD_MOUNTAIN/FOLD_VALLEY/TABS/LABELS/ARTWORK/GUIDES. Díl včetně tabů a popisků lze přesunout jako celek, role a text samostatně editovat; žádné duplicitní vykreslované cesty. PDF stejné cesty, vložený font s českou diakritikou, správný MediaBox a 100mm kalibrace; instrukce 100 % / skutečná velikost. Atomic output používá dočasné soubory a success až po celém balíku; selhání nesmí poškodit předešlý export ani vyhlásit dokončeno.

Legacy: read-only otevření v0.2.0 s upozorněním. Panelový převod pouze přes explicitní ověřenou mm mapu, do nového souboru. Kompletní `house_with_dome.apcraft` má typy mimo P2 a nebude vydáván za plně migrovaný nový projekt; originál zůstane dostupný v legacy pohledu. Neznámá verze nebo payload se odmítne, či uchová bez možnosti ztrátového save. Schválením tohoto kontraktu vlastník přijímá tuto konkrétní mez kompatibility, nikoli ztrátu starých dat.

## Implementační balíčky

Každý řádek navazuje na [jedinou queue](../../05_WORK_QUEUE.json); AC mají konkrétní GIVEN/WHEN/THEN v normativním souboru. Finální PASS je až pro skutečný implementovaný produkt a připnutý CODE SHA. P1 experiment s panelem není P2 PASS.

| Ticket | Story / baseline / IN | OUT a závislosti | Ověření a demo | Odhad |
|---|---|---|---|---|
| PC-006 | Autor vytvoří správně rozměrovaný dům a bezpečně ho uloží. Dnes smíšené mm/m a permissive schema. Zavést panelovou doménu, IDs, jednotky, world transform, konstrukční commands, atomic save a legacy read-only | obecný CAD/CSG a úplná migrace báně; po PC-005 a přijetí GATE-P2 | AC-G01–G05/I05–I07: analytické rozměry/plochy, 10m/1000cm/10000mm, parent transform, negativní NaN/Inf/zero, přerušit save před replace, future schema, původní sample hash; demo nový→rozměry→save→reopen | 5–8 dnů |
| PC-007 | Autor chápe a upraví spoj; dnes není 2D/picking a tab owner není globální. Selection hub, 3D/2D picking, cut/fold, tree unfold, tab A/B/off/width/taper, orientace a undo | obecné cyklické sítě, díry; po PC-006 | AC-C01–C06/C09/C10/G07: index permutations, convex/concave, tab overlap a ownership, incomplete coverage, non-manifold/cycle rejection, undo; demo vyber→cut→tab B→undo. AC-C02 přes dvě stránky čeká PC-009 | 7–11 dnů |
| PC-008 | Autor ručně tvoří stránky a neztratí layout při změně konstrukce. Dnes jen pack při exportu. Zavést pages/tray/placements, drag/numeriku/snap/alignment, oba locks, invalidaci a kompletní materiálovou validaci | automatický packing, tiled; po PC-007 | AC-L01–L04/L06/L08–L10/I01–I04: přesun/rotace/save, delete page/undo, velký díl, stale střechy při zachování stěn, split lineage, 1:200 a 5mm tab, tiny overlap vs edge touch. Demo dvě stránky→kolize→oprava→změna střechy | 6–10 dnů |
| PC-009 | Autor předá editovatelný tisk; dnes SVG/PDF nesouhlasí v orientaci/Y a diakritika není vložená. Společný snapshot, SVG všech stránek, PDF, summary, legenda, font a chyby IO | round-trip, obrazový návod, DXF/PNG rozšíření; po PC-008 | AC-X01–X07/X10/C02, kompletní §4 demo. Nezávisle parsovat XML/PDF geometry, render, MediaBox, text, vektorové operátory, Inkscape editace celého dílu/textu/barvy. Změna zoomu/stránky bez změny exportu, failure write/font/asset a canonical repeat | 4–7 dnů |
| PC-010 | Jiný reviewer ověří konkrétní přírůstek včetně chybových stavů; implementátor si neuděluje approval | fyzický proof neuděluje agent; po PC-009 | připnutý CODE SHA, vlastní negativní/hraniční geometrie, evidence všech P2 AC, opravy a re-review. Výsledkem digitální AGENT_VERIFIED a PO_PENDING; tiskový balík pro P3 | 2–4 dny |

Součet 24–40 soustředěných člověkodnů. Odhad obsahuje běžné opravy, nejistota zůstává zejména v picking/GPU a split/join. Jediný integrační owner; geometrii a review oddělit. Paralelní práce pouze na oddělených souborech/worktrees, žádný sdílený mutable `.apcraft`.

P0/P1 tickets PC-000–005 mají skutečné výstupy a evidence v queue; PC-006–011 se neprohlašují implementované. P4–P6 rozpad do nových ticketů vznikne při přípravě etapy, cílové epiky se nemažou.

## Přesnost a negativní přejímka

Beze změny: délka `max(0.01 mm,1e-6 L)`; plocha `max(0.01 mm²,1e-6 A)`, bez tabů a artwork. Panelový spike dosahuje řádově 1e-14 mm a dokládá dosažitelnost pro tento řez, nikoli pro libovolné modely. Predikáty/degenerace/odstupy mají samostatné meze v ADR. Datová integrita nemá uživatelský bypass.

Dodatečné explicitní demo požadavky nad číslovanými AC: upozornění na detail pod 0.5 paper mm a tab pod 2 mm (E06), snap a přesný vstup bez tichého zaokrouhlení (E07), samostatné locks (E07), paired joint legenda s čísly dílů a stránek (E16), dirty po save→undo→jiná akce při stejné hloubce zásobníku (E13), klíčové klávesové ovládání a čitelnost při Windows DPI 100/150/200 % (E13). Evidovat samostatné demo položky, nikoli ztratit v obecné formulaci.

## Dokončení a akceptace

1. Core numerika + topologie, persistence/command integrace a relevantní regrese. Původní zelená sada nestačí; P0 červené diagnostiky převést na opravené kontroly pro nový podporovaný model, legacy omezení neskrýt xfail.
2. Skutečný Windows desktop a souborové dialogy, picking oběma směry, spoje přes dvě stránky, změna modelu a safe save/reopen.
3. Otevřít konkrétní SVG v reálném Inkscape, zapsat verzi; přesunout celý díl a upravit samostatný text/barvu na kopii. P2 nevyžaduje druhý editor jako hard gate.
4. Nezávislé čtení geometrie SVG/PDF a vektorového PDF, diakritika a kalibrace. Canonical compare ignoruje jen dohodnutá metadata, ne identity a cesty.
5. Jiný reviewer na konkrétním CODE SHA, uzavřené major/blocker nálezy, relevantní re-review.
6. Předání projektu, snapshotu/exportu, verzí a tiskových instrukcí. Fyzický výtisk a sestavení v P3 zůstává PO_PENDING, dokud jej člověk skutečně neprovede.

Schválení tohoto konkrétního kontraktu je jediná produktová brána k produkční P2 a dosud neproběhlo. Podle výslovné opravy realizačního mandátu z 5. listopadu 2026 se dokončené ucelené balíky v již autorizovaném rozsahu po ověření a nezávislé revizi integrují a pushují na `master` bez další rutinní žádosti; postup je v `AGENTS.md` a §6 mandátu. Integrace P0 + P1 není produktovým přijetím tohoto kontraktu, varianty B ani kompatibility. Nejsou třeba další souhlasy s běžnými implementačními metodami v přijatém scope; produkční release zůstává samostatný.
