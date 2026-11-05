# ArchPapercraft Studio — produktový a realizační mandát ADLC

Verze 1.0 · 2026-11-05 · návrh k realizaci v nové Codex session.

## 1. Produktový cíl a rozhodnutí vlastníka

Tvůrce postaví architektonický model, rozhodne o jeho dělení a spojích, ručně upraví rozmístění dílů a vyexportuje přesnou, graficky dále editovatelnou vystřihovánku. Výsledný model musí být možné vytisknout, vystřihnout a sestavit. Celá dlouhodobá vize zahrnuje architektonické detaily, materiálové kontroly, výztuhy, grafickou nadstavbu, návod a varianty modelu.

Potvrzená rozhodnutí z této přípravy:

1. Oživení se má řídit ADLC a konkrétními ověřenými přírůstky.
2. Tvůrce má plnou kontrolu nad rozmístěním na stránky. Automatika je volitelná pomoc.
3. Editovatelný vektorový výstup je základ. SVG pro další grafické úpravy a vektorové PDF pro tisk.
4. P2 obsahuje základní ruční rozmístění, propojení 3D ↔ 2D, švy a chlopně; nejde až o vzdálené rozšíření.
5. Všechny epiky navržené v tomto balíku patří do roadmapy. Zařazení do roadmapy neznamená okamžitou autorizaci jejich implementace.
6. Změna modelu nesmí potichu zahodit ruční rozmístění ani vydávat starý rozvin za aktuální.
7. Externě upravené SVG se v základu pouze exportuje. Jeho zpětný import je samostatná pozdější capability.

P0 + P1 jsou prvním realizačním balíkem. Produkční P2 následuje po přijetí konkrétního kontraktu vlastníkem. Tuto bránu nelze splnit pouze technickou revizí agentem. Následná fyzická akceptace vyžaduje člověka, ale nebrání souběžné nezávislé analytické práci na dalších epicích.

## 2. Výchozí stav a meze dosavadních důkazů

Repo: https://github.com/DaliborZ-tech/papercraft . Zkontrolovaný `master`: `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`, poslední commit 1.3.2026. Stav znovu ověř. Jde o referenci, nikoli příkaz k návratu starého checkoutu.

Python desktop, PySide6, NumPy, vlastní OpenGL viewport, geometrické presety, scene graph, švy, rozvin, chlopně, packing a exportéry. `pyproject.toml` deklaruje Python >=3.10, PySide6 >=6.6, NumPy, ReportLab, svgwrite, SciPy a PyOpenGL; volitelně DXF a OCC. Přesné verze a skutečné prostředí zatím nebyly ověřeny během běhu. Nenastavuj závislosti podle paměti jiného projektu.

Předběžné statické nálezy k reprodukci:

| ID | Zdroj | Pozorování / otázka k ověření |
|---|---|---|
| PC-F01 | `core_geometry/backend.py` | Mesh difference/intersection vrací `a`, union spojí sítě. Nepodporované CSG nesmí být úspěchem. |
| PC-F02 | backend, primitives, pyproject | Deklarace `pythonocc-core`, importy `OCP`; ověřit instalaci a skutečnou kompatibilitu backendu. |
| PC-F03 | `unfolder/strategies.py` | `generate_rings` vytváří lichoběžníky; pro kuželový pás je analytický rozvin mezikruhová výseč. |
| PC-F04 | `paper_analyzer/classifier.py` | Klasifikace podle lokálních úhlů nezaručuje rozvinutelnost. Ověřit na jemně triangulované kouli. |
| PC-F05 | `ui/papercraft_panel.py` | Packing probíhá před generováním chlopní; obálka tisku je neúplná. |
| PC-F06 | `tests/test_unfolder.py` | Řada testů ověřuje tvar pole nebo počet, nikoli správnost rozvinu. |
| PC-F07 | exact unfold + seam graph | Ověřit chybějící hranice, uzavření cyklů, pokrytí faces, překryvy a konzistenci ID. Předběžná otázka, ne prokázaný runtime nález. |
| PC-F08 | UI + scene graph | Ověřit picking, transformace rodičů, invalidaci a zachování ručního stavu. Nepředpokládat funkčnost podle nabídky menu. |

