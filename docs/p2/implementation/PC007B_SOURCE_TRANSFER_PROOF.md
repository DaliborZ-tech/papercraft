# C: native tab → skutečný zdrojový válec/kužel

Nový pure matematický přírůstek; **nezávislé review PENDING**. Výchozí commit
`d26c4c16ea259c55bdbedd0472a3faebaf5b8286`. Nemění `curved_tabs.py`, body geometrii,
schema, registry, UI ani export. Source/test SHA-256 a actual import jsou
v [manifestu](evidence/c-source-transfer-source.json); parent není vydáván za nový kód.

Samotný reference Rim κ=±1/3 necertifikuje actual binary zdroj H≈√800. Tento
přírůstek řeší právě rozdíl R/κ, skutečný nativní papírový obrys, derivace a
společný rámec. **Není to EXACT konektor, fyzické P3 ani scene-wide clearance.**

## Rozhraní a povinné podmínky binderu

`curved_tabs_chart.certify_native_tab_chart(rim, tab, actual_base_commands,
actual_apex, chart_matrix, chart_translation, *, source_ids, source_digest)`
vrací `CERTIFIED_NATIVE_CHART` nebo `UNRESOLVED`. Podporuje M+L pro referenční
válec a jeden orientovaný minor circular M+A pro kužel; žádné náhradní C/polyline.
`actual_base_commands` musí být přesně skutečná společná hranice body/tab union,
actual_apex vrchol obou skutečných straight CUT stran. Matematika tuto podmínku
vrací jako explicitní caller condition, **nepředstírá prohlídku projektu**.
Reference affine A/trans se může otáčet i zrcadlit. Actual endpoint-circle A
nemusí být přesně její obraz; právě tento rozdíl se zde omezí i v derivaci.

`curved_tabs_transfer.certify_source_transfer(rim,tabs,cap,limits,binding,receiver,
max_cells=10000,max_depth=14,max_pairs=10000,unresolved_obstacle_ids=())` znovu
počítá native certifier, nepřijímá starý cached report. Vrací jen
`CERTIFIED_TRANSFER` / `UNRESOLVED`; native chyby a skutečné source negativní
svědky uchovává odděleně. `SourceTransferBounds` vyžaduje:

- outward exact intervaly actual R a κ, rim/body IDs, current source IDs+digest;
- explicitní `SAME_ORIENTED_SOURCE_TURN_BY_NATIVE_CHART`: θ zdrojového kruhu je
  tatáž orientovaná reference θ, ne nově odhadnutá podle vzorků či nearest;
- `BOUNDED_NATIVE_SHARED_BASE_CHART`: dokázaná bijekce χ celé reference tab
  oblasti na skutečný nativní papír, actual A a sup‖Dχ−A‖. Per-slot
  `TabChartBounds(tab_id,matrix,derivative_remainder,position_error,digest)` musí
  pokrýt přesně aktivní IDs. Jeden obecný A je dovolen pro společný chart případ;
- actual world frame Q (sloupce radial/tangent/outward_z) a rigorózní whole-frame
  operator reserve, navíc samostatný center/world position reserve. Chybějící
  derivace/operator/position nejsou implicitně nula. Společný Rim frame se nesmí
  zaměnit za tab-center frame a znovu přičíst center_turn.

`ReceiverTransferBounds` vyžaduje actual cap/holes IDs+digest a
`EXACT_COMMON_FRAME_COPLANAR`; interval roviny musí být **přesně [0,0]**. Radius,
center, in-plane frame a každá hole mají explicitní nejistotu. Nenulový či
nejistý contact gap není opraven průmětem do roviny. Printed side zůstává omezen
na původní back→front rodinu. Binder zodpovídá za aktuálnost/hash a registry,
samotný řetězec proof-kind není důkaz proti nesprávnému či lživému adaptéru.

## 1. Actual native chart: důkaz přes celou plochu

Reference minor circle má racionální kvadratickou reprezentaci. Pro původní
`q=κb/(4R)`, endpoints `(±xe,fe)` a `w=(1−q²)/(1+q²)` jsou homogeneous controls
`H0=(−xe,fe,1)`, `H1=(0,w*fe+xe²/(R/κ),w)`, `H2=(xe,fe,1)`.
Pro L jde o lineární trojici s váhami 1. Reference A/trans se aplikuje na
homogeneous numerátor i translation×weight. Actual SVG A používá již schválený
`curve_topology._endpoint_arc_node`: algebraický center/weight jsou intervaly,
fixed endpoints/radius/sweep zůstávají exact numeric vstupy. Neprovádí se konverze
přes source center/sweep ani předpoklad, že binární rotation je přesná isometrie.

