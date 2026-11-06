# Nezávislá revize návrhu P2 v1.2

Reviewer: samostatný agent `/root/integration_review`, 6. listopadu 2026. Není autorem návrhu, UX, spike implementace ani produkčních změn. Vlastní zápisy jsou omezené na tento report a `evidence/review-*`. Reviewer neprovedl commit, změnu větve, merge ani push.

**Finální posuzovaný CODE: `d4ce76e38b3632c72964adf3e438c5632849caa9`. BASE: `6eb8977011854b242ab1dac8ea929e262e3b9563`. Verdikt: APPROVED_IN_SCOPE.** Původní pin `580e7bbb6e98b3b688952ee750508f5bca0501ca` měl CHANGES_REQUIRED; oba nálezy níže jsou nezávisle uzavřeny nad novým pinem. Schválen je návrh a jeho izolované experimenty, nikoli implementovaný produkt.

Rozsah: autorizovaný PC-012, návrh a izolované geometrické experimenty, traceability, UX, plán implementace, uchování prototypu. Není to schválení implementace A/B/C/D, nové persistence, fyzické sestavitelnosti ani produktové přijetí v1.2.

## Nálezy na původním pinu

| ID | Závažnost a konkrétní reprodukce | Požadavek na uzavření | Stav |
|---|---|---|---|
| DR-01 | MAJOR v experimentální klasifikaci. `developability_evidence(Loft(Profile('circle',20,20), Profile('circle',20,20),1.4,0,180))` na580e7bb vrátí `EXACT_PLANAR`, `regularity_proof=null`, minimum vzorkovaného Jacobianu603.185789. Analyticky `S=(1−2.4v)C0`; při `v=5/12` všechny parametry u kolabují do jednoho bodu, Jacobian≈6.77e−14. Tři testované v tento bod minou. Návrh správně singularitu zakazuje, executable však připouštěl EXACT pouze po konečném screeningu. | D4 zavádí analytickou půleliptickou rodinu s kladnou dolní mezí Jacobianu a jednoduchou trim hranicí. Půlotočka i obecná kruhová rovinná singularita jsou analyticky odmítnuty. Neprokázané rodiny a záporná hloubka nedostanou EXACT; závěrečný guard vyžaduje konečnou kladnou analytickou mez. | CLOSED naD4; vlastní46/46 kontrol |
| DR-02 | MINOR: nové aktivní normativní pointery měly skutečné náhrady české diakritiky znakem `?`, např. řádek3 `04_ACCEPTANCE_AND_VERIFICATION.md` začínal `Aktivn? roz???en?`. Původní zbytek téhož UTF-8 souboru byl správný. Nešlo o terminálové zobrazení. | D4 opravuje nové aktivní texty, názvy ve frontě a záznam historie; validator nově kontroluje poškozené znakové vzory. Vlastní čtení UTF-8 i validator prošly. | CLOSED naD4 |

DR-01 je reprodukován v [nezávislém skriptu](evidence/review-oracles.py) a [původních výsledcích](evidence/review-oracles-580e7bb.json). Autor dostal oba nálezy před dokončením revize; reviewer nenapsal jejich opravu.

## Kontrola návrhu a návaznosti požadavků

| Oblast | Závěr revize |
|---|---|
| Vstup vlastníka a model A | Manuální konstrukce z prázdného projektu, bez podmínky vodotěsného objemu. První autorská verze výslovně PC-006A+B, celý A včetně IO/rozvinu/ručních stránek/SVG/PDF; výztuha s dírou, pásek, podhled, samostatná základna a nezávislé přesahy. Dům je fixture. |
| B | Skutečné line/arc/cubic zdroje, rohy a korespondence, otvory v materiálu. Homotetický gotický/obloukový loft je pozitivní podporovaná rodina; nezávisle změněný/pootočený profil nesmí automaticky EXACT. Bézier extruze má vlastní mez chyby délky. |
| C | Válec/kužel a válcový limit, seam, intervalová tab ID a overrides, vektorový výstup. EXACT plášť oddělen od aproximovaného spojovacího prvku; cílový footprint není důkaz rigidního/isometrického ohnutí. |
| D | Zachovaný cíl, vysvětlené odmítnutí EXACT/UNRESOLVED, následně editovatelná odvozená segmentovaná varianta s konzervativním budgetem a plným výrobním průchodem. Samotné odmítnutí ani tisíce experimentálních triangle islands nejsou hotové D. |
| Spoje a materiál | Assembly oddělená od material adjacency. EdgePair, SurfaceTrace a GlueRegion, žádné oříznutí přesahu ani vnitřní CUT. UV přepočet závisí na provenance, ne stejných číselných parametrech po změně trimu. |
| Identity a změny | Feature/interval lineage, reference bez nearest/index fallback, immutable snapshot, autoritativní coverage. Oba locks, receiving join, split lineage a povinný skutečný mixed wall–roof fold fixture přetrvávají. |
| Úplnost implementačního kontraktu | PC-006A/B pouze první verze; celé P2 zahrnuje B/C/D, všechny původní digitální invarianty, reálný externí editor a DPI. Všech16 epic zachováno. PC-009 není první export vlastní geometrie. |
| Persistence a historie | Generické schema se neuzavírá na house-only modelu; před freeze A UI a B/C/D serial fixtures. Legacy read-only, prototyp jen rozpoznaný adapter/Save As, originál chráněný. Historické piny/review se nepřepisují. |
| Plán a autorizace | Smysluplné vertikální řezy, odhad59–100 člověkodnů implementace, rezerva oddělená, první A19–32; součty odpovídají tabulce. Přepočet po006A/B. Nová v1.2 `PO_PENDING`, předchozí skutečné přijetí v1.1 je historie; push návrhu neuděluje nové přijetí. |

