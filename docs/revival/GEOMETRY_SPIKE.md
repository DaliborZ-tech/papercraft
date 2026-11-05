# Geometrická diagnostika P0/P1

Datum: 5. listopadu 2026. Samostatný analytik: agent `geometry_analysis`. Zdroj produktu: `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`. Rozsah je diagnostika a návrh kontraktu; produkční moduly nebyly změněny. Tento analytik neuděluje nezávislé schválení celé sady P0/P1.

Experimenty potvrzují, že rovinný panelový základ umí dosáhnout požadované digitální přesnosti. Současná obecná mesh pipeline ale nedokládá správnou topologii, konstrukční identitu ani bezpečné spoje. Doporučení pro P2: autoritativní parametrické panely a orientované významové hrany; mesh ponechat jako zobrazovací projekci. Válec a kužel patří až do ověřeného E11 řezu. Klasifikaci jemné sítě nelze používat jako certifikát rozvinutelnosti.

## Reprodukce a význam výsledků

Z kořene repozitáře byl skutečně spuštěn příkaz:

```powershell
uv run --python 3.12 --with numpy --with scipy --no-project tools/revival/geometry_probe.py
```

Po dokončení instalace integrátorem byl stejný probe ověřen také v hlavní `.venv`:

```powershell
.venv\Scripts\python.exe -u tools/revival/geometry_probe.py
```

Windows 11 build 26300, CPython 3.12.15, NumPy 2.5.4, izolované prostředí; žádná globální instalace. První běh použil dočasné prostředí spravované `uv`, závěrečný běh hlavní `.venv`. Přesný interpreter, příkaz, délka běhu, verze a všechny naměřené hodnoty jsou v [geometry-results.json](evidence/geometry-results.json), terminálový výstup závěrečného běhu v [geometry-run.log](evidence/geometry-run.log). Skript je [geometry_probe.py](../../tools/revival/geometry_probe.py).

Poslední běh: **exit 0, 11 experimentů, 1 PASS, 10 DEFECT_REPRODUCED, 0 ERROR**. Před experimenty prošly čtyři analytické kontroly nezávislého průnikového orákula: totožné čtverce, dotyk hranou bez plochy, poloviční překryv a obrácený winding. `DEFECT_REPRODUCED` znamená úspěšné doložení vady produktu, nikoli funkční PASS. Runtime výjimky mají samostatné `ERROR` a nenulový exit. Jde o diagnostický runner, nikoli další započítanou pytest sadu.

Samostatná orákula: analytické délky/plochy panelů a rotačních povrchů, shoda kopií hran podle jejich 3D původu, Gaussova křivost hladké koule a součet úhlových deficitů uzavřeného polyedru, nezávislý convex clipping pro průnik ploch. Expected hodnoty nejsou výstupem testovaného unfolderu. Nejsou zde použity screenshoty jako náhrada numeriky.

## Otázky, výsledky a interpretace

