# PC-008 — nezávislá revize segmentovaného vektorového výstupu

Aktuální následný verdikt: **APPROVED_IN_SEGMENTED_SOURCE_TO_ACTUAL_VECTOR_COMPONENT_SCOPE**, přesný source **`5ad3cc0ac53ab68a09d1ff7ccd39fe90ade7f7c4`**. **SO01 CLOSED,0 otevřených BLOCKER/MAJOR/MINOR** v tomto komponentovém scope. Původní otevřený stav níže zůstává historický; závěrečný dodatek uvádí přezkoušení a přesné meze numerického fixture.

11.11.2026. Reviewer `/root/commands_review`, autor `/root/authoring_export`. Původní source **`26873c6d0950af412ba531f01440c3506b3dd6b1`**; dokumentační4ab07ef nemění runtime. Scope: nový `segmented_output_validation.py`, autoritativní zdroj ve snapshotu, hook/metadata vektorového writeru a související testy. UI, nový proof harness, budoucí integračníd762 ani celé D/P2 tímto nejsou schváleny.

**Průběžný stav: SO01 MINOR OPEN — normativní relativní plošný budget používá body+TAB.** Autor/root přijali úzkou opravu. End-to-end false-SAFE s platnou velkou chlopní nebyl doložen a tato zpráva jej netvrdí. Závěrečný připnutý dodatek bude následovat po opravě.

## Připnutí a skutečné výsledky

[Runner](evidence/pc008-output-review-archive.py) používá fresh exact `git archive`, explicitní `PYTHONPATH`, izolovaný subprocess a porovnává skutečné importy/hash tří dotčených modulů s Git blobs (LF normalizace výslovná). Archivuje i oba původní project fixtures, takže žádná souběžná práce jiného worktree nevstupuje do výsledku. [Manifest původních testů](evidence/pc008-output-review-archive-26873c6.json).

- **48 původních PASS /117.50s**, [JUnit](evidence/pc008-output-review-original-26873c6.xml), skutečné LINE64 i curved96, autoritativní closure, tab union, metric source/frame a staging fault testy.
- **14 vlastních hlavních PASS /2.37s**, [oracles](evidence/pc008-output-review-own.py), [manifest](evidence/pc008-output-review-archive-own-26873c6-final02.json), [JUnit](evidence/pc008-output-review-own-own-26873c6-final02.xml). Samostatná kandidátní velká tab zkouška je vyřazená z tohoto počtu výslovně, protože její fixture nedošel přes již existující hard BEND_UNRESOLVED. Nejde o PASS ani o potvrzený bug.

Vlastní drobný zdroj je `S(u,v)=(16u,8uv,12v)` se16 materiálovými trojúhelníky, explicitním rozpočtem0.26mm a ručními pozicemi. Expected plocha se odvozuje z původních actual source-plane operands pomocí přesného Fraction cross produktu. Kladné intervalové konce `lo,hi` ověřuje nezávislá racionální nerovnost `4 lo² ≤ |cross|² ≤ 4 hi²`; nevolá výpočet očekávání implementovaným `_source_material_area`. Skutečné SVG číslice čte samostatná XML/MLZ/shoelace kontrola. PDF cesty čte dříve samostatně revidovaný exact-token reader a jejich shoelace se porovnává se SVG. Tato numerická regrese není fyzický důkaz.

Negativy odmítly současné vynechání registry/source (zbývající flattening ho nezakryje), plošně invariantní přesun CUT, vymyšlenou TAB, maskování materiálu jako reference, změnu actual plane, falešný EXACT status, nadlimitní hloubku65, NaN a podvržené UUID. Žádná výjimka nevypíná běžnou konstrukční validaci nesouvisejícího materiálu. Snapshot zdroje zůstává detached; mutace vráceného bindingu zasáhne pouze jeho caller data a nezamoří immutable canonical cache.

