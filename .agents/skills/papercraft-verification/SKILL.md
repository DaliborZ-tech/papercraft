---
name: papercraft-verification
description: Ověřuj geometrii, změny, skutečné UI a výrobní výstupy Papercraftu pomocí nezávislých očekávání a správného druhu důkazu.
---

# Ověřování geometrie a výroby

Načti příslušné [numerické a výrobní kontrakty](../../../04_ACCEPTANCE_AND_VERIFICATION.md), [AC v1.2](../../../docs/p2/v1.2/ACCEPTANCE.md) a relevantní [spiky](../../../docs/p2/v1.2/GEOMETRY_SPIKES.md). Tolerance a přejímky určuje specifikace, ne tento skill.

Expected výsledek odvoď analyticky, z ručně určené topologie nebo nezávislého čtení výstupu. Zahrň negativní i hraniční případ. Shodné očekávání vypočtené stejným helperem není nezávislé orákulum.

Příklad: konečné nulové vzorky neprokazují regularitu celého loftu. [DR-01](../../../docs/p2/v1.2/INDEPENDENT_REVIEW.md) našel kolaps mezi vzorky; kontroluj oblast platnosti pozitivního důkazu a odděluj vzorkované maximum od prokázané meze. Podobně přesný válcový plášť necertifikuje ohyb jeho chlopní.

Připni zdroj ověřovaného výsledku a uveď důkaz: numerika, UI automatizace, skutečný editor, nový uživatel nebo fyzická stavba. Jeden druh nenahrazuje druhý. Chybějící důkaz zůstává NOT_RUN/BLOCKED s důvodem. Selhání neskrývej odstraněním testu či změkčením AC.

Reviewer ověří také, zda důkaz pokrývá právě vydávaný commit a skutečně požadovaný výsledek. Zjištění přenes do produktu a cíleného postupu přes [smyčku poučení](../../../AGENTS.md#projektové-skills-a-poučení).

Ve více worktrees ověř i cestu skutečně importovaného aplikačního modulu. Sdílené prostředí s editable instalací může spustit jiný checkout, přestože Git SHA a hashe souborů odpovídají zamýšlenému adresáři. Příklad: nativní B průchod [run04](../../../docs/p2/implementation/evidence/pc006b-desktop-95482c5-run04/results.json) nedostal novou akci; nástroj nyní váže import k vlastnímu `src` a před spuštěním kontroluje i zaznamená `__file__`. Takové selhání harnessu není produktová regrese ani PASS cílového zdroje.

Při práci s nejistou geometrií porovnej známou negativní reprodukci také po přidání nezávislé nejistoty. V [K01](../../../docs/p2/implementation/PC006B_DOMAIN_REVIEW.md) vzdálená překážka s neznámou tloušťkou původně vymazala již prokázanou kolizi. Neurčená tloušťka či vrstva má zůstat explicitně nejistá, nesmí oslabit jistý negativní důkaz jiné dvojice. Použij oba vstupy a zachovej i meze hledání; nenahrazuj je obecnějším tvrzením o fyzické sestavitelnosti.

Při nahrazení křivky tětivami ověř zvlášť metriku, topologii a skutečný materiál v každé dotčené kontrole. [P01/P02](../../../docs/p2/implementation/PC007A_PLANAR_REVIEW.md) prošly poziční tolerancí, přesto skryly průnik a překryv. Příklad: vlastní svědek mezi uzly musí ověřit také příjemce a celý ohyb; obal nejistoty nesmí dostat výsledek „volno“ jen proto, že proxy nekoliduje. Přenos opravy layoutu na kontakt či ohyb dolož samostatně.

Při přesném čtení výrobního výstupu zachovej původní číselné tokeny před převodem do float. [V01](../../../docs/p2/implementation/PC007A_VECTOR_OUTPUT_REVIEW.md) ukázal, že kontrola dvou již zaokrouhlených hodnot nerozpozná ztracené číslice. Příklad: ručně zapsané `1.00000000000000001` v souřadnici, transformaci i jednotkách stránky musí zůstat přesné, nebo být bezpečně odmítnuté. Neodvozuj přesnost skutečného souboru jen z očekávané přesnosti writeru.

Odvozený chybový odhad nenahrazuje další normativní přejímku. [V02](../../../docs/p2/implementation/PC007A_AREA_INTEGRATION_REVIEW.md) prošel polohovou mezí, ale nikoli plochou; volnější mez plochy odvozená z obvodového pásu nesměla změnit původní AC. Příklad dalšího použití: délková chyba extruze se násobí hloubkou. Ověř výslednou čistou plochu včetně otvorů samostatně a celý řetězec source→výstup proti původní mezi, nikoli jen každou mezikontrolu se stejnou volnou rezervou.

Za materiálový producer považuj i příkaz, který má pouze dělit topologii. LS04 v [LINE přírůstku](../../../docs/p2/implementation/PC008_LINE_SUBDIVISION_DELIVERY.md) splnil polohovou a délkovou mez, ale float projekce změnila původní2mm² na9/4mm² ještě před rozvinem. Porovnej kanonický zdroj s opravdu uloženými body při příkazu, načtení i změně měřítka; shodný export nového chybně změněného polygonu nestačí. Otvory a plochy společného dílu mají jeden původní body-only budget, nikoli vlastní toleranci pro každý otvor.

Relativní plošnou toleranci normalizuj původním tělem bez chlopní, i když ověřuješ celý výsledný materiálový union. [SO01](../../../docs/p2/implementation/PC008_SEGMENTED_OUTPUT_REVIEW.md) našel ve writeru normalizaci tělem i chlopněmi; izolovaný numerický comparator se skutečnými SVG/PDF tokeny rozlišil body20000mm², tab2000mm² a chybu0,021mm²: správná mez je0,020, nikoli0,022. Způsobilost takového numerického fixture nezaměňuj za doménový/bend/native důkaz; původní velké modely se bezpečně zastavily na jiné kontrole. Další použití rady musí znovu ověřit oba odlišné základy plochy.

Editovatelnost ověř také skutečným psaním a uložením v cílovém editoru. [C-06](../../../docs/p2/implementation/evidence/pc006a-C06-svg-text-whitespace.md) prošel původním XML/render auditem, ale při postupném psaní víceslovného popisku v Inkscape mizely mezery. Příklad: uprav jeden label na víceslovný Unicode text, ulož a nezávisle přečti přesný obsah i nezměněné ostatní objekty. Odliš bezpečné odmítnutí vstupu testovacím nástrojem od produktové vady; uchovej oba výsledky. Úspěch jednoho editoru necertifikuje jiné editory, jiné konstrukční řezy ani nového uživatele.

Při změně certifikované reprezentace verzuj také kontrakt odvozené cache. [PF-01](../../../docs/p2/implementation/PC007A_LOFT_PERFORMANCE_REVIEW.md) zachoval správnou geometrii, ale starý 803bodový řez se tvářil jako aktuální a končil chybou cache. Ověř načtení starého výsledku jako neaktuálního, zachování zdroje/kotvy/layoutu a explicitní přepočet; zvlášť ověř, že poškozený výsledek se současným kontraktem zůstává blokovaný. Příklad přenosu: nová verze odvozené segmentace nesmí mlčky přijmout starý certifikát ani zahodit rozmístění autora.
