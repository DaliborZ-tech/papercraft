# PC-008 — zachovaný cíl a potvrzené odvozené generace

Komponentový zdroj domény: `95fa2c7c0e5a5d50f0763ae2a461a4e5e2821872`.
Samostatný hromadný příkaz: `0210118e02dd7f65dc6161b5f86cfda2b2dbdf29`.
Základ `a31d3ee` a schválená numerika `eeaf081`, review `62248d7`.
Nezávislé schválení nové domény a batch příkazu zůstává **PENDING**.

Původní `ruled_loft`, jeho živé profily, explicitní korespondence a autorský díl
zůstávají v témže projektu. `SegmentedVariant` ukládá neměnnou zdrojovou kopii,
geometrický fingerprint, zadaný rozpočet, skutečný certifikát a source/UV mapování
každého odvozeného trojúhelníku. Trojúhelníky mají vlastní profily, surface UUID,
part UUID, kotevní frame a umístění. Párovaný řez odkazuje na oba skutečné edge UUID.
Výstupní index numerické komponenty není persistentní identita.

Pro cíl může tisknout jedna potvrzená generace nebo původní cíl. Ostatní generace
včetně jejich layoutu zůstávají zachované. Není to obecná volba ignorování chyb:
registr a jeho původ se ověřují celý, nesouvisející tiskové díly se validují běžně
a zastaralá vybraná varianta blokuje snapshot. Obnovení původního odmítnutého cíle
z něj neudělá EXACT ani exportovatelný model. Spoje k externímu materiálu nelze
při změně generace potichu přemapovat; autor je musí výslovně upravit.

Veřejné příkazy na `AuthorProject`:

- `preview_segmented_variant(target_id, max_deviation_mm=.25, max_cells=4096,
  max_depth=16)` vrací oddělený náhled a token. `preview_geometry` obsahuje skutečné
  world souřadnice budoucích materiálových frames, source patch UUID a parametry.
- `add_segmented_variant(target_id, preview_digest=token, ...)` znovu ověří živý
  zdroj; nepřijímá mesh ani připravený projekt. Neaktuální token a UNRESOLVED
  skončí `SegmentationError` bez částečné změny.
- `update_segmented_variant(old_id, preview_digest=token, ...)` vytvoří novou
  neměnnou generaci a zachová předchozí. `select_segmented_variant(id)` a
  `restore_segmented_target(target_id)` výslovně mění tiskový výběr.
- `segmented_variant_status(id)` vrací APPROXIMATE, STALE nebo UNRESOLVED se
  zdrojem a důvodem. Fingerprint zahrnuje skutečné body, IDs, roviny, pose,
  měřítko a korespondence; samotná revize není důkaz aktuálnosti.
- `material_part_ids()` a `print_material_view()` vymezují skutečný materiál.
  Layout, snapshot a přímé bend dotazy používají tuto shodnou volbu.
- `set_placements({part_id: {page_id, x_mm, y_mm, rotation_deg, ...}})` aplikuje
  pouze explicitní volby autora v jednom doménovém rollback/validate kroku.
  Nevolí stránku, rozteč, natočení ani packing a neobchází zámky. Jeden undo
  vrátí celý příkaz; stávající controller má navíc vlastní validační hranice.

Snapshot odděluje materiálové, referenční a neaktivní surface IDs. Původní
odmítnutý stav je v `construction_checks.reference_targets`, potvrzený důkaz
v `segmented_variants`. Každý odvozený díl má `flattening.mode=APPROXIMATE` vůči
zachovanému cíli a zvlášť `material_surface_mode=EXACT_PLANAR_TRIANGLE`.
Chlopně nejsou součástí původní plošné aproximace; mají samostatné connector checks.

Pro vlastní `S=(40u,20uv,30v)` zůstává původní stav **REJECTED**, determinant
`−24000`. Rozpočet `.25 paper mm` dává 64 dílů a 84 párovaných řezů. Numerická
mez je `.15625 mm`, po skutečném rovinném frame je doložená mez přibližně
`.15625000000000389 mm`. Rezerva vychází z přesné racionální rekonstrukce
finite-input rovin a operátorové meze společného pose. Normálová mez zahrnuje
změnu roviny a condition reserve; délková mez zahrnuje skutečnou plochou metriku.

Globální komponentová kontrola dokládá RAW triangle graph přes jednu z konečné
sady racionálních projekcí, přesné oddělení vnitřků a jen deklarované společné
UV kontakty. Není to univerzální 3D intersection solver. Limit je 512 dílů a
200000 párů přes všechny projekce. Neprokázaný nebo vyčerpaný případ je UNRESOLVED;
perturbace materiálového frame je uvedena samostatně. Tisk ani fyzické sestavení
tím nejsou ověřené. V tomto pinu je potvrzená numerika LINE/LINE; obecné nativní
zdrojové profily zůstávají uložené a API připravené pro další samostatně revidovanou
curved numeriku. ARC/C zde nejsou skrytě nahrazené tětivami.

Schema 5 zavádí přísný registr generací. Známé schema 4 se otevírá jako bezpečná
kopie s povinným Save As; jeho původní soubor se nepřepisuje. Starší envelopes
nesmějí nést nový registry/tag. Uložené reporty, mapování i materiálové vazby se
při čtení ověřují proti skutečnému neměnnému zdroji, nikoli jen proti změnitelnému
hashi. Veškerý stav zůstává dostupný i pro undo/redo.

[Doménová evidence](evidence/pc008-domain-95fa2c7/results.json) obsahuje backendový
editovatelný projekt, snapshot a JUnit: 36 cílených PASS / 23,74 s. Dřívější úplný
běh 911 PASS / 287,79 s je výslovně před-final WIP, nikoli PASS finálního pinu.
[Batch evidence](evidence/pc008-domain-batch-0210118/results.json) obsahuje 59
cílených PASS / 27,14 s a přesně připnuté pozorování 64 explicitních změn:
setter `.0838 s` / 1 validace, controller `.3968 s` / 4 validace, jeden undo/redo.
Sekvenční baseline byla `5.6905 s`. Je to lokální backendové pozorování, ne slib
stálého výkonu ani nativní průchod. Skutečné UI, nový uživatel, oba vektorové
výstupy odvozené varianty a fyzické P3 mají vlastní navazující ověření.

Skills: konstrukce vedla oddělení fyzického materiálu od reference a skutečné
švy; UI vedlo oddělený náhled, výslovné potvrzení, návrat a hromadné ruční volby;
verification vedlo celoplošné meze, raw data a negativní podvržení vazeb; delivery
vedlo oddělené piny a pravdivě čekající review. Technická evidence není lidská
přejímka použitelnosti a tento komponentový výsledek neuzavírá celé D/B3/P2.