Skutečný SVG transform s tokenem`25.00000000000000001` zůstal přesným Fraction odlišným od25, nepřeváděl se na float surrogate. Malformed actual transform vyvolal typed failure před publikací. Samostatná chyba až při **druhé** skutečné publikaci owned souboru doložila, že první nový soubor byl již os.replace zveřejněn a rollback obnovil všechny předchozí owned bytes včetně manifestu; foreign binary zůstal byte-identical.

## Analytika zdroje, součtu mezí a bounded práce

Uzavřený autoritativní source replay kontroluje všechny registry, vybranou generaci, původní reference i netiskové starší generace, normální materiál, spoje a legitimní union chlopní. Canonical cache má2 immutable JSON hodnoty a klíč obsahuje celý actual source včetně významového insertion order; snapshotové porovnání následně normalizuje object key order, nikoli pořadí seznamů. Obyčejný status/digest nenahrazuje plný replay.

Konečné source limity32MiB, depth64,500000nodes,4096parts/surfaces,8192profiles,8variants a64pages končí typed UNRESOLVED. Actual geometry se čte jako M/L/C/A/Z přes exact-token SVG/PDF readers; jejich dřívější nezávislé parserové revize zůstávají vlastními důkazy a tento přírůstek je nenahrazuje.

Plocha původního materiálového těla vzniká z actual3D plane operandů před paper frame; extension je čistý union delta, nikoli součet překrývajících se záložek. Místní frame position/edge délkové chyby se přičítají k actual serialized chybám. Target→material mez se přičte právě jednou, další publication error násobí actual pose operator. Přísnější digitální materiálové meze a celý target budget jsou kontrolovány současně; jednotlivé mezikroky nedostávají nový plný target budget. Žádný statement nemění nerozvinutelný hladký cíl na EXACT.

## SO01 — TAB nesmí rozšířit relativní toleranci těla

Původní řádek314 počítá `max(1/100, source_area[0]/1000000)`, ale `source_area` je již`body_area + net_connector_extension`. Normativní04 a poučení SK011 určují relativní referenci **bez chlopní**. Pro kladnou extension a tělo nad10000mm² je vrácený budget objektivně vyšší než body-only; samotná union area se může dál kontrolovat přísně jako celek, avšak chlopeň nesmí zvýšit povolenou odchylku těla. Doporučená úzká oprava je využít již vypočtené`body_area[0]` jako referenci relativního budgetu.

**MINOR normativní odchylka**, nikoli tvrzení prokázaného produkčního false-SAFE. Autor ji výslovně potvrdil a root zadal opravu. Vlastní pokusy o plný velký model použily nejprve400×1200mm twisted target, pak receiver a plochý první patch; všechny po odstranění původního overflow korektně skončily BEND_UNRESOLVED. Bezpečný hard bend se neobchází ani neacknowledguje jako warning. Raw jsou zachovány jako nezpůsobilá příprava scénáře, ne jako falešný FAIL writeru:
[run01](evidence/pc008-output-review-own-tab-area-26873c6.xml), [run02](evidence/pc008-output-review-own-tab-area-26873c6-run02.xml), [run03](evidence/pc008-output-review-own-tab-area-26873c6-run03.xml), [run04](evidence/pc008-output-review-own-tab-area-26873c6-run04.xml), [run05](evidence/pc008-output-review-own-tab-area-26873c6-run05.xml).

## Pravdivost příprav a skills

Vlastní časná area zkouška nejprve indexovala SketchPlane jako dict; poté80digit Decimal oracle nemohl rozhodnout84digit certifikovaný interval. Obě přípravy jsou zachovány ([raw01](evidence/pc008-output-review-own-own-26873c6.xml), [raw02](evidence/pc008-output-review-own-own-26873c6-run02.xml)); finální přesná kvadratická nerovnost je silnější a bez zaokrouhleného expected. Doplňkové dva vlastní testy nejprve měly chybný import ExportWriteError a XML encoding alias`utf8`; zachováno [raw](evidence/pc008-output-review-own-own-26873c6-final.xml). Pouze finální opravený run je uveden jako14 PASS.