Zdrojový manifest rozlišuje přečtené soubory a otázky k ověření. V této přípravě nebyl spuštěn pytest, desktop ani fyzická stavba. Počty z commit messages nejsou dnešní baseline. Historické tvrzení „všechno funguje“ musí být ověřeno uživatelským průchodem.

## 3. Reconnaissance a první pracovní balík

### PC-001 — Stav repozitáře a reprodukovatelná baseline

Přečti AGENTS a relevantní lokální pravidla, pokud existují; README, specifikaci, manuál, pyproject, sample, entry point, UI, scene/transform/node, project IO a dotčené moduly. Prohledej existující workflow před zakládáním nových. Nevymýšlej obsah podle názvu. Zaznamenej branch, SHA, dirty state a cizí práci bez zveřejnění tajných údajů.

V izolovaném prostředí ověř instalaci, import, dependency check a testy. Odděl core a Qt/OpenGL výsledky; zapiš OS, Python, balíčky, příkazy, časy, exit code, přesný počet PASS/FAIL/SKIP a důvod skipu. Neinstaluj globálně ani neobcházej firemní proxy. Chybí-li přístup, označ konkrétní limit a pokračuj dostupným rozsahem.

Spusť aplikaci a projdi nový projekt → vložit/editovat objekt → uložit → otevřít → švy → rozvin → export. Na Windows ověř desktop, OpenGL a reálné souborové dialogy. Headless Qt je dílčí ověření, ne důkaz použitelnosti viewportu. Pokud pracuješ na Linuxu, připrav přesný malý Windows reproduction pack a nech platformní proof pending.

Výstup: jeden `BASELINE_REPORT.md`, aktuální stav a reprodukovatelné příkazy. Selhání neskrývej změnou testů. Po prvním informativním výsledku neopakuj full suite bez důvodu.

### PC-002 — Diagnostika geometrie a exportu

Vytvoř malé referenční fixtures: panel, krabice, domeček, válec, kuželový pás, jemná koule a přesunutý/otočený rotační objekt. Každý experiment má otázku, očekávaný analytický výsledek, aktuální výsledek a interpretaci. Měř délky, plochy, párování, počet/pokrytí ploch a tiskové rozměry. Nezávislé orákulum nesmí kopírovat stejný algoritmus.

Doplň diagnostické testy tam, kde dokazují konkrétní vadu. Produkční opravy P2 do tohoto balíku neschovávej. Minimální oprava prostředí/test harness je možná jen odděleně, s vysvětlením a původním výsledkem. Známá očekávaná selhání nesmějí skrýt jiné výjimky; stav dokumentuj.

Výstup: `FINDINGS.md` s klasifikací blocker/major/minor, reprodukcí a návrhem; `GEOMETRY_SPIKE.md` s analytickými kontrolami a throwaway prototypem, pokud rozhodnutí vyžaduje experiment. Spike není hotové nové jádro.

### PC-003 — Rozhodnutí o obnově

Porovnej opravu současného jádra, náhradu pouze geometricko-papírové pipeline a širší přestavbu. U každé varianty uveď přínosy, rizika, migraci projektů, náklady podložené discovery a zachovatelné moduly. Nevol automaticky úplný rewrite ani automaticky zachování všeho.

Výchozí doporučení k ověření: parametrická konstrukce jako autoritativní model, společná geometrie pro 3D i papírové díly, explicitní konstrukční spoje; trojúhelníková síť slouží především jako projekce pro zobrazení a později import. Bez nezbytného důvodu nedělej z prvního řezu obecný CAD.

Výstup: `ARCHITECTURE_DECISION.md` s vybranou variantou a důvody. Změna stacku je skutečný tradeoff, který musí být předložen vlastníku s konkrétním dopadem. PySide6 ani Python samy o sobě nejsou doloženou příčinou problému.

