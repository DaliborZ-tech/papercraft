# Prostorové ostění a rozvinutelná extruze — digitální přírůstek

11.11.2026. Ověřený **CODE `a46f179331a5ab94fec7b68ba52b2f9431ac699b`**. Tento přírůstek dodává B1, B2 a vlastní Bézierovu extruzi. Celé PC-007A/P2 pokračuje B3→D, C, zbývajícími změnami/provenance, výrobní konsolidací a závěrečným vlastním historickým modelem. Přijetí kontraktu vlastníkem není přijetím celé implementace. Nový uživatel: **0 účastníků / NOT_RUN**; fyzická stavba: **P3 / NOT_RUN**.

## Co lze použít

Z vlastních úsečkových, obloukových a kubických profilů lze vytvořit plochu mezi dvěma zdroji, určit párování a směr úseků i začátek rozvinu a později je upravit. B1 zachovává vlastní gotický otvor ve stěně a ostění s druhým profilem1,2× v nenulové hloubce; B2 je skutečný rovinný mezikruhový pás s dírou, nikoli falešný objem. Samostatně nakreslený kubický profil lze extrudovat do rozvinutelného pásu. Přesný režim je omezen doloženou rodinou; jiné cíle se odmítnou nebo zůstanou nerozhodnuté.

Zůstává propojený výběr3D↔papír, vlastní ruční stránky, přetažení, obě locks, Save/New/Open, undo a vektorové SVG/PDF. Zrušená editace náhledu nic nepřepíše. Náhled a vlastní zápis exportu běží na pozadí; Cancel před publikací zachová starý export, pozdní Cancel po začátku atomické publikace pravdivě ohlásí dokončení. Starší výsledek loftu se načte jako neaktuální a **Ctrl+R** jej výslovně obnoví při zachování zdrojů, kotev a rozmístění. Poškozená cache současného kontraktu je tvrdá chyba, nikoli cesta k automatickému přijetí.

Spuštění z kořene s připraveným prostředím: `.venv\Scripts\python.exe -m archpapercraft`. V nabídce **Vytvořit** použijte vlastní profil, **Kopie profilu do hloubky**, **Plocha mezi dvěma profily** a **Upravit profily a šev**. Pracovní příklady k otevření:

- [B1 — vlastní gotická stěna a ostění](evidence/pc007a-loft-B1-desktop-a46f179-run01/loft-B1/loft-B1.apcraft), [PDF](evidence/pc007a-loft-B1-desktop-a46f179-run01/loft-B1/export/model.pdf), [SVG ostění](evidence/pc007a-loft-B1-desktop-a46f179-run01/loft-B1/export/page-c76c2a80-0a87-4885-8810-4e5dc8680ca9.svg).
- [B2 — rovinný kruhový pás](evidence/pc007a-loft-B2-desktop-a46f179-run01/loft-B2/loft-B2.apcraft), [PDF](evidence/pc007a-loft-B2-desktop-a46f179-run01/loft-B2/export/model.pdf), [SVG pásu](evidence/pc007a-loft-B2-desktop-a46f179-run01/loft-B2/export/page-749de8c4-14aa-4447-842b-eefa96f38c3a.svg).
- [Bézier — vlastní profil a extruze](evidence/pc007a-loft-Bezier-desktop-a46f179-run01/loft-Bezier/loft-Bezier.apcraft), [PDF](evidence/pc007a-loft-Bezier-desktop-a46f179-run01/loft-Bezier/export/model.pdf), [SVG](evidence/pc007a-loft-Bezier-desktop-a46f179-run01/loft-Bezier/export/page-32c72169-6e7a-4c2a-926a-2cd50adef59e.svg).

Jde o projekty vytvořené skutečnými Qt vstupy v aplikaci, nikoli o připravené JSON vložené do controlleru. V PDF tiskněte100 % / skutečná velikost a ověřte100mm kalibraci; uvedený digitální důkaz není skutečný výtisk.

## Co bylo skutečně ověřeno