| Experiment | Analytické očekávání | Naměřeno | Interpretace |
|---|---|---|---|
| Panel 20 × 10 mm, dvě triangles | Plocha 200 mm², čtyři vnější řezné hrany, žádný konstrukční řez triangulační diagonálou | Plocha 200.00000000000006; největší chyba délky 3.56e-15 mm. Přímé `unfold_part` bez seam setu vrátí 0 cut; cesta přes `auto_seams` vrátí 4 cut. Diagonála je interní fold entry. | Numerika je dobrá; veřejné přímé API spoléhá na explicitní zahrnutí fyzické hranice. Auto cesta tuto konkrétní mezeru zakrývá. Interní triangulace nesmí být výrobní přehyb. |
| Krabice 10 × 20 × 30 mm bez švů | Plocha 2200 mm²; celý uzavřený povrch nelze položit bez explicitních řezů. Ne-tree sousedství se musí ověřit. | 12/12 faces, plocha 2200, délky do 1.43e-14 mm, 11 folds, 0 cuts. Sedm původně sdílených hran má nespojené 2D kopie, největší mezera 94.8683 mm. | Zachování délek jednotlivých trojúhelníků ani součet ploch nestačí. BFS vytvoří implicitní praskliny, které nejsou označené jako cuts a nemají párování. |
| Tatáž krabice přes `auto_seams` | Explicitní seam set, úplné pokrytí; žádné neoznačené praskliny | 12/12 faces, 7 seam edges, 14 jejich 2D výskytů, 11 folds, 0 neoznačených prasklin. Konkrétní naměřený net bez plošného překryvu. | Zvolená automatická cesta tento případ řeší. Výběr kostry obecně nedokazuje nekolizní rozvin; na stejné úrovni priority používá runtime `id(edge)`, tedy neposkytuje deterministickou geometrii. |
| Referenční dům, osm významových panelů | Dvě stěny 100 × 40, dvě 60 × 40, dva štíty b=60/h=30, dvě střechy 100 × sqrt(1800); plocha bez podlahy/chlopní 23085.281374 mm² | 14/14 triangles, plocha 23085.28137423857; maximum chyby délky 1.43e-14 mm; největší chyba plochy jednoho panelu 4.55e-13 mm² | Požadovaných 0.01 mm / 0.01 mm² je pro tento rovinný řez dosažitelných bez změny tolerance. Toto je ručně určený geometrický fixture, nikoli hotová aplikace nebo fyzicky přijatý dům. |
| Válec r=10/h=30 z analytického profilu | Obdélník 20π × 30, plocha 600π | Přímý `generate_rings` přesně 62.831853 × 30, plocha 1884.955592 | Speciální válcový případ je při správném profilu správný. |
| Tentýž válec z capped mesh, 64 segmentů | Extrahovaný profil má r=10 a výšku 30 | r=9.846153846, z=0.46875 a 29.53125, tedy výška 29.0625 | Binning posune konce profilu dovnitř a průměrování zahrne centra uzávěrů. Ani nepřesunutý objekt nedává analytické rozměry. |
| Kuželový pás r1=10/r2=20/s=30 | Mezikruhová výseč: R1=30, R2=60, úhel 2π/3, oblouky 20π a 40π, radiální hrany 30 | Lichoběžník má správnou plochu 900π, ale obě spojované strany 43.4391579 mm | Chyba strany 13.4392 mm (+44.8 %). Plošný test by vadu minul. Obrys je chybný pro přesný kuželový rozvin. |
| Jemná koule r=10, 64 segmentů/32 rings | Hladká Gaussova křivost 1/r²=0.01; nelze přesně rozvinout bez deformace nebo explicitních facet cuts | Jedna patch, všech 3968 faces označeno DEVELOPABLE, lokální úhel nejvýše 5.6316°. Celkový úhlový deficit 12.566370614358682 ≈ 4π, minimum deficitu vertexu 0.00094508 > 0 | Malé lokální úhly neurčují nulovou Gaussovu křivost. Tvrzení classifier docstringu neodpovídá jeho algoritmu. |
| Rigidní posun/rotace válce | Lokální profil a rozměry nezávislé na world umístění | Posun [100,200,300] změní radius na přibližně 223.7169; samotná rotace X o 90° vrátí `None`, kombinace této rotace a posunu vytvoří falešný vícebodový profil. Rigidní exact unfold jednoho páru triangles se mění jen do 2.27e-13 mm. | Chyba je v extrakci vůči globálnímu počátku/Z, nikoli v délkovém unfolderu. Osy/parametrický profil musí pocházet z lokálního elementu. |
| Dvě oddělené triangles | Přímé API odmítne nepropojený vstup nebo vrátí celé pokrytí | `unfold_part([0,1])` vrátí 1 face bez chyby; wrapper `unfold_all_parts` vrátí správně obě komponenty | Přímé API může ztratit faces. Guard a úplnost jsou nutné i když UI obvykle používá wrapper. |
| Non-manifold hrana se třemi triangles | Odmítnutí nebo konkrétní unsupported | Vráceny 3 faces bez chyby, dva triangles se překrývají plochou 50 mm² | Čistě stromové rozložení bez validace neumí garantovat materiálovou plochu. |
| Chlopeň na spodní hraně CCW čtverce 20 × 20 | Chlopeň vně materiálu; obrácení indexace nemění stranu | Forward hrana vytvoří 80 mm² materiálového překryvu, reversed 0 | Levá normála samotné hrany není definice vnější strany materiálu. |
| Stejný match ID ve dvou dílech | Právě jedna chlopeň na spoji | Dva samostatné volané generátory vrátí dvě chlopně | `seen_match` je lokální na part; nepředstavuje globální vlastnictví spoje. |
| Vnější hřeben / konkávní roh / přeznačené vertex ID | Hřeben mountain, konkávní valley; přeznačení vertex ID nesmí změnit polaritu | +90° / −90°. Pouhá výměna ID 0 a 1 na nezměněném hřebeni dá −90° | Znaménko se chybně odvozuje ze setříděných indexů. Model nemá explicitní potištěnou stranu. |
| Dvě geometricky různé plochy se stejným centroidem/plochou | Odlišné entity/shape content nesmějí být zaměněné | Čtverec 10 × 10 a obdélník 20 × 5, oba centrované a se dvěma triangles: `part_hash=4d4596b4d2d0` pro oba | Centroid+plocha+facecount není identita entity ani spolehlivý hash tvaru. Persistované entity ID oddělit od revize obsahu. |