Označme křivku `B=N/w`, actual tildou a jejich rozdíly Δ. Pozitivní Bernsteinovy
váhy dávají globální `w_min>0`. Hull homogeneous controls omezuje N,w a jejich
derivace (degree-2 derivative controls jsou `2(H[i+1]−H[i])`). Z přesných identit

```
w̃ ΔB = ΔN − B Δw
w̃ ΔB' = ΔN' − ΔB w̃' − B Δw' − B' Δw
```

plynou celointervalové δB a δB′ používané v kódu. Žádné maximum ze vzorků se
nepoužívá. Oblouky sdílejí **racionální kvadratický parametr**, nemusí sdílet
lineární úhlový parametr; proto zde nevzniká skrytá chyba derivace reparametrizace.

Pro reference apex Q a actual Q̃ se použije fan
`F(λ,t)=Q+λ(B(t)−Q)`, `G(λ,t)=Q̃+λ(B̃(t)−Q̃)`.
Protože obě strany jsou skutečné přímky apex↔base endpoint, jde právě o skutečnou
hranici materiálu. V `Dχ−A` se λ vyruší:

```
Dχ−A = [ΔB−ΔQ, ΔB'] [B_native−Q_native, B_native']⁻¹
```

`‖inverse‖ ≤ sqrt(U1²+U2²)/D_min`, kde U1/U2 omezují normy sloupců a D_min
celý determinant. Reference conic má `x'(t)≥2*xe*w` (derivace jeho lineárního
x-numerátoru, denominator≤1); pro všechny t tedy

`D_min = 2*xe*w * [depth−F−(xe+|offset|)*fprime] > 0`.

Actual determinant je zdola omezen `|det A|D_min` minus tři bilineární
perturbační členy z δB+δQ a δB′. Navíc celý actual base zůstává v otevřené
polorovině pod actual apex: margin `depth−F−(δB+δQ)/σ_min(A)>0`.
Determinant zachová znaménko a směr paprsku je přísně monotónní v polorovině;
fan je proto globálně jednoznačný. Nejde pouze o test lokálního Jacobianu.
V apexu je mapa spojitý jednostranný Lipschitz limit; netvrdíme klasickou
jedinečnou derivaci v tomto rohu. Meze platí pro celý interior i všechny
jednostranné limity. Rozdíl poloh má samostatnou mez max(δB,δQ).

## 2. Source R/κ a všechny normalizované fáze

Reference f(x), θ(x) zůstávají z téhož native chart. Pro source R_s,κ_s:

```
γ=acos κ, d(κ,t)=(cos[tπ+(1−t)γ], sin[tπ+(1−t)γ])
P_s=R_s[(1−α)r0+αrθ] +(1−α)x*t0 +(y−αf)d_s
α=max(0,(relief−y)/(relief−f))
```

`|∂κ d|=(1−t)/sqrt(1−κ²)`. Přes celý hull native/source κ tedy
`‖Δd‖≤Δκ/h_min`, pro **každé stejné normalizované t∈[0,1]**. Není to odhad jen
počátku/konce. Když aritmetika nedokáže h_min>0, vrací unresolved.

Nechť `a` omezuje source half-angle, `c=1−(κ_native*a)²/2`,
`F=R_native|κ_native|a²/2`, `L=relief−F`, `p=|κ_native|a/c`.
Použije se `|α_x|≤p/L`, `|α_y|≤1/L`, `|θ_x|≤1/(R_native*c)`:

```
δJx ≤ ΔR [p*a/L + 1/(R_native*c)] + p(1+F/L) Δd
δJy ≤ ΔR a/L + (1+F/L) Δd
δJ ≤ sqrt(δJx²+δJy²)
```

Native certifikát dává principal strain e. Weyl omezuje source J singular values
na `[max(0,1−e−δJ),1+e+δJ]`. Actual material má metrickou matici Dχ a skutečný
world frame Q. Exact Gram row sums a Weyl pro jejich rigorózní remaindery dávají
`a_min,a_max,q_min,q_max`. Celkový interval je

`[q_min*(1−e−δJ)/a_max, q_max*(1+e+δJ)/a_min]`.

Tím se zvlášť omezí obě principal strains, včetně nonzero metric chyby binární
rotace či reflection chartu. Samotný δposition se v této rovnici nikdy nevyskytuje.
Position má oddělenou mez: `‖D_s‖≤D_native+ΔR*a+F*Δd`; numeric chart a world-pose
position rezervy se přidají zvlášť, nikoli jako náhrada δJ.

## 3. Source globální mapa, clearance a kontakt

Transfer lokálních singular values sám neprokazuje globální injectivitu. Source
collar ji zde dostává nezávisle: souřadnice v=relief(y−f)/(relief−f) je určena
výškou při t<1, tangent roste v x. Při t=1 se použije explicitní kladná determinant
mez v (x,v). `|x−R_s sinθ|` má mez
`ΔR*a + (R_s,max+R_native*κ_native²)a³/6`. Kód z ní omezuje oba křížové členy.
Collar a rigidní část mají oddělené radial interiors na hranici R_s−relief.

