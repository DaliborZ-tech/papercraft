# Nezávislá revize PC-007A — rovinné zdrojové křivky a UI

Integrační poznámka: původní otevřené nálezy níže patří pinu `e3a545f`. Doplňující nezávislá revize `820ab66` na konci zprávy uzavřela **P01/P02 CLOSED VERIFIED**. Původní FAIL je zachovaný. Následné úpravy kontaktů, ohybu a přesného přímého obrazu kolineární kubiky vyžadují vlastní doplňující revizi; toto schválení není automaticky schválením celé PC-007A.

Reviewer: samostatný agent `bend_adapter_review`, nikoli autor zde revidované implementace. Zdroj **`e3a545fffb05abcbf6ff5e8071f43b21ce5131f2`**, 9. 11. 2026. V tomto pinu není implementován nový loftový modul, jehož jsem autorem; tuto vlastní produkci zde nereviduji.

**CHANGES_REQUIRED: P01 a P02 MAJOR jsou OPEN.** Rovinný přírůstek nelze schválit na základě zelených původních testů. Celá PC-007A, B1/B2/B3, novice test ani digitální P2 nejsou dokončené.

## P01 — tětivová projekce neprokazuje topologii nativního obrysu

Vlastní uzavřený profil má kubiku `(0,.0005)→(10,.0005)`, řídicí body `(3,−.001),(7,−.001)` a zbývající rovné hrany přes `(10,0),(0,0)` zpět na začátek. Projekce při chybovém rozpočtu `.002 paper mm` obsahuje jen čtyři rohy platného obdélníku. Skutečná kubika však má v `u=.5` bod **`[5,−.000625]`**, tedy kříží protější spodní hranu `y=0` dvakrát.

`add_surface` i snapshot prošly; jediný SMALL_DETAIL warning lze potvrdit. `curve_profiles` obsahuje CERTIFIED a native CUT skutečně publikuje tuto křížící se kubiku. Pozitivní délková/tětivová mez není pozitivním důkazem jednoduchosti materiálového obrysu.

[Raw source a přijatý snapshot](evidence/pc007a-planar-review-P01-crossing.json). Požadovaná oprava: samostatně doložit nativní průsečíky/oddělenost hran i otvorů, nebo konzervativně vrátit blokující neurčitost. Nepřijímat reprezentaci jako důkaz topologie a nepřekrýt chybu varováním malého detailu. Chybový rozpočet samotný nedává oprávnění odstranit průsečík.

## P02 — layout certifikuje proxy, tiskne jinou materiálovou hranici

Vlastní platný zdroj `10×10 mm` má tři rovné strany a pravou kubiku `(10,0)→(10,10)` s řídicími body `(10.0015,3),(10.0015,7)`. Projekce je obdélník `10×10`; skutečný nativní obrys se uprostřed vyklene ven o **`.001125 mm`**. První díl je na stránce na `[40,40]`, druhý obdélník `2×10` na `[50.0005,40]`.

`validate_layout` vrací **prázdný seznam**, snapshot se vydá. Ve výsledné nativní hranici ale v okolí `u=.5` existuje skutečný materiálový překryv se šířkou **`.000625 mm`**; nejde o dotyk ani nulovou plochu. Zdroj prvního dílu je samostatně topologicky platný, takže samotná oprava P01 tuto vadu neřeší.

[Raw source a přijatý snapshot](evidence/pc007a-planar-review-P02-native-layout-overlap.json). Požadovaná oprava: při porovnání s tiskovým obrysem zahrnout doloženou vnější mez reprezentace a zůstat blokující při neurčitosti, nebo bezpečně adaptivně vyhodnotit skutečné nativní hranice. Nezměnit význam „bez kolize“ na „pro neznámý jiný obrys“. Stejný rozdíl mezi autoritou a projekcí je nutné posoudit i u příjemce/clearance; bez samostatné reprodukce zde tento třetí dopad není veden jako další prokázaný nález.

## Skutečně provedené ověření

- Přečtené dotčené zdroje zahrnují `profile_curves`, upravené project/model/paper/attachments/exporter a CurveSketch/editor, profilové umístění a hlavní okno. Přečten samostatný core curve report; jeho schválení není schválení topologie/layoutu nebo tohoto integračního pinu.
- Stávající dotčené profile/curve widget/workspace/domain/interior persistence/material testy byly reviewerem skutečně spuštěny: [71 PASS / 7,11 s](evidence/pc007a-planar-review-existing.xml).
- [Vlastní samostatné orákuly](evidence/pc007a-planar-review-own.py): [12 PASS / 2 FAIL](evidence/pc007a-planar-review-own-initial.xml). Dvě selhání jsou přesně výše uvedené P01/P02; neodstraňují se ani se nepřeznačují na přijatelné warning.

