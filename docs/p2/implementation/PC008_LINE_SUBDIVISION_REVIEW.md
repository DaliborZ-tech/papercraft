# PC-008 / AU13 — nezávislé review živého LINE split/merge

Reviewer `/root/commands_review`, 11. 11. 2026, není autorem aplikace/UI (`/root`) ani čisté matematiky (`geometry_analysis`). Vlastní izolovaný worktree `papercraft-profile-subdivision-review`, větev `review/au13-line-9b87c89` vznikl z přesného **9b87c89e1507b1df56940e4c08d213532a5216ad**. Žádný produkční soubor se v něm nemění. Všechny běhy jsou navíc z fresh exact archivu konkrétního pinu, s explicitním PYTHONPATH, Qt offscreen a skutečnými import/hash guards. [Runner](evidence/pc008-line-subdivision-review-run.py), [vlastní oracles](evidence/pc008-line-subdivision-review-own.py).

**Finální verdikt: APPROVED_IN_LINE_TECHNICAL_INCREMENT_SCOPE.** Přesný CODE **24e08019a711c5c7c19ca73a5ac35e5093dfb4d0** a METADATA **93f650c4a22a9d1dffd3b65c69f4b9505d5889f7** prošly komponentovou i samostatnou kontrolou skutečných native/SVG/PDF/Inkscape artefaktů. LS01–LS05 a LINE-BEND01 jsou CLOSED / VERIFIED v tomto rozsahu; žádný zbývající zásadní nález bránící tomuto LINE přírůstku. Balík je technicky připraven k integraci/pushi po níže vymezené mechanické aktualizaci closure metadat a jejich úzké kontrole. Celé AU13/AU14/PC008/P2, produktové přijetí, nový uživatel ani fyzické P3 se tím neuzavírají.

## Skutečně provedené běhy

| Pin / scope | Vlastní nezávislé spuštění |
|---|---|
| 9b87c89 původní pure/domain/widget | 77 PASS, 2.19 s [JUnit](evidence/pc008-line-subdivision-review-original-9b87c89.xml) |
| 9b87c89 vlastní první oracles | 7 PASS / 3 FAIL, 0.97 s, skutečné LS01/02/03 [JUnit](evidence/pc008-line-subdivision-review-own-9b87c89.xml), [manifest](evidence/pc008-line-subdivision-review-9b87c89.json) |
| a770f8a původní s known bend fixem | 80 PASS, 3.55 s [JUnit](evidence/pc008-line-subdivision-review-original-a770f8a.xml) |
| a770f8a vlastní rozšíření | 17 PASS / 5 FAIL, 2.64 s; stejné tři problémy a dvě další varianty téhož LS02 [JUnit](evidence/pc008-line-subdivision-review-own-a770-expanded.xml) |
| 694db185 původní po LS01/02/03 opravě | 89 PASS, 3.96 s [JUnit](evidence/pc008-line-subdivision-review-original-694db18.xml) |
| 694db185 vlastní včetně nového area oracle | 22 PASS / 1 FAIL, 2.62 s; LS04 [JUnit](evidence/pc008-line-subdivision-review-own-694db18.xml), [manifest](evidence/pc008-line-subdivision-review-694db18.json) |
| 694db185 cílené nové hole cases | Dva samostatné FAIL, 1.20 s každý; společná LS05 příčina [split](evidence/pc008-line-subdivision-review-own-694-hole-split.xml), [edit](evidence/pc008-line-subdivision-review-own-694-hole-edit.xml) |
| 24e08019 původní po LS04/05 opravě | 95 PASS, 4.51 s [JUnit](evidence/pc008-line-subdivision-review-original-24e0801.xml) |
| 24e08019 vlastní dosavadní a whole-body three-hole oracle | 26 PASS, 2.58 s [JUnit](evidence/pc008-line-subdivision-review-own-24e0801.xml), [manifest](evidence/pc008-line-subdivision-review-24e0801.json) |
| 24e08019 další cílený scale/load area oracle | 1 PASS, 1.08 s [JUnit](evidence/pc008-line-subdivision-review-own-24e0801-scale.xml), [manifest](evidence/pc008-line-subdivision-review-24e0801-scale.json) |

Běhy se nesčítají jako jedinečné testy. Autorovy full1447/1450 a další full běhy nejsou zde vydávány za vlastní fullsuite. Původní native StopIteration ani chybná expectation 90/144 versus skutečně zadané 100/160 nejsou prohlášeny za finální PASS. Novější native/export/editor výsledky musí být posouzeny zvlášť. Staré manifesty a JUnit FAIL se nepřepisují.

