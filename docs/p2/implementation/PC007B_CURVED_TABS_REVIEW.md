# PC-007B / C — nezávislá matematická revize chlopní s curved-base collar

Reviewer `geometry_analysis`, autor komponenty `bend_obstacles`, oprava CI01
od integračního ownera; 11. 11. 2026. Reviewer není autorem `curved_tabs.py`
a neměnil produkci, její testy, staging, commit ani historii.

**APPROVED_IN_SCOPE pro přesný zdroj
`3a60d7db53db4f2ff305a15ec51f2077e7065bee`; CI01 MINOR CLOSED / VERIFIED.**
Schválení platí pouze pro deklarovanou čistou numerickou rodinu a její
podmíněný `CERTIFIED_APPROXIMATE`. Neznamená celé C, nezávislé schválení
doménového adaptéru, skutečnou native materiálovou unii, save/reopen, UI,
výrobní soubory, okolní svět ani fyzickou sestavitelnost.

Původní posuzovaný zdroj byl `54b9459c250d0c27a4528ab72983aac0b5bfd58e`,
evidence head `f577c36c0269b86173dbc01b5af476b647d12811`. Jeho numerické
meze prošly auditem, ale obsahoval níže reprodukovanou nejednoznačnost identity.
Historické výsledky a jediný FAIL zůstávají zachované.

## Připnutí a skutečně spuštěné zkoušky

Skutečný import byl při obou pinech ověřen jako
`C:\Users\dalib\projects\papercraft-curved-tabs\src\archpapercraft\authoring\curved_tabs.py`,
Python3.12.15. Pracovní soubory produkce/testů odpovídaly příslušnému pinu
(prázdný diff); změny reviewera jsou jen tento report a nové raw důkazy.

| Přesný zdroj | Zkouška | Výsledek |
|---|---|---|
| 54b9459 | Autorovy curved-tab + existující area testy | [74 PASS /7.24 s](evidence/pc007b-curved-tabs-review-54b9459-original.xml) |
| 54b9459 | První vlastní matematická sada | [22 PASS /4.12 s](evidence/pc007b-curved-tabs-review-54b9459-own.xml) |
| 54b9459 | Stejná matematika + vlastní CI01 negativ | [22 PASS /1 FAIL /3.14 s](evidence/pc007b-curved-tabs-review-54b9459-own-ci01.xml) |
| 3a60d7d | Všech23 vlastních případů +4 delta varianty + autorův nový CI01 test | [28 PASS /2.21 s](evidence/pc007b-curved-tabs-review-3a60d7d-fixed.xml) |

Původních23 případů včetně nezměkčeného CI01 očekávání je uchováno jako
[přesný versioned script](evidence/pc007b-curved-tabs-review-own-54b9459.py).
V [aktuálním scriptu](evidence/pc007b-curved-tabs-review-own.py) se při delta
review změnila pouze očekávaná binding SHA konstanta a přibyly4 varianty
known/unknown thickness × distinct/aliased IDs; matematická očekávání zůstala.
Binding manifesty [54b9459](evidence/pc007b-curved-tabs-review-54b9459-binding.json)
a [3a60d7d](evidence/pc007b-curved-tabs-review-3a60d7d-binding.json) připínají
skutečné soubory i reviewerovy scripty. Finální SHA256 produkce je
`e64ef4cd8b886735203d7b2a75fbf050af861c7863a27ee2fb026d7024ac9d3b`.

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest docs/p2/implementation/evidence/pc007b-curved-tabs-review-own.py tests/authoring/test_curved_tabs.py::test_owner_and_cap_may_not_reuse_one_ambiguous_entity_identity -q
```

## Nezávislý matematický audit

Reviewer ručně odvodil skutečný Jacobian mapy. Pro `H=relief-f`,
`D=B-G(x,f)`, `alpha=(relief-y)/H` v collar platí
`Jx=t+alpha*D'+alpha_x*D` a `Jy=d-D/H`. Tím byly přezkoušeny zvlášť
normové meze perturbace a všechny tři položky skutečné Gramovy matice.
Odhad tangenciální složky D používá rozdíl
`R(sin(theta)-sin(k*theta)/k)`, nikoli chybný předpoklad x=R*theta pro cone.
Row-sum bound symetrické Gramovy chyby dává eigenvalues v `[1-eta,1+eta]`;
principal strain je proto ohraničena `1-sqrt(1-eta)`, je-li eta<1.
Minimum s nezávisle platnou `||J-Q||` mezí je bezpečné. Nejde o označení
změny orientace báze za prokázanou deformaci materiálu.