### PC-004 — UX a produktový kontrakt

Navrhni konkrétní rozložení pracovního prostoru: strom konstrukce, propojený 3D pohled, 2D díly/tiskové stránky, vlastnosti vybraného dílu/spoje a přehled problémů. Režimy Konstrukce / Díly a spoje / Stránky / Grafika / Návod mohou sdílet výběr; první verze zobrazí pouze skutečně realizované schopnosti.

Dodej obrazovky nebo lehký prototyp základních stavů: prázdný projekt, domeček, vybraný spoj a protikus na jiné stránce, změněný díl čekající na kontrolu, kolize chlopně, exportní souhrn. Přesun mezi 3D/2D nesmí ztratit kontext. Časté akce mají být dostupné přímo; přesné parametry také číselně. Destruktivní editace mají undo. Technické termíny nejsou povinná znalost modeláře.

Výstup: `UX_CONTRACT.md`, `P2_IMPLEMENTATION_CONTRACT.md`, mapování epic → požadavek → AC → test/demo, aktualizovaná jediná queue a nezávislé review celé P0/P1 sady.

### Konec prvního balíku

Předlož rozhodnutelný výsledek. Brána není neurčité „mohu pokračovat?“: ukaž doporučenou variantu, UX, seznam toho, co přesně dostane vlastník v P2, co zůstane později a konkrétní tradeoffy. Pokud nejsou produktové alternativy sporné, otázka má být jediná: přijetí tohoto konkrétního P2 kontraktu. Než ji položíš, dokonči vše nezávislé a dostupné. Zablokované prostředí popiš samostatně.

## 4. Architektonické hranice pro cílové řešení

Následující je výchozí kontrakt k dopracování v P1, ne hotová implementace ani příkaz přidat všechny entity hned.

### Autoritativní data a projekce

- `Project`: verze schématu, jednotky vstupu, měřítko, materiály, konstrukce, stránky a autorská metadata.
- `ModelElement`: stabilní ID, typ, parametry, hierarchie, transformace a revision.
- `SurfaceRegion` / `BoundaryEdge`: významové plochy a orientované hrany se stabilním původem. Dočasný triangle index není identita.
- `Joint`: dvojice kompatibilních hran/intervalů, orientace, typ spojení, tolerance a vlastník chlopně. Hrana nemusí být lepený spoj.
- `PaperPart`: rozvinutá geometrie, vazba na konstrukci, vnitřní fold edges, hranice a revize zdroje.
- `Tab` / `GlueStrip`: explicitní odvozená geometrie, vlastnictví spoje a autorský override.
- `Page` / `Placement`: stabilní ID stránky, formát/materiál, part ID, posun v paper mm, rotace, samostatné zámky pozice/rotace.
- `Artwork`: grafika v souřadnicích dílu nebo stránky; konstrukce a potisk se nesmějí nechtěně přepsat navzájem.
- `AssemblyStep`, `ValidationIssue`, `ExportSnapshot`: postupně podle epic; vždy reference na konkrétní revision.

Doména a geometrie bez Qt widgetů. UI vysílá příkazy; aplikační vrstva řeší validaci, undo a invalidaci. Export nesmí číst nesouvisející globální UI stav. Služby nemají vyžadovat spuštěný viewport. Dlouhá geometrická operace musí mít stabilní vstupní snapshot; zastaralý výsledek se neaplikuje na novější projekt.

### Jednotky, geometrie a topologie

Zvol a zdokumentuj jeden interní délkový systém. Doporučení: model mm, paper mm; měřítko oddělený bezrozměrný převod. UI může přijímat m/cm/mm. U vstupu 10 m při 1:100 musí na papíře vzniknout 100 mm. Žádné další unit-to-mm na již převedené souřadnice.

