# PC-007A — nezávislá numerická revize nativních hranic loftu

9.11.2026. Reviewer `/root/authoring_independent_review` není autorem nové komponenty `loft_curves.py`, jejích testů, návrhu rootu ani původního loft solveru. Starší vlastní revize exportního zaokrouhlování není autorstvím této komponenty. Produkce a autorovy testy nebyly reviewerem měněny.

**Přesný source `0fe6595bfc27c8fed14fbf72c7d4399b51c41fdf`: APPROVED_IN_NUMERIC_COMPONENT_SCOPE, 0 BLOCKER / 0 MAJOR.** Schválení platí pro podmíněnou reprezentaci již doloženého solver reportu, její skutečné binární L/C kontroly, hlášené celointervalové poziční a globální délkové meze. **Nejde o schválení celé PC-007A/P2, topologie, sestavené geometrie, persistence, UI, SVG/PDF serializace ani fyzické sestavitelnosti.**

## Připnutý zdroj a provedené kontroly

Pracovní strom na `revival/p2-loft-curves` byl před vlastními reporty čistý a HEAD odpovídal source výše. Reviewer vytvořil izolovaný `git archive` přesného commitu a nastavil import pouze z jeho `src`. [Importované moduly, cesty a SHA-256](evidence/pc007a-loft-curves-review-imports.json) zahrnují skutečné `loft_curves`, `loft_geometry` a `curves`; všechny odpovídají Git textu s výhradně LF/CRLF checkout konverzí. Runtime SHA-256 nového `loft_curves.py` je `321c74efe4567f8ead29fbb956d4cfdee89769129a0f8170b8f21957a8c37eba`. [Záznam archivu](evidence/pc007a-loft-curves-review-source.json).

- Autorovy připnuté fitter/solver testy: **51 PASS / 4.91s**, [JUnit](evidence/pc007a-loft-curves-review-0fe-tests.xml). Ruff obou nových source/test souborů PASS.
- [Vlastní nezávislé oracles](evidence/pc007a-loft-curves-review-own.py): **21 PASS / 9.48s**, [finální JUnit](evidence/pc007a-loft-curves-review-own-0fe-complete.xml). Očekávání nevycházejí z produktového `_norm_upper`, `_distance_bounds` nebo `_derivatives`.
- První vlastní běh měl [13 PASS / 5 FAIL](evidence/pc007a-loft-curves-review-own-0fe.xml): reviewer mylně požadoval, aby globální bound dominoval součtu již outward zaokrouhlených veřejných lokálních boundů. Produkt správně sčítá přesné racionální příspěvky a globál zaokrouhlí jednou; součet lokálních veřejných zaokrouhlení může být nepatrně vyšší. Oracle byl opraven na nezávislé racionální normové intervaly a jejich součet, bez změny produkce nebo očekávaných skutečných délek. [Opravený meziběh 18 PASS](evidence/pc007a-loft-curves-review-own-0fe-rational.xml) je zachovaný vedle finální rozšířené sady.

## Poloha pro celý stejný parametr

Pro každý skutečně vrácený cubic segment reviewer sestrojil přesné racionální kontrolní body `B₀…B₃` z binárních floatů a nezávisle stupeň3 lineárního interpolantu se stejnými konci `D₀…D₃`. Rozdíl je Bernsteinův polynom `Σ bᵢ(t)(Bᵢ−Dᵢ)` s nezápornými koeficienty, jejichž součet je1. Proto `|C(t)−L(t)| ≤ max |Bᵢ−Dᵢ|` **pro každý t celého intervalu**, nikoli jen v uzlech nebo na testovací mřížce.

Vlastní test porovnává přesné racionální čtverce těchto norem s lokálním i globálním deklarovaným η. Také ověřuje, že `reported_position − source_δ − reserve` skutečně pokrývá každou z těchto norem. Při platném původním SAME-u důkazu `|F−L|≤δ` tedy trojúhelníková nerovnost dává hlášenou mez pro skutečné vrácené C. Zdrojový δ nesmí být zaměněn za Hausdorff/tětivovou vzdálenost; dřívější L01 v [samostatné loft revizi](PC007A_LOFT_REVIEW.md) je relevantní předpoklad, nikoli něco, co tento fitter znovu dokazoval z vrcholů.

Další nezávislá analytická rodina je `F(u)=(a·u,b·u²)`, s dyadickými kontrolovatelnými vstupy. Reviewer odvodil přesné quadratic Bernstein kontroly každého nerovnoměrného intervalu a nezávisle je zvýšil na cubic stupeň. Odchylka **skutečných binárních nativních kontrol** od těchto přesných kontrol kryje F−C na celém intervalu přímo, bez spoléhání na sampled shodu. Zkoušeny i téměř přímé křivky s `b=2⁻⁴⁰`, velkým posunem a intervalem délky2⁻²⁰; žádný arbitrary epsilon nepřevádí skutečně zakřivenou hranici na falešné přesné L.

Skutečná source kubika `(0,0),(1,0),(3,0),(6,0)` při normálové extruzi má přesnou arclength mapu `3u+3u²`; reversed má `9u−3u²`. Nativní výstup správně zůstává více L segmenty, nikoli falešnými zakřivenými C. Reviewer vyhodnotil maxima rozdílu lineárního interpolantu a této analytické kvadratické mapy přesně na krajích a případném vnitřním kritickém bodě každého intervalu. Tím je nezávisle ověřeno zachování stejného parametru na celém intervalu také tam, kde je geometrický locus přímka a rychlost není konstantní.