| Připnutý průchod | Výsledek |
|---|---|
| [Celá regresní sada](evidence/pc007a-integrated-suite-a46f179-run01.xml), [úplný log](evidence/pc007a-integrated-suite-a46f179-run01.log) | **1179 PASS /220,34s**, žádný přeskočený případ |
| [Windows B1](evidence/pc007a-loft-B1-desktop-a46f179-run01/results.json) | PASS_REQUESTED_FIXTURE /198,891s |
| [Windows B2](evidence/pc007a-loft-B2-desktop-a46f179-run01/results.json) | PASS_REQUESTED_FIXTURE /52,64s |
| [Windows Bézier](evidence/pc007a-loft-Bezier-desktop-a46f179-run01/results.json) | PASS_REQUESTED_FIXTURE /30,25s |
| Inkscape1.4.4: [B1 stěna](evidence/pc007a-loft-B1-inkscape-a46f179-wall-run01/editor-results.json), [B1 ostění](evidence/pc007a-loft-B1-inkscape-a46f179-loft-run01/editor-results.json) | oba PASS |
| Inkscape: [B2 disk](evidence/pc007a-loft-B2-inkscape-a46f179-disk-run01/editor-results.json), [B2 pás](evidence/pc007a-loft-B2-inkscape-a46f179-band-run01/editor-results.json), [Bézier](evidence/pc007a-loft-Bezier-inkscape-a46f179-run01/editor-results.json) | všechny PASS |

Windows běhy procházejí od prázdného projektu přes skutečné kreslení a číselné vstupy, náhled, editaci/Cancel, ruční stránky a locks, 3D výběr, nativní uložení/nový/otevření/export až po nezávislé čtení vektorů. Guard ověřuje Git SHA, hashe zdrojů i skutečnou importovanou cestu worktree. Použit skutečný NVIDIA OpenGL4.6, nativní Windows dialogy a skutečný Inkscape včetně psaní víceslovného Unicode popisku a uložení. Samotné opakování implementátorem ani GUI automat není test s novým člověkem.

**LX-01:** původní export měl9049 příkazů a Inkscape změnil i normativní plochu. Ohraničené slučování zachovalo obloukové C, rohy, generátory a původ úseků a zmenšilo B1 na21 příkazů, z toho16C. [Přesné čtení aktuálního roundtripu](evidence/pc007a-loft-B1-inkscape-a46f179-loft-run01/diagnostic-reserialization.json) dává maximum změny souřadnice2,2575571e−6mm a změnu Greenovy plochy2,1645146356e−5mm². Vyhovuje i původnímu přísnému editorovému prahu2e−5; norma, harness ani preference editoru se nezvětšily. Celý source→actual SVG/PDF řetězec má navíc samostatnou původní polohovou, topologickou a plošnou kontrolu; malý editorový rozdíl sám tento řetězec nenahrazuje. Historické FAIL běhy9049 a69 příkazů jsou uchované v [průběhu](PC007A_LOFT_PROGRESS.md).

## Revize, rizika a další práce

Komponenty mají vlastní nezávislé revize: [doména](PC007A_LOFT_DOMAIN_REVIEW.md), [intrinsic plocha](PC007A_LOFT_INTRINSIC_AREA_REVIEW.md), [widget](PC007A_LOFT_UI_REVIEW.md), [workspace](PC007A_LOFT_WORKSPACE_REVIEW.md), [skutečný výstup](PC007A_LOFT_OUTPUT_REVIEW.md), [výkon/cache](PC007A_LOFT_PERFORMANCE_REVIEW.md), [export na pozadí](PC007A_EXPORT_JOB_REVIEW.md), [slučování](PC007A_LOFT_COALESCING_REVIEW.md) a [V4 rezerva/SK-012](PC007A_LOFT_COALESCING_V4_REVIEW.md). Integrační review konkrétního CODE a finální metadata se evidují samostatně před publikací; autor si nezávislé schválení neuděluje.

První B1 náhled trval87,078s a editovaný náhled30,422s při souběžných testech. Je to dosud citelné čekání, i když lze návrh zrušit; nejde o izolovaný výkonový benchmark. Exportní worker nezaručuje odezvu během předchozí tvorby snapshotu na hlavním vlákně. Jeden první full-suite pokus na historickém73f3437 skončil [Windows access violation při GC](evidence/pc007a-integrated-suite-73f3437-run01-abort.json); příčina zůstává UNRESOLVED, úplný stderr chybí. Následné celé sady1175 a1179 i všechny uvedené skutečné aplikace prošly; tento incident se neskrývá tvrzením o dokonale stabilním prostředí.

Následuje potvrzená segmentovaná varianta D a B3, C s autorskými dělenými chlopněmi, povinné změny společného dílu a split/merge provenance, PC-009/DPI/klávesnice, PC-010/historická architektura a chybějící AC-US08. Jediný aktuální stav určuje [queue](../../../05_WORK_QUEUE.json). Původní přijetí celého P2 v1.2 a autorizace dalších řezů zůstávají platné; tento dílčí digitální výsledek nevyvolává další rutinní produktovou bránu.