## Nezávislá matematika a vymezení čisté komponenty

Pro cubic restriction je vlastní expected odvozen z nezávislé endpoint/derivative Hermite identity: `Q0=P(a), Q1=P(a)+(b-a)P'(a)/3, Q2=P(b)-(b-a)P'(b)/3, Q3=P(b)`. Vyhodnocení původního polynomu používá přímo Bernstein binomickou formuli, ne implementovaný de Casteljau helper. Tři neuniformní i obrácené intervaly jsou přesně Fraction shodné; jde o identitu celého polynomu, nikoli konečné vzorkování.

Nested split 1/3, dále 2/5 potomka a inverse merge mají ručně odvozené globální source intervals a reverse trim start/end. ReferenceID zůstává stejné. Near-boundary `2/3+2^-80` se nesnapne k sousedovi či sharedpointu. Opačné 90° arc děti ponechávají stejný immutable zdroj a přesné sweep 30/60; nominal point bounds pro 30° mají nezávislé `x²=27/4, y=±3/2` uvnitř úzkých racionálních intervalů. To je důkaz nominal source matematiky, nikoli manufacturing SVG arc topology.

Shared endpoint po změně jedné geometrické generace zůstává UNRESOLVED i při souhlasné zobrazené souřadnici. Přesná source/replay historie odmítá reuse retired ID, nepodporovaný one-to-many single-edge adapter i nadlimit 1025 events. Serialized history je striktní event replay, nikoli důvěra dodaným child controls. Lokální scalar wrapper bezpečně převádí malformed arithmetic na typed odmítnutí.

## Aplikační konstrukce a UI

Historická hrana se převádí na celý deklarovaný řetězec, ne na první child. Hinge/glue musí zůstat odlišné od omezené semantic-axis chord výjimky. PaperFrame ukládá stabilní root/axis/anchor identity; retired vertex se řeší explicitním source parametrem. History jsou součástí part_input a source geometrie se při editaci synchronizuje jako deklarovaný nový zdroj, nikoli nearest fit. Přísné neznámé schema6 a legacy1–5 s podvrženým novým registry field zůstávají odmítnuté; known-copy SaveAs není in-place migrace.

Vlastní Qt zkoušky používají skutečný dialog/controller API: external live-name change během modal preview blokuje stale confirmation a zachová novější stav; rozepsaný hlavní numerický rozměr bez Enter se commitne před vytvořením dialogové source kopie a následný Cancel neprovede split. Původní widget scénáře ověřují opravitelné chyby, bezpečné Cancel/Undo/Redo a selection context. Nejde o native Windows ani nového modeláře.

Live ARC/CUBIC split je explicitně odmítnut bez mutace. Loft φ/trim adapter není automaticky získán čistou matematikou; širší AU13 zůstává pending. Změna source profilů loftu se nesmí vydávat za podporované automatické remapování.

## Nálezy, původní důkazy a uzavření

**LINE-BEND01 — známý nativní missing consumer.** Původní 9b bend.py hledá retired whole-edge pouze v active world boundary, což u existující chlopně vede ke StopIteration. Root a770f8a8bed102bcf8538d0e57e4f5659f809949 převádí skutečný edge_source přes _surface_world_points a rozšiřuje assembly key o použité history a všechny skutečné source profily, včetně druhého profilu loftu. Zdroj zůstává celý, bez first-child. Dva vlastní replays 2/7 s known i unknown materiálem mají stejnou connector geometry a bend status před/po splitu. **Komponentová oprava i finální skutečný native24e proof ověřeny.** Původní fullsuite PASS nepřekrývá původní native FAIL.

**LS01 MAJOR — nekontrolovaná float projekce zdroje. CLOSED / VERIFIED po 694 a zachováno 24e.** 9b/a770 přijaly open LINE `(1e16,0)→(1e16+4,3)`, scale1, split1/4. Nový material point je `(1e16,.75)` místo exact `(1e16+1,.75)`; kolmá odchylka je 0.6 mm, ale historický full-edge dále tvrdí původní straight hinge. Původní vlastní repro beze změny expected nyní bezpečně odmítne. Source→actual whole-LINE position guard využívá convex endpoint L1 bound. Globální součet endpoint length reserves je uplatněn na celý profil napříč histories, nikoli nová .01 rezerva pro každý child.

