# PC-008 — zdroj a skutečné výrobní výstupy odvozené varianty

Finální komponentový zdroj: `26873c6d0950af412ba531f01440c3506b3dd6b1`,
předek `c77c09baa6115ed9681765324bcd259f33adc998`, základ domény `e51f127`.
Worktree `papercraft-segmented-output`, větev `revival/p2-segmented-output`.
Nezávislá revize této nové exportní komponenty je při zápisu **PENDING**.
Existující review matematiky ani LINE domény není automatickým schválením writeru.

## Úzké změny a uzavření zdrojů

Snapshot přidává u projektu s odvozenými generacemi jednou úplný oddělený
`construction_checks.segmented_source_project` z běžného `to_dict`.
Není v něm snapshot ani rekurzivní důkaz. Nový `segmented_output_validation.py`
jej striktně otevře pouze v paměti, ověří skutečnou doménu a znovu vytvoří
kanonický snapshot. Porovnání požaduje přesnou shodu celé coverage, všech
tiskových dílů, cest, labels, frames, spojů, aktivních generací i referenčních
a neaktivních ploch. Změněný report/hash, náhrada trojúhelníku stejně velkým
polygonem nebo vydání nesouvisející plochy za netisknoucí referenci tím neprojdou.
Změna autorské kotvy je podporovaná: nový frame se znovu odvodí ze skutečného
profilu a musí projít stejnou kontrolou. Zdrojové soubory se neotvírají k zápisu.

Omezení vstupu jsou32MiB pro jednotlivou serializovanou kontrolovanou strukturu,
hloubka64,500000 uzlů,4096 parts/surfaces,8192 profiles,8 generací a64 stránek.
Překročení končí typed UNRESOLVED. Source cache má nejvýše2 záznamy, klíčem je
skutečný celý neměnný obsah včetně autorského pořadí registrů, hodnotou pouze
neměnný JSON kanonického výsledku. Aktuální revize sama nestačí. Proměnné
návratové hodnoty nejsou sdílené s cache. Source capability/persistence schema
se tím nemění; jde o další publish-time evidence.

## Přímá geometrická kontrola skutečných souborů

Guard se spouští i pro LINE-only a curved D s prázdným `curve_profiles`.
Stávající nezávislé SVG/PDF readery čtou původní číselné tokeny, skutečné
transformace, coverage a CUT topology; publisher jim u tohoto řezu zadává
konečný budget400000 topology nodes a40000 commands. Žádná obrazová náhrada.
Nová kontrola srovná příkazy celých skutečných obrysů s kanonickým zdrojem,
jejich polohu, délku, stránku a čistou materiálovou plochu. Řezy se nesmí ztratit
ani přibýt. Na metrikách zůstává0.01mm a plocha
`max(0.01mm², 1e-6 × sourceLower)`.

Finální area baseline jde **přímo od zdrojové roviny** materiálového trojúhelníku,
před paper frame: přesné Fraction souřadnice profilu a basis dávají vektorový
součin, jeho velikost je obalena směrovaným sqrt a převedena scale².
Legitimní autorské chlopně přidávají ověřený čistý přírůstek unionu oproti jádru;
nepřičítá se překrývající se plocha chlopně dvakrát. Nejde o tvrzení přesné
plochy původního hladkého cíle. Ten je nadále APPROXIMATE s původním reportem
odchylek, délek a normal-angle. Zdrojový původ, skutečný core i konektory uzavírá
kanonické znovuodvození, samotná shoda plochy nestačí.

Idealizovaná izometrie zdrojové roviny podle skutečného anchor/axis má přesné
intervalové meze. Odchylka skutečného kanonického paper frame i rozdíl délek
se přičítají k naměřené serializační odchylce; mezikrok nedostane novou celou
toleranci. Původní target→material bound se počítá jednou, poté se přidá
publication reserve přes doložený pose operator. Celkový target budget autora
musí stále platit. CUT union obsahuje i legitimní chlopně; právě přítomnost
chlopně není důvodem zahodit certifikát nezměněného trojúhelníkového jádra.