## Vlastní ověření

Pracovní adresář `C:\Users\dalib\projects\papercraft-p2-v12-design`, absolutní interpreter `C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe`, `PYTHONPATH` ukazuje na `src` návrhového worktree. Nebyla provedena instalace ani spuštění WIP aplikace z bundle.

- `python -m pytest -q --junitxml=docs/p2/v1.2/evidence/review-tests-580e7bb.xml`: **253 PASS**, 0 fail/error/skip,4.15s. Původních213 testů +40 spike případů. [Vlastní JUnit](evidence/review-tests-580e7bb.xml).
- `python tools/spikes/p2_v12_geometry.py --output docs/p2/v1.2/evidence/review-run-580e7bb/geometry.json`: exit0,3.544s. [Vlastní surová data](evidence/review-run-580e7bb/geometry.json). Runner obsahuje source SHA a hashe zdrojů.
- `python -m ruff check tools/spikes tests/spikes`: PASS.
- `python docs/p2/v1.2/evidence/review-oracles.py`: **77/77** vlastních kontrol PASS a odděleně reprodukce DR-01. Ručně odvozené vzorce pro determinant−71061.15168784338 i opačný twist; kuželový pás a obrácené poloměry; válcový limit; roof trace/gap/oversize contact; základna1600−100=1500; arc/chord/sagitta, změna boční délky záložky a relief. Oracle očekávání nevznikají voláním výrobního helperu.
- `git diff --check BASE CODE`: PASS; produkční `src/` a `pyproject.toml` mají vůči BASE prázdný diff. P0/P1 baseline zůstává předkem návrhu.
- `git bundle verify`, `git bundle list-heads`, SHA256: PASS, bundle končí na `f9507e325c479c8b703e7f52c410de6847958720`, hash `9430a97e1668e3ba862ec720c8558a034034144af5d0b47c911956a1f2b5f769`. Vlastní obnova do nového prázdného bare repozitáře po načtení prerequisite BASE dosáhla přesného SHA a ověřila model/UI/test/nástroj/editorový důkaz přes `cat-file -e`. Žádný projektový checkout se při tom neměnil.

První reviewer integrity harness dokončil obnovu, ale selhal při úklidu read-only Git packu; následný úklid odmítla tool policy. Temp je ponechaný, žádný další úklid se neprovádí. Další spuštění bezpečně ponechává bare repository. Druhý rozpracovaný integrity průchod zachytil, že autor mezitím legitimně opravoval spike: hash právě měněného pracovního souboru již neodpovídal připnutému běhu580e7bb. Tyto pokusy nejsou PASS finálního pinu. Finální čistý průchod po připnutíD4 je uveden níže.

## Finální re-review oprav na D4

Delta580e7bb→D4 obsahuje opravy DR-01/02, jejich raw důkazy a20 nových spike regresí; doplňuje rizika vyplývající ze spikeů a výslovně rozlišuje certifikát pláště od konektoru v C. A/B/C/D, první verze006A/B, odhad, autoritativní geometrický model a jednotlivé gate významy zůstávají stejné. Produkční `src/` a `pyproject.toml` se nemění ani vůči BASE.

