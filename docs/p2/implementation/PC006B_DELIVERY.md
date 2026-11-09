# PC-006B — vlastní otevřená stavba a autorské spoje

9.11.2026. Digitální implementace A a společného dílu je ověřena na zdroji **`eb08f97f3ced9c547bd818f97e47d29f9b73a548`**. [Nezávislé materiálové review](PC006B_MATERIAL_REVIEW.md), [review autorských příkazů](PC006B_COMMANDS_REVIEW.md) a [původní doménové nálezy](PC006B_DOMAIN_REVIEW.md) rozlišují konkrétní zdroje, opravy a meze. Závěrečný technický verdikt určuje poslední dodatek nezávislého review, nikoli autor tohoto předání.

**Skutečný test s novým člověkem AC-US08 je NOT_RUN, účastníků 0.** Vlastník potvrdil nedostupnost účastníka. První autorskou verzi proto neoznačujeme za plně uživatelsky ověřenou ani produktově přijatou. Fyzický výtisk/sestavení patří do P3. Úplné A/B/C/D a závěrečný historický model zůstávají součástí navazujícího P2.

## Výsledek v aplikaci

Prázdný projekt umožňuje vytvořit vlastní stěny, střechu s přesahem, základnu, výztuhu se skutečným otvorem, podhled a samostatný dvoustranný pásek. Spoj lze určit hrana–hrana, hrana–vnitřní čára nebo lepicí oblastí. Přesah se neořezává na stěnu; otevřená stavba nemusí mít dno.

Panel spojů ukazuje konkrétní protikus a lepicí stranu. Autor nastaví šířku, zkosení/trojúhelník, vlastní kreslený obrys, počet a mezery, upraví nebo vypne jednotlivou stabilně identifikovanou chlopeň. Prostorový náhled ukazuje cílové kontakty. Přejmenování modelu/plochy/dílu je v Úpravy, F2 a vlastnostech; odstranění ukáže konkrétní dopad na díl/spoje a zachová znovupoužitelné skici. Celou změnu lze vrátit. Kontextové akce odpovídají výběru; odstranění nepřebírá Delete z rozepsaného textu.

Spuštění v připraveném prostředí kořenového checkoutu: `.venv\Scripts\python.exe -m archpapercraft`. Ve vedlejším worktree je nutné nastavit jeho vlastní `src` jako `PYTHONPATH`; sdílená editable instalace jinak může načíst kořenový checkout. Nativní ověřovací nástroj tuto vazbu kontroluje sám.

## Konkrétní digitální důkazy

[Windows průchod run06](evidence/pc006b-desktop-eb08f97-run06/results.json) prošel za 170,969 s skutečným `app.main`, Qt vstupy, OpenGL 4.6 NVIDIA a šesti nativními Save/Open/Export dialogy. Nevkládá připravenou geometrii do controlleru ani JSON. Projekt vznikl v UI; doménové API slouží při auditu pouze ke čtení.

- [Model A](evidence/pc006b-desktop-eb08f97-run06/model-A/model-A.apcraft), [snapshot](evidence/pc006b-desktop-eb08f97-run06/model-A/snapshot.json), [SVG/PDF](evidence/pc006b-desktop-eb08f97-run06/model-A/export), [otevřený editor](evidence/pc006b-desktop-eb08f97-run06/model-A-reopened-desktop.png).
- [Společný díl](evidence/pc006b-desktop-eb08f97-run06/mixed-part/mixed-part.apcraft), [snapshot](evidence/pc006b-desktop-eb08f97-run06/mixed-part/snapshot.json), [SVG/PDF](evidence/pc006b-desktop-eb08f97-run06/mixed-part/export).
- [Celá testovací sada](evidence/pc006b-eb08f97-all-tests.xml): **630 PASS, 0 FAIL, 0 SKIP**, 60,92 s. Další dílčí a nezávislé kontroly se k tomuto číslu nepřičítají jako unikátní testy.
- [Skutečný Inkscape průchod](evidence/pc006b-inkscape-eb08f97-run01/editor-results.json): PASS na čerstvém A výstupu s otvorem; posun skupiny, barva a skutečné postupné psaní Unicode popisku zachovaly ostatní geometrii/texty, oba CUT obrysy, sedm rolí, jednotky i 100mm kalibraci. Originální bundle zůstal shodný.

