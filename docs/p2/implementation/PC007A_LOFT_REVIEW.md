# PC-007A — nezávislá matematická revize loft komponenty

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; autor komponenty je jiný agent. Přesný zdroj **`bf1aff7c515f0becc98ee39714e925225629abb6`**, větev `revival/p2-loft-math`, worktree `C:\Users\dalib\projects\papercraft-loft-math`. Před revizí byl pracovní strom čistý. Produkční soubory a autorovy testy nebyly revidujícím měněny.

**Verdikt: CHANGES_REQUESTED — L01 MAJOR OPEN.** Nezávislá analytika potvrzuje zkoušené pravidelné rodiny a odmítání některých nepodporovaných případů, ale report může udávat nepravdivou mez chyby parametrického mapování. To brání použití certifikátu pro návazné spoje, autorské body a přesné source-reference mapování.

**Aktuální následná revize:** oprava `39f049dbd459f67dd27d9661773780a41612d59f` níže uzavírá L01; APPROVED_IN_NUMERIC_COMPONENT_SCOPE. Výše uvedený původní verdikt a FAIL zůstávají historickým důkazem.

## L01 — tětivová geometrická mez není mez interpolace v parametru

Jednoduchý regulární zdrojový kubický segment má řídicí body `(0,0)`, `(1,0)`, `(3,0)`, `(6,0)`. Z nezávislé Bernsteinovy expanze plyne `C(t)=(3t+3t²,0)` a rychlost `3+6t >= 3`. Druhý profil je shodný ve výšce 10, tedy jde o normálovou extruzi bez singularity. Jeho správný rozvin je `[arclength(C,t),10v]=[3t+3t²,10v]`.

Křivka leží přesně na přímé tětivě, takže `certify_curve` pro geometrii/délku potřebuje jen parametry `[0,1]`. Loft je převzal i pro `sample_loft`, které v parametru lineárně interpoluje uložené body. Výsledek na `u=v=0.5`:

| Veličina | Analyticky | V reportu / mapování |
| --- | --- | --- |
| Stav rodiny | Normálová regulární extruze | EXACT |
| Světový bod | `[2.25,0,5]` | `[3,0,5]` |
| Bod rozvinu | `[2.25,5]` | `[3,5]` |
| Skutečná bodová chyba | 0,75 | deklarovaná mez `7.389644451905042e-12` |

Geometrický Hausdorff/tětivový bound může být nulový a délkový deficit nulový, a přesto je interpolace **ve stejném zdrojovém parametru** chybná. Report výslovně poskytuje BOUNDED_PARAMETER_INTERPOLATION a globální position bound; nejde proto jen o povolenou alternativní parametrizaci stejné množiny bodů. Závada může přesměrovat zdrojový autorský bod nebo spoj.

Doporučení: při konstrukci parametrické sítě zahrnout správnou mez druhé derivace, například `sup|C''| h²/8`, a odpovídající mez interpolace kumulativní obloukové délky pro rozvin, nebo vyhodnocovat analytický zdroj a samostatně certifikovat lokální arclength mapování. Nepřepisovat tvrzení na přesnost délky ani nepřidávat jen vzorky bez globální meze. Následná zkouška musí zahrnovat nelineárně parametrizovanou kolineární kubiku i skutečně zakřivenou kubiku a vnitřní body celého intervalu.

Nález byl integračnímu ownerovi předán ihned, včetně konkrétního reprodukovaného bodu. Oprava a její následné nezávislé review zatím čekají.

## Ověření a ostatní zjištění

Spuštění ze zdrojového worktree s `PYTHONPATH` na jeho `src` a Pythonem `C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe`:

```powershell
python -m pytest tests/authoring/test_curves.py tests/authoring/test_loft_geometry.py -q --junitxml=docs/p2/implementation/evidence/pc007a-loft-review-original.xml
python -m pytest docs/p2/implementation/evidence/pc007a-loft-review-own.py -q --junitxml=docs/p2/implementation/evidence/pc007a-loft-review-own-initial.xml
```

- Původní testy: **52 PASS / 2,13 s**, [JUnit](evidence/pc007a-loft-review-original.xml).
- Vlastní analytika: **14 PASS, 1 FAIL / 0,65 s**, [zdroj](evidence/pc007a-loft-review-own.py), [JUnit](evidence/pc007a-loft-review-own-initial.xml). FAIL je produktový L01 a zůstává zachovaný.

Vlastní pozitivní důkazy používají kruhový kuželový pás s analytickým `R=sqrt(r²+(H/(k−1))²)` a `theta=πr/R`. Pro rostoucí i zmenšující se profil, zápornou hloubku a paper scale 0,1 byly vlastní body uvnitř interpolačních intervalů porovnány se skutečnou parametrickou plochou a analytickým rozvinem. Byla zkontrolována hlášená globální úhlová mez a deficit celého obvodu, nikoli jen délky jednotlivých listů nebo vrcholové reziduum.

Vlastní B2 tvoří čtyři čtvrtoblouky s poloměry 2 a 3: sjednocení patchů má skutečný otvor, obsahuje bod `(0,2.5)`, neobsahuje počátek a jeho plocha odpovídá `5π` v odvozené poziční toleranci. Součet všech vnitřních obloukových úseků byl porovnán s `4π` a vnějších s `6π`; oba deficity samostatně kryje reportovaná boundary-length mez. Tím je přezkoušen i účel autorovy opravy předchozího malého planar length bound v `bf1aff7`, ne pouze přečtena formule.

