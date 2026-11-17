# C — stočený plášť a autorské dělené chlopně

11.11.2026. Technický přírůstek v autorizovaném P2 v1.2, integrační owner root.
Dokončení celého P2, nového uživatelského testu a fyzického P3 zůstává samostatné.
Finální integrační revize a publikace tohoto přírůstku jsou právě rozpracované.

Autor nakreslí vlastní kruhový profil, vytvoří druhý profil a plášť, vybere
skutečný krycí disk a kontaktní stranu a navrhne dělené trojúhelníkové chlopně.
Počet, šířka nebo mezera, hloubka, nelepící pás, minimální lepicí plocha,
vypnutí jednotlivého slotu a posun vrcholu jsou editovatelné. Náhled pracuje
na oddělené kopii; potvrzení uloží autorský záměr a označí rozvin k přepočtu.
Materiál i návrh lze vrátit jedním Undo. Ruční stránky, rotace a zámky zůstanou
zachované po uložení a otevření.

Válec i souosý kuželový pás mají přesný rozvin těla. Kruhový spoj je výslovně
omezená aproximace: samostatně ověřuje zdroj, nativní materiál, deformující
se nelepící pás, dostupnou lepicí plochu, sousední chlopně a vymezený pohyb
v sestavě. Neověřená situace zůstává UNRESOLVED; neznámá tloušťka neprohlašuje
materiálovou vůli. Digitální geometrická mez1 % neurčuje pružnost ani pevnost
papíru. Skutečný výtisk a sestavení patří do P3.

Sdílená základna chlopně je jednou jako značený ohyb, nevzniká dvojitý řez.
SVG nese nativní kruhové oblouky a oddělené CUT/TABS/GUIDES/LABELS. PDF zůstává
vektorové a jeho aproximace se kontroluje na skutečných číselných operandech.
Ověření source/native deformace a ověření výrobních vektorových metrik jsou
samostatné důkazy. Grafické kontrolní body PDF nejsou novým modelem deformace.

## Zdroj, revize a regrese

Produkční zdroj **8f1ec6382d527c719133958e7eb6f78a724ef5d5** integruje
samostatně revidovanou [geometrickou základnu](PC007B_CIRCULAR_BODY_FOUNDATION_REVIEW.md),
[přenos zdroje](PC007B_SOURCE_TRANSFER_PROOF.md),
[composer/doménu/publikaci](PC007B_CIRCULAR_PRODUCER_REVIEW.md)
a [UI](PC007B_CURVED_AUTHORING_UI_REVIEW.md). CUI01–CUI04 jsou uzavřené na
`e1c06f5`; reviewer jiný než autor provedl vlastní chyby a jejich replay.

Celá stávající sada na8f: **1751 PASS,0 failures/errors/skips,574,32s**.
[Původní JUnit, plný log a pravdivě dodatečně zaznamenaná vazba](evidence/pc007b-c8-full-8f1ec63-run01/binding.json).
Nový diagnostický čteč SVG je na **52836321810f7a8a0c6a8d43b801f98ed875bbde**;
produkční `src` je oproti8f byte-identický. Má samostatných16 testů PASS.
Počty těchto odlišných výběrů se nevydávají za jeden opakovaný úplný běh.

Kombinovaný experimentální formát8 umí kopírovací načtení známého C6 i LINE7,
zachová zdroje, identity, staré cache, kotvy a ruční layout. Uložení kopie
chrání původní soubor. Podstrčené nové registry ve starém obalu se odmítnou.
Kontroly C obsahují i relevantní historii vzdáleného materiálového dílu;
jeho původní papírová osa se rozřeší sémanticky po rozdělení.

## Skutečný průchod a výstupy

Ve všech případech se kreslí od prázdného projektu skutečnými widgety.
Průchod zahrnuje náhled, Cancel, chybějící materiál a opravu v dialogu,
chybnou kontaktní stranu, příliš širokou chlopeň a opravu, vypnutí slotu0,
úpravu vrcholu slotu1, Undo/Redo, explicitní přepočet, volný i zamčený ruční
přesun, propojený3D/2D výběr a nativní dialogy Save/New/Open/Export.

| Model | Nativní Windows důkaz | Stav |
|---|---|---|
| Válec r10/h30 | [8f run02](evidence/pc007b-C-cylinder-desktop-8f1ec63-run02/results.json),111,719s | PASS technické UI |
| Kužel r10→20, nominální s30 | [8f run02](evidence/pc007b-C-cone-desktop-8f1ec63-run02/results.json),157,266s | PASS technické UI |
| Téměř válec r10→10,00001/h30 | [528 run02](evidence/pc007b-C-near-desktop-5283632-run02/results.json),132,078s | PASS technické UI |

