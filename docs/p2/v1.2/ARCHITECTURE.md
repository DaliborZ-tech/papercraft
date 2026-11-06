# ADR-002 — konstrukční doména pro autorské papírové modely

P2 v1.2, návrh před stabilizací persistence. Výchozí Python/PySide6 z varianty B zůstává. Autoritativní model omezený na dům nahrazuje konstrukční graf. Implementace tohoto ADR ještě není dodána. [Spiky](GEOMETRY_SPIKES.md) ověřují jeho kritické předpoklady; [audit kódu](CODE_DISPOSITION.md) určuje, co lze zachovat.

## Volba a alternativy

| Varianta | Důsledky | Rozhodnutí návrhu |
|---|---|---|
| Rozšiřovat `build_house` dalšími presety a polyline mesh | Rychlé další ukázky, ale žádné vlastní profily, vnitřní připojení ani pravda o hladkém rozvinu | Zamítnout jako autoritu; ponechat numerický fixture |
| Vlastní omezená analytická konstrukční doména + odvozené meshe | Přímo vyjadřuje autorské křivky, otevřené plochy, materiál a rozvin; přesný režim je omezen důkazem | **Doporučeno**, navazuje na variantu B; implementovat vertikálně přes reálné UI |
| Plný externí BREP/CAD kernel jako nutná základna | Obecnější operace, ale integrace, distribuce a topologická jména nejsou v dostupném prostředí ověřené; kernel sám nedokazuje papírový rozvin | Pozdější adapter/spike pro prokázaný požadavek, ne blokace vlastní tvorby ani skrytá povinná závislost |

## Čtyři vrstvy, jedna geometrická pravda

`ConstructionDocument` obsahuje konstrukční graf a sestavu. `MaterialPlan` popisuje, které plochy tvoří vystřihované díly, jejich švy, spojovací prvky a rozviny. `PageLayout` umísťuje díly do paper mm. `ExportSnapshot` je validovaná neměnná projekce téhož materiálu/layoutu. UI a renderer neposkytují alternativní geometrii. Domain nemá Qt ani souborové dialogy.

| Entita | Uložená data a invariant |
|---|---|
| `SketchPlane` | Stabilní ID, lokální origin a ortonormální báze, rigidní umístění v assembly; konstrukční mm |
| `Vertex`, `CurveSegment` | Vlastní ID a revision; line, circular arc (centrum/radius/start/sweep, nikoli jen sampled body) nebo cubic Bézier (4 body), orientace a doména parametru |
| `Profile`, `Loop` | Uspořádané orientované segment refs s intervaly, explicitní start/seam, otevřený/uzavřený stav, corners; `outer` a `hole` nejsou zaměnitelné. Žádné indexové identity |
| `SurfaceFeature` | PlanarRegion, ExtrudedProfile, CylindricalPatch, ConicalPatch nebo RuledLoft. Generující profily, parametry a correspondence jsou uchovány; vnější/vnitřní trim loops explicitní |
| `SurfacePatch` | Stabilní potomková identita feature, lokální parametrizace `S(u,v)`, materiálová orientace/printed side, trim-domain. Mesh je odvozená cache s mapou triangle→patch/UV |
| `Attachment` | EdgePair / SurfaceTrace / GlueRegion, obě reference s orientací/intervalem, zvolená strana, assembly placement a režim. Žádný povinný druhý boundary edge |
| `Seam` | Cut / scored fold / smooth bend / glue seam a případný fold angle. Oddělený material graph; cut neodpojí automaticky sestavený dům a attachment neslepí dva papírové díly v jeden |
| `Connector` | Owner, příjemce, source hinge segments, obrys nebo generátor s přetrvávajícími override, počet/rozteč/gap/relief, fold side, paper-mm rozměry; samostatný pásek je vlastní material part |
| `MaterialPart`, `FlatteningResult` | Persistované ID, lineage a uživatelské číslo; sémantické pokrytí patchů/intervalů, PaperFrame, mapování surface↔material, certifikát režimu, revisions a error report |
| `Page`, `Placement` | Fyzické rozměry a margin, page ID nebo tray, poloha kotvy/úhel, nezávislé zámky, pořadí; žádné implicitní přebalení |

Tyto názvy jsou kontrakt významu, ne již zmrazená třída nebo JSON schema. Konkrétní serializační testy musí předcházet první stabilní verzi.

## Vlastní kreslení a plochy mezi profily

