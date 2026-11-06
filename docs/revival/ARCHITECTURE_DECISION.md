# Rozhodnutí obnovy — ADR-001

> Aktualizace 6. 11. 2026: tento dokument zachovává stav původního P0/P1 a v1.1. V1.1 byla skutečně přijata vlastníkem, potom byl cíl rozšířen. Aktivní návrh [P2 v1.2](../p2/v1.2/README.md) a jediná queue určují nynější rozsah/stav; review a baseline piny zůstávají historické. Povinné mixed-part testy se neruší. Push návrhu není jeho produktové přijetí.

Stav: doporučení P1 k přijetí spolu s kontraktem P2. Datum 5. 11. 2026.
Baseline: `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`. Produkční změny nejsou součástí tohoto ADR.

## Doporučení a varianty

Nahradit geometricko-papírovou pipeline za parametrickou panelovou doménu, zachovat Python/PySide6 a použitelný desktopový obal. P2 bude omezený, skutečně editovatelný domeček. Mesh bude projekce stejné domény pro zobrazení a picking. Žádné obecné CAD nebo tvrzení o přesném rozvinu koule.

| Varianta | Co zachová | Přínos | Náklady a rizika | Kompatibilita |
|---|---|---|---|---|
| A: opravovat dnešní mesh pipeline | téměř všechny moduly | rychlá jednotlivá oprava exportu/hranice | samotné opravy neřeší triangle identity, jednotky, cykly ani zachování autorských dat; nutný dodatečný významový model | zdánlivě malá migrace, ale odvozené indexy mění význam |
| B: nahradit pipeline, zachovat aplikaci — doporučeno | Qt, command rozhraní, preferences, numerické utility a exportní knihovny | panelové orákulum, společná 3D/2D identita, explicitní spoje | nový datový formát, picking a 2D editor jsou skutečná práce; legacy oddělit | read-only legacy reader + nový schema formát, originál zachovat |
| C: širší přestavba v jiném stacku | produktové zadání a fixtures | možnost jiného UI/renderingu | všechny interakce/persistence/export znovu, bez důkazu přínosu proti B; chybí důvod měnit Python/Qt | nejtěžší migrace a distribuce |

Rozhodnutí vychází z reprodukcí ve [FINDINGS.md](FINDINGS.md), nikoli z jazyka nebo stáří aplikace. Strategie A je vhodná jen pro izolované hotfixy před obnovou; proti B odkládá stejný přepis identity. C nyní nemá doloženou návratnost.

Odhad B pro P2: 24–40 soustředěných člověkodnů včetně cílených oprav a review; A 28–48, C 45–75. Jde o plánovací intervaly, ne benchmark výkonu týmu nebo slib data. Podklad: pět existujících propojených rizikových vrstev bez hotového ručního editoru; rozpad B je v kontraktu. Nejistota ±40 %: renderer/picking na dalších GPU, robustní split/join, editor a legacy data. Po PC-006 aktualizovat podle skutečného průchodu, nerozšiřovat scope bez evidence.

## Mapa keep / fix / replace

| Modul | Rozhodnutí | Konkrétní hranice |
|---|---|---|
| `app.py`, `ui/main_window.py`, preferences | keep/fix | zachovat entry point, menu, docks, téma; připojit application commands a jednotný výběr |
| `commands/command_stack.py` | fix | zachovat rozhraní; dirty podle revize/save tokenu, nikoli pouze délky undo zásobníku; transakční undo i pro layout |
| `core_geometry/units.py`, transform utility | keep/fix | zachovat převody; validovat doménu scale, world transform skládat přes rodiče |
| `core_geometry/primitives.py`, `arch_presets` | keep legacy | rendering starých projektů; P2 dům vznikne z panelových povrchů, ne z objemových stěn s vnitřními plochami |
| backend CSG | quarantine | nepodporovaný příkaz vrací typed unsupported; žádná závislost P2 na OCC |
| scene graph / stable IDs | replace authority | element UUID a významové surface/edge ID; starý strom lze zobrazit, mesh hash není identita |
| classifier / seam graph / exact + approximate unfold | replace for P2 | validace panelů a explicitní orientované spoje; legacy mesh pipeline zůstane označena experimentální |
| tabs / markings | replace geometry | jeden vlastník spoje, skutečné vnější hranice, printed-side polarita |
| packer | keep optional legacy, new validation | automatika mimo P2; nový layout ukládá autorské placements a validuje kompletní materiál |
| SVG/PDF exporters | replace traversal, keep libraries | stejný immutable snapshot, společná transformace, part-first skupiny, vložený font |
| project IO | replace writer, legacy reader | schema, integrita, atomický save, explicitní neztrátový import podporované podmnožiny |

## Data, identity a API hranice

Nové moduly navržené pro P2: `domain/project.py`, `domain/construction.py`, `domain/joints.py`, `domain/layout.py`, `application/commands.py`, `geometry/panels.py`, `geometry/unfold.py`, `validation/issues.py`, `exporter/snapshot.py`. Konkrétní souborové rozdělení může tým upravit; sémantika je závazná. Core nesmí importovat Qt.

