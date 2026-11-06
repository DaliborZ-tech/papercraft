# Traceability: epiky → požadavky → AC → ověření

> Aktualizace 6. 11. 2026: tento dokument zachovává stav původního P0/P1 a v1.1. V1.1 byla skutečně přijata vlastníkem, potom byl cíl rozšířen. Aktivní návrh [P2 v1.2](../p2/v1.2/README.md) a jediná queue určují nynější rozsah/stav; review a baseline piny zůstávají historické. Povinné mixed-part testy se neruší. Push návrhu není jeho produktové přijetí.

Toto je pohled nad jedinou frontou `05_WORK_QUEUE.json`, nikoli druhý tracker. Normativní text kritérií zůstává v `04_ACCEPTANCE_AND_VERIFICATION.md`. P2/P3/future stav NOT_RUN znamená, že návrh a experiment nejsou implementační PASS. Původní legacy vady jsou doložené ve FINDINGS; tabulka níže hodnotí přejímku budoucího podporovaného produktu.

## Zachování celé vize

| Epic | Požadavek / IN a pozdější scope | Etapa | Capability závislosti | Ticket | AC | Test/demo |
|---|---|---|---|---|---|---|
| E01 | Obnova a ADLC | P0/P1 | — | PC-000–005 | AC-B01–B05; evidence a nezávislé review | baseline, bootstrap, review |
| E02 | Konstrukční panely | P2, rozšíření P5 | E01 rozhodnutí | PC-006 | AC-G01–G05/G07 | numerika/domény/world transform |
| E03 | Propojené pracovní prostředí | P2 minimum; P4 měření/gizma/sekce | E02/E12 | PC-007 | AC-C01/C02 | Windows 3D↔2D picking; DPI |
| E04 | Švy a rozvin | P2 tree; P4 paint/locks/auto | E02/E12 | PC-007 | AC-C03/C04/C07; AC-G07 | split/join, negative cycles, undo |
| E05 | Chlopně/spoje | P2 tapered A/B/off; P4 pásky | E04 + jednotky E06 + E12 | PC-007 | AC-C05/C06/C08/C09/C10 | owner, winding, convex/concave |
| E06 | Papír/materiál | P2 varování; P4/P5 kompenzace/vlákna | E02/E05 + fyzický proof konkrétního řezu | PC-008 + budoucí | AC-I04; epic materiál AC | detail<0.5mm/tab<2mm warning; později analytika+stavba |
| E07 | Ruční stránky | P2 A4/snap/oba locks; P4 ostatní formáty a skupiny | E02/E05/E12/E13 minimum | PC-008 | AC-L01–L03/L06/L09 | drag, numeric, rotation, delete/undo, save |
| E08 | Validace/volitelná automatika | P2 validace; P4 packing; později tiled | E05/E07/E12 | PC-008 | AC-L04–L10 | full envelopes, locks v automatice až P4 |
| E09 | Vektorový export | P2 SVG/PDF; P4 varianty; později DXF/PNG | E07/E08/E12 | PC-009 | AC-X01–X10 | XML/PDF reader, Inkscape, font, calibration |
| E10 | Architektonické detaily/knihovna | P5 otvory/ostění/výztuhy/presety | E02–E06/E12 + fyzický proof | budoucí | AC-G06; epic otvor/instance AC | holes/winding/triangulation + editor + stavba |
| E11 | Rotační tvary | P5 válec→kužel→báně; import později zvlášť | E02/E04–E06 + fyzický proof | budoucí | AC-R01–R05 | analytic profiles/arcs, near-cylinder, curvature |
| E12 | Identita a autorská práce | P2 revision/lineage minimum; P4 varianty/diff | E02, průřez | PC-006/008 | AC-I01–I04/I08 | stabilní kotva společného dílu, invariantní body kořenové stěny; závislé plochy v dopadu; split bez index reassignment |
| E13 | Persistence/undo/recovery | P2 safe save; P4 recovery/snapshot/bundle | E01/E02/E12 | PC-006/008 | AC-I05–I07; epic dirty/close AC | fault injection, schema, cancel close, keyboard/DPI |
| E14 | Kvalita a stavba | P0 geometrie; P2 digitální; P3 fyzický | ověřovaný řez, nikoli hotový celý E14 | PC-002/005/010/011 | vše relevantní + P3 protokol | independent review, measured calibration/build |
| E15 | Grafika | P2 SVG roles; P6 editor/textury; round-trip později | E09/E12/E13 | PC-009 + budoucí | AC-X10/A01–A03/L07 | part grouping nyní, přenosné assets a round-trip conflicts později |
| E16 | Návod/podsestavy | P2 díly/spoje legenda; P6 kroky/obrazový návod/animace | E03/E05/E12/E15 dle scope | PC-009 + budoucí | AC-N01–N03; epic legenda | paired joints/pages nyní; revision/cycles/access model později |