Příkazy `AddLine`, `AddArc`, `AddBezier`, `SplitSegment`, `MoveControlPoint`, `CloseLoop`, `AddHole`, `CreatePlanarRegion`, `ExtrudeProfile`, `LoftProfiles`, `PlaceFeature` pracují nad stejnými entitami jako šablony. Číselné délky/poloměry/úhly jsou validované; snap je pomoc, nevytváří skrytou shodu bodů. Základní endpoint-coincident a zadané rozměry jsou explicitní omezení. P2 není obecný nelineární constraint solver: konflikt rozměrů odmítnout s výčtem, nikoli posunout jinou geometrii potichu.

Obrysy mohou být konkávní, s více otvory. Smyčky musejí být jednoduché, otvory uvnitř vnější smyčky, bez vzájemného dotyku/průniku; otevřený profil je platný pro extruzi/loft, ale nestačí pro vyplněnou PlanarRegion bez koncových spojnic. Validace používá analytické průsečíky tam, kde jsou podporované, a jinak doložené intervalové/adaptivní meze; nejistota je explicitní chyba, ne úspěch. Materiálová triangulace respektuje díry; fan triangulation zde není přípustná.

Dva profily ve stejné rovině mohou být rovinný pás definovaný trim smyčkami. V různých rovinách se vytváří `S(u,v)=(1-v)C0(u)+v C1(phi(u))`. Autor zadá začátek, směr, odpovídající rohy a monotónní po částech definované `phi`; automatický návrh musí být viditelný. Uzavřené profily mají seam, gotický vrchol je explicitní corner, nikoli vyhlazený vzorek. Každý interval mezi rohy má vlastní patch; crossing rulings, nulová plocha a singularita uvnitř trim oblasti se odmítají. Různé velikosti profilů neznamenají automaticky homotetii a stejné počty bodů neznamenají vhodnou korespondenci.

## Spoje jsou reference na sestavení, nikoli pouze hrany

`EdgePair` odkazuje na dva orientované úseky hran a efektivní délku. `SurfaceTrace` odkazuje na zdrojovou hranu a cílovou křivku **v UV ploše**, včetně intervalů a materiálové strany. `GlueRegion` obsahuje zdrojový a cílový trim region nebo explicitní jeden příjemce pro konektor. Každý odkaz nese vlastní ID i revision dependency; prostorová koincidence nevede k automatickému spojení.

U A je stěna nahoře v rovině střechy, její stopa však leží uvnitř trim obrysu přesahující střechy. Přesah v UI znamená **horizontální vzdálenost v půdorysu**, případně explicitně přepnutou vzdálenost podél plochy; režim i hodnoty se uloží. Pro sklon 45° dává 500mm horizontální okapový přesah 707.106781mm po střeše. Štítový přesah se měří podél hřebene. Žádné zaměnění těchto délek. Připojení budovy na základnu používá vnitřní půdorysnou stopu/region, základna nemusí mít otvor kopírující stěny.

Material adjacency se vytvoří pouze tehdy, když jde o skutečně souvislý materiál a validní rozvin. Hrana stěny přilepená uvnitř samostatné střechy se nikdy sama nezmění na přehyb jednoho listu. T-junction assembly je povolená; non-manifold jedné materiálové plochy se odmítá nebo vyžaduje explicitní samostatný díl. Lze mít několik lepených dílů na jedné základně; kontrolují se konflikty příjemcových oblastí, ne globální zákaz každé vícečetné incidence.

## Chlopně a skutečná lepicí plocha

Generátor vytváří souvislý zkosený lem nebo jednotlivé záložky s per-tab ID. Autor může nastavit obrys, počet, rozteč, šířku, gap, relief, trojúhelníkovou špičku, vypnout konkrétní záložku nebo změnit owner. Dvojí chlopeň na témže intervalu vyžaduje výslovnou konstrukci se samostatnými příjemci; jinak je konflikt. Base line se vykreslí jako jediný přehyb, ne dvojitý řez.

U zakřivené hrany kontinuální pásek a řada záložek nejsou geometricky totéž. Jednotlivé přímé hinge segmenty mají měřenou odchylku od ideální křivky a mezery pro ohyb. Příjemcova oblast se testuje po transformaci záložky do sestavené polohy, v metrice povrchu. Je-li chlopeň sama nedevelopovatelná, nesmí být schválena jako přesná; autor musí zvolit dělení nebo explicitní aproximaci. Trojúhelníková špička sama nezaručuje dostatečnou lepicí plochu.

Kontroly: (a) plochá materiálová obálka včetně všech záložek a výřezů, (b) relief a dostupný prostor pro ohyb podle zadané tloušťky/vůle, (c) kontakt s definovanou příjemcovou oblastí bez děr a mimo stranu potisku, (d) sousední záložky v sestavené poloze. Minimální gap/plocha je nastavený práh s jednotkou, ne odvozený z gramáže. Bez materiálového profilu uvést `MATERIAL_CLEARANCE_UNVERIFIED`; žádný příslib fyzické pevnosti.

