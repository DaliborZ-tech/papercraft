# Nezávislá revize P0/P1

**Verdikt: APPROVED_IN_SCOPE.** P0/P1 dodává ověřené podklady a rozhodnutelný P2 kontrakt. Nejde o schválení hotového produktu, PO akceptaci, fyzickou sestavitelnost nebo release.

Datum: 5. listopadu 2026. Reviewer: samostatný agent `independent_review`, odlišný od integračního autora i `geometry_analysis`. Reviewer neprovedl produkční implementaci ani opravy revidovaných dokumentů; vlastní pouze tento report a `evidence/reviewer-*`.

- BASE: `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`.
- První revidovaný CODE: `98cf6abeb238aaaa66b791780a31d75f7dcae3f1`.
- Opravy a závěrečný schválený CODE: **`5b01bb26e6b4c3da8d75afdca19cad5d6b43d576`**.
- Diff: `git diff BASE..CODE`; cílené re-review oprav `git diff --ignore-space-at-eol 98cf6ab..5b01bb2`. Produkční `src/`, původní `tests/` a `pyproject.toml` jsou beze změny proti BASE.

## Rozsah a ověřené důkazy

Přečten normativní mandát, epiky a AC; následně baseline, findings, geometrický spike, ADR, UX a jeho screenshoty/HTML, P2 kontrakt, traceability, queue a diagnostické skripty. Ověřeno bezpečné umístění checkoutu a příslušný preflight záznam; osm nezměněných původních souborů briefu je i nyní byte-for-byte shodných s předbootstrapovými SHA256. Devátý soubor je vědomě aktualizovaná jediná queue, tento rozdíl je výslovně dokumentován. Bootstrap hashe všech devíti souborů před/bezprostředně po bootstrapu jsou v původním záznamu. Byte shoda PDF blobů s pracovním stromem byla samostatně ověřena, `.gitattributes` chrání nové důkazy před CRLF konverzí.

Vlastní read-only strukturální kontrola potvrdila 12 unikátních ticketů, acyklické závislosti, všech 16 epic a 61 explicitních AC, přetrvávající blokaci P2 před přijetím vlastníkem a syntaxi šesti stavů prototypu. Srovnání variant a odhady jsou přiměřeně označené jako plánovací intervaly s nejistotou; nejsou prezentované jako naměřená produktivita. Read-only legacy režim a nepřítomnost plné migrace báně/gotiky v P2 jsou konkrétním, viditelným tradeoffem pro vlastníka.

Původní JUnit/logy skutečně obsahují 213 PASS / 0 FAIL / 0 SKIP; oddělený Qt-prohibited core subset 44 PASS je správně označený jako podmnožina. Reviewer full suite neopakoval: produkční kód se nezměnil a nové vlastní cílené kontroly byly informativnější. Windows proof má skutečný `app.main`, platný NVIDIA OpenGL kontext, QTest interakce a automatizaci nativních Windows souborových dialogů vlastního procesu, bez mockování cest. Fresh output directory a vytvořené soubory podporují tvrzení o save/open/export průchodu. Nejde o důkaz ergonomie nebo všech budoucích P2 interakcí.

Zvlášť ověřeno, že červené diagnostiky nejsou schované pomocí XFAIL/SKIP ani záměny runtime výjimek za očekávanou vadu. Reviewer jejich explicitní běh zopakoval: **0 PASS / 6 FAIL / 0 ERROR / 0 SKIP**, exit 1, pytest 0.38 s. Všech šest selhání jsou konkrétní assertions proti uvedeným vadám. Exit 0 jiného diagnostického sběrače není vydáván za zelený produkt.

## Vlastní numerické a negativní kontroly

Zdroj a reprodukce: [reviewer-checks.py](evidence/reviewer-checks.py), [reviewer-results.json](evidence/reviewer-results.json). Jde o nové analyticky určené fixtures; očekávání nejsou převzatá z integrátorova průnikového helperu ani ze zkoumaného unfolderu.