Vlastní jiná orákula volí Pythagorejský parametr t tak, že sin(k*theta)
a cos(k*theta) jsou přesné zlomky. Pro k=±1/3 jsou pomocí triple-angle
identit racionální také sin(theta),cos(theta). Skutečné analytické J se pak
vyhodnotilo v85místné Decimal aritmetice při **phi=atan(4/3)**,
cos(phi)=3/5, sin(phi)=4/5, a při více vnitřních y. Eigenvalues tohoto JᵀJ
leží uvnitř reportované strain meze. To jsou nezávislé bodové kontroly;
celodoménový pozitivní důkaz tvoří výše přezkoušené nerovnosti, nikoli maximum
těchto bodů nebo autorovy preview vzorky.

Injektivita collar je rovněž oddělená od lokálního Jacobianu. V souřadnici
`v=relief*(y-f)/(relief-f)` je před koncem ohybu z=v*b_phi s b_phi>0;
z určí v a tečná souřadnice je přísně monotónní v x. Ve finální rovině
pozitivní `collar_injectivity_margin` zaručuje radiální monotónnost při
konstantní tečné souřadnici. Rozsahy tečných souřadnic mají souvislé v řezy;
collar a rigidní materiál mají oddělené interiéry v z, respektive ve finálním
poloměru R-relief. Ostrý přechod na relief není vydávaný za hladkou pružnost.

Native base byla nezávisle odvozena racionální parametrizací kružnice.
Pro oba k znaky i±1e-20 body přesně splňují kružnici se středem `(0,-R/k)`;
nenulové k zůstává A, nikoli eps-válec. Zdrojové délky používají skutečnou
atan šířku a source-gap interval, nikoli nominal_base. Sdílená base se
nevyskytuje mezi cut-side A příkazy. **Tento audit však neviděl skutečný body
adaptér:** flag `requires_exact_shared_native_base_in_body_adapter=True` je
podmínka, kterou nelze nahradit tvrzením tohoto certifikátu.

## Celá fáze, kontakt a negativní důkazy

Body-distance audit použil generátorovou radiální referenci. Její vzdálenost
od zpětného otevřeného cone/cylinder těla je nejméně y*h po celém intervalu
phi; analytická mez odchylky od G vede k deklarované dolní mezi mimo collar.
Pro cylinder je vzdálenost této reference přesně y pro každou fázi. Vlastní
odlišné mezifáze a vnitřní body rigidní části tuto mez potvrdily. Sibling
proof byl přezkoušen pro nezávislé fáze: kladné radiální minimum, celé angular
sektory včetně negativního flat y, periodický odstup, dolní sin mez a odečet
obou collar odchylek. Vzorky nepřisuzují clearance.

Kontakt se týká skutečné rigidní glue triangle nad relief, ne celého nominálního
trojúhelníku. Vlastní přesné očekávání je
`xe*(depth-relief)^2/(depth-fe)`. U válce široké volby je9/8 mm².
Při hole radius0.1 přesně v apexu tohoto triangle je chybějící materiál
**0.01*atan(0.5)** mm²: jde o sektor kruhu v ručně určeném wedge. Vlastní
vysokopřesné očekávání skutečného kontaktu leží uvnitř certifikovaného intervalu,
prokázaná chybějící plocha nepřekračuje tento sektor a duplicita stejné díry
nezdvojnásobí chybějící materiál. I když zbývá více než minGlue1, certifikátor
správně vrátí INVALID podle svého výslovného kontraktu plného podložení glue
triangle; otvor se nevyplní ani chlopeň potichu neořízne.

