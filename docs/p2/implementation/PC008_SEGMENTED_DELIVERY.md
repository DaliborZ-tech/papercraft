# D a gotické B3 — digitální přírůstek řízené aproximace

11.11.2026. Ověřený **CODE `e7826dd9b8b90843cdba72a6ae6fd52f0936a1ea`**. Odvozený materiál nyní projde skutečnou aplikací až po oba vektorové výstupy; původní hladký cíl zůstává uložený a není falešně označen EXACT. [Finální nezávislá revize](PC008_INTEGRATION_REVIEW.md) schválila tento D/B3 technický přírůstek bez otevřených nálezů; [integrace a publikace](PC008_INTEGRATION.md) evidují skutečný následný stav. Celé PC-008/P2, nové lidské použití a fyzické sestavení tím nejsou dokončené.

## Výsledek pro autora

Z prázdného projektu lze nakreslit dva vlastní profily a vytvořit plochu mezi nimi. Při odmítnutém přesném rozvinu lze opravit tvar/párování, nebo výslovně uchovat konstrukční cíl a použít **Vytvořit → Odvodit rovinné díly s povolenou odchylkou**. Autor zadá např.0,25mm na papíře, porovná původní cíl a skutečné nové díly, uvidí konzervativní polohovou/délkovou/normal-angle mez a počty dílů/řezaných spojů a výslovně přijme konkrétní výsledek. Nepodařený nebo neaktuální náhled potvrdit nelze. Počítání na odděleném projektu nezmění živý model.

Výsledkem jsou samostatné rovinné díly s globálně jedinečnými krátkými názvy P4,P5… pro tisk. Popisný konstrukční kontext zůstává ve stromu/vlastnostech. Starší nebo vlastní autorské názvy se při otevření nemění. Každý díl má zdrojovou identitu, UV intervaly a párované řezy; geometrie původního cíle, starší generace i jejich vlastní layout zůstávají zachované. Tiskne se jen výslovně zvolená aktuální generace. Změna zdroje ji zneaktuální a export zablokuje; lze změnu vrátit nebo potvrdit novou generaci. Změna aktuálního materiálu se nesmí skrýt jako pouhé staré cache.

**Ruční rozmístění více dílů** nechává autora vybrat Ctrl/Shift díly, stránku, počátek/rozteče, sloupce a případné společné natočení. Náhled nevymýšlí rozmístění ani neodemkne zámky. Původní drag a jednotlivá čísla zůstávají použitelné; celý hromadný krok má jedno undo. Původní cíl lze prohlédnout nebo vrátit pro tisk; je-li stále nerozvinutelný, jeho export pravdivě zůstane blokovaný.

SVG i PDF vycházejí ze stejného snapshotu. Odvozené díly mají vůči původnímu cíli metadata **APPROXIMATE**; jejich rovinný materiál lze rozvinout přesně, což neuděluje přesný rozvin původní hladké ploše. Lepicí spoje/chlopně jsou samostatná autorská práce a mají vlastní kontroly. Samotný aproximační certifikát trojúhelníkového jádra je neschvaluje.

## Skutečné projekty a důkazy

- [LINE D — vlastní projekt](evidence/pc008-D-line-desktop-e7826dd-run01/D-segmented/D-segmented.apcraft), [PDF](evidence/pc008-D-line-desktop-e7826dd-run01/D-segmented/export/model.pdf), [SVG1](evidence/pc008-D-line-desktop-e7826dd-run01/D-segmented/export/page-5371efa4-7f00-45b7-8cff-c539cc048b35.svg), [SVG2](evidence/pc008-D-line-desktop-e7826dd-run01/D-segmented/export/page-d14fdf16-69e6-455e-92df-662a5136f1eb.svg). Vlastní dva úsečkové profily dávají prokazatelně nerozvinutelný cíl `S=(40u,20uv,30v)` paper mm,64 dílů/84 párovaných řezů a ručně32+32 dílů na dvou stránkách.
- [B3 — samostatně nakreslené gotické otvory](evidence/pc008-D-gothic-desktop-e7826dd-run01/D-gothic/D-gothic.apcraft), [PDF](evidence/pc008-D-gothic-desktop-e7826dd-run01/D-gothic/export/model.pdf), [SVG1](evidence/pc008-D-gothic-desktop-e7826dd-run01/D-gothic/export/page-c67c7cdb-0a2a-469b-a1cf-f8220fd458a9.svg), [SVG2](evidence/pc008-D-gothic-desktop-e7826dd-run01/D-gothic/export/page-6149ff66-8df0-4a54-89c1-88e228249666.svg). Otvory mají40×30 a36×25mm, rovnoběžné zdrojové roviny jsou10mm od sebe. Druhý otvor je znovu kreslený, nikoli kopie hotového domu nebo homotetický preset. Součástí průchodu je skutečná numerická úprava konců a oblouků. EXACT se odmítne; potvrzená varianta má96 trojúhelníků a dvě skutečné stěny s otvory, tedy98 tiskových dílů na dvou ručních stránkách48+48 a obě stěny.