| Nezávisle zadané očekávání | Výsledek skutečného průchodu |
| --- | --- |
| Dlouhá stěna 100×40 paper mm, štít 60×40 + 60×30/2 | 4000 a 3300 mm² zdrojového materiálu |
| Základna 130×100, výztuha s otvorem 2700−300 | 13000 a 2400 mm²; otvor také ve SVG/PDF |
| Přesah jednoho okapu 500→800 model mm při 1:100 | Původní vnitřní připojovací čára stěny zachována, ostatní okapy/hřeben beze změny |
| Čtyři horní chlopně, mezera 1 paper mm; jedna vypnutá, jedna vlastní | Aktivní plochy 56, 60, 60 mm²; s dolní 144 a stěnou 4000 je CUT 4320 mm² v SVG i PDF |
| Společný stěna–střecha díl, změna výšky i zdrojového profilu | Všechny čtyři původní souřadnice stěny invariantní, stránka 2, kotva [60,60], 30° a oba zámky zachované |
| Uložení → nový projekt → otevření → zoom/pan → přepočet aktuálního modelu | Všechny umístěné díly viditelné bez Home; kamera zachovaná, dokument zůstane uložený |

## Kontrola ohybu a její meze

Registr zahrnuje skutečné materiálové plochy i ostatní aktivní chlopně v sestavené poloze, včetně sourozenců. Posuzuje **jednu pohybovanou přímou chlopeň při ostatních již složených**, nikoli plán celé montáže. Konkávní obrys není nahrazen konvexním obalem. Předané překážky, nejisté vrstvy a případně nevyhodnocené překážky jsou explicitně vyjmenované; aktuální pohybovaná a skutečně vypnuté chlopně do překážek nepatří.

Známý materiál má deklarovanou tloušťku, vůli, rezervu a konečný lokální pás ohybu/kontaktu. Doložená kolize nebo nerozhodnutý výpočet blokuje export. Protilehlé/neznámé vrstvy bez fyzických offsetů nemají jistý kladný výsledek. Bez tloušťky probíhá pouze omezené hledání geometrických svědků: nenalezení střetu není důkaz jeho nepřítomnosti. Vzorový model A má tloušťku neznámou a výslovně přijatá digitální varování; nevydává se za materiálový certifikát. Ani kladný numerický výsledek nenahrazuje fyzickou P3.

Materiálový report je navázaný na úplný assembly digest a stejný snapshot v SVG, PDF metadatech a manifestu. B02 je pokryt digitální kontrolou v tomto deklarovaném rozsahu; zakřivené chlopně C potřebují vlastní důkaz v PC-007B.

Schema 3 je stále experimentální. Rozpoznané starší authoring schema 1/2 se čtou jako kopie se zachovanými identitami a ruční prací; starý zdroj nelze přepsat ani po undo/redo či neúspěšném příkazu. Ostatní legacy projekty zůstávají read-only podle přijaté kompatibility. Žádná nevratná migrace neproběhla.

## Revize, opravy a osvojitelnost

Původní B01/B03/B04/B05 mají samostatně doložené opravy; komponentový sweep kernel má vlastní schválení. Nová nezávislá R01 reprodukce odhalila, že neurčená vrstva oslabila již blokující numerický stav: oprava `022e9fa` zachovává závažnější stav, původní příčinu i úplný inventář. Diagnostika `9097e61` pojmenuje také překážející chlopeň a její konkrétní díl pro výběr v UI.

[run04](evidence/pc006b-desktop-95482c5-run04/results.json) zůstává FAIL ověřovacího nástroje: import z jiného editable checkoutu. Driver nyní kontroluje skutečný modul i čisté připnuté zdroje. [run05](evidence/pc006b-desktop-d2a3b73-run05/results.json) odhalil skutečnou produktovou vadu: po layoutu zbytečný přepočet změnil jen devět `source_revision`. Oprava `eb08f97` zachovává revizi již aktuálního zdroje; skutečná geometrická/materiálová změna ji nadále aktualizuje. Oba FAIL běhy a dřívější chyby zůstaly uložené.

AC-US01–07 mají technické průchody začátku/výběru, konkrétních akcí, 3D↔2D, odmítnutí nepoužitelné lepicí plochy, zrušení, undo/redo, názvů a bezpečného odstranění. To je důkaz chování UI, nikoli pozorování začátečníka. [Protokol nového uživatele](../v1.2/USABILITY_TEST.md) je připraven, AC-US08 zůstává otevřený. Skills byly skutečně použity pro konstrukci, C05 preflight, nezávislá matematická očekávání a připnutí důkazů; úzká SK-007/008 jsou v ledgeru s oddělenou revizí a pending účinností.

Další práce: PC-007A nativní oblouky/Bézier a ostění B, potom PC-007B pláště C, PC-008 použitelná alternativa D, PC-009/010 konsolidace a závěrečný vlastní historický model AC-AU19. [Aktualizovaný odhad a rizika](../v1.2/ESTIMATE_AND_RISKS.md) nezaměňují člověkodny s dobou běhu agentů. Žádný z těchto rozsahů se tímto předáním neodkládá za P2.