Zvol osy, orientaci polygonů, normály a transformace včetně rodičů. Používej polygonové hranice, díry a významové hrany; vnitřní triangulace nesmí vytvořit řeznou čáru. V první verzi planar panels a ověřené rovinné spoje; analytický válec/kužel až v příslušném řezu. Dvojitě zakřivená plocha nemá přesný bezdeformační rozvin. Nabídni aproximaci s chybou, nebo ji odmítni.

Neztrácej protikusy při dělení dílu. Tab může být na jedné straně spoje, případně nahrazen páskem či bezchlopňovým spojem; oboustranné chlopně musí být výslovný záměr. Nekompatibilní hrany se nesmí spojit podle pouhé podobnosti délky.

Mountain/valley značení vychází z orientované geometrie a explicitní přední/potištěné strany, nikoli ze setříděných vertex indexů. P1 definuje konvenci na analytickém vnějším hřebenu a konkávním rohu; P2 ji ověří také při změně indexace, otočení dílu a obrácení papírové strany. Zrcadlení není zaměnitelné s rotací a nemá být tiše podporované bez vlastního kontraktu. Generátor chlopní musí určit vnější stranu skutečného materiálového obrysu včetně vnitřních otvorů.

### Pipeline a závislosti

Parametrická konstrukce → validované povrchy a spoje → švy/rozvin → chlopně a značky → úplná geometrie pro tisk a její obálky → ruční/volitelné automatické rozmístění → validace → SVG/PDF ze stejného snapshotu.

Grafika má jinou kolizní sémantiku než konstrukční materiál. Packing používá geometrii dílu včetně chlopní a potřebných odstupů; pracovní pomocné značky mají definovanou politiku. Export nikdy nevolá automatické přeskládání bez explicitního příkazu autora.

### Identita a změny

Odděl `entity_id`, obsahovou revision a uživatelské číslo dílu. Determinismus znamená stejný projekt a exportní nastavení → stejný geometrický/identitní obsah; timestamps v PDF mohou být normalizované, pokud se porovnávají bytes.

Nezměněné díly si zachovají pozici, rotaci, zámky a grafiku. Změněný díl dostane stav ke kontrole; původní pozice se zachová, pokud existuje jednoznačná kontinuita. Split/merge vyžaduje mapování předchůdců; nejednoznačné grafické či rozvrhové reference se označí, nesmějí tiše přeskočit na jiný díl. Smazání prvku nesmí ponechat zdánlivě platný export či visící referenci.

Změna měřítka odděluje přepočet konstrukce od fyzické šířky chlopní, fontu a tloušťky linek. Výchozí chlopně a tiskové značky zůstávají v praktických paper mm; uživatelská volba může politika změnit. Změna této politiky se uloží a má undo.

### Persistence a kompatibilita

Atomický save s rollback/recovery, explicitní schema version a validace reference integrity. Nevratná migrace bez zálohy je nepřípustná. Starý sample `.apcraft` je fixture: buď doložený import, nebo srozumitelně odmítnutá verze s originálem zachovaným. Částečná podpora se označí a nesmí při uložení potichu odstranit neznámá data. Ztrátová konverze vyžaduje nový soubor a rozhodnutí autora.

### Exportní kontrakt

SVG: jeden soubor na stránku, `width`/`height` v mm a odpovídající `viewBox`, transformace zachovávající měřítko, stabilní ID dílů a logické skupiny CUT / FOLD_MOUNTAIN / FOLD_VALLEY / TABS / LABELS / ARTWORK / GUIDES. Potenciálně také editorové vrstvy, ale nespoléhat na proprietární atributy pro základní význam. Chlopně a řezy nesmějí kreslit duplicitní společnou hranu; text má dohodnutou font politiku. Při text-to-path je nutné zachovat i editovatelnou variantu nebo explicitní nastavení.