Neurčené contact buňky přispívají jen do horní meze, pozitivní uncovered oblast
je negativní důkaz. Kladný gap kontaktní roviny1e-40 zůstává INVALID: průmět
není kontakt. Vlastní known positive-area overlap přežil současně neznámou
tloušťku, cizí unresolved obstacle i vyčerpaný contact-cell budget. Finite
pair/depth/cell budget a neznámá tloušťka nedostanou CERTIFIED. Arbitrární
seam turns31/97, -7/31,5/4 zachovaly12 slotů a66 párů; skutečný průchod tab
přes šev zůstal INVALID. Off/custom ověřuje inventář,55 párů a stálé ID.

Přímá [raw numerická rekapitulace](evidence/pc007b-curved-tabs-review-3a60d7d-summary.json)
připíná narrow b0.24/depth9.5/relief0.6/minGlue1/max strain1% pro cylinder,
coneR10/k=-1/3, coneR20/k=+1/3 a near±1e-20. Všechny jsou podmíněné
CERTIFIED_APPROXIMATE. Široká technická volba se při zpřísnění na1% správně
neprohlásila za ověřenou. Žádná z těchto hodnot není materiálová vlastnost papíru.

## CI01 MINOR — nejednoznačná owner/receiver identita, nyní uzavřeno

Původní pure API kontrolovalo pouze shodu owner/receiver řetězců s Rim/Cap.
Po nastavení `Cap.part_id=Rim.body_id` a odpovídajících Tab.receiver_id
nad dvěma různými geometriemi vracelo CERTIFIED_APPROXIMATE. Protože nejsou
dokumentované role namespaces a doména používá globální UUID, integrační owner
výslovně stanovil odlišné body/cap entity v tomto podporovaném kontraktu.
Nejde o nalezené podhodnocení geometrického boundu.

Fix3a60d7d přidal pouze2řádkový guard před geometrií aktivního tab,9řádkovou
regresi a5 řádků explicitního kontraktu. Žádná matematická mez, mapa, tolerance
nebo numerické ABI se nezměnila. Reviewer přečetl přesný diff a zopakoval
nezměkčený původní negativ. Alias je INVALID i s neznámou tloušťkou a nic
nezůstane v checked_ids; odlišná ID mají původní pozitivní výsledek, případně
UNVERIFIED při neznámém materiálu. **CI01 CLOSED / VERIFIED.** Skutečné UUID,
globální registry a lineage nadále patří do doménového adaptéru.

## Skills a nepokryté přejímky

Skutečně načteny AGENTS, všechny4 projektové skills, AC-C/AU10/AU11,
numerické tolerance, kontrakt a produktová analýza. Konstrukční skill vyžaduje
odlišit skutečnou base, nelepený collar a rigidní glue; verification skill
whole-domain důkaz a jiná orákula, skutečný import/hash a zachovanou FAIL
evidenci. Delivery skill se uplatnil samostatným CI01 nálezem a novým exact-pin
delta review. UI skill zde znamená pravdivé omezení výsledku, nikoli zkoušku UI.

Schválení nezahrnuje fyzický průchod **celého povoleného nelepeného collar**:
jeho body/cap kontakty jsou výslovná výjimka digitálního modelu, nikoli důkaz
pružnosti, tloušťkové kompenzace, lepidla či přístupu ruky. Ostatní překážky
jsou mimo solver a jejich nejistoty musí zůstat v úplné sestavě. Rovněž čeká
skutečný body-native union a transformace/source trim, printed side nad tímto
jediným podporovaným back→front případem, kompletní regenerační/persistenční
integrace, UI tvorba/off/custom, ruční layout, SVG/PDF a jejich skutečné čtení.
AC-US08:0 nových účastníků / NOT_RUN; P3:NOT_RUN. Celé C/P2 se tímto neuzavírá.