Subbudget .01 není topology/clearance licence: fyzický historický handle kontroluje skutečné binary potomky, přesnou collinearitu, spojitost a monotonicitu i vracené projected endpoints. Zdravé fyzické refs se při topology-only splitu nesmějí změnit na falešně zdravý zdroj. Paper-axis chord výjimka zůstává oddělená; záměrná autorská geometry edit má samostatnou saveable UNRESOLVED cestu.

**LS02 MINOR — globální historical UUID alias. CLOSED / VERIFIED po 694, zachováno 24e.** Po split→merge dvou profilů šlo v raw payload sjednotit různé retired cut vertices na stejné UUID. Retired set jej sloučil a from_dict přijal dvě odlišné point creations. Další vlastní varianty: dvě root histories stejného profilu a vertex→retired-edge typová kolize. Nové creation ownership napříč root/event/profile i typy jsou jedinečné; legitimní sdílený původní seed stejného profilu mezi sousedními root edges stále projde. Integrity bug není vydáván za doložený geometry swap.

**LS03 MINOR — malformed rational není typed error. CLOSED / VERIFIED po 694, zachováno 24e.** Serialized split parameter `1/0` unikal z _scalar/Fraction jako ZeroDivisionError mimo ProjectFormatError. Přesný původní vlastní repro má nyní typed odmítnutí: ArithmeticError se lokálně normalizuje na ValueError a doménový reader odmítne formát. Nejde o povolení takové hodnoty.

**LS04 MAJOR — position/length nenahrazuje area. Historický FAIL694; CLOSED / VERIFIED24e.** Scale1/1024, uzavřený profile `[(1e16,0),(1e16+2,2^20),(1e16+4,0)]` má source area 2 mm². Split první hrany v1/4 se na694 přijme a actual float area je9/4 mm²: delta1/4 > původní .01. Position≈.000488 mm i globální délková rezerva přesto projdou. Expected/actual jsou nezávislé exact Fraction shoelace, nikoli implementovaný validační helper. Na24e je stejný split atomicky odmítnut. V02/SK011 se týká i této hranice, bez nové tolerance v mezikroku a bez chlopní v relativní referenci.

**LS05 MINOR — wrong-profile fyzický reference lookup při hole editaci. Historické FAIL694; CLOSED / VERIFIED24e.** Po změně na `profile_id in surface.source_profile_ids()` se outer joint edge řešil proti aktualizovanému HOLE profilu. Skutečný two_panels fixture s platným vzdáleným otvorem měl dvě nesprávné reakce: split hole edge1/2 se odmítl kvůli lookupu outer edge v hole; prostý hole vertex edit bez jakékoli subdivision historie přepnul nezměněný outer joint na UNRESOLVED. Nový helper kvalifikuje skutečného active/historical vlastníka hrany. Oba původní vlastní replays nyní zachovají zdravý outer joint; actual material/contact revalidation otvoru není vypnutá.

## Matematika opravy plochy a její vlastní další oracles

_check_subdivision_area porovnává přímo přesný translation-relative Green integrál actual binary LINE a deklarované canonical-history LINE. Nezměněné ARC/CUBIC členy na obou stranách jsou stejné, proto se ruší přesně; při mixed boundary je pro relativní normalizaci konzervativně lower0, nikoli neprokázaná sampled reference. Kontroluje se canonical source chain continuity a pro all-LINE také orientace. Pro absolutní plochy platí `||A|-|B|| ≤ |A-B|`; není použit position annulus.

Explicitní geometry edit deklaruje nový source; untouched canonical split point se nemění na starý rounded float jen kvůli editaci jiného rohu. Konstrukční odmítnutí přeslimitní topology-only změny tím není obcházeno.

V material part se sčítají konzervativní absolutní odchylky outer/holes všech dotčených rovinných surfaces. Plane/rigid-transform Jacobian počítá přesné binary vstupy a outward sqrt interval; error používá horní a source-body reference dolní mez. Různé orientace otvorů nemohou falešně rušit nejistotu. ONE body-only tolerance vylučuje chlopně. Nepodporovaná loft konstrukce tím nedostává nový podporovaný adapter.

Vlastní whole-body oracle má jiný skutečný outer rectangle a tři oddělené triangle holes: scale1/8192, source net area125/32 mm². Každá přijatá díra získá1/256 mm². První dva splity projdou; třetí by dal celkovou chybu3/256>.01 a je atomicky odmítnut. To ověřuje skutečný callsite přes material body, nikoli jen per-profile formuli.

Další vlastní oracle vytvoří přijatelné zaokrouhlení, ověří closed load a změní scale×2: chyba plochy se násobí4, set_scale odmítne se zachováním celé původní dictionary a zfalšovaný raw scale odmítne typed ProjectFormatError. Původní tolerance ani malé prvky nebyly odstraněny.