Vlastní B1 je dvouoblouková gotika s vrcholem `[0,sqrt(3)]`, středy `[±1,0]`, sweep −60°, homotetií 2 a hloubkou 3. Hrot zůstává skutečným FOLD_CREASE mezi patchi; tessellace je DISPLAY_ONLY_NOT_FOLD. Vrcholové rulingy jsou ve výsledku společné. Vlastní negativní případy ověřují singularitu záporné homotetie v analytickém `v=1/(1−k)`, 30° twist jako NONDEVELOPABLE, nedýadickou stacionaritu kubiky, nepodporovaný dílčí interval a vyčerpaný rozpočet. Explicitní forward/reverse intervaly byly porovnány s analytickými světovými body a lineage.

Omezení rozsahu jsou v API viditelná: celý profil a jeho assembled intersections stále validuje volající; certifikát pokrývá explicitně párované intervaly. Konečný soubor nulových determinantů není používán jako kladný důkaz obecného loftu. Homotetie vychází z přesné racionální algebraické shody binárních kontrolních bodů; rychlost kubik má intervalovou dolní mez, ne pouhou absenci nalezené nuly. Konzervativní nedoložený případ se vrací jako UNRESOLVED.

## Skills a nepokryté přejímky

Skutečně načteny čtyři projektové skills a příslušné AU09/B1/B2/B3, kontrakt a geometrické spiky. Konstrukční skill vyžaduje zachovat gotický roh a prázdný vnitřní region, což vlastní zkoušky kontrolují. UI skill znamená pravdivý význam certifikátu a opravitelné nepodporované korespondence; pure komponenta nepředstírá UI a L01 se nesmí skrýt jen textovou nápovědou. Verification skill vede ke skutečnému bodovému protikladu mimo vrcholy sítě a nezávislé analytické parametrizaci. Delivery skill vyžaduje opravu a nové review konkrétního pinu před předáním.

Tato revize nepokrývá persistenci, skutečné nakreslení a editaci profilů/loftu v UI, ruční layout, SVG/PDF, editovatelnost v reálném editoru, nového uživatele ani fyzickou sestavitelnost. Celá PC-007A a AC-AU09 nejsou splněné existencí pure numerické komponenty. Předchozí samostatný nález R01 v `curves.py` zůstává navíc otevřený do vlastního opravného review.

## Následné review opravy L01 — `39f049d`

Přesný zdroj **`39f049dbd459f67dd27d9661773780a41612d59f`**, 9. 11. 2026. Přečtena změna numeriky i nové autorovy regrese, bez změn produkce reviewerem.

**L01 CLOSED; APPROVED_IN_NUMERIC_COMPONENT_SCOPE** pro opravený loft a jeho hlášené meze v deklarovaných rodinách. Tato formulace neschvaluje celou PC-007A, nativní SVG writer ani dosud neuzavřený samostatný curve R01.

Oprava ponechává původní geometrický/délkový certifikát a přidává nezávislé dělení pro interpolaci ve zdrojovém parametru: globální `M=sup|C''|`, požadované kroky z `M/(8*budget)` a závěrečnou mez ze **skutečného největšího rozdílu sousedních parametrů** ve sjednocené síti. Proto nerozhoduje jen nominální počet rovnoměrných kroků. Při pravidelné křivce má oblouková délka `L''=(C'·C'')/|C'|`, tedy `|L''|<=|C''|`. Stejná mez proto kryje místní lineární interpolaci pravé arclength souřadnice i světového bodu. Výpočet nevydává tuto identitu bez prokázané regularity.

Celkový poziční bound nyní **sčítá** globální součet prefixových obloukových gapů, největší místní interpolační mez a numerickou rezervu uzlů. V předchozím `max(prefix,local)` by souběžné chyby mohly zůstat mimo mez. Konkrétní report tyto tři členy vystavuje samostatně. Maximální počet uzlů se po sjednocení sítí kontroluje znovu; nedostatečný rozpočet vrací UNRESOLVED, nikoli falešně přesnou síť.

- Původní vlastní sada včetně nezměněného L01 orákula a dvě nové vícepatchové zkoušky: **17 PASS / 0,90 s**, [JUnit](evidence/pc007a-loft-review-own-39f049d.xml).
- Autorovy curve+loft regrese: **55 PASS / 2,54 s**, [JUnit](evidence/pc007a-loft-review-original-39f049d.xml).

Nové vlastní případy používají dvě navazující kubiky s `C(t)=(3t+3t²,3t²)` a zápornou normálovou hloubkou 7, paper scale 1 a 0,1. Analytická druhá derivace `(6,6)` nezávisle stanoví požadovanou místní interpolační mez. Body uvnitř deseti parametrických buněk mají očekávanou světovou polohu z polynomu a očekávanou flat x z nezávislé kvadratury explicitní rychlosti `hypot(3+6t,6t)`, v druhém patchi včetně celého prefixu prvního patche. Reportovaná mez kryla všechny tyto chyby, správně sečetla členy a malý rozpočet bezpečně odmítla.

Původní `pc007a-loft-review-own-initial.xml` s chybou 0,75 zůstává zachovaný. Zelený nový běh potvrzuje opravu konkrétní příčiny i přenos na zakřivený vícepatchový případ; není důkaz nového člověka, fyzické stavby ani všech budoucích integrovaných mapování.