Vlastní pozitivní zkoušky ověřily skutečný otvor uvnitř konkávního vnějšího obrysu (trojúhelníky nevyplňují otvor ani chybějící roh), nativní kruhové CUT příkazy a původní segmentové identity; ortogonální rotace a zrcadlení zachovají rádius/koncové body a správně obrátí SVG sweep. Existující rovný šev/chlopeň na materiálu s jinou obloukovou hranou zachová skutečný A příkaz a samostatné tab UUID. Kružnice r=.1 má SMALL_DETAIL, r=2 a r=20 jej nedostanou jen kvůli hustotě tessellace.

Skutečný starší schema3 model A byl načten z diskové kopie, změněn novým copy_profile příkazem, vrácen/znovu proveden, následoval neúspěšný materiálový příkaz a pokus uložit na původní cestu. Původní cesta zůstala blokovaná, Save As zachoval její bajty a nová kopie se načetla beze změny.

Vlastní offscreen Qt případy zkontrolovaly no-op raw přesnost kubických řídicích bodů, staged Cancel bez mutace projektu, neúplné rozepsané číslo s odmítnutím dialogu a profilový copy dialog se skutečným psaním hloubky bez Enter. Nezávislé očekávání: původní rovina má `u=[.8,.6,0],v=[0,0,1]`, normálu `[.6,−.8,0]`; hloubka `1.25 m` posune počátek `[10,20,30]` na **`[760,−980,30] model mm`**. Jednotky modelu se nezamění s papírem, původní projekt se pouhým potvrzením návrhu nemění.

## Skills a meze závěru

Před revizí skutečně načteny čtyři projektové skills a příslušné AU08/AU13/AU15–17 a US přejímky. Konstrukce: materiálový obrys a díra mají přednost před display mesh; chlopeň není ztotožněna se vzorkovanou hranou. UI: staged vstup/no-op/cancel a číselná hloubka jsou kontrolovány skutečnými Qt událostmi; lepší použitelnost se neodvozuje ze vzhledu. Verification: explicitní nativní midpoint proti proxy a rozdíl topologické versus poziční meze odhalily P01/P02. Delivery: okamžité předání zásadních nálezů a nový review pin jsou podmínkou následného technického schválení.

Žádný nativní desktop/editor jsem v tomto úkolu nespouštěl; desktop rezervuje integrační owner. Zdejší offscreen Qt nenahrazuje skutečný Windows průchod, interoperabilitu SVG/PDF, studii s novým člověkem ani fyzický výtisk. AC-US08 má stále 0 účastníků a P3 je samostatně NOT_RUN. Tento report neposkytuje schválení vlastní loftové produkce reviewera ani celé PC-007A.

## Dodatečná nezávislá revize oprav — 820ab66

Zdroj oprav **`820ab6672d6a3f252391807b4c2c626c51a040bb`**, 9. 11. 2026. Výše uvedené původní nálezy a FAIL evidence zůstávají historicky platné pro e3a545f; nepřepisují se zpětně. **P01 a P02 jsou v novém pinu CLOSED / VERIFIED. Opravy rovinné topologie a materiálových/layout/exportních mezí jsou APPROVED_IN_SCOPE.** Tento technický závěr není schválení celé PC-007A ani nové loftové produkce reviewera, celého P2, studie s člověkem nebo fyzického proofu. Skutečný nativní průchod aktuálním integračním výsledkem provádí a dokládá integrační owner samostatně.

Protože v pracovním stromě souběžně pokračuje jiná práce, reviewer použil `git archive` přesného commitu do odděleného dočasného adresáře. Test skutečně importované cesty prošel; [manifest](evidence/pc007a-planar-review-820ab66-source.json) obsahuje exact pin, skutečný modul a SHA256 všech archivovaných aplikačních Python zdrojů. Žádnou rozpracovanou produkci reviewer neměnil ani do výsledku nepřimíchal. Před dotčenou prací byly znovu skutečně přečteny všechny čtyři projektové skills a relevantní AC.