## Úzké review diagnostického harness delta

Delta9290a0156e112021d926075d05a9c6b5ca817a5c zachovává skutečný window.run a jeho operation: wrapper jen čte exception traceback a znovu vyhodí původní exception, skutečné UI stále zobrazuje chybu. FAIL-partial dictionary se zapisuje před screenshot capture, aby chyba fotografování neschovala source. Žádná domain command/result/geometry injekce.

Opravená explicitní tab oracle `100×2×(1+.6)/2=160 mm²` odpovídá skutečně vytvořenému full[0,1] connectoru; driver kontroluje interval/width/taper/count/shape/overrides a původní .01 mm² se nemění. Historický expected90/144 FAIL zůstává. Independent wall+roof+tab expected je `4000+100*hypot(30,35)+160`, base13000 mm². Spojení driveru s konečným skutečným artefaktovým důkazem24e je ověřeno v následující části.

## Uplatněné skills a zbývající důkazy

AGENTS a všechny čtyři skills byly skutečně načteny; po opravě24e znovu i čtyři dotčené texty. Construction oddělil source identity od hinge/material certainty a root/page kotvy; UI prověřil C05/stale/Cancel a srozumitelnou opravnou cestu; verification vedl k exact cubic/arc/trim oraclům, global aliases a samostatnému area svědku LS04 včetně holes a scale; delivery zachoval všechny pin/FAIL výsledky a neuzavírá celé P2 komponentovým PASS.

Nové lessons/metadata autora se budou revidovat zvlášť; širší efficacy není prokázána touto opravou. Nový člověk0/NOT_RUN a P3 zůstávají oddělené, fyzické sestavení není potvrzené. Review nemění produkci ani native desktop. Finální source/artifact/publication scope musí být konkrétně doložen před integrací.


## Finální samostatný audit skutečných artefaktů a metadat

Audit neotevírá GUI. [Samostatný script](evidence/pc008-line-subdivision-review-artifacts.py) vytvořil fresh CODE archive a ověřil skutečné importy/hash; [raw výsledek](evidence/pc008-line-subdivision-review-artifacts-24e0801.json). METADATA93f650c zachovává published6796c63 jako ancestor a nemá žádný src/tools/tests/pyproject rozdíl oproti schválenému CODE24e. Normativní mandát/AC zůstávají beze změny. [Metadatový audit](evidence/pc008-line-subdivision-review-metadata-93f650c.json) ověřil také všech43 relativních odkazů v dotčených skills/delivery.

Nativní výsledek skutečného app.main od prázdného projektu má119 source hashů shodných s připnutým archivem a22 ověřených artifact hashů; skutečný import author_window je v určeném source WT. Tři skutečné nativní dialogy Save/Open/Export byly přijaty. Snapshot po skutečném Save/New/Open je přesně shodný s novým načtením přes příslušnou produkční doménu, po standardní JSON normalizaci tuple/list. Uložená dictionary se nemění.

Vlastní audit znovu a nezávisle přehrál obě uložené lineage historie z Fraction source intervals, bez použití history resolveru pro expected: spodní whole root split→merge→split a horní hinge split1/4. Souřadnice actual children odpovídají zdroji. Uložený wall/roof/base znamená3 source surfaces,2 skutečné material parts a2 stránky, bez vynechaného či reference-only prvku. Root axis, hinge a interior attachment používají historické root IDs; connector ponechává full[0,1],width2,taper.6,count1,trapezoid a vlastní tab ID. Part frame a placement mají správnou stránku2,[60,60],30° i oba locks. Všechny čtyři původní wall body mají samostatně odvozené stejné page coordinates před/po operacích. Nově vložené body je pouze doplňují.

Očekávané plochy jsou odvozeny nezávisle z původních zadávaných rozměrů: wall4000, roof100√2125, tab160, base13000mm². Odmocnina používá vlastní integer-isqrt racionální interval s70 desetinnými místy, nikoli unfolded cache. Skutečné SVG je samostatně tokenizováno do Fraction LINE polygonu. Skutečné PDF načítá již nezávisle schválený precise raw-token/CTM decoder; vlastní exact shoelace počítá plochu až z jeho skutečných serializovaných kontur v papírových jednotkách. Decoder nebyl zaměněn za source nebo cache certifikát.

