# PC-007A — dílčí předání rovinných autorských křivek

9. 11. 2026. Autor může v aplikaci nakreslit vlastní úsečky, kruhové oblouky a Bézierovy křivky, vytvořit skutečný otvor, upravit úsek, bezpečně změnu vrátit, přidat chlopeň na přímé hraně, ručně rozmístit díly a vydat obě vektorové podoby. [Nezávislá integrační revize](PC007A_PLANAR_INTEGRATION_REVIEW.md) schválila tento konkrétní rovinný podbalík na **`63ab275a5fe9b92bdb370a5ec3dedf1c5f70a65e`**; produkční `src` odpovídá `3252544`, následující změna pouze zpřesňuje pozorování skutečného doručení klávesových zkratek v harnessu.

**Celý PC-007A zůstává IN_PROGRESS.** Prostorové ostění B1, B2/B3 a extruze Bézier zatím nemají integrované skutečné UI předání. Jejich numerika a rozpracovaný doménový přírůstek nejsou vydávány za dokončené B. C/D, další povinné kotvy a závěrečný vlastní historický model PC-010 zůstávají v autorizované frontě. AC-US08 má stále **0 účastníků, NOT_RUN**; vlastník nemá nového uživatele k dispozici. Fyzický výtisk a sestavení jsou P3.

## Co lze otevřít a vyzkoušet

V připraveném kořenovém checkoutu spusťte `.venv\Scripts\python.exe -m archpapercraft` a otevřete [editovatelný projekt](evidence/pc007a-desktop-63ab275-run04/curves-planar/curves-planar.apcraft). Vznikl od prázdného modelu skutečným klikáním a psaním v aplikaci, bez vložení hotové geometrie do controlleru nebo JSON. Obsahuje stěnu 12×10 modelových metrů s kruhovým otvorem průměru 4 m v měřítku 1:100, samostatný vlastní Bézierův díl s chlopní a protikus. Tři díly jsou ručně rozmístěné na dvou listech.

Vyberte díl ve 3D nebo na papíře, zvolte jeho úsek ve vlastnostech a použijte „Upravit vybraný úsek profilu“. Změnu lze zrušit v dialogu nebo vrátit Ctrl+Z. Oblouk se kreslí přes průchozí bod, Bézier přes dva úchopy; prázdný a rozpracovaný stav vysvětluje následující krok. Kopie profilu do hloubky zachová původní skicu a vytvoří nové identity. Přímé švy se nenahrazují tětivou zakřivené hrany.

Při kreslení zůstává neplatný návrh k opravě; staged editace ani dialog chlopně nemění zdroj před potvrzením. Ruční stránka, natočení, zámky a přepočet zůstávají součástí stejného workflow. Tipy lze vypnout a opakovaně vyvolat, přímé akce a zkratky zůstávají dostupné. Toto je technicky ověřené ovládání; nejde o pozorování nového člověka.

## Skutečné digitální důkazy

- [Windows průchod](evidence/pc007a-desktop-63ab275-run04/results.json): **PASS, 63,406 s**, `app.main`, skutečný modul z připnutého worktree, NVIDIA OpenGL 4.6, tři nativní Save/Open/Export dialogy. Pozorovány skutečné `QAction.triggered`, včetně dvou přepočtů a jednoho exportu, nikoli pouze odeslané klávesy.
- [Celá testovací sada](evidence/pc007a-suite-63ab275-run03.xml): **908 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, 76,47 s. Dílčí a nezávislé běhy nejsou přičítány jako další unikátní testy.
- [Snapshot](evidence/pc007a-desktop-63ab275-run04/curves-planar/snapshot.json), [PDF](evidence/pc007a-desktop-63ab275-run04/curves-planar/export/model.pdf), [SVG první stránky s otvorem](evidence/pc007a-desktop-63ab275-run04/curves-planar/export/page-878bc2af-ea42-4965-a195-8f649d9f0c9b.svg), [SVG druhé stránky s Bézierovým dílem](evidence/pc007a-desktop-63ab275-run04/curves-planar/export/page-d7504779-c410-4310-9979-a218d653b519.svg), [manifest](evidence/pc007a-desktop-63ab275-run04/curves-planar/export/.author-export.json).
- Skutečný Inkscape 1.4.4: [Bézierova stránka](evidence/pc007a-inkscape-63ab275-page1-run03/editor-results.json) **PASS / 14,500 s**, [stránka s otvorem](evidence/pc007a-inkscape-63ab275-page2-run04/editor-results.json) **PASS / 14,093 s**. Názvy adresářů jsou pořadí editorových běhů; skutečné vstupní soubory jsou uvedené v `origin_source`. Posun skupiny, barva a skutečně napsaný Unicode popisek zachovaly nativní A/C, otvory, ostatní texty, role, jednotky i kalibraci. Originální balík zůstal nezměněný.