## Rozvin: důkaz, nejistota a řízená aproximace

`FlatteningCertificate` má `mode=EXACT|APPROXIMATE|UNRESOLVED|REJECTED`, family/method, source IDs+revisions, paper scale, trim-domain, forward/inverse map, metrické reziduum, chybu reprezentace křivky a zvlášť odchylku od cílové 3D plochy. Certifikát je cache invalidovaná změnou vstupu. Kontrola pokrytí porovnává autoritativní požadované patch intervaly s výsledky, nikoli jen počet RAM dílů.

EXACT je povolen pro roviny, analytický válec/kužel a doloženou extruzi/homotetickou kuželovou rodinu s regularitou a rozměrovou kontrolou. Numerický výpočet může mít doloženou omezenou chybu pod digitální tolerancí. Obecný ruled loft vyžaduje `det(C0',r,r')=0` v celém pravidelném intervalu, `r=C1(phi(u))-C0(u)`. Nenulový determinant dává negativní důkaz; konečná sada nulových vzorků není důkaz. Pokud aktuální solver nedokáže rozhodnout, stav je UNRESOLVED a přesný export je blokovaný. Kusový roh se posuzuje po intervalech; singulární vrchol musí být explicitní hranicí, nikoli bod skrytý uvnitř.

APPROXIMATE musí vytvořit **odvozenou variantu**, uchovat původní cílovou plochu a autorův zvolený error budget. P2 nabídne řízené rozdělení na ploché segmenty; mezi nimi jsou skutečné švy/přehyby, jejich rozviny jsou přesné pro segmentovaný model, nikoli pro původní hladkou plochu. Report uvádí maximální geometrickou odchylku v model/paper mm, rozdíl relevantních délek a normál, počet dílů/švů a jak se chyby měřily či ohraničily. Pouhé měření ve vrcholech neomezuje chybu uvnitř. Chybí-li spolehlivá mez nebo budget neprojde, varianta zůstává neexportovatelná jako ověřená aproximace. Nikdy se nepromítne síť do roviny s neohlášenou změnou rozměrů.

