# Akceptační a ověřovací kontrakt

> Aktivn? roz???en? 6. 11. 2026: [P2 v1.2 akceptace](docs/p2/v1.2/ACCEPTANCE.md) je normativn? dodatek. D?m n??e je numerick? regrese. Povinn? jsou t?? vlastn? modely A/B/C/D; otvory (AC-G06), p?sky (AC-C08) a digit?ln? ??sti v?lce/ku?ele/odm?tnut? dvojit? k?ivosti (AC-R01?R05) jsou ji? P2. Ka?d? podporovan? ?ez proch?z? skute?n?m UI, IO, rozvinem, ru?n?m layoutem a SVG/PDF. P?vodn? mixed-part kotvy, p?esnost a ochrana pr?ce z?st?vaj?. Nov? produktov? AC jsou NOT_RUN; spike nen? UI proof, fyzick? v?tisk z?st?v? P3.

Verze 1.0 · Normativní součást zadání. Číselné tolerance jsou návrh požadované digitální přesnosti; P1 musí experimentálně doložit jejich dosažitelnost nebo předložit zdůvodněnou změnu. Nejsou tvrzením o přesnosti domácí tiskárny.

## 1. Referenční model P2

Projekt `reference_house_v1`: tělo délka 10 m, šířka 6 m, výška stěn 4 m; sedlová střecha, hřeben o 3 m nad stěnou, pro základní numerický fixture bez přesahu; měřítko 1:100. Tisk A4 210 × 297 mm, okraje 10 mm, chlopeň výchozí 5 mm na papíře. Model může být složen z více dílů a stránek podle autorských švů; nefixovat počet dílů testem proti náhodné implementaci.

Očekávání: dvě boční stěny 100 × 40 mm, dvě čelní obdélníkové části 60 × 40 mm a dva štítové trojúhelníky se základnou 60 mm a výškou 30 mm; výška hřebene celkem 70 mm; sklonová délka střechy `sqrt(30² + 30²) = 42.426406871... mm`, délka střechy podél domu 100 mm. Uzavření obvodu těla 320 mm bez chlopní. Základní fixture zvolí jednoznačnou konstrukci styku stěna/střecha a zdokumentuje ji; tloušťková kompenzace v tomto digitálním fixture vypnuta.

Fyzická stavba může použít dokumentovaný přesah střechy a podporu, ale pak jde o samostatný fixture s přepočteným orákulem. Neopravuj nesestavitelný vzor ručními zásahy mimo aplikaci bez evidence vady.

## 2. Numerické kontrakty a testovací orákula

- Požadovaná délková odchylka v čisté digitální geometrii: nejvýše `max(0.01 mm na papíře, 1e-6 × referenční délka na papíře)` pro přesné rozviny. Reprezentace/export nesmí přidat další zaokrouhlení nad tento limit. Topologická tolerance a minimální detail jsou jiné pojmy a musí mít vlastní definici.
- Dvě párované lepené hrany mají kompatibilní efektivní délku v této toleranci, pokud není explicitně navržená vůle. Ověřit také orientaci, referenční bod, interval a typ spojení; pouhá stejná délka nestačí.
- Zachování plochy rovinných dílů: odchylka nejvýše `max(0.01 mm², 1e-6 × plocha)`, bez chlopní a grafiky, se správným odečtením otvorů.
- Průnik vnitřních ploch dílů je konstrukční kolize; dotyk společné hrany není automaticky plošný průnik. Numerický epsilon nesmí schovat viditelný překryv. P1 definuje robustní predikáty a odstupy packing.
- Nezávislé orákulum: ruční analytické vzorce, jednoduché ručně určené topologie, nebo nezávislý validátor. Test volající tentýž helper pro expected a actual nic neprokazuje.
- Metamorfní kontroly: rigidní transformace zachová délky, plochy, spoje a místní rozvin; přeuspořádání triangle indexů nezmění významové part identity; ekvivalentní jednotkový vstup dá stejný fyzický výsledek.
- Fyzický výtisk: kalibrační 100mm úsečka se změří pravítkem; doporučená tolerance ±0.5 mm pro přijetí konkrétního výtisku. Překročení znamená nejprve diagnostiku tisku, nikoli automaticky chybu geometrie. Výsledek a měřidlo uvést; nezaručovat všechny tiskárny.

## 3. Matice akceptačních kritérií