| Vlastní kontrola | Očekávání / výsledek | Závěr |
|---|---|---|
| Rigidně transformovaný pravoúhlý trojúhelník | Délky 3, 4, 5 a Heronova plocha 6 přesně zachovány; přímé API přesto vrací 0 boundary cuts | Pozitivní numerika potvrzena, mez hranic potvrzena zvlášť |
| Uzavřený pravidelný tetrahedron hrany 4 | 4/4 faces, 0 cuts, neohlášená mezera kopií sdílené hrany 8 mm | Ne-tree closure vada potvrzena na jiném tělese než integrátorova krabice |
| Kuželový pás r1=3, r2=8, s=13, h=12 | Plocha přesně 143π = 449.247749 mm², spojovací strana 20.389706 místo 13 mm | Plošné orákulum samo vadu neodhalí, délkový nález potvrzen |
| Téměř válcový přímý profil r1=10, r2=10+1e-10, h=30 | Konečné souřadnice a spojovací strana 30 mm | Tento hraniční fixture PASS; nejde o obecné schválení E11/profil extractor |
| Jiný vnější hřeben, změna vertex ID | +73.739795° → −73.739795° při nezměněné geometrii | Chybná polarita podle indexů potvrzena |
| Chlopeň do obdélníkového materiálu | Celý polygon uvnitř materiálu, analytická plocha překryvu 48 mm² | Winding/exteriér vada potvrzena bez integrátorova clipping algoritmu |
| Non-manifold hrana se třemi pravoúhlými faces | Dva výsledné trojúhelníky přesně splývají, průnik 24 mm² | Chybějící odmítnutí a overlap potvrzeny |
| Průnik dvou disjunktních boxů | Má být prázdný nebo unsupported; vráceno 12 faces | Jednoznačně potvrzena i intersection větev placeholder CSG |
| Nezávislé čtení uloženého PDF/XML | PDF šířka 297.000013 mm, SVG 210 mm pro landscape | Exportní rozpor potvrzen z konkrétních souborů |

Vlastní příkazy:

```powershell
.venv\Scripts\python.exe docs\revival\evidence\reviewer-checks.py
.venv\Scripts\python.exe tools\revival\validate_delivery.py
.venv\Scripts\python.exe -m pytest tools\revival\test_diagnostic_contracts.py -ra --junitxml=docs/revival/evidence/reviewer-diagnostic-contracts.xml
```

První příkaz skončil exit 0, přesný čas/interpreter/CODE pin ukládá JSON; strukturální validátor exit 0. Třetí příkaz skončil očekávaným exit 1 se šesti konkrétními produktovými vadami. [Validační výstup](evidence/reviewer-validation.log), [diagnostický log](evidence/reviewer-diagnostic-contracts.log), [JUnit](evidence/reviewer-diagnostic-contracts.xml). PowerShell v přesměrovaném logu zobrazuje warning stderr jako `NativeCommandError`; rozhodující je skutečný exit procesu a assertion/JUnit výsledek, nikoli tato prezentační obálka.

## Nálezy této revize a jejich uzavření

| ID | Závažnost | Nález na prvním CODE | Podmínka uzavření | Re-review na 5b01bb2 |
|---|---|---|---|---|
| RV-01 | minor | Empty UX ukazoval celý strom domu, vybranou střechu, dvě stránky a kontextové akce, v rozporu s požadavkem „žádné díly“ | Podmíněně zobrazit skutečně prázdný strom a skrýt/neaktivovat kontextové akce; obnovit screenshot | CLOSED: zdrojový delta a nový screenshot vizuálně ověřeny, strom má žádné objekty/díly a 0 stránek |
| RV-02 | minor | GEOMETRY_SPIKE nepřesně přiřazoval falešný vícebodový profil samotné rotaci X90; JSON pro ni obsahuje None | Rozlišit samotnou rotaci a rotaci kombinovanou s posunem podle existujících dat | CLOSED: text odpovídá JSON; nedošlo ke změně měření |

Opravný commit dále přidává guard proti vrácení už zrevidované fronty jednorázovým preparation helperem a vrací raw evidence do byte-preserving Git režimu. Obsah numerických záznamů se tím nemění. Tento delta byl samostatně zkontrolován. Žádný blocker/major nález v P0/P1 deliverable nezůstává otevřený.

## Co schválení nezahrnuje

Produktové PC-F01–F20 zůstávají otevřené do odpovídající implementace P2/E11; tato revize schvaluje jejich pravdivou diagnostiku a kontrakt nápravy, nikoli jejich funkčnost. Digitální P2 AC jsou stále NOT_RUN. Kontrakt správně obsahuje obousměrný výběr, manuální švy/chlopně, ruční stránky a oba vektorové exporty, bezpečnou persistence, stale/identity pravidla, společný snapshot i konkrétní legacy mez. Veškeré epiky zůstaly v roadmapě.

Skutečný externí editor, nové P2 interakce na Windows, další GPU/DPI varianty, OCC větev, rotační/děravé obecné topologie a fyzický výtisk/stavba nejsou tímto schválené. Jejich požadované ověření a vlastník/etapa jsou jasně určené. Technické schválení P0/P1 umožňuje předložit konkrétní P2 kontrakt vlastníkovi. **PO verdict = PENDING; GATE-P2 není přijata; release = NOT_READY.**

Následné čistě administrativní uložení tohoto reportu a uvedení PC-000–005 do odpovídajícího technicky ověřeného/PO_PENDING stavu nemění schválený implementační kontrakt. Jakákoli změna jeho významu, rozsahu či matematických závěrů vyžaduje cílenou revizi nového pinu.