- `Project(schema_version=1, project_id, revision, model_units="mm", scale_ratio, elements, joints, pages, placements, tab_overrides, acknowledgements)`; display units jsou pouze UI preference projektu.
- `ModelElement(entity_id: UUID, kind, parameters_mm, parent_id, local_transform, content_revision)`. `SurfaceRegion.id = element_id + semantic_key`, například `wall.front.rectangle` a `roof.left`; `BoundaryEdge` má orientovanou referenci na polygonový interval. UUID/původ jsou oddělené od hashe obsahu i čísla dílu.
- `Joint(id, edge_a, edge_b, reversed, interval_a, interval_b, mode=cut|fold, tab_owner=a|b|none, revision)`. Stejná délka neprokazuje sousednost; jen explicitně způsobilý spoj konstrukce.
- `PaperPart(id, surface_ids, source_revision, boundary_loops, fold_paths, lineage, paper_frame)`. `PaperFrame(root_surface_id, anchor_vertex_id, axis_edge_id, orientation, front_side)` persistuje významovou kotvu a osu rozvinu. Jednoznačná kontinuita členství povrchů drží ID i při změně jejich rozměrů; obsahová revision se mění. Split má nové ID a seznam předchůdců, merge totéž. Žádné připojení podle indexu.
- `Placement(part_id, page_id, x_mm, y_mm, rotation_deg, position_locked, rotation_locked, source_revision, review_state)`. X/Y umísťují kotvu PaperFrame, nikoli minimum měnící se obálky; rotace určuje směr jeho osy. Díl má právě jednu lokaci: stránka nebo odkládací plocha. P2 zavede oba nezávislé zámky.
- `ValidationIssue(id, code, severity, entity_refs, source_revisions, location, repair_action)`; potvrzení konkrétního varování se váže na hash příslušného vstupního snapshotu.
- `ExportSnapshot(project_revision, settings_revision, parts, tabs, labels, placements, pages, issues, digest)`: pouze validovaná aktuální data. Exportéry nesmí číst viewport či spouštět packing.

Příkazy vrací `CommandResult(success, issues, changed_ids, revision)`; chyba nebo nepodpora neprovede částečnou mutaci. `build_surfaces(snapshot)`, `unfold_panels(snapshot)`, `build_print_geometry(snapshot)`, `validate_layout(snapshot)`, `make_export_snapshot(project)` jsou deterministické služby bez widgetů. Pokud později přijde worker, výsledek aplikuje pouze shodná input revision; AC-I08 je podmínka jeho zavedení.

## Jednotky, orientace a numerika

Model mm, papír mm, scale je kladný konečný bezrozměrný poměr. 10 m = 1000 cm = 10000 mm; při 1:100 jde vždy o 100 mm. Do exportu jde již paper geometrie; žádné další unit-to-mm. World = parent_world × local, sloupcové vektory; osy X délka domu, Y šířka, Z nahoru, pravotočivě. Záporné souřadnice/úhly platí; nulový přesah platí. Délky/scale musí být kladné; NaN/Inf a degenerace se odmítají před mutací. Záporná determinantová transformace/zrcadlení v P2 nepodporována.

Povrchy jsou orientované z vnější potištěné strany. Papírové lokální hranice mají vnější loop CCW a případné díry CW. Interiérová triangulace nevytváří řez ani přehyb. Při cut je řez pouze po vnějším obrysu včetně chlopně; základ chlopně je fold/glue značka, ne duplicitní cut.

Podepsaný úhel: edge tangent podle boundary face A, normály A/B podle deklarované přední strany; úhel `atan2(t·(nA×nB), nA·nB)` se kalibruje na hřebenu jako mountain. Pokud volba orientovaného páru převrátí znaménko, převrátí se současně orientace tangent, takže význam drží. P1 analytická konvence: vnější hřeben střechy s otištěným vnějškem = mountain, vnitřní konkávní roh = valley; přepnutí printed side prohodí oba. P2 musí doložit permutaci vertex/edge/face indexů, rotaci a SVG/PDF. Dnešní `_compute_dihedral` nelze převzít bez této opravy.

Materiál leží vlevo od orientovaného loopu; vnější chlopeň jde doprava. Pro díry stejná zásada generuje chlopeň do prázdna otvoru, ne do materiálu. Díry nejsou P2 scope, ale datový model je nestratí; E10 přidá triangulaci a vlastní proof.

P2 rovinné panely bez děr; graf fold spojů každého rozvinovaného dílu musí být strom, nebo být rozdělen dodatečnými explicitními cut hranami. Join, který vytvoří cyklus či překryv, odmítnout s důvodem a beze změny. Celý model může být uzavřený, součet dílů musí pokrýt všechny významové povrchy právě jednou. Nekopírovat BFS domněnku, že položené trojúhelníky samy dokazují uzavření.