| Materiál | Nezávislé očekávání | Skutečné SVG | Skutečné PDF / maximální chyba |
|---|---|---|---|
| wall+roof+tab | 8769.772228646443…mm² | 8769.772229mm² | 8769.772000000002…mm²; ≤0.000228647mm² |
| základna | 13000mm² | 13000mm² | chyba ≤2.728×10^-12mm² |

SVG chyba smíšeného dílu je ≤3.536×10^-7mm². Vše je pod původní .01mm² mezí; tab není důvodem zvětšit relativní body-only budget. Actual CUT pokrytí je přesně shodné s material part registry a správnými stránkami, closed paths jsou skutečně uzavřené v obou formátech. Není to tvrzení fyzické slepitelnosti; snapshot přiznává bounded bend UNVERIFIED, unknown material a přijetí pouze digitálního varování.

Obě editorové kopie mají zdroj24e, shodný připnutý editor driver a po4 skutečných ověřených hashích. Originální bundle (.author-export.json, obě SVG i PDF) zůstal byte-identical. Nezávislá XML/token kontrola potvrzuje všechny původní path IDs, příkazy a local coordinates (max drift0 na stránce1 a2.9×10^-7mm na stránce2), role, oba page units/viewBox a100mm calibration. Přímý group transform změnil celek o10/15px, lineární část zůstala; změněný label má přesně „Žluťoučký – vlastní díl“ a požadovanou barvu. Ostatní texty zůstaly stejné. Reviewer viděl skutečné app i oba editor screenshots; agentní průchod není nový uživatel.

Finální JUnit obsahuje **1465 skutečných testcase,0 failure/error/skip**, XML čas326.213s a odpovídající úplný UTF16 console log1465 passed/326.23s. Sada nebyla znovu pouštěna jen kvůli tomuto auditu. Native24e32.734s a Inkscape15.672s/18.015s jsou skutečné běhy autora, nezávisle kontrolované přes jejich zdroje a artefakty.

Původní 9b/929 native FAIL zůstávají skutečným produkčním missing-consumer důkazem; 929 raw traceback potvrzuje StopIteration v retired-boundary lookup, žádná dodaná hotová geometrie jej nenahradila. A770 FAIL je naopak přesně zachované chybné oracle90/144 při skutečně zadaném100/160. Původní aborted fullsuite není1465 PASS a jeho důvod/schema-fixture oprava není oslabením loaderu. Vlastní audit měl dva krátké harness chyby: porovnal Python tuple snapshot s JSON listem a poté zaměnil Page list za ID dictionary. Jsou doloženy v [harness poznámce](evidence/pc008-line-subdivision-review-artifact-harness-attempt01.json); opravy mění pouze čtení/normalizaci očekávané reprezentace, nikoli produkt nebo numerické prahy.

## Nové poučení, aktuální schválení a meze

SK015 construction consumer-coverage rada odpovídá doložené příčině LINE-BEND01 a skutečné opravě/full-hinge bend/cache i actual selected-relation průchodu. Text neprohlašuje všechny jiné consumers automaticky za opravené. Aktuální product repair a text jsou **APPROVED_IN_SCOPE**; účinnost na příštím jiném consumeru zůstává **PENDING_NEXT_USE / NOT_RUN**.

SK011 LINE transfer pravdivě zachovává **INITIAL_TRANSFER_FAILED_LS04**. Nový verification odstavec správně považuje i topologický command za producer a požaduje původní canonical source→actual body area, load/scale a jednu souhrnnou body-only normu pro otvory/plochy. Přímá oprava a její aktuální oracles/artefakty jsou schválené; to nesmí zpětně změnit první transfer na úspěšný ani prohlásit širší další efficacy za ověřenou.

Metadata93f650c správně ponechává pending scope: live ARC/CUBIC adapters, loft trim/φ, širší AU13/AU14, C/schema6 adapter, PC009/010, novice0/NOT_RUN a P3/NOT_RUN; celé PC008/P2 zůstává IN_PROGRESS. Experimentální schema7 zná copy/SaveAs1–5 a nepropouští dosud neznámý C6 pouhou změnou verze. Toto schválení není dokončení budoucího integračního adaptéru ani produktové přijetí.

Jediná zbývající předpublikační práce je mechanické closure metadata: v delivery rozlišit analytické očekávání a skutečně serializovanou plochu, zastaralý queue review text LINE694 změnit na24e a připojit toto finální schválení v queue/SK015/SK011 při zachování pending širších přejímek. Tento následný konkrétní commit má dostat úzký doc/source-identity recheck; není potřeba nová1465sada ani nový produktový souhlas.