| Ověření přesného CODE | Skutečný výsledek |
|---|---|
| [Celá sada](evidence/pc008-integrated-suite-e7826dd-run01.xml), [úplný log](evidence/pc008-integrated-suite-e7826dd-run01.log) | **1370 PASS /315,60s**,0 failures/errors/skips |
| [Windows LINE D](evidence/pc008-D-line-desktop-e7826dd-run01/results.json) | PASS_REQUESTED_FIXTURE /39,109s |
| [Windows Gothic B3/D](evidence/pc008-D-gothic-desktop-e7826dd-run01/results.json) | PASS_REQUESTED_FIXTURE /99,313s |
| Inkscape LINE [strana1](evidence/pc008-D-line-inkscape-e7826dd-page1-run01/editor-results.json) / [strana2](evidence/pc008-D-line-inkscape-e7826dd-page2-run01/editor-results.json) | oba PASS /17,641s a15,5s |
| Inkscape Gothic [strana1](evidence/pc008-D-gothic-inkscape-e7826dd-page1-run01/editor-results.json) / [strana2](evidence/pc008-D-gothic-inkscape-e7826dd-page2-run01/editor-results.json) | oba PASS /19,203s a15,703s |

Oba Windows běhy začínají skutečně prázdnou aplikací přes `app.main`, mají vlastní PID, source SHA/hashe/importy, skutečný OpenGL a nativní Save/New/Open/Export. Geometrie se nevkládá do controlleru ani nepřipravuje JSON injekcí. Driver provádí také nemožný hard-budget negativ, oddělený náhled, explicitní potvrzení, ruční výběr a grid, undo-redo celého kroku, drag/obě locks, source edit→STALE→Undo a skutečné propojené vybrání odvozeného dílu v3D. Oddělené orákulum čte původní analytické profily/UV a skutečné SVG/PDF plochy i oba gotické otvory. Editorové důkazy používají skutečný Inkscape včetně posunu, barvy, víceslovného Unicode psaní a uložení; původní exportní bundle zůstává beze změny.

## Kontrakty a nezávislé revize

[LINE doména95](PC008_SEGMENTATION_DOMAIN_REVIEW.md), [matematika zakřivených zdrojů3a](PC008_SEGMENTATION_CURVES_REVIEW.md), [batch API651/BP01](PC008_BATCH_PLACEMENT_REVIEW.md), [UI1f/DU01](PC008_UI_REVIEW.md) a [source→actual writer5ad/SO01](PC008_SEGMENTED_OUTPUT_REVIEW.md) jsou nezávisle schválené komponenty. SO01 zachovává přímou plošnou kontrolu celého materiálu s chlopněmi, ale relativní tolerance má původní základ samotného těla. Po sobě jdoucí výpočty nedostávají každý znovu celou původní toleranci. Původní mezivýsledky, neúspěchy a jejich skutečný rozsah zůstávají uložené.

Výstupní kontrola uzavírá celý zdrojový projekt včetně živého cíle, dějin generací, skutečných child profilů/ploch/frame/labels, spojů, chlopní a placements. Kanonický readonly replay musí odpovídat snapshotu; samotný hash, text APPROXIMATE ani dodaná cache nestačí. Samostatní čtenáři ověří skutečné SVG/PDF souřadnice, pokrytí, topologii, délky a čistou plochu přímo proti zdrojovému materiálu. Selhání nezmění dřívější owned ani cizí soubory. Source binding má konečné limity32MiB/depth64/nodes500000/4096 parts/8 generations/64 pages/cache2; přesáhnutí znamená bezpečné odmítnutí, nikoli potlačenou chybu. Vektorové zdrojové metadata mají v doložených bězích řádově megabajty.

Formát5 je experimentální autorská doména; známé starší autorské formáty včetně4 se otevírají jako ověřené kopie se SaveAs a bez přepsání originálu. Původní staré projekty mimo známý copy adaptér zůstávají read-only. Nejde o úplnou migraci staré báně/gotiky ani novou podmínku uzavřeného objemu.

## Co zůstává otevřené

Finální integrační review spojilo právě tento CODE, nové skutečné artefakty a metadata a uzavřelo opravu čitelných označení DU02. Celé PC-008 ještě vyžaduje aplikační split/merge provenance a povinné změny společného dílu/trimů. C těla a dělené chlopně, výrobní/klávesnicová/DPI konsolidace PC-009 a závěrečný vlastní historický model PC-010 zůstávají v autorizovaném rozsahu. **AC-US08:0 nových účastníků / NOT_RUN; fyzický výtisk a sestavení P3 / NOT_RUN.** Technický GUI průchod ani matematika tyto důkazy nenahrazují. Aktuální stav a další autonomní práce: [queue](../../../05_WORK_QUEUE.json).