Digitální tolerance beze změny mandátu: délky `max(0.01 mm, 1e-6 L)`; plochy `max(0.01 mm², 1e-6 A)`. Nejsou to merge epsilon. Topologické vztahy primárně podle ID; numerická shoda sdílených konců v modelu: `1e-7 mm` v panelovém fixture. Minimální délka podporovaného panelového edge: `1e-4 model mm`; menší odmítnout jako degeneraci, ne sloučit bez příkazu. Detail pod 0.5 paper mm, chlopeň pod 2 mm = autorské varování. Žádné tvrzení o fyzické výrobě z těchto čísel.

Robustní kolize: broad phase AABB, narrow phase orient2d a polygon intersection, oddělit interior průnik od dotyku hran. Kandidát knihovny může být vybrán při implementaci; přejímka vyžaduje nezávislé fixtures včetně skoro kolineárních hran. Souřadnice pro predikáty lze kvantovat na 1e-5 paper mm s detekcí kolapsu prvku (chyba, žádné tiché zmizení). Plošný průnik nad 1e-8 mm² po této kvantizaci je kolize; menší nejistý výsledek je hlášení k přezkoumání, ne automatický PASS. Doporučený rozestup při budoucím packingu 2 mm mezi kompletními obrysy; line width a značení mají vlastní obálku, grafické pozadí vlastní sémantiku.

## Invalidace a persistence

Změna střechy invaliduje její povrchy, spoje na okapu, chlopně a dotčené kontroly; nezměněné samostatné stěny/layout zůstanou. Obsahuje-li part stěnu i střechu, je stale celý part. Jeho persistovaný rámec v nezměněné stěně zachová polohy všech bodů této stěny; změna obrysu či obálky neposouvá kotvu. Další plocha připojená přes změněnou geometrii je dotčená závislostí. Chybějící/neplatná kotva vede k `ANCHOR_UNRESOLVED` a blokaci kompletního exportu, nikoli náhradě centroidem. Volbu kotvy, lineage i povinné smíšené testy definuje [MIXED_PART_LAYOUT_CONTRACT](MIXED_PART_LAYOUT_CONTRACT.md). Díl s jednoznačnou kontinuitou si podrží placement a dostane `needs_review`; zaniklý part zůstane jako lineage reference k vyřešení, ne jiný díl stejného pořadí. Dokud chybí přepočet/pokrytí, kompletní export blokován. Měřítko mění konstrukční paper geometrii; chlopně 5 mm, fonty a stroke v paper mm zůstanou, dokud autor explicitně nezmění uloženou politiku. Každý příkaz má undo celého dopadu.

Save: validace → dočasný soubor ve stejném adresáři → flush/fsync → os.replace → dirty save token. Chyba před replace zachová originál, obnova pracuje s kopií. Novější schema odmítnout; neznámá data nesmějí mizet při save. Přesná fault injection je součást PC-006.

Legacy rozhodnutí: sample lze dnes načíst a semanticky round-trip testovat; jeho vykreslitelnost není správný měřítkový import. P2 legacy otevře v read-only compatibility pohledu, jasně označí v0.2 a zakáže přepis originálu novým writerem. Převod pouze pro ověřené elementy s explicitními mm, do nového souboru a s reportem. Sample s gotickým oknem a bání není plně v P2 panelovém scope: nabídnout původní read-only pohled, případný částečný import pouze jako pojmenovanou kopii po rozhodnutí autora; nikdy tiché vypuštění. Žádná nevratná migrace.

## Export a offline provoz

Pipeline: construction → surfaces/joints → unfold → tabs/labels → complete print geometry → autorský layout → validation → snapshot → SVG/PDF. A4 portrait i landscape používají stejné page transformace; PDF osa Y se převádí jednou. SVG stránka → `part-UUID` → CUT/FOLD_MOUNTAIN/FOLD_VALLEY/TABS/LABELS/ARTWORK/GUIDES; roles navíc třídy, žádné duplicitní cesty. Stránkové ARTWORK/GUIDES mimo díly. Text zůstává editovatelný, PDF vloží dostupný font s českou diakritikou; jeho distribuci/licenci tým ověří při balení, chybějící font je konkrétní chyba. Kalibrace 100 mm a instrukce 100 % / skutečná velikost.

Referenční editor P2: Inkscape na Windows, přesná verze zapsaná při proof; druhý editor volitelný. Dnešní interoperabilita není tvrzena. Síť není potřebná za běhu aplikace ani při exportu. PDF mimo fyzickou stránku nelze označit kompletní bez dlaždic; P2 dlaždice neimplementuje. Integrita a stale jsou tvrdé chyby; překryv a přesah doporučeného okraje uvnitř papíru lze vědomě přijmout pro konkrétní revizi. SVG kopie mimo viewBox nese varování; částečný PDF musí být explicitně označen jako částečný.