### Workspace a baseline

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-B01 | Prázdný otevřený VS Code root → clone → `.git` a projekt přímo v něm, žádná další podsložka | Cesty, remote, SHA; P0 |
| AC-B02 | Root obsahuje brief → bootstrap → brief i jiné nekolizní soubory beze změny, repo root sedí | Hash před/po; P0 |
| AC-B03 | Existuje kolidující soubor či jiný Git → příprava → žádné přepsání/mazání, konkrétní kolize vyřešena před aplikací | Preflight proof; P0 |
| AC-B04 | Dostupné prostředí → instalace/testy → přesné příkazy, verze, exit code a výsledky včetně skipů | Logy; P0 |
| AC-B05 | Chybí Windows/OpenGL → report → core výsledek oddělen, desktop pending a přesný reproduction pack | Evidence; P0/P1 |

### Geometrie a rozvin

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-G01 | 10 m, 1000 cm nebo 10000 mm → 1:100 → vždy 100 mm na papíře | Nezávislý výpočet; P2 |
| AC-G02 | Referenční domeček → rozvin → odpovídající rozměry, plochy a úplné pokrytí všech povrchů | Numerika/topologie; P2 |
| AC-G03 | Stejná konstrukce pod rodičovskou rotací/posunem → 3D/export → konzistentní world geometrie a nezměněný místní rozvin | Metamorfní test; P2 |
| AC-G04 | Parametr mimo svou definovanou doménu nebo NaN/nekonečno či degenerovaná plocha → změna → konkrétní odmítnutí, žádná částečná mutace. Kladné délky nesmějí být nulové/záporné; podepsané souřadnice a úhly i nulový přesah mohou být platné | Negativní test; P2 |
| AC-G05 | Nepodporované CSG → příkaz → unsupported s důvodem, nikoli úspěch s původním tělesem | Reprodukce a regrese; P0/P2 |
| AC-G06 | Díl s otvorem → rozvin/export → otvor zachován, žádné překrývající fan triangles přes díru | Geometrie + editor; E10 |
| AC-G07 | Uzavřený cyklus ploch nebo problematická topologie → rozvin → konzistence ověřena, případně dodatečný řez/odmítnutí, nikdy ztracené faces | Adversarial; P2 dle podporované topologie |

### Výběr, švy a chlopně

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-C01 | Díl ve 3D/2D → klik → zvýrazněný odpovídající protějšek i strom, správná identita | Reálný GUI; P2 |
| AC-C02 | Spoj přes dvě stránky → výběr → obě hrany a čísla/stránky dostupné bez ručního hledání | Reálný GUI; P2 |
| AC-C03 | Způsobilý přehyb → změnit na řez → odpovídající split, párování a pokrytí, undo vrátí vše | Core + GUI; P2 |
| AC-C04 | Nepodporovaný join/nezpůsobilá hrana → příkaz → vysvětlení, původní stav beze změny | Negativní; P2 |
| AC-C05 | Chlopeň na straně A → přesun na B → jediná nová chlopeň, žádná stará navíc, platné párování | Core + GUI; P2 |
| AC-C06 | Vypnutí/změna šířky chlopně → save/reopen/undo → korektní geometrie i override | Persistence; P2 |
| AC-C07 | Ručně uzamčený šev → automatický návrh → šev zachován | Test; E04 rozšíření |
| AC-C08 | Samostatný lepicí pásek → vytvoření → nový díl s vlastní identitou a oběma referencemi spoje | Core/GUI; E05 rozšíření |
| AC-C09 | Vnější hřeben střechy a vnitřní konkávní roh s deklarovanou potištěnou stranou → značení → správná a odlišná mountain/valley polarita; obrácení potištěné strany vymění význam, pouhé obrácení indexace hrany nikoli | Nezávislý convex/concave fixture + SVG/PDF; P2 |
| AC-C10 | Díl otočený na stránce nebo hrana s obrácenou indexací → chlopeň → stále vně materiálu na správné straně spoje. Zrcadlení je buď samostatně validované, nebo explicitně nepodporované | Geometrie + export; P2 |

### Stránky a validace

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-L01 | Díl → drag/číselná poloha a rotace → stejné umístění v UI, save/reopen i exportu | GUI/export; P2 |
| AC-L02 | Díl přesunut na jinou stránku → export → právě jedna instance na správné stránce | Integrace; P2 |
| AC-L03 | Neprázdná stránka → odstranit → díly nezmizí, přejdou do odkládací plochy nebo explicitního cíle; undo obnoví | GUI; P2 |
| AC-L04 | Chlopeň přesahuje papír nebo jiný díl → kontrola → konkrétní zvýraznění včetně chlopně | Geometrie + GUI; P2 |
| AC-L05 | Zamčený díl a automatika → spustit → poloha/rotace dle zámků nezměněna, výsledek lze celý vrátit | Test; E08 automatika |
| AC-L06 | Příliš velký díl → packing → žádné skryté zmenšení; odkládací plocha či explicitní tiled režim | Negativní; P2 kontrola / E08 |
| AC-L07 | Překrývající grafické pozadí → kontrola → žádná falešná konstrukční kolize; fyzický díl je dál kontrolován | Validátor; grafika |
| AC-L08 | Potvrzené konkrétní varování → export → přijetí platí jen pro dotčené revize; změna znovu vyžádá kontrolu | Integrace; P2 |
| AC-L09 | Neumístěný díl → kompletní export → odmítnutí s nabídkou umístění; explicitní částečný export musí být jasně označen | Negativní GUI; P2 |
| AC-L10 | Přijatý přesah mimo fyzickou stránku či rozbitá reference → kompletní tiskový export → příznak přijetí nezruší chybu integrity ani neoznačí ořezaný PDF za úplný; SVG zachová původní geometrii mimo viewBox a nese upozornění | Negativní integrace; P2 |