Každý případ má dvě ručně rozmístěné stránky, vlastní editovatelný `.apcraft`,
snapshot, všechna SVG a PDF, screenshoty, zdrojové/importní vazby a SHA256
přímo v uvedené složce. Kuželový vstup má hloubku28,28427125 paper mm kvůli
skutečně zadaným šesti desetinným místům modelového vstupu; očekávání se
počítá ze skutečného zdroje. Jeho odchylka od nominálního s30 nepřepisuje AC.

Nezávislá očekávaná plocha materiálu válce s11 aktivními chlopněmi je
1897,4955921538758mm²; skutečné PDF1897,4955921538685. Kužel očekává
2839,973323116419mm²; skutečné PDF2839,9732485552063. Tolerance zůstává
původní `max(.01, 1e-6 * original_body_area)`; chlopně nezvětšují relativní
základ tolerance. Nezávislé orákulum používá analytickou plochu pláště
a trojúhelník s orientovanou kruhovou úsečí; nevolá výrobní geometrii.

Obě stránky válce i kužele prošly skutečným Inkscapem1.4.4: přesun celého
dílu, barva a víceslovný Unicode text, zachované identity/role, kalibrace a
nezměněný původní soubor. Důkazy `pc007b-C-*-inkscape-8f1ec63-page*-run01`
jsou v [evidence](evidence/). Krycí stránka téměř válcového případu také prošla
(18,375s); stránka pláště má zachovaný editorový FAIL (19,5s) popsaný níže.

## Nálezy a poučení

První kuželový běh na d5 zůstává FAIL: krycí disk ve správné světové poloze
byl odmítnut kvůli rozdílu mezi zdrojovou rovinou a běžným posunem plochy.
`e42ee67` podporuje přesně doložený posun při identické jednotkové lineární
části. Používá původní racionální binární operandy, žádné přichytávání středu.
Jedna representovatelná odchylka v posunu se nadále odmítne. Neprokázaná
relativní rotace zůstává UNRESOLVED.

První téměř válcový běh8f zůstává FAIL závěrečného testovacího orákula.
Původní float čteč SVG ztratil přesnost při odčítání velkých členů kruhu
s poloměrem≈30milionůmm. Samostatné původní tokeny dávají při stabilním
Decimal Greenově čtení1897,496534642135230mm² proti analytickému očekávání
1897,496534631882340; nezávislý reviewer rozdíl≈1,03e-8mm² potvrdil vlastním
výpočtem. Oprava se týká diagnostického čteče a opakovaného běhu; výrobní
tolerance i původní FAIL zůstaly zachované.

Editorový FAIL na stránce téměř válcového pláště má odlišnou příčinu:
Inkscape zaokrouhlil parametr poloměru≈30000000,004 na30000000. Původní
porovnání všech operandů vyhodnotilo rozdíl0,004mm jako změnu souřadnice.
Nezávislé přímé čtení skutečného uzavřeného CUT před/po uložení ukazuje
rozdíl plochy≈1,29e-6mm². Toto dílčí měření ještě nedokazuje shodu celé
křivky a její délky. Doplnění plné geometrické kontroly a následný skutečný
editorový replay jsou PENDING; polohová mez2e-5 ani výrobní metriky se
nezvětšují. Původní selhání zůstává v
[původním reportu](evidence/pc007b-C-near-inkscape-5283632-page2-run01/editor-results.json).

[Diagnostické iterace kombinace](evidence/pc007b-combined-format-diagnostics-run01/README.md)
oddělují skutečnou integrační vadu historické osy od chyb fixture a spuštění.
SK013 přenos na přepínač C odhalil také odmítnuté rozepsané vstupy; produkt
opraven, cizí replay proběhl, další účinek zpřesněné rady zůstává pending.

## Zbývající rozsah

Live dělení oblouků/Bézierů, trim/phi a úplné smíšené kotvy pokračují v PC-008
s oddělenou verzí9 formátu a kopírovacím zachováním formátu8. Celý PC-007B
ani AU13 se tímto omezeným přírůstkem neprohlašují dokončené. PC-009 sjednotí
průchody a výstupy, PC-010 vytvoří vlastní historický model přes skutečné UI
a dodá závěrečné nezávislé ověření. **AC-US08:0 nových lidí/NOT_RUN;
fyzické P3/NOT_RUN.** Produktové přijetí kontraktu zůstává platné a není
přijetím dokončené implementace.
