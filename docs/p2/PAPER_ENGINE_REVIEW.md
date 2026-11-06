# Historický checkpoint PC-007/008 — papírové jádro P2 v1.1

**Verdikt na revidovaném pinu: CHANGES_REQUIRED.** Jádro má doloženou správnou numeriku a smíšený díl, ale chybějící část runtime projekce lze potichu vynechat z kompletního snapshotu. Připnutá sada navíc není 90 PASS. Tento checkpoint se po zásadním upřesnění vlastníka zachovává jako historický důkaz; není schválením celého P2 v1.1 ani nového návrhu v1.2.

Datum: 6. listopadu 2026. Reviewer: samostatný agent `integration_review`, odlišný od autora jádra a integračního ownera. BASE: `2a341e1e64a26d5b1b4c1cde46dfb9603f964069`; revidovaný CODE: **`3fcf8773ae24e67341ee2f4975588916e58f04cd`**. Scope: `domain/paper.py`, související změny modelu/persistence a připnuté core/paper testy. Rozpracované UI, controller a SVG/PDF renderer jiných agentů nejsou součástí tohoto review.

## Vlastní příkazy a důkazy

Práce proběhla v odděleném detached worktree přesně na CODE; hlavní checkout ani cizí soubory se neměnily. Příkazy použily hlavní `.venv` interpreter a pinned `src`, nikoli rozpracované importy jiných agentů. Původní full suite ani GUI se v tomto checkpointu neopakovaly.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
<root>\.venv\Scripts\python.exe -m pytest tests/panel/test_domain.py tests/panel/test_project_io.py tests/panel/test_paper.py -ra --junitxml=<root>/docs/p2/evidence/paper-review-tests.xml
<root>\.venv\Scripts\python.exe <root>/docs/p2/evidence/paper-review-checks.py <pinned-worktree> 3fcf8773ae24e67341ee2f4975588916e58f04cd
```

První příkaz: **89 PASS / 1 FAIL / 0 SKIP**, exit 1, pytest 6.12 s. [JUnit](evidence/paper-review-tests.xml). Všech 33 připnutých paper případů prošlo; selhává dřívější identity/revision test v `test_domain.py`, který po zavedení českých zobrazovaných názvů stále porovnává `.name` s anglickými semantic keys. V pracovním stromu byla souběžná necommitnutá úprava tohoto testu; tvrzení 90 PASS z takového stromu nelze přenést na revidovaný CODE.

Druhý příkaz: exit 0, 2.21 s, vlastní analytické a negativní kontroly. [Zdroj](evidence/paper-review-checks.py), [výsledky](evidence/paper-review-results-3fcf877.json). Exit 0 znamená dokončený sběr důkazů, ne zelený produkt: reprodukce chybějící runtime části má ve výsledku výslovně `blocked=false`.

## Nezávislá numerika a chování

| Kontrola | Očekávání / skutečný výsledek | Závěr |
|---|---|---|
| Jiný dům 12×8 m, stěna 5 m, převýšení 3 m, 1:100 | 8 unikátně pokrytých povrchů; nezávislý shoelace součet 34400 mm², bez chlopní; při všech cut spojích 30 boundary cest | Numerika a pokrytí tohoto fixture PASS; žádná vnitřní triangulační diagonála |
| Vlastnictví a vnější strana chlopní | 13 konstrukčních spojů má právě po jedné chlopni; vnější body mají zápornou orientaci vůči směru CCW boundary hrany a kolmou vzdálenost 5 mm | One-owner a geometrický exteriér PASS; po A→B stále jediná chlopeň, CUT neobsahuje základnu tab jako další řez |
| Společný wall-left/roof-left, kotva [60,60], rotace 30°, oba zámky | Analytické rohy stěny [60,60], [146.602540378444,110], [126.602540378444,144.641016151378], [40,94.641016151378] | Shoda s nezávislou rotací/posunem |
| Převýšení střechy 3000→3500, save/reopen před přepočtem | Zachová se stará cache střechy, celý smíšený part stale a exportní kontrola hlásí STALE_PART | Stará projekce se nevydává za aktuální |
| Explicitní přepočet téhož partu | Nová sklonová délka 46.097722286464 mm; drift všech čtyř kořenových bodů stěny 0.0 mm; stejný frame a oba locks | Povinný smíšený numerický příklad PASS v core |
| Split smíšeného partu | Nové odlišné part IDs, lineage původního dílu a stránkové body obou potomků zachované | Rigidní mapa a kontinuita tohoto splitu PASS |
| Nezávislé konvexní/konkávní normály a orientovaná osa | Vnitřní roh valley, vnější mountain; společná výměna stran a halfedge nemění význam, potištěná strana jej prohodí | Polaritní orákulum PASS; význam nevychází z indexu vertexu |
| Stěna přes dvě změněné střešní plochy | Referenční lokální y se změní `40+2·hypot(30,30)` =124.852813742386 na `40+2·hypot(30,35)` =132.195444572929 mm | Pohyb 7.342630830543 mm odpovídá analytice; tato stěna je závislostně dotčená, nelze slíbit všechny stěny nepohnuté |
| Potvrzení tiskového okraje | Varování lze potvrdit, ale další změna placementu zneplatní digest potvrzení | Revision-bound přijetí PASS |
| Fyzický přesah a zfalšované potvrzení | Obyčejné acknowledge odmítnuto; ani ruční zapsání digestu do acknowledgements nepromine hard chybu a kompletní snapshot je blokován | Oddělení integrity a autorských varování PASS |
| Kolize s kalibračním/footer pásem | Materiál stěny umístěný do spodního pásu vyvolá PRINT_GUIDE_OVERLAP | Footer kontrola v core PASS |
| Zfalšovaná persisted cache s posunutým rohem | INVALID_GEOMETRY a odmítnutý snapshot | Kontrola cache proti autoritativní geometrii funguje pro tento případ |
| Neplatný next-part counter | Bool, 0, −1, string, necelé číslo a hodnota pod aktuálními lidskými čísly odmítnuty při načtení | Čítač nepřebírá pořadí seznamu a má typovou/intervalovou kontrolu |

Připnuté testy dále ověřují cycle rejection beze změny projektu, nemožný saddle net s překryvem, neplatného receivera, vnější obálku včetně chlopní, printed-side/split, uchování lidských čísel a neplatnou kotvu bez fallbacku. Tyto výsledky byly skutečně znovu spuštěny. Neznamenají podporu obecného non-manifold mesh importu: současná veřejná doména omezuje konstrukci na osm house surface typů a její validace nepovoluje jiné sousednosti. Právě toto omezení musí posoudit nový autorský návrh v1.2, ne vydávat house test za obecný geometrický kernel.

## Nálezy na 3fcf877

| ID | Závažnost | Konkrétní reprodukce | Podmínka uzavření |
|---|---|---|---|
| EP-01 | major | Validní ruční grid osmi dílů na dvou A4, scale .005, bez chlopní: issues=[] a snapshot obsahuje 8 částí. Potom `engine.parts.pop(pid)` při stále osmi autoritativních `project.part_records`: issues stále [], snapshot úspěšně obsahuje jen 7 částí. `validate_layout` a `snapshot` iterují pouze runtime cache a neporovnávají její členství se zdrojem (`paper.py:576,658`) | Před validací/exportem ověřit shodu celé projekce s autoritativními records i surface coverage/identity. Chybějící, cizí nebo duplicitní RAM part musí být hard integrity issue; nelze jej odkliknout ani potichu vynechat. Přidat samostatný negativní test a re-review konkrétního preservation pinu |
| EP-02 | minor, blokace deklarace výsledků pinu | Revidovaný CODE má 89 PASS/1 FAIL, nikoli deklarovaných 90 PASS; identity test stále používá `.name` místo nového `.semantic_key` | Uložit smysluplnou opravu testu do review pinu a skutečně spustit tento pin. Zachovat kontrolu semantických změn i geometrie nedotčených stěn; nepřepsat expected podle chybné geometrie |
| EP-03 | minor, numerická mez | `PanelProject.new_house(length_mm=.001,width_mm=.002,wall_height_mm=.001,roof_rise_mm=.001,scale=1e155)` projde domain validací, ale `PanelEngine(project)` vyhodí raw `OverflowError` z `project.scale**2` na řádku 314. Navíc po neúspěšné inicializaci zůstane osm nových part_records | Použít stabilní výpočet/typed validaci nebo explicitní numerickou doménu a nenechat neúspěšnou inicializaci zanechat zdánlivě current stav. Takový obrovský díl samozřejmě není tisknutelný, ale numerická chyba nemá být neřízená Python výjimka |

EP-01 a EP-02 byly ownerovi předány ihned po reprodukci, EP-03 po samostatném numerickém experimentu. Žádnou produkční opravu neprovedl reviewer.

## Změna produktového cíle a další postup

Vlastník následně zásadně upřesnil autorský cíl: reference house je fixture, nikoli hranice editoru. Na jeho pokyn se další schvalování P2 v1.1/UI zastavilo ve prospěch návrhu v1.2 a skutečných geometrických spikeů. Otevřené nálezy tohoto checkpointu proto nejsou ignorované ani prohlášené za opravené; jejich stav na případném preservation pinu vyžaduje vlastní cílené posouzení. Staré pozitivní výsledky ani nedostatky se zpětně nepřepisují podle nové roadmapy.

Tento report neschvaluje kompletní PC-007/008, UI, renderer SVG/PDF, externí editor interoperability, digitální P2 ani fyzickou sestavitelnost. P3 zůstává samostatný lidský výtisk a stavba. Nové v1.2 návrhové schválení bude mít samostatný CODE, požadavky A/B/C/D a report; není implicitním pokračováním scope tohoto checkpointu.