### Identita a persistence

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-I01 | Ručně rozmístěné stěny → změna střechy → neovlivněná ID/pozice/rotace/zámky zachované; povinně také společný díl stěna–střecha s persistovanou kotvou v nezměněné stěně: po přepočtu zůstávají všechny její body na stránce stejné, celý díl je před přepočtem stale. Plochy připojené přes změněnou geometrii patří do dopadu. Neověřovat pouze oddělené díly | Integrace; P2; fixture a pravidla v docs/revival/MIXED_PART_LAYOUT_CONTRACT.md |
| AC-I02 | Změněný díl → kontrola → označen revision/stale, starý rozvin nelze vydávat za aktuální | Core + GUI; P2 |
| AC-I03 | Split/merge nebo pořadí položek → reference → žádné přiřazení grafiky/placement k jinému dílu podle indexu | Adversarial; P2 dle scope |
| AC-I04 | Měřítko 1:100 → 1:200 → konstrukce poloviční, výchozí chlopeň zůstává 5 mm podle uložené politiky, nové kolize hlášeny | Numerika; P2 |
| AC-I05 | Save/reopen projektu → stejný obsah → zachovány odkazy, jednotky, layout a override, bez tichých oprav | Round-trip; P2 |
| AC-I06 | Přerušený save/chybný JSON/novější schema → otevření/obnova → originál nepoškozen, konkrétní zpráva | Fault injection; P2 minimum, P4 recovery |
| AC-I07 | Existující sample → import → ověřená migrace nebo pravdivě odmítnutá verze bez ztráty dat | Fixture; P1 rozhodnutí/P2 |
| AC-I08 | Změna modelu během dlouhého výpočtu → dokončení staré práce → výsledek neaplikován jako aktuální | Integrační test; při zavedení workeru |

### SVG, PDF a externí editor

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-X01 | A4 stránka → SVG → 210 × 297 mm, odpovídající viewBox, stabilní IDs a definované skupiny | XML + analytika; P2 |
| AC-X02 | SVG → otevřít v grafickém editoru → jednotlivý díl, text i konstrukční čára editovatelné a měřítko sedí | Skutečný editor s verzí; P2 |
| AC-X03 | Stránky → PDF → správný MediaBox/fyzický rozměr, vektorové cesty, česká diakritika | PDF struktura + render; P2 |
| AC-X04 | Tentýž snapshot → SVG/PDF → shodná geometrie, polohy, otáčení, stránky a měřítko v toleranci | Nezávislé čtení; P2 |
| AC-X05 | Změna zoomu nebo otevření jiné stránky → export → žádná změna uloženého rozvržení | Integrace; P2 |
| AC-X06 | Opakovaný export stejného snapshotu → srovnání → stejná ID/geometrie, metadata oddělena | Canonical comparison; P2 |
| AC-X07 | Selhání zápisu/fontu/assetu → export → konkrétní chyba, žádné falešné „hotovo“ ani poškozený předchozí výstup | Fault injection; P2 |
| AC-X08 | Skrytá pracovní čísla → čistý export → konstrukční cut/fold viditelné, pouze zamýšlené značky skryté | Export kontrola; rozšíření |
| AC-X09 | DXF → výrobní aplikace → prokázané jednotky a vrstvy, žádné duplicitní řezání hrany | Skutečný editor/zařízení dle tvrzení; později |
| AC-X10 | SVG otevřené v editoru → vybrat a přesunout celý díl → společně se přesunou řezy, přehyby, chlopně, text i part artwork; role zůstávají samostatně editovatelné, bez duplicitních vykreslených cest | Skutečný editor; P2 |

### Rotační tvary, grafika a návod