Sdílená kvadratická derivace pro nerovnoměrné kroky je správně vážená sousedními délkami intervalů. Výsledné binární controls však obecně nemají přesně shodné derivace. Vlastní racionální výpočet skutečných endpoint derivací ověřuje hlášený bound jejich skoku a `exact_c1_of_binary_controls`; report jej pravdivě odlišuje od ideálního C1 návrhu. Zaokrouhlení každého kontrolního bodu není vydáváno za přesné C1 ani za důkaz budoucího decimal writeru.

## Délky celých obou hranic

Každý cubic má délku alespoň své tětivy a nejvýše skutečného control polygonu. Reviewer přepočítal každou eukleidovskou vzdálenost samostatnou **racionální odmocninovou obálkou přes integer `isqrt` s200 binárními zlomkovými bity**; nepoužil produktové Decimal/sqrt helpery. Každý vrácený lokální excess bound pokrývá `control-polygon upper − chord lower`. Samostatně jsou sečtené příspěvky všech segmentů všech patchů v první a druhé source hranici; globální bound pokrývá source chain bound + horší z těchto součtů + reserve. Samostatné pole pro součet obou hranic pokrývá oba celé řetězce.

To odpovídá `|len(F)−len(C)| ≤ |len(F)−len(L)| + |len(C)−len(L)|`. Druhý člen je omezen součtem control-polygon excessů, první musí být dodán platným source solverem pro **celý řetězec**, nikoli lokálním maximem.

Vlastní12patchový asymetrický případ střídá skutečně zakřivenou první/druhou hranici. Global excess je větší než3× největší místní příspěvek. Budget mezi lokálním a globálním příspěvkem je správně odmítnut; fitter neclampuje controls ani nemění source report. Kruhové kuželové a koplanární pásy různých poloměrů, opačného poměru a reversed směru byly navíc porovnány s analytickými délkami `πr`; skutečné cubic délky odečetla nezávislá numerická kvadratura derivace. Kvadratura je další testovací oracle, nikoli pozitivní důkaz celointervalové polohy.

Vlastní gotický profil ze dvou60° oblouků poloměru2 a přímé základny má délku `4π/3+2`; druhý profil má dvojnásobnou délku a nenulovou hloubku. Součty native délek splňují reportovanou globální mez, skutečný hrot zůstává ostrý mezi source patchi a základna zůstává L. Reverzní closed loop správně přehodí controls, orientaci source intervalu i směr; poslední explicitní ruling je reprezentovaný Z bez duplicitní nulové closing hrany. **Délkový důkaz closing rulingů je výslovně mimo tento helper** a musí ho doplnit volající.

## Adversarial vstupy a integrační hranice

Negativní vlastní testy odmítají záporné source meze, NaN bod, opakovaný parametr, chybnou same-u provenance, chybějící proof scope, nulovou regularitu, nezachovatelný nebinární bod, nemožně těsný budget a extrémně nerovnoměrný interval způsobující nepodporovaný control výpočet. Neprovede se tichý clamp nebo mutace input reportu; výsledkem je UNRESOLVED.

Numerický certifikát je **podmíněný pravdivostí a aktuálností source reportu**, nikoli ověření libovolného přepsaného JSON. Helper neporovnává report se zdrojovými profily ani nekontroluje source revisions; pouhé nastavení EXACT nebo změna kladného δ na příliš malé číslo z nedoloženého vstupu nevytvoří skutečný source důkaz. Caller má použít aktuální výsledek schváleného solveru. Rovněž musí ověřit skutečnou vazbu source identit: prázdný string profile ID a truthy neřetězcový segment ID projdou současným numerickým guardem. To nemění zde prokázané numerické meze, ale není to schválení takové provenance pro persistovaný projekt či export. `LoftProfile` samotný umožňuje anonymní pure numerické vstupy; absence reálné identity proto musí zůstat integrační podmínkou, nikoli tvrzením, že ji tento helper certifikoval.

Celková topologie native smyček, jejich případné samopřekřížení, skutečné otvory a assembled intersections zůstávají callerovi. Actual binary geometry bound nepokrývá zaokrouhlení při uložení SVG/PDF; writer musí ze stejného snapshotu doložit vlastní mez a zachovat společný end-to-end rozpočet. Samostatné technické schválení tohoto fitteru nedovoluje přičíst další nezávislou0.01mm exportní chybu nad již čerpanou rozvinovou toleranci.

## Uplatnění skills a meze předání

Skutečně načtené skills konstrukce, ověřování a delivery vedly k zachování gotického rohu, rozlišení source C oproti skutečné rozvinuté L hranici, nezávislému racionálnímu důkazu přes vrácené controls, globálnímu sčítání obou řetězců a přesnému připnutí zdroje. Dřívější poučení o sampled hodnotě versus globální mezi bylo použito v aktuálním výsledku; nejde o obecný či lidský proof účinnosti skillu.

Tato revize byla pouze souborová a numerická. UI, nový uživatel, nativní desktop, save/reopen, layout, skutečný externí editor, SVG/PDF a fyzický výtisk nebyly spuštěné a nejsou přijímané tímto verdiktem. Nezávisle schválená komponenta je konkrétní vstup pro navazující implementaci a review; nepředbíhá digitální předání PC-007A ani celého P2.