Párování: fyzické otevřené boundary hrany panelu dostanou v `compute_edge_match_ids` sekvenční IDs, přestože nemají protikus. P2 musí rozlišovat volnou hranici a skutečný `Joint`; nesmí přilepit náhodnou druhou hranu podle stejné délky. Diagnostické metriky zachovávají 3D původ hran. U explicitních švů jsou nesouhlasící 2D kopie očekávané a v JSON nesou `explicit_seam=true`; `unmarked_crack_count` počítá pouze skutečně neohlášené praskliny.

## Nálezy a návrh opravy pro implementační kontrakt

| Podklad | Závažnost | Konkrétní zdroj | Doporučení |
|---|---|---|---|
| PC-F01 | blocker pro pravdivý CSG výsledek | `core_geometry/backend.py:79`, `:85`, `:92` | Unsupported výsledek/konkrétní výjimka před mutací. Concat se nesmí označit jako solid union. P2 obecné CSG nemusí implementovat. |
| PC-F03 | major; mimo základní planar P2 | `unfolder/strategies.py:130` | Analytická výseč se dvěma oblouky, radiálními spojovacími hranami a přesnými lokálními parametry. U near-cylinder limitu použít stabilní válcovou větev. |
| PC-F04 | major; blocker tvrzení přesného obecného rozvinu | `paper_analyzer/classifier.py:95` | Oddělit vizuální smooth patch od rozvinutelnosti. Parametrické analytic types a validované developability, mesh pouze explicitně aproximovaně. |
| PC-F06 | major mezera důkazů | `tests/test_unfolder.py` | Pět původních testů ověřuje shape/count. Přidat numeriku, explicitní topologii a negativní případy. Nelze je považovat za certifikaci geometrie. |
| PC-F07a | major | `unfolder/exact_unfold.py:169`, `:256` | Každý face musí být reprezentovaný právě jednou, každá materiálová boundary explicitní, každý non-tree spoj buď geometricky uzavřený, nebo explicitně cut/rejected. Guard disconnected/non-manifold. |
| PC-F07b | major | `core_geometry/stable_ids.py:88`; `seam_editor/auto_seams.py:122` | Entity ID uložit, revizi hashe oddělit. Spanning-tree tie break podle stabilního původu hrany, nikoli adresy objektu v paměti. |
| PC-F07c / AC-C09 | major | `unfolder/exact_unfold.py:39` | Tělesová orientace a potištěná strana určují polaritu. Ne směr setříděných indexů. |
| PC-F07d / AC-C05/C10 | major | `tabs_generator/tabs.py:103`, `:220` | Materiálové loops a orientované halfedges určují exteriér. Globální joint vlastní jednu chlopeň, ne lokální výskyt match čísla. |
| PC-F03 / AC-R05 | major; E11 | `unfolder/strategies.py:27` | Parametrický lokální profil je autoritativní; extrakce libovolné world mesh není prokázaný import rotačního tělesa. |

Závažnost hodnotí dopad při používání dané schopnosti. Odložení E11 nečiní chybný kužel nebo kouli funkční; P2 je musí buď skrýt, nebo jasně označit jako legacy nepodporovanou schopnost bez falešného PASS. Integrátor slučuje tyto reprodukce s diagnostikou UI/exportu v `FINDINGS.md`.