SVG má na každé odvozené part group režim APPROXIMATE a UUID varianty, cíle
a trojúhelníku; metadata obsahují celý zdrojový důkaz. PDF má stejný digest
konstrukčního důkazu a APPROXIMATE registry v Keywords. Guard čte i skutečná
metadata obou souborů. `.author-export.json` nese konkrétní direct-source meze
pro každou part a oba skutečné formáty. Původní atomický staging, rollback,
font fallback a cizí soubory zůstávají ve stávající transakci beze změny.

## Konkrétní důkazy a meze

[Připnutý backend proof](evidence/pc008-output-26873c6/raw/results.json) obsahuje
skutečné importované umístění writeru, SHA zdroje i hashe aplikace a probe.
V obou případech zůstává původní přesný loft REJECTED, všechny tiskové díly
jsou APPROXIMATE a mají ruční layout na dvou listech.

| Backend fixture | LINE64 | Nezávislé gotiky96 |
|---|---:|---:|
| Snapshot | 0.185s | 0.379s |
| Cold export, po vyprázdnění source caches | 5.139s | 10.591s |
| Warm export | 4.325s | 9.185s |
| Zdrojový binding, kompaktní JSON | 483127B | 878257B |
| Celý snapshot, kompaktní JSON | 854977B | 1591773B |
| Výstupní balík včetně manifestu | 5412056B | 10075984B |
| Max source→actual position | 1.831e-5mm | 1.798e-5mm |
| Max source→actual material area | 1.089e-5mm² | 6.520e-6mm² |

Cold a warm balíky jsou ve všech bytes shodné. Vektory jsou rovněž byte-identical
s historickým [c77 mezikrokem](evidence/pc008-output-c77c09b/raw/results.json);
268 zpřísnil přímé ověřování a jeho manifest. C77 porovnával area k již
kanonickému CUT po frame, a proto jej tato zpráva nevydává za finální direct-source
gate. Historické raw se nemění. Část velikosti tvoří opakovaný úplný zdrojový
důkaz, nejde o velikost samotných vektorových path dat.

Finální důkazy testů:48 D-output PASS/89.35s; po závěrečném doplnění pose operatoru
se dotčené actual LINE/curved, direct-area a legit TAB testy zopakovaly4 PASS/24.48s.
Předchozí c77 celé D domain/output/batch mělo112 PASS/106.23s a stávající
writer/curve/material/connector/loft regrese88 PASS/66.88s včetně LD024000π.
Ruff i diff check prošly. Nejde o tvrzení nového úplného full-suite běhu na268.
Vlastní reprodukce dvou strain faktorů1.00013 ukazuje přenos SK011: každý
mezikrok jednotlivě projde plošnou mezí, jejich skutečný součet publisher odmítne.
Výstupní mutace posunu se zachovanou plochou, chybného režimu i chybějícího
zdroje jsou odmítnuty a původní owned/foreign bytes zůstanou stejné.

Zachované první neúspěchy v této evidenci jsou konkrétně vysvětlené: replay
musí zachovat autorské pořadí registrů; kanonický interní JSON může mít tuples
a numpy.float64, které běžný JSON encoder právem serializuje; test neurčuje
valley u chlopně s opačným skutečným směrem; příliš velká první strain fixture
byla správně odmítnuta již paper guardem. Každé zpřesnění má následný průchod,
žádný historický raw nebyl nahrazen.

Použité skills: konstrukce odděluje původní cíl, skutečné materiálové jádro
a konektor; verification používá skutečné soubory, analytickou kontrolu prvního
LINE trojúhelníku i samostatné direct-area negativní orákulum; delivery připíná
zdroj a zachovává FAIL i rozlišení důkazů. SK011 má tímto konkrétní další použití,
jeho nezávislé zhodnocení přenosu zde čeká na review. Širší účinnost zůstává
pending. UI/UX se neposuzuje z backendových stopkami. V tomto starším základu
není rootův asynchronní export; actual UI responsiveness a cancel zůstávají
**NOT_RUN** do jeho integrace. Nativní D průchod, nový uživatel a fyzická stavba
jsou pro tento komponentový pin rovněž **NOT_RUN**.