| ID | Given / When / Then | Proof / etapa |
|---|---|---|
| AC-R01 | Válec r=10 mm, h=30 mm → rozvin → plášť 20π × 30 mm, správné párování | Analytika + stavba; E11 |
| AC-R02 | Kuželový pás r1=10, r2=20, s=30 mm → rozvin → vnitřní R=30, vnější R=60 mm, úhel 2π/3, oblouky 20π a 40π | Nezávislá analytika; E11 |
| AC-R03 | r1≈r2 → výpočet → stabilní válcový limit bez NaN nebo neomezených chyb | Numerika; E11 |
| AC-R04 | Koule/jiná dvojitá křivost → přesný režim → odmítnutí nebo explicitní aproximace s definovanou chybou | Adversarial; E11 |
| AC-R05 | Posunutý/otočený objekt → rozvin → profil a lokální rozměry zachovány | Metamorfní; E11 |
| AC-A01 | Grafická editace dílu → uložit/export → stejná konstrukce a spoje | Regrese; E15 |
| AC-A02 | Potisk přes šev → 3D/2D → návaznost a přesah doloženy kontrolním výtiskem | GUI + fyzický; E15 |
| AC-A03 | Externí SVG s cizími IDs/revision či změněnou konstrukcí → budoucí import → konflikt/odmítnutí bez částečného poškození | Negativní; pouze round-trip epic |
| AC-N01 | Návod odkazuje na díl → změna dílu → dotčený krok ke kontrole, žádný falešně aktuální návod | Integrace; E16 |
| AC-N02 | Montážní závislosti tvoří cyklus → návrh pořadí → vysvětlení a možnost ruční opravy | Test; E16 |
| AC-N03 | Požadavek na přístup ke spoji → UI → autorská poznámka odlišena od automatického geometrického důkazu | UX/review; E16 |

## 4. Povinné demo P2

1. Na Windows vytvořit referenční dům a ukázat jeho rozměry; vybrat plochu ve 3D a najít odpovídající 2D díl, potom opačně.
2. Změnit způsobilý šev, přesunout chlopeň na protikus a upravit její šířku. Ukázat návrat undo a opětovné redo.
3. Ručně uspořádat díly na dvě či více A4 stránek, jeden otočit, jeden uzamknout, jeden přesunout mezi stránkami.
4. Vyvolat kolizi chlopně a přesah tiskové oblasti, ukázat přesnou diagnostiku a opravu. Neumístěný díl nesmí být nepozorovaně vynechán.
5. Změnit střechu; ukázat stale stav dotčených dílů a zachování nedotčených stěn. Přepočítat a zkontrolovat dopad.
6. Uložit, aplikaci zavřít, znovu otevřít; ukázat zachování konstrukce, ručního layoutu a identit.
7. Exportovat SVG i PDF. SVG otevřít v reálném grafickém editoru a upravit kopii textu/barvy. Nemíchat tuto kopii zpět do projektu jako podporovaný import.
8. Zkontrolovat vektorové PDF, kalibrační úsečku, fyzické rozměry a soulad s layoutem. Předat konkrétní balík pro výtisk a sestavení.

P2 je AGENT_VERIFIED jen po splnění přijatého digitálního kontraktu a nezávislé revizi. Pokud chybí Windows či editor, je digitální akceptace neúplná. P3 fyzická sestavitelnost může zůstat PO_PENDING; nesmí být prezentována jako hotová.

## 5. Fyzická akceptace P3

Předat projekt, přesný export, verze a krátký postup tisku 100 %. Vlastník či tester změří 100mm kalibraci, vystřihne díly a sestaví je bez změny konstrukční geometrie. Zaznamená papír/gramáž/tloušťku, problémová místa, přístup ke spojům, nesedící hrany, nutné výztuhy a případné ruční zásahy. Fotografie jsou užitečný důkaz, nejsou automatická povinnost této analytické session.

Po nesedícím spoji určit, zda jde o rozměry, tloušťku, přesah chlopně, pořadí montáže nebo tiskové škálování. Oprava má konkrétní regresi. Po změně dotčeného konstrukčního principu zopakovat relevantní fyzický proof. Nový počet zelených unit testů fyzickou kontrolu nenahrazuje.

## 6. Evidence a rozhodnutí

Každý AC má v implementačním ticketu stav NOT_RUN / PASS / FAIL / BLOCKED / NOT_APPLICABLE s důvodem, konkrétní zdrojový pin a důkaz. NOT_APPLICABLE není nástroj na odstranění požadavku: musí odpovídat výslovnému rozsahu etapy. Statický závěr, automatický test, skutečný GUI proof a fyzický proof jsou různé druhy důkazu.

Reviewer kontroluje i to, zda očekávání testu nebylo odvozené z chybné implementace. Ověří nejméně jednu negativní a jednu hraniční situaci dotčeného algoritmu. Technický review verdict: APPROVED_IN_SCOPE / CHANGES_REQUIRED / INCOMPLETE_EVIDENCE. PO_ACCEPTED a release readiness se evidují zvlášť.