| Nezávislé očekávání | Skutečné SVG | Skutečné PDF |
| --- | ---: | ---: |
| Stěna 120×100 paper mm | 12000 mm² | 12000 mm² |
| Otvor R20, plocha 400π | 1256,637061436 mm² | 1256,633813685 mm² |
| Čistá stěna bez otvoru | 10743,362938564 mm² | 10743,366186315 mm² |
| Bézierova plocha 2060 + chlopeň 128 | 2188 mm² | 2188 mm² |
| Protikus 80×10 | 800 mm² | 800 mm² |

Odchylka čisté plochy stěny je **0,003247751 mm²**, pod původní normou **0,010743363 mm²**. Je doložená Greenovým integrálem skutečných serializovaných PDF kubik a samostatným orákulem; neposuzuje se pouze tětivový náhled. Polohová a plošná tolerance jsou dvě různé přejímky.

## Revize a opravy, které předání podmiňují

[P01/P02](PC007A_PLANAR_REVIEW.md) odhalily nativní průnik a překryv mezi platnými zobrazovacími tětivami. Samostatná nativní topologie a garantovaný/možný materiál nyní blokují neprokázaný odstup. Kontrola zahrnuje také příjemce chlopně a celý ohyb; neurčitost jiné překážky nesmaže jistou kolizi. [Materiálová revize](PC007A_MATERIAL_INTEGRATION_REVIEW.md) rozlišuje zdrojové a artefaktové důkazy. Výpočet konkrétní bezpečně vzdálené křivkové překážky klesl z 53,84 na přibližně 2,28 s pomocí doložených celointervalových vyřazení, nikoli ignorování překážek.

[V01](PC007A_VECTOR_OUTPUT_REVIEW.md) opravil ztrátu číselných lexémů před float převodem. Skutečný soubor se čte přesně, včetně CTM a vlastností stránky. [V02 a následná oprava](PC007A_AREA_INTEGRATION_REVIEW.md) zachovávají původní nevyhovující PDF a příliš volný testovací práh. Publisher nyní kontroluje čisté plochy skutečného SVG/PDF a zpřesňuje oblouky nejvýše čtyřmi pokusy bez změny normy. Neúspěch zachová celý předchozí balík i cizí soubory. Přesnější zápis CTM odstraňuje zbytečnou plošnou chybu rotace.

Nativní [run01](evidence/pc007a-desktop-61168e0-run01/results.json) zachytil skutečný points-only bug náhledu chlopně; oprava používá společný renderer nativních cest. [Run02](evidence/pc007a-desktop-2944c0f-run02/results.json) má historický harness PASS, ale jeho PDF nezávisle nesplnilo V02 — proto není finálním kladným důkazem. [Run03](evidence/pc007a-desktop-3252544-run03/results.json) nedokončil exportní dialogovou sekvenci; přesnou příčinu nedoručené zkratky nelze zpětně doložit. Run04 výslovně aktivuje okno a pozoruje spuštění akcí.

Původní [editorový Bézier FAIL](evidence/pc007a-inkscape-2944c0f-bezier-run02/editor-results.json) byl nezávisle odlišen od vady produktu: Inkscape nahradil závěrečnou přímou `L` stejnou uzavírací hranou `Z`. Harness nyní normalizuje pouze přesnou shodu, zachovává C/A i skutečně odlišnou krátkou hranu. Nové skutečné roundtripy prošly.

## Meze a pokračování

Schema 4 je experimentální autorský formát s nativními profily. Rozpoznané starší projekty se otevírají jako kopie, původní soubory nelze přepsat ani po undo či chybě příkazu. Historický prototyp i důkazy zůstávají zachované. Tento podbalík neuzavírá produkční doménu na preset domu ani nezaručuje obecné prostorové loftování.

Platí původní [kontrakt v1.2](../v1.2/P2_IMPLEMENTATION_CONTRACT.md), [akceptace](../v1.2/ACCEPTANCE.md) a jediná [queue](../../../05_WORK_QUEUE.json). Navazuje integrace ostění B a extruze přes skutečné UI, potom C/D a závěrečný historický model. Nový člověk ani fyzický výtisk nejsou nahrazené implementátorem nebo automatem. Integrace tohoto podbalíku není produktové přijetí celé P2.