Původní chybná klasifikace podle malých triangle úhlů a lichoběžníkový rozvin kužele se nepoužijí pro certifikaci. [Primární studie o diskrétní rozvinutelnosti](https://www.cs.cmu.edu/~kmcrane/Projects/DiscreteDevelopable/paper.pdf) popisuje rozdíl mezi ruled a developable geometrií; návrh používá vlastní analytická orákula a spiky, nikoli obecný slib z publikace.

## Identita, kotvy a invalidace

### Rozhodnutí ovlivněná skutečnými spiky

- Homotetický kruhový/eliptický/gotický loft má analyticky nulový determinant a doloženou kladnou dolní mez Jacobianu na hladkých intervalech. Gotický vrchol je roh: doména musí uchovat dva intervaly a skutečný přehyb podél rulingu. Proto samotný obecný `Surface(vertices)` nestačí a certifikát obsahuje i regularitu a trim.
- Pootočený kruhový loft dává nezávisle `D=-71061.15168784338` mm³ pro zadaný parametr. Naopak nulové vzorky bez známé rodiny zůstávají UNPROVEN. Proto jsou důkaz a numerický screening různá pole, nikoli jedno boolean `is_developable`.
- Pro 64×16 buněk téže aproximace je vzorkované maximum0.005054mm, ale analytická horní mez0.016452mm. Proto `sampled_max` nemůže splnit hard0.01mm rozpočet. Hraniční délky, plocha a normály se evidují zvlášť; pouze vzdálenost má v tomto spiku globální mez. Tisíce triangle islands jsou experiment, nikoli přijatelný výchozí výrobní návrh.
- Střešní stopa má při změně přesahu jiné UV a stejné world body. Proto UV souřadnice samy nejsou stabilní referencí: zdrojový wall-top interval a feature provenance určují přepočet stopy. Gap1mm znamená žádný kontakt, i když UV projekce leží uvnitř regionu. Otvor základny sníží kontakt1600→1500mm² a přeruší20mm kontaktního intervalu.
- U24 záložek válce je mismatch oblouk–tětiva0.009087mm, ale potřebná změna boční délky přibližně0.113955mm. Proto Connector nese vlastní aproximační/materiálový status nezávislý na EXACT válcovém plášti. Výpočet cílové kontaktní oblasti není důkaz dosaženého rigidního ohybu; UI musí tento rozdíl vysvětlit a vyžadovat opravu nebo explicitně omezené aproximované připojení.

Podrobné parametry, jednotky, vlastní orákula a negativní případy jsou ve [spicích](GEOMETRY_SPIKES.md). Čísla výše jsou důsledky pro návrh dat, ne nové univerzální fyzické tolerance.

UUID patří autorské entitě/feature, topologická provenance potomkům. Editace segmentu zachová ID; split vytvoří dvě nová ID a explicitní intervalovou lineage. Reference na původní interval se přemapuje pouze jednoznačným pravidlem, jinak `REFERENCE_UNRESOLVED` s náhledem. Žádný fallback podle indexu, podobnosti názvu nebo nejbližšího bodu. Preset rozbalí tutéž sekvenci feature příkazů a výsledné entity mají plná uložená data; otevření projektu nezávisí na aktuální verzi presetového kódu.

PaperFrame může být explicitně kotven k vrcholu a směru rovinné plochy nebo k persistovanému materiálovému bodu a tangenci `(patch_id, u, v, tangent_ref)`. Parametr sám nestačí, pokud se profil reparametrizoval: reference má provenance a vyžaduje validaci. Při přepočtu se zachová rámec a placement, ne levý horní roh bounding boxu. Nezměněná rigidní oblast kořenové stěny zachová všechny své body; změněná křivost root oblasti obecně všechny body zachovat nemůže, a UI to předem vysvětlí. Merge preferuje explicitně zvolený přijímací díl, split dědí kotvu do příslušného potomka, ostatní dostanou novou identitu a deterministicky zachovaný world-to-page rámec. Chybějící kotva je hard error.

Obsahové revisions a graf závislostí odlišují změnu konstrukce, rozvinu, layoutu a zobrazení. Potvrzení varování je vázáno na konkrétní digest dotčených entit a nastavení. UNRESOLVED/stale, chybějící díly, poškozené reference a přesah fyzické stránky nelze potvrzením ignorovat. Background job při pozdějším zavedení aplikuje výsledek jen při shodě vstupního digestu.

## Persistence a kompatibilita

Pracovní jméno nového formátu je `ArchPapercraft.AuthorProject`, první stabilní schema vznikne až po průchodu A, přípravných B/C round-trip fixtures a nezávislé revizi reference/lineage modelu. Předtím je formát označen `experimental` a obsahuje writer/build version. Žádná nevratná migrace a žádné přepisování originálu při otevření.

Staré mesh `.apcraft` zůstávají read-only. Rozpracovaný `ArchPapercraft.PanelProject` schema1 je **experimentální prototyp**, nikoli nový legacy závazek na libovolnou budoucí editovatelnost. Převod do autorské domény bude explicitní Save As nad kopií, s rozbalením osmi ploch do skutečných skic a features, mapou stable IDs, spojů, frame, placement a chlopní; pokud konkrétní draft build nelze jednoznačně rozpoznat, jen read-only a konkrétní zpráva. Smíšený fixture ověří před/po všechna wall page coordinates. Nevkládat pouze původní 4 parametry domu do nového obalu.

Uložení obsahuje zdrojový konstrukční graf, lokální jednotky/transforms, seams/attachments/connectors, layout/locks, explicitní provenance a volitelné stale caches oddělené od autority. Validace duplicitních JSON klíčů, neznámé verze, neplatných ID/references, nekonečna a atomický zápis se převezmou. Změna runtime pole cache nesmí umožnit vynechat materiál při exportu.

## Výstupní adaptér a hranice schema freeze

Snapshot nese orientované složené cesty (line/arc/cubic), díry a role CUT/FOLD_MOUNTAIN/FOLD_VALLEY/TABS/LABELS/ARTWORK/GUIDES plus neřezané lepicí značky v GUIDES. SVG uchová editovatelné křivky a compound paths. PDF křivky reprezentuje podporovanými vektorovými operátory s doloženou chybou; kruhový oblouk převedený na Bézier není matematicky totožný, musí mít vyčíslenou mez v paper mm. Jediný snapshot, souřadnice, jednotky a stránky pro oba výstupy. [SVG path specifikace](https://www.w3.org/TR/SVG2/paths.html) definuje line/arc/cubic a uzavření cesty; konstrukční identitu ani fyzickou sestavitelnost neposkytuje.

Před schema freeze: A end-to-end v UI; serializovatelné B/C/D fixtures včetně odmítnutí a aproximační varianty; reprodukované spiky v tomto balíku; review entity/reference/certifikátů; fault-injection IO a smíšená kotva. Další dodávání je postupné, ale žádná z těchto schopností nesmí být odsunutá do neurčitého budoucího rozšíření datového modelu.