- [Přehrání původních vlastních orákulů: 14 PASS / 1,59 s](evidence/pc007a-planar-review-820ab66-replay.xml). P01 nyní odmítne `add_surface` a zachová původní projekt; P02 zablokuje snapshot. Dřívější dva negativní testy zůstaly beze změny očekávání.
- [Nové nezávislé orákuly](evidence/pc007a-planar-review-fixed.py): [13 PASS / 2,79 s](evidence/pc007a-planar-review-820ab66-independent-expanded.xml). Mezery `.009` a především `.015 mm` mezi dvěma čistě rovnými díly v projektu obsahujícím křivku jsou blokující `CURVE_LAYOUT_UNRESOLVED`; `.025 mm` je volná. Při `.015 mm` by rezerva `.01 mm` jen na jedné straně nestačila, takže test konkrétně kontroluje obě hranice, také při rotacích 37°, 141° a 283°. Potvrzení této chyby se odmítá atomicky. V čistě úsečkovém projektu se umělá křivková nejistota nezavádí.
- Fyzický list: rovný soused v křivkovém workflow vzdálený `.005 mm` od okraje dostane hard `CURVE_SHEET_UNRESOLVED`, vzdálený `.025 mm` jej nedostane. Analytické body kolem kruhového otvoru při měřítku 1 a .01 doložily, že skutečný materiál je v možném obalu, garantovaný materiál nevstupuje do skutečné dutiny a střed otvoru zůstává prázdný.
- Vlastní fault injection změnil **skutečně zapsané** staged SVG na mělký křížící se kubický obrys z P01, přičemž zachoval očekávaný počet dílů i smyček. Publikace byla zablokována a všechny bajty předchozího exportního balíku zachovány; staging nezůstal. Nešlo pouze o kontrolu předserializačních dat.
- [111 cílených autorových regresí reviewerem skutečně spuštěno / 9,57 s](evidence/pc007a-planar-review-820ab66-targeted.xml): topology/material/export guard/profile curves/widgets/workspace/vector oracle. To doplňuje vlastní orákuly, nenahrazuje je. Úvodní [9 PASS](evidence/pc007a-planar-review-820ab66-independent.xml) bylo následně rozšířeno na výše uvedených 13; neopakuje se jako dalších 9 nezávislých případů. První běh nového harnessu [7 PASS / 2 FAIL](evidence/pc007a-planar-review-820ab66-harness-ack-error.xml) chybně očekával, že hard error lze potvrdit; produkt správně odmítl `acknowledge`. Harness byl opraven na explicitní očekávání odmítnutí. Tento FAIL není produktová regrese a byl zachován.

Přečtené opravy oddělují nativní topologický důkaz od poziční projekce: Bernsteinovy/analytické oddělovací důkazy, intervalové endpoint-form oblouky, přesné zlomky skutečných SVG/PDF operandů a explicitní neurčitost po vyčerpání rozpočtu. Materiálové možné/garantované množiny tvoří vnější obaly tětiv včetně koncových čepiček a numerické rezervy, otvorů a přesných rovných chlopní; cache a zdroj se před použitím porovnávají. Layout vytváří obaly v souřadnicích stránky a v křivkovém workflow rezervuje `.01 paper mm` na každém dílu včetně čistě rovných sousedů. Nejistý odstup/list se nestává přijatelným warning.

Meze skutečných vektorových kontrol jsou v reportech pojmenované pravdivě: PDF kontroluje skutečné souřadnice stránky, topologii a rozestupy (nebo konkrétně přijaté již známé překryvy); SVG postserializační kontrola prokazuje lokální CUT topologii a úplnost očekávaných dílů/smyček, **netvrdí přesný postserializační důkaz rozestupů na stránce**. SVG rozestupy stojí na zdrojových konzervativních obalech a rezervě formátu. Kontrolu nelze vydávat za obecný detektor libovolné změny platného tvaru proti zdroji nebo za důkaz fyzické sestavitelnosti. V pokrytém rozsahu nebyl nalezen další zásadní nález.

Skills se zde uplatnily konkrétně: konstrukce chrání skutečnou dutinu a vystřihovanou hranici; verification používá analytický midpoint a mezeru vyžadující rezervu obou stran, uchovává původní FAIL a hlídá skutečný import; UI zachovává atomické odmítnutí a vysvětlenou opravnou cestu místo potvrzení nejistoty; delivery vydává nový exact-pin závěr s omezeným rozsahem. AC-US08 má nadále **0 účastníků / NOT_RUN**, fyzický P3 **NOT_RUN**. GUI automat ani tato nezávislá technická revize je nenahrazují.