Čtyři skills skutečně načteny: konstrukce odlišila hladký target, skutečný materiál a lepicí extension; UI chrání pravdivý APPROXIMATE/UNRESOLVED a opravitelné odmítnutí, neřešila zde nové ovládání; verification vedla k racionálnímu source oraclu a skutečným bytes; delivery zachovává SO01 i všechny historické přípravy a odděluje komponentu od celého předání. Nový modelář, native Windows UI/editor, curved doménový bridge jako celek, kompletní D a P3 zůstávají mimo toto review. Reviewer neupravuje produkci, staging, commit ani desktop.

## Připnutá oprava SO01 — 5ad3cc0

Přesný následný source **`5ad3cc0ac53ab68a09d1ff7ccd39fe90ade7f7c4`** mění pouze relativní referenci na`body_area[0]/1000000` a přidává dva audit fields popisující tuto skutečnost. Net union area se nadále kontroluje v actualSVG iPDF; chlopeň je zahrnuta v porovnávané geometrii, ale nikdy nerozšiřuje povolenou chybu těla. Finite source replay, původní domain/bend guardy, source→frame reserves, úplné coverage, atomická publikace a target δ součet se nemění.

Fresh archive/import guards zopakovány na přesném opravném pinu: [manifest](evidence/pc008-output-review-archive-5ad3cc0.json).

- **3 cílené původní PASS /7.03s**, [JUnit](evidence/pc008-output-review-original-5ad3cc0.xml): dva numeric comparator případy bez/s chlopní a existující plná legitimní TAB-domain publikace.
- **14 vlastních PASS /2.54s**, [JUnit](evidence/pc008-output-review-own-5ad3cc0.xml), se stejnými racionálními/actual-byte/closure/cache/rollback očekáváními. Jediný původní navržený velký physical/domain tab fixture je stále výslovně deselected kvůli známému BEND_UNRESOLVED, není přejmenován na PASS a jeho raw přípravy zůstávají. Není potřeba opakovat všech48 původních117s regresí pro tento jednořádkový tightening; runtime mění právě referenční plošný budget.

Nový autorův test je poctivě **COMPARATOR_ONLY**: vlastní explicitně zadané matematické tělo má trojúhelník200×200/2=20000mm², případná chlopeň200×20/2=2000mm². Nahrazuje pouze source-binding/area-oracle vstup komparátoru; neprohlašuje tento200mm spoj za potvrzený domain/bend/native workflow. SkutečnéSVG/PDF mají nejprve původní geometrii a projdou. Posun pouze protilehlého BODY vertexu o0.00021mm ponechá hinge iTAB beze změny a dává přesnou odchylku100×0.00021=0.021mm². Platná mez je0.020, dřívější chybná reference sTAB by poskytla0.022. Každý actual formát se samostatně odmítne pro plochu; poziční/délkové a target meze tuto chybu neskrývají. Expected algebra nevyužívá implementovaný source-area helper. Plné source-plane/math ověření zajišťují odděleně vlastní14 skutečných doménových případů a původní source replay testy.

**SO01 CLOSED / VERIFIED; APPROVED_IN_SEGMENTED_SOURCE_TO_ACTUAL_VECTOR_COMPONENT_SCOPE.** Neexistuje zde tvrzení prokázaného historického end-to-end false-SAFE, ani velkého bezpečně ohýbaného fixture. Schválení se vztahuje na původní26873c6 a úzkou opravu5ad3cc0; source/artifact pin budoucí integrace, proof harness, native D, skutečný editor, AC-US08, celé D/C/P2 a P3 vyžadují své vlastní důkazy/review. Historické přípravy se nezpětně neopravují. Reviewer nevytvořil produkční změnu, staging ani commit.