- Vlastní `pytest -q --junitxml=docs/p2/v1.2/evidence/review-tests-d4ce76e.xml`: **273 PASS**,0 fail/error/skip,5.88s = původních213 +60 izolovaných spike případů. [JUnit](evidence/review-tests-d4ce76e.xml).
- Vlastní runner `p2_v12_geometry.py --output docs/p2/v1.2/evidence/review-run-d4ce76e/geometry.json`: exit0,4.753s. [Raw výsledky](evidence/review-run-d4ce76e/geometry.json) jsou pod `results` přesně stejné jako připnutá opravená autorská evidence. Skutečné source hashe obou souborů odpovídají záznamu.
- [Vlastní analytické re-review](evidence/review-final-checks.py): **46/46 PASS**, [výsledky](evidence/review-final-checks-d4ce76e.json).27 kombinací kruhu/elipsy/gotiky, faktorů0.25/1.4/3 a±180/540°; čtyři jiné singularity s analytickým `v*=(1−k cosφ)/(1+k²−2k cosφ)`; kladná mez půlkruhového/půleliptického pásu; negativní hloubka; zachované pozitivní prostorové rodiny a pootočené negativní rodiny. Konečné nulové vzorky ani koplanarita samy nedávají EXACT.
- `ruff check tools/spikes tests/spikes`: PASS. Návrhový validator **18/18 PASS**, [raw](evidence/review-validator-d4ce76e.json), žádný chybějící lokální odkaz.
- [Vlastní integrity skript](evidence/review-integrity.py): **20/20 PASS**, [raw s jednotlivými příkazy](evidence/review-integrity-d4ce76e.json). Striktní JSON bez duplicit/NaN; unikátní tickety; kombinovaný DAG `depends_on`+`completed_by`; všech18 nových AC; skutečné původní přijetí v1.1 a oddělené v1.2 `PO_PENDING/accepted_by_owner=false`; všechny produkční P2 execution flagsfalse a produktové AU stáleNOT_RUN; všech16 epic; source/runtime diff; přesná bundle obnova v novém bare repozitáři včetně zdrojů a důkazů.

Na přesnémD4 má `git diff --check BASE D4` jedinou kosmetickou výtku: nový prázdný řádek na EOF `GEOMETRY_SPIKES.md:152`. Všechny ostatní soubory prošly. Integrační owner již připravil jeho odstranění; `git diff --check` nad tímto pracovním administrativním delta prošel. Toto odstranění bez změny textu/algoritmu je výslovně zahrnuté do schváleného administrativního follow-up. Není to neuzavřený věcný nález.

Při kontrole primárních referencí souhlasí [Perriollat/Bartoli §4](https://encov.ip.uca.fr/publications/pubfiles/2013_Perriollat_etal_CAVW_developable.pdf) s požadavkem determinantové identity a vyřazení vnitřní singularity; [W3C SVG paths](https://www.w3.org/TR/SVG2/paths.html) podporuje line/arc/cubic a compound subpaths pro díry. CMU PDF překročilo fetch limit; kontrolována pouze [autorská projektová stránka](https://www.cs.cmu.edu/~kmcrane/Projects/DiscreteDevelopable/). Specifická číselná tvrzení tohoto review stojí na vlastních analytických výpočtech, nikoli převzetí z publikací.

## Meze verdiktu

Nová aplikace, nové round-trip schéma, nové A/B/C/D UI průchody, vektorové výstupy a jejich editor/DPI proof jsou NOT_RUN. Materiálový kontakt není pevnost ani fyzická sestavitelnost; skutečný výtisk je P3. Zachovaný362-testový prototyp není tímto reportem nově schválen. Opravy historických EP nálezů nemají globální review pouze díky archivaci.

**APPROVED_IN_SCOPE:** žádný otevřený zásadní nález návrhu/spikeů nezůstává. Povolena je následná čistě administrativní změna obsahující tento report a jeho raw evidence, doplnění ověřovacích metadat/odkazů, výše uvedený EOF fix a zapsání technického verdiktu PC-012/fronty. Nesmí přitom změnit revidovaný produktový kontrakt, algoritmy, `PO_PENDING/accepted_by_owner=false`, NOT_RUN nových produktových AC ani autorizovat produkční P2. Takový administrativní commit nepotřebuje opakovat celé review; integrační owner ověří jeho omezený diff.

Master integraci, zachování případných nových remote změn, bezpečný push a shodu lokálního/vzdáleného SHA provádí integrační owner. Případnou věcnou změnu integračního výsledku je nutné znovu posoudit v potřebném rozsahu. Technické schválení a push návrhového balíku nejsou přijetím nového kontraktu za vlastníka.