Základní SVG hierarchie: stránka → skupina `part-<stable-id>` s umístěním/rotací → vnořené sémantické skupiny pro konstrukci, chlopně, popisky a grafiku. Stránkové GUIDES/ARTWORK jsou samostatně. Každý fyzický díl lze v externím editoru vybrat a přesunout jako celek včetně čísel a chlopní. Sémantické role lze navíc označit metadaty/třídou; nevytvářet duplicitní vykreslované cesty jen kvůli dvěma druhům organizace. P1 může doložit ekvivalentní editorově použitelnou strukturu, ale musí splnit skupinovou i sémantickou editaci.

Validace rozlišuje neprominutelné chyby integrity (rozbité reference, neaktuální geometrie, neplatná čísla, chybějící část modelu) a autorská varování (například zvolený překryv nebo přesah tiskového okraje). Potvrzení varování není oprava integrity. Přesah mimo doporučenou tisknutelnou oblast, ale stále uvnitř fyzické stránky, lze vědomě přijmout s upozorněním na možnosti tiskárny. Přesah mimo fyzickou stránku nelze označit jako kompletní tisknutelný výstup bez korektního dlaždicování nebo změny formátu. Editovatelný SVG může zachovat i geometrii mimo viewBox, ale exportní souhrn musí upozornit na její umístění. Částečný/ořezaný PDF je pouze výslovně označený částečný výstup, nikdy úplná vystřihovánka.

PDF: vektorové konstrukční cesty a text, vložené dostupné fonty s českou diakritikou, správný fyzický rozměr stránky a identická geometrie jako SVG. Bitmapové textury jsou přípustné; rasterizace celé stránky ne. Povinná tisková instrukce 100 % / skutečná velikost, kalibrační úsečka a rozlišení měřítka modelu od škálování tiskárny. PDF vrstvy nejsou automaticky povinností první verze; logické skupiny SVG ano.

Externí SVG editor v P2: otevření a editace, nikoli round-trip. Konkrétní editory zvolit a zaznamenat v P1 podle dostupnosti; nejméně jeden skutečný editor musí být ověřen před tvrzením interoperability. Druhý je doporučený další proof, ne vymyšlený PASS.

## 5. ADLC a odpovědnosti

| Krok | Povinný výsledek | Co se nedá zaměnit za dokončení |
|---|---|---|
| Intake/discovery | Uživatelský cíl, skutečný stav a deduplikace | Pouhé převzetí starého README |
| Analýza | Scénáře, IN/OUT, pozitivní/negativní AC | Seznam názvů funkcí |
| Architektura | Data, geometrie, kompatibilita, konkrétní tradeoff | Obecný obrázek modulů |
| UX | Ovládání a význam prázdných, chybových, dirty/stale stavů | Jen screenshot ideálního stavu |
| Implementace | Nejmenší ucelený funkční přírůstek | Třídy, které se nedají použít přes aplikaci |
| Ověření | Numerické testy + integrace + reálný desktop/export | Existuje soubor nebo zelený shape test |
| Nezávislé review | Jiný agent, konkrétní CODE pin, AC a důkazy | Implementátor přepne roli a schválí se |
| Opravy/re-review | Uzavřené nálezy a relevantní regrese | První PASS po více neanalyzovaných pokusech |
| Předání/akceptace | Demo a srozumitelný výsledek, PO verdict zvlášť | AGENT_VERIFIED vydávané za PO_ACCEPTED |
| Learning | Konkrétní prevence opakovaného problému | Další obecný procesní dokument |

Role jsou odpovědnosti, ne povinnost rozjet mnoho session. Doporučené rozdělení: coordinator/integrator, geometry specialist, UX/product analyst, implementer, QA a independent reviewer. V P0 lze paralelně analyzovat geometrii a UX; závislá rozhodnutí zůstanou sekvenční. Při paralelních zápisech použij oddělené worktrees nebo jednoznačně oddělené soubory. Nesdílej mutable projektový soubor mezi testy/agentními procesy.

Reviewer dostane problém, normativní AC, základní SHA, změnový CODE SHA, diff, příkazy a evidence. Musí provést vlastní cílené kontroly, zejména analytické geometrické případy a hraniční stav. Nedostatek Windows, fyzického proof nebo grafického editoru není PASS; má přesný follow-up. Pro numerické/topologické jádro je nutný adversarial pohled na degenerace, orientaci, díry, cykly a změny ID.