Tělo neporovnáváme pomocí globálního δ nekonečných kuželů: při odlišném κ by
takový δ nebyl konečný. Přímý source důkaz místo toho dává rigidní části

`distance ≥ relief*h_min − R_s,max*a²/2 − tangent_defect − depth*a`.

Tato mez se převede přes q_min a numerical position reserve. Sibling sektory
používají skutečný R_s,min, native x/f region a source D_s meze. Každý unordered
aktivní pár má celou nezávislou phase×phase kontrolu; source gaps zahrnují skutečnou
radius/world metric. Relief-contact výjimka zůstává přesně původní nelepený collar.
Nebylo prokázáno jeho fyzické ohnutí, pružnost ani kompenzace tloušťky.

Ve finále d(κ,1)=−r0 **přesně pro každý κ**. Lepicí triangle je rigidní v actual
source frame; od native triangle se liší jen radiální translací ΔR, ne rotací
κ do jiného cap plane. Konzervativní allowance eroduje outer disk a nafoukne
každou skutečnou kruhovou hole o source/receiver/frame nejistotu. Původní finite
whole-triangle contact solver pak musí dokázat plné pokrytí i **nezměněné minGlue**.
Dolní area se násobí q_min²; horní je plocha CELÉHO triangle×q_max², nikdy jen
plocha erodovaného proxy. Neurčené pokrytí není známý negative ani pozitivní proof.

Coincident sibling source glue má samostatný pozitivně-plošný negativní svědek,
platný pro všechny admitted společné R/κ; unrelated unknown wall jej neodstraní.
Native negative report se rovněž zachová, ale bez source robustního důkazu se
nepřejmenuje na svědka skutečného source. Unknown okolní překážky blokují celkové
kladné předání. Každá z obou contact fází má konečný max_cells budget; reportuje
se native/transfer/celková spotřeba, plus max_depth a pair budget.

## Ověření a meze předání

První běh nového transferu 34 PASS; po přidání actual chartu/per-slot cover,
slant30/pose a singular precision guards aktuálně **58 nových PASS**. Relevantní
regrese s původní C matematickou sadou a area helperem: **133 PASS**, 6.53 s.
Raw předchozí běhy zůstaly zachované, nebyl odstraněn žádný FAIL ani oslaben AC.

Analytická očekávání: skutečný binární H=Float(√800) splňuje H²+100≠900;
nezávislá Decimal85 kontrola actual κ intervalu; oba cone rims10/20 s native
slant30; celé cubic-free native A/L packet arrays pro všech12 slotů; přesná
affine cylinder shear χ(x,y)=(x+ε*y/depth,y); reflected rational orthogonal chart;
null chart, source interval κ→1 pod aritmetickým rozlišením, nesprávný sweep,
ellipse/C unsupported, apex collapse, velká receiver/hole/frame nejistota,
minGlue1 a strain1% zůstaly stejné. Extra floating mezifáze jsou označené pouze
jako cross-check analytického vzorce, nepoužívají se v certifikačním rozhodnutí.

```powershell
python -m pytest tests/authoring/test_curved_tabs_chart.py tests/authoring/test_curved_tabs_transfer.py tests/authoring/test_curved_tabs.py tests/authoring/test_curve_area.py -q --junitxml=Temp/c-source-transfer-freeze.xml
ruff check src/archpapercraft/authoring/curved_tabs_chart.py src/archpapercraft/authoring/curved_tabs_transfer.py tests/authoring/test_curved_tabs_chart.py tests/authoring/test_curved_tabs_transfer.py
git diff --check
```

Spuštěno Python3.12.15 ze sdílené `.venv`, lokální pytest `src` / ověřený import.
Construction skill: skutečná native continuity/collar/receiver, žádný plane fake.
Verification: celointervalové derivace, source metrika, analytické negative/unknown.
Delivery: izolovaný přírůstek, source binding a nezávislé review pending.
UI skill: missing proof má konkrétní unresolved důvod; žádný nový UI průchod zde
netvrdíme. Přenos poučení DR01/P01/P02/V02 se zde ověřuje oddělenou metrikou,
globální injectivitou, skutečným materiálem a minGlue; nikoli novým user/P3 testem.

Doménová integrace musí nezávisle ověřit actual shared-base body/tab material
union, source angular identity, actual cap common-frame a serializované current
registry. Samotné přijetí libovolného dictu/proof-kind toto neprokazuje. Proto je
tento matematický přírůstek podmíněný a **nenahrazuje review domain/UI/output**.