## Geometrický kontrakt doporučený pro P2

Souřadnice modelu v mm, papíru v mm, měřítko bezrozměrné. Základní fixture má stěny 10000/6000/4000 model mm a střechu se vzepětím 3000 model mm; papír na 1:100 odpovídá tabulce. Bez podlahy, bez přesahu, nulová kompenzace tloušťky, stěna/štít/střecha sdílejí matematické hrany. Hranice jsou významové polygonové smyčky; triangulace je jejich odvozená projekce. První join dovolí ověřený acyklický graf sousedních planar panels. Neověřený cyklus či non-manifold join se odmítne před mutací; alternativou je explicitně navržený cut s párováním. Žádná face nesmí zmizet.

Mountain/valley: při pohledu na deklarovanou potištěnou přední stranu je vnější hřeben mountain a konkávní žlab valley. Pro outward normály `nA,nB` a tangent `tA` vedenou **orientovanou boundary plochy A** je kladný `atan2(tA·(nA×nB), nA·nB)` v této konvenci mountain. Při výměně A/B se zároveň obrátí tangent a znaménko fyzikálního významu zůstane. Otočení globálních vertex ID nemění význam. Obrácení potištěné strany vymění role; rigidní posun/rotace je zachová. Obě konvence musejí být před tiskem ověřeny geometricky i v SVG/PDF. Reflections v P2 explicitně odmítnout, dokud nemají vlastní validovaný kontrakt.

Chlopně: outer loop CCW, holes CW při pohledu z potištěné strany, tedy materiál vlevo orientované boundary. Exteriér materiálu je vpravo (na hole loop směrem do otvoru). Není dovoleno nahradit tuto informaci setříděnými indexy hrany. Jediný uložený owner na `Joint` řídí tab A/B/off; geometrie se vytvoří až z aktuální orientované boundary. U změny ownera odstranit starou a vytvořit novou v jednom undo příkazu. V P2 nejsou holes implementační IN, jejich datový význam musí být zachován pro E10.

Před exportem ověřit injektivní pokrytí surface IDs → part membership, integritu obou stran každého spoje, efektivní délky/intervaly a orientaci, konečnost souřadnic, validní jednoduché boundary a průniky vnitřních materiálových ploch. Dotyk hranou s nulovou plochou není kolize. Pro skoro kolineární orientace použít robustní predikáty (například adaptivní přesnost/fallback), ne velký epsilon zakrývající překryvy. Numerický epsilon, topologické ID, minimální fyzický detail a požadovaná přesnost 0.01 mm jsou různé věci. Diagnostický clipping používá 1e-10 jako početní toleranci a 1e-8 mm² jako report floor; nejsou to přijaté produktové tolerance. Těsné dotyky a malé viditelné překryvy musí mít samostatné P2 adversarial testy.

Po chlopních a značkách vznikne kompletní tisková geometrie a obálka. Teprve tato geometrie vstupuje do kontrol stránky a volitelného packing. Offset/odstup se udává v paper mm; žádné tiché zmenšení. Core služby nesmějí potřebovat Qt viewport ani UI stav.

## Throwaway prototyp a limity

`cone_band` ve skriptu navíc sestaví mezikruhovou výseč z analytických poloměrů a úhlu, vzorkovanou 1024 segmenty na oblouk (2050 bodů včetně obou konců). Plocha 2827.431416905244 mm² proti 900π dává chybu 0.001972 mm². Dokládá dostupnou přesnost jednoduchého parametrického tvaru; nezavádí nový produkční kernel. Produkce potřebuje skutečné arcs nebo dokumentovaný sagitta/length error budget a robustní téměř válcový limit. Žádná garance E11 nevzniká pouhým tímto prototypem.

Experimenty neověřují GUI picking, reálné dialogy, OpenGL, import sample ani externí editor a fyzickou stavbu. Jednotkovou chybu legacy pipeline, world transformy, invalidaci ručního layoutu a exportní snapshot měří integrátor odděleně. Tento report nedokládá splnění celého AC-G02 nebo AC-C09/C10 v produktu; dodává reprodukci a přesná očekávání pro jejich implementaci a review.