Počet opravných kol není univerzální stop. Další pokus musí mít novou diagnózu nebo užitečný ověřovací cíl. Opakované selhání stejného přístupu vede ke změně postupu nebo druhému odbornému pohledu. Neopakovat náhodně testy až do prvního zeleného běhu.

## 6. Git, autonomie a rozsah změn

### Povinné umístění a bootstrap repozitáře

Vlastník výslovně požaduje: **agent naklonuje repo přímo do adresáře, ve kterém už je VS Code otevřený.** To je konečný kořen checkoutu; žádná automatická podsložka `papercraft`, jiný disk nebo odhadnuté `C:\\Users\\...`. Nezaměňuj vlastní cloudový scratch za workspace uživatelova VS Code. V multi-root workspace zjisti skutečně aktivní cílový root; při nejednoznačnosti je nutná jediná konkrétní otázka na cílový adresář.

1. Zjisti a zaznamenej skutečný absolutní workspace root a cwd. Ověř jeho obsah, případný vlastní `.git` a zda neleží v jiném nadřazeném Git worktree. Nepoužívej náhodný terminálový cwd jako důkaz, pokud se neshoduje s otevřeným rootem.
2. Prázdný root bez Git použij jako `git clone https://github.com/DaliborZ-tech/papercraft.git .`, se správným working directory. Tečka je podstatná.
3. Pokud jde již o checkout tohoto repa, ověř remote a dirty state a pokračuj v něm. Neprováděj nový clone ani reset. Jiný repo root či nadřazený worktree nezměň na papercraft a nevytvářej v něm bez rozhodnutí vlastníka vnořený repo.
4. Je-li root neprázdný, ale bez Git, nesmaž ho. Může obsahovat předaný brief. Proveď staging clone do dočasného adresáře, kompletní preflight kolizí sledovaných cest a bezpečné přenesení checkoutu včetně `.git` do otevřeného rootu až po úspěšné kontrole. Porovnej obsah existujících cest, rozliš soubor/adresář/symlink a zohledni Windows case-insensitive názvy. Shodné soubory lze ponechat; nesouvisející nekolizní soubory zůstanou nedotčené. Neprováděj částečný přesun před dokončením kontroly. Pokud se nedá bezpečně provést celý krok, použij zálohu a vratný postup, nebo předlož konkrétní kolizi vlastníkovi. Žádné `--force`, mazání, automatické stashování cizích dat ani tajné přepsání. Dočasný staging není konečné umístění projektu.
5. Po bootstrapu musí `git rev-parse --show-toplevel` odpovídat otevřenému rootu, remote musí odpovídat požadovanému repu a sledovaný obsah musí odpovídat naklonovanému commitu. Původní nesledované soubory ponech a nevkládej automaticky do commitu. Předané zadání lze vědomě zařadit do dokumentace podle tohoto mandátu.

Autorizace P0 zahrnuje tento clone/bootstrap. Přístupový problém diagnostikuj běžným přihlášeným Git/connector prostředím bez vyzrazení credentials. Vytvoření vývojového prostředí a závislostí následuje až po ověření správného kořene.

Před zápisem ověř pracovní strom. Cizí dirty změny nemaž a nezařazuj do vlastního commitu. Použij izolovanou pracovní větev od aktuálního stavu, např. `revival/p0-p1-contract`, pokud nekoliduje s existující prací. Výchozí větev tohoto projektu je `master`; nekopíruj develop→master pravidla z TestFlow nebo TestMap.

První mandát dovoluje analytické podklady, diagnostické testy/fixtures a oddělené technické spiky. **Oprava vlastníkem z 5. listopadu 2026:** dokončený ucelený balík v již autorizovaném produktovém rozsahu musí být po ověření a nezávislé revizi integrován a pushnut na `master`, bez další rutinní žádosti. Tato aktuální autorizace zahrnuje P0 + P1 a budoucí ověřené a nezávisle schválené balíky v jejich autorizovaném rozsahu; nejde o oprávnění převzaté z jiného projektu.