Žádný capability vztah nevyžaduje dokončení celého E14 před implementací. Ticket DAG PC-000→001→002→003→004/005→006→007→008→009→010→011 je acyklický; PC-004 má navíc PC-001 a PC-005 čeká PC-003+004. P4–P6 dostanou konkrétní tickety při přípravě etapy, nikoli fiktivní implementační stav.

## Úplná matice explicitních AC

| AC | Normativní požadavek | Etapa / owner | Test nebo demo / důkaz | Stav přejímky |
|---|---|---|---|---|
| AC-B01 | Prázdný otevřený VS Code root → clone → `.git` a projekt přímo v něm, žádná další podsložka | P0 / PC-000–001 | Cesty, remote, SHA; P0 | NOT_APPLICABLE: root nebyl prázdný; B02 ověřeno |
| AC-B02 | Root obsahuje brief → bootstrap → brief i jiné nekolizní soubory beze změny, repo root sedí | P0 / PC-000–001 | Hash před/po; P0 | PASS: bootstrap hashes/root |
| AC-B03 | Existuje kolidující soubor či jiný Git → příprava → žádné přepsání/mazání, konkrétní kolize vyřešena před aplikací | P0 / PC-000–001 | Preflight proof; P0 | NOT_APPLICABLE: žádná rozdílná kolize/jiný Git; preflight před zápisem PASS |
| AC-B04 | Dostupné prostředí → instalace/testy → přesné příkazy, verze, exit code a výsledky včetně skipů | P0 / PC-000–001 | Logy; P0 | PASS: přesně evidovaná instalace a výsledky |
| AC-B05 | Chybí Windows/OpenGL → report → core výsledek oddělen, desktop pending a přesný reproduction pack | P0 / PC-000–001 | Evidence; P0/P1 | NOT_APPLICABLE: Windows/OpenGL dostupné; core/desktop odděleny, repro pack hotový |
| AC-G01 | 10 m, 1000 cm nebo 10000 mm → 1:100 → vždy 100 mm na papíře | P2 / PC-006 | Nezávislý výpočet; P2 | NOT_RUN |
| AC-G02 | Referenční domeček → rozvin → odpovídající rozměry, plochy a úplné pokrytí všech povrchů | P2 / PC-006 | Numerika/topologie; P2 | NOT_RUN |
| AC-G03 | Stejná konstrukce pod rodičovskou rotací/posunem → 3D/export → konzistentní world geometrie a nezměněný místní rozvin | P2 / PC-006 | Metamorfní test; P2 | NOT_RUN |
| AC-G04 | Parametr mimo svou definovanou doménu nebo NaN/nekonečno či degenerovaná plocha → změna → konkrétní odmítnutí, žádná částečná mutace. Kladné délky nesmějí být nulové/záporné; podepsané souřadnice a úhly i nulový přesah mohou být platné | P2 / PC-006 | Negativní test; P2 | NOT_RUN |
| AC-G05 | Nepodporované CSG → příkaz → unsupported s důvodem, nikoli úspěch s původním tělesem | P2 / PC-006 | Reprodukce a regrese; P0/P2 | NOT_RUN |
| AC-G06 | Díl s otvorem → rozvin/export → otvor zachován, žádné překrývající fan triangles přes díru | Pozdější capability / viz epic | Geometrie + editor; E10 | NOT_RUN |
| AC-G07 | Uzavřený cyklus ploch nebo problematická topologie → rozvin → konzistence ověřena, případně dodatečný řez/odmítnutí, nikdy ztracené faces | P2 / PC-007 | Adversarial; P2 dle podporované topologie | NOT_RUN |
| AC-C01 | Díl ve 3D/2D → klik → zvýrazněný odpovídající protějšek i strom, správná identita | P2 / PC-007 | Reálný GUI; P2 | NOT_RUN |
| AC-C02 | Spoj přes dvě stránky → výběr → obě hrany a čísla/stránky dostupné bez ručního hledání | P2 / PC-007, PC-009 | Reálný GUI; P2; PC-007 příprava, finální přes2stránky až PC-009 po008 | NOT_RUN |
| AC-C03 | Způsobilý přehyb → změnit na řez → odpovídající split, párování a pokrytí, undo vrátí vše | P2 / PC-007 | Core + GUI; P2 | NOT_RUN |
| AC-C04 | Nepodporovaný join/nezpůsobilá hrana → příkaz → vysvětlení, původní stav beze změny | P2 / PC-007 | Negativní; P2 | NOT_RUN |
| AC-C05 | Chlopeň na straně A → přesun na B → jediná nová chlopeň, žádná stará navíc, platné párování | P2 / PC-007 | Core + GUI; P2 | NOT_RUN |
| AC-C06 | Vypnutí/změna šířky chlopně → save/reopen/undo → korektní geometrie i override | P2 / PC-007 | Persistence; P2 | NOT_RUN |
| AC-C07 | Ručně uzamčený šev → automatický návrh → šev zachován | Pozdější capability / viz epic | Test; E04 rozšíření | NOT_RUN |
| AC-C08 | Samostatný lepicí pásek → vytvoření → nový díl s vlastní identitou a oběma referencemi spoje | Pozdější capability / viz epic | Core/GUI; E05 rozšíření | NOT_RUN |
| AC-C09 | Vnější hřeben střechy a vnitřní konkávní roh s deklarovanou potištěnou stranou → značení → správná a odlišná mountain/valley polarita; obrácení potištěné strany vymění význam, pouhé obrácení indexace hrany nikoli | P2 / PC-007 | Nezávislý convex/concave fixture + SVG/PDF; P2 | NOT_RUN |
| AC-C10 | Díl otočený na stránce nebo hrana s obrácenou indexací → chlopeň → stále vně materiálu na správné straně spoje. Zrcadlení je buď samostatně validované, nebo explicitně nepodporované | P2 / PC-007 | Geometrie + export; P2 | NOT_RUN |
| AC-L01 | Díl → drag/číselná poloha a rotace → stejné umístění v UI, save/reopen i exportu | P2 / PC-008 | GUI/export; P2 | NOT_RUN |
| AC-L02 | Díl přesunut na jinou stránku → export → právě jedna instance na správné stránce | P2 / PC-008 | Integrace; P2 | NOT_RUN |
| AC-L03 | Neprázdná stránka → odstranit → díly nezmizí, přejdou do odkládací plochy nebo explicitního cíle; undo obnoví | P2 / PC-008 | GUI; P2 | NOT_RUN |
| AC-L04 | Chlopeň přesahuje papír nebo jiný díl → kontrola → konkrétní zvýraznění včetně chlopně | P2 / PC-008 | Geometrie + GUI; P2 | NOT_RUN |
| AC-L05 | Zamčený díl a automatika → spustit → poloha/rotace dle zámků nezměněna, výsledek lze celý vrátit | Pozdější capability / viz epic | Test; E08 automatika | NOT_RUN |
| AC-L06 | Příliš velký díl → packing → žádné skryté zmenšení; odkládací plocha či explicitní tiled režim | P2 / PC-008 | Negativní; P2 kontrola / E08 | NOT_RUN |
| AC-L07 | Překrývající grafické pozadí → kontrola → žádná falešná konstrukční kolize; fyzický díl je dál kontrolován | Pozdější capability / viz epic | Validátor; grafika | NOT_RUN |
| AC-L08 | Potvrzené konkrétní varování → export → přijetí platí jen pro dotčené revize; změna znovu vyžádá kontrolu | P2 / PC-008 | Integrace; P2 | NOT_RUN |
| AC-L09 | Neumístěný díl → kompletní export → odmítnutí s nabídkou umístění; explicitní částečný export musí být jasně označen | P2 / PC-008 | Negativní GUI; P2 | NOT_RUN |
| AC-L10 | Přijatý přesah mimo fyzickou stránku či rozbitá reference → kompletní tiskový export → příznak přijetí nezruší chybu integrity ani neoznačí ořezaný PDF za úplný; SVG zachová původní geometrii mimo viewBox a nese upozornění | P2 / PC-008 | Negativní integrace; P2 | NOT_RUN |
| AC-I01 | Změna střechy zachová nedotčené stěny/placements; u společného dílu persistovaná kotva v nezměněné stěně a všechny její body na stránce beze změny; celý part stale do přepočtu, závislé plochy explicitně dotčené | P2 / PC-008 | Povinně oddělený i smíšený fixture, rotace30°, save/reopen/undo, neplatná kotva bez fallbacku; MIXED_PART_LAYOUT_CONTRACT.md; exportní shoda v PC-009 | NOT_RUN |
| AC-I02 | Změněný díl → kontrola → označen revision/stale, starý rozvin nelze vydávat za aktuální | P2 / PC-008 | Core + GUI; P2 | NOT_RUN |
| AC-I03 | Split/merge nebo pořadí položek → reference → žádné přiřazení grafiky/placement k jinému dílu podle indexu | P2 / PC-008 | Adversarial; P2 dle scope | NOT_RUN |
| AC-I04 | Měřítko 1:100 → 1:200 → konstrukce poloviční, výchozí chlopeň zůstává 5 mm podle uložené politiky, nové kolize hlášeny | P2 / PC-008 | Numerika; P2 | NOT_RUN |
| AC-I05 | Save/reopen projektu → stejný obsah → zachovány odkazy, jednotky, layout a override, bez tichých oprav | P2 / PC-006 | Round-trip; P2 | NOT_RUN |
| AC-I06 | Přerušený save/chybný JSON/novější schema → otevření/obnova → originál nepoškozen, konkrétní zpráva | P2 / PC-006 | Fault injection; P2 minimum, P4 recovery | NOT_RUN |
| AC-I07 | Existující sample → import → ověřená migrace nebo pravdivě odmítnutá verze bez ztráty dat | P2 / PC-006 | Fixture; P1 rozhodnutí/P2 | NOT_RUN |
| AC-I08 | Změna modelu během dlouhého výpočtu → dokončení staré práce → výsledek neaplikován jako aktuální | Při zavedení workeru / PC-006–009 nebo později | Integrační test; při zavedení workeru | NOT_RUN |
| AC-X01 | A4 stránka → SVG → 210 × 297 mm, odpovídající viewBox, stabilní IDs a definované skupiny | P2 / PC-009 | XML + analytika; P2 | NOT_RUN |
| AC-X02 | SVG → otevřít v grafickém editoru → jednotlivý díl, text i konstrukční čára editovatelné a měřítko sedí | P2 / PC-009 | Skutečný editor s verzí; P2 | NOT_RUN |
| AC-X03 | Stránky → PDF → správný MediaBox/fyzický rozměr, vektorové cesty, česká diakritika | P2 / PC-009 | PDF struktura + render; P2 | NOT_RUN |
| AC-X04 | Tentýž snapshot → SVG/PDF → shodná geometrie, polohy, otáčení, stránky a měřítko v toleranci | P2 / PC-009 | Nezávislé čtení; P2 | NOT_RUN |
| AC-X05 | Změna zoomu nebo otevření jiné stránky → export → žádná změna uloženého rozvržení | P2 / PC-009 | Integrace; P2 | NOT_RUN |
| AC-X06 | Opakovaný export stejného snapshotu → srovnání → stejná ID/geometrie, metadata oddělena | P2 / PC-009 | Canonical comparison; P2 | NOT_RUN |
| AC-X07 | Selhání zápisu/fontu/assetu → export → konkrétní chyba, žádné falešné „hotovo“ ani poškozený předchozí výstup | P2 / PC-009 | Fault injection; P2 | NOT_RUN |
| AC-X08 | Skrytá pracovní čísla → čistý export → konstrukční cut/fold viditelné, pouze zamýšlené značky skryté | Pozdější capability / viz epic | Export kontrola; rozšíření | NOT_RUN |
| AC-X09 | DXF → výrobní aplikace → prokázané jednotky a vrstvy, žádné duplicitní řezání hrany | Pozdější capability / viz epic | Skutečný editor/zařízení dle tvrzení; později | NOT_RUN |
| AC-X10 | SVG otevřené v editoru → vybrat a přesunout celý díl → společně se přesunou řezy, přehyby, chlopně, text i part artwork; role zůstávají samostatně editovatelné, bez duplicitních vykreslených cest | P2 / PC-009 | Skutečný editor; P2 | NOT_RUN |
| AC-R01 | Válec r=10 mm, h=30 mm → rozvin → plášť 20π × 30 mm, správné párování | Pozdější capability / viz epic | Analytika + stavba; E11 | NOT_RUN |
| AC-R02 | Kuželový pás r1=10, r2=20, s=30 mm → rozvin → vnitřní R=30, vnější R=60 mm, úhel 2π/3, oblouky 20π a 40π | Pozdější capability / viz epic | Nezávislá analytika; E11 | NOT_RUN |
| AC-R03 | r1≈r2 → výpočet → stabilní válcový limit bez NaN nebo neomezených chyb | Pozdější capability / viz epic | Numerika; E11 | NOT_RUN |
| AC-R04 | Koule/jiná dvojitá křivost → přesný režim → odmítnutí nebo explicitní aproximace s definovanou chybou | Pozdější capability / viz epic | Adversarial; E11 | NOT_RUN |
| AC-R05 | Posunutý/otočený objekt → rozvin → profil a lokální rozměry zachovány | Pozdější capability / viz epic | Metamorfní; E11 | NOT_RUN |
| AC-A01 | Grafická editace dílu → uložit/export → stejná konstrukce a spoje | Pozdější capability / viz epic | Regrese; E15 | NOT_RUN |
| AC-A02 | Potisk přes šev → 3D/2D → návaznost a přesah doloženy kontrolním výtiskem | Pozdější capability / viz epic | GUI + fyzický; E15 | NOT_RUN |
| AC-A03 | Externí SVG s cizími IDs/revision či změněnou konstrukcí → budoucí import → konflikt/odmítnutí bez částečného poškození | Pozdější capability / viz epic | Negativní; pouze round-trip epic | NOT_RUN |
| AC-N01 | Návod odkazuje na díl → změna dílu → dotčený krok ke kontrole, žádný falešně aktuální návod | Pozdější capability / viz epic | Integrace; E16 | NOT_RUN |
| AC-N02 | Montážní závislosti tvoří cyklus → návrh pořadí → vysvětlení a možnost ruční opravy | Pozdější capability / viz epic | Test; E16 | NOT_RUN |
| AC-N03 | Požadavek na přístup ke spoji → UI → autorská poznámka odlišena od automatického geometrického důkazu | Pozdější capability / viz epic | UX/review; E16 | NOT_RUN |

Doplňky z epic bez číslovaného AC jsou výslovně v P2 kontraktu: malý detail/chlopeň, snap/alignment, samostatné locks, díly/spoje legenda, dirty při větvení undo a Windows DPI/klávesnice. Tyto demo položky jsou NOT_RUN; nejsou zrušeny absencí číselného ID.

AC-I07: P1 rozhodnutí a dnešní sample round-trip prozkoumány; P2 legacy read-only/refusal bez ztráty se musí implementovat a ověřit, proto zde NOT_RUN. AC-G05: P0 reprodukce vady hotová, P2 odmítnutí unsupported zatím NOT_RUN. AC-L06 v P2 ověří odmítnutí/zachování velikosti a odkládací plochu bez packingu. AC-X10 P2 ověří skupinu všech implementovaných part složek; interní artwork přibývá v E15, struktura a prázdná role už v P2.