Před integrací ověř čistý stav nebo bezpečně odděl cizí práci, remote a aktuální `origin/master` po fetch. Použij fast-forward, pokud je možný, jinak standardní merge. Zachovej vzdálené změny. Konflikty a věcnou změnu integrovaného výsledku znovu ověř a nech nezávisle zkontrolovat v potřebném rozsahu. Push prováděj bez force a ověř shodu lokálního a vzdáleného SHA. Předání obsahuje vzdálený commit a GitHub odkazy na výstupy. Přepis historie, produkční release, placené služby ani produkční implementace dosud neautorizovaných etap tím povoleny nejsou.

Integrace a push P0 + P1 nejsou přijetím kontraktu P2, varianty B ani navržené kompatibility. `GATE-P2` nadále vyžaduje skutečné samostatné přijetí vlastníkem. Přijetí produktu, technická revize a integrace do `master` se evidují odděleně. Aktivní pracovní instrukce pro další session jsou také v `AGENTS.md`.

V P2 po přijetí kontraktu jsou běžné implementace, opravy, cílené testy, refactoring v daném řezu a review autonomní. PO rozhoduje o významné změně produktu, ztrátě kompatibility, placeném nákladu nebo přijetí reálného omezení. Nemá rozhodovat o metodě triangulace či opakovaně schvalovat bezpečný diagnostický experiment.

Nevytvářej v repozitáři instalovatelné globální agentní skilly bez potřeby. Stačí projektové pracovní instrukce a šablona úkolu. Nepřenášej staré TestFlow security incidenty, limity či protocol fáze do papercraftu.

## 7. Kvalita, rozsah testů a předání

Detailní numerické hodnoty a scénáře jsou v `04_ACCEPTANCE_AND_VERIFICATION.md`; jeho kritéria jsou normativní součást tohoto mandátu. P1 je může zpřesnit, ale nesmí je potichu oslabit. Relevantní změna tolerance či user meaning musí mít důvod a review; změna produktové garance jde vlastníkovi.

Každý ticket má problém/story, baseline, IN/OUT, závislosti, data/UX impact, AC, způsob ověření, implementační plán, review a krátký demo scénář. Ověřuj úměrně změně: core při matematice, Qt při příkazech a persistence, reálné GUI při interakcích, exportní obsah při tisku. Full v checkpointu, opakovat až po změně či nové nejistotě. Snapshot obrázku není sám důkaz numerické přesnosti.

Stavy: PLANNED → READY → IN_PROGRESS → IMPLEMENTED → IN_REVIEW → CHANGES_REQUIRED / AGENT_VERIFIED → PO_PENDING → PO_ACCEPTED. BLOCKED je doplňkový stav s důvodem a odblokovací podmínkou. Release readiness samostatně; žádný technický stav sám neznamená schválení vydání. Pro technickou údržbu bez produktové akceptace lze ticket uzavřít technickým verdiktem podle kontraktu.

Report pro PO má nejprve výsledek: co teď skutečně jde udělat, jak to vyzkoušet, co bylo ověřeno, co zůstává neověřené a jaké konkrétní rozhodnutí je potřeba. Za tím stručně SHA/branch a odkazy na důkazy. Neukončuj celý balík po jednom diagnostickém podúkolu. Současně nezamlč známý blocker jen proto, aby výsledek vypadal hotově.

Závěrečné P0/P1 deliverables: aktuální baseline, reprodukované nálezy a experimenty, keep/fix/replace mapa modulů, vybraná architektura, kompatibilita/migrace, UX, přesný P2 kontrakt s AC, závislosti všech epic, realistický odhad s nejistotami a nezávislý review verdikt. Pokud některý proof objektivně chybí, musí být jasné, které rozhodnutí blokuje a které další práce lze dokončit.
