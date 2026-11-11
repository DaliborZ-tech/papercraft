# PC-007B / C — attached native-base collar, matematický rozsah

Komponenta `authoring/curved_tabs.py`, nezávislé review zatím **PENDING**.
Původní `394e500` checkpoint je nadále historický experiment, nikoli tento důkaz.
Žádné UI, persistence, skutečný výrobní export, nový uživatel ani fyzické P3
nejsou touto komponentou ověřeny. Celé C/P2 zůstává nedokončené.

## API a výslovné předpoklady

`Rim(radius_mm,radial_slope,rim_id,body_id,seam_turn=0)` určuje skutečný kruhový
okraj otevřeného analytického těla. Osa z míří ven přes okraj; tělo leží pod z=0.
Válec R10/H30 odpovídá k=0. Kužel10/20/slant30 má na spodním okraji R10,k=−1/3,
na horním R20,k=+1/3. Skutečné konečné tělo je podmnožinou posuzovaného
polonekonečného generátorového těla; výška se proto v dolní mezi neuplatní.
Osa, rovina, source trim, šev a transformace musí být v adaptéru doloženy.

`Tab` drží ID, center_turn, nominal_base_mm, depth, relief, owner, receiver,
enabled, custom triangle tip offset a minimální požadovanou source gap.
`periodic_tabs` dává stabilní UUID pro slot, nezávislé na rozměrech/off/custom.
Středy jsou uprostřed pravidelných slotů od podélného švu. Chlopeň přes šev
se odmítá: v otevřeném rozvinu by se rozdělila na dva konce papíru.
Generátor přijímá buď nominal_base, nebo gap_mm. Gap znamená **minimální skutečnou
mezeru**; dosažená mezera je reportována intervalem, nikoli falešnou rovností.

`Cap(radius_mm,part_id,holes,contact_side='front',plane_offset_mm=0)` je skutečný
materiálový disk minus sjednocení kruhových děr v rim souřadnicích. Nenulová rovina
kontaktu se odmítá; rovinný průmět sám není kontakt. Rodina podporuje tab back →
cap front, ohyb dovnitř a apex uvnitř poloviny half-base. Ostatní strany/tvary
nejsou automaticky přeskládány. Printed side a obecný autorský polygon přidá
doména při budoucím napojení; komponenta takové rozšíření neslibuje.

`Limits` vyžaduje max position, max differential deformation, **minGlue**, thickness
a clearance. Default minGlue se v produktu nenašel, proto žádný nepřidáváme.
Technický limit deformace není materiálová vlastnost papíru.

Owner těla a příjemcova cap jsou v tomto podporovaném kontraktu samostatné
entity s odlišnými ID. Stejné ID není implicitně kvalifikované rolí; takový
nejednoznačný odkaz se odmítne. Doménový adaptér navíc ověří globálně jedinečné
skutečné UUID a odpovídající registry; samotný math certifikát tuto registry nemá.

`certify_tabs(...,max_cells,max_depth,max_pairs,unresolved_obstacle_ids)` vrací
CERTIFIED_APPROXIMATE / UNVERIFIED / UNRESOLVED / INVALID s inventářem, každým
aktivním dílem, páry a důvody. Neznámá tloušťka nevrátí CERTIFIED. Známá negativní
geometrie má přednost před cizí nejistotou. Nevyčerpané obecné okolní překážky
jsou mimo tento solver a musí zůstat unresolved v celkové sestavě. Scope je
explicitně jen analytické body + všechny aktivní sibling tabs + cap. Owner
nemá tento dílčí výsledek vydat za úplný scene certificate.

## Skutečná spojená native hranice, nikoli tětiva

Všechny rozhodné vstupy se čtou přesně jako Fraction (float znamená své přesné
binary číslo). Pro b=nominal_base a q=kb/(4R):

`xe=(b/2)/(1+q²)`, `fe=−kb²/(8R)/(1+q²)`.

Při k≠0 body `(±xe,fe)` leží **přesně** na kružnici se středem `(0,−R/k)`
a poloměrem `|R/k|`. Nativní A má small-arc flag0 a sweep(k<0). Base v materiálu
je tento oblouk, obě strany jsou přímé do apex. Při k=0 je base přesná úsečka.
Skutečná poloviční source úhlová šířka je `a=2 atan|q|/|k|`; pro k=0 `a=b/(2R)`.
Source arclength2Ra je proto samostatný interval. Žádná eps větev neztotožní
blízké různé poloměry a nevydá cone za přesný válec.

Na krátkém oblouku je base graf y=f(x). Doložena je kladná výška collar a větší
sklon obou stran trojúhelníku než mez |f'|. Flat region je tedy jednoduchý,
souvislý a obsahuje celou skutečnou base. Vrací se zvlášť shared_base_commands
a cut_side_commands: base nesmí být druhý CUT. Adaptér **musí** stejný native
oblouk použít v body hranici a materiálové unii; samotný tento math modul to
v neexistujícím projektu nepředstírá. Transformovaný/zaokrouhlený SVG/PDF výstup
bude vyžadovat zvláštní ověření skutečně publikovaných souřadnic.

## Celá mapa a rozsah deformace

`h=sqrt(1−k²)`, `β=atan2(h,−k)`, φ∈[0,β],
`dφ=(k cosφ−h sinφ)r0+(h cosφ+k sinφ)z`,
`Gφ(x,y)=Rr0+x t0+y dφ`,
`B(x)=Rr(θ(x))`, `θ=asin(kx/R)/k` (pro k=0 θ=x/R).

`Dφ=B−Gφ(x,f(x))`,
`α=max(0,(relief−y)/(relief−f(x)))`, `Pφ=Gφ+αDφ`.

Na base P=B pro **všechny fáze**, na y=relief P=G. Celý glue triangle nad relief
je rigidní a při φ=β leží v cap rovině. Collar je výslovně nelepený a deformovaný;
neexistuje přerušená flat hranice ani nevysvětlený skok na rigidní trojúhelník.

Pro horní mez a≤1/4, `c=1−(ka)²/2`, `L=relief−R|k|a²/2>0`:

`T=R(1+k²)a³/6`, `V=Ra²/2+R|k|a²/2`,
`Dmax=Ra²/2+T+R|k|a²/2`, `fprime=|k|a/c`.

Z |sin t|≤|t|, 1−cos t≤t²/2 a |sin t−t|≤|t|³/6 vyplývá |D|≤Dmax pro
celý materiál a všechny fáze. Derivace α dávají

`Ex=a/c+(1/c−1)+fprime+fprime Dmax/L`, `Ey=Dmax/L`.

`sqrt(Ex²+Ey²)` je mez ||J−Q||, nikoli automaticky skutečná strain: zahrnuje rotaci
báze. Samostatně se omezí Gramova matice JᵀJ:

`Aerr=2[(1+k²)a²/(2c)+fprime T/L]+Ex²`,
`Cerr=2V/L+Ey²`,
`Berr=T/L+a/c+fprime+fprime V/L+Ex Ey`,
`η=max(Aerr+Berr,Cerr+Berr)`.

Pro η<1 jsou singular values v `[sqrt(1−η),sqrt(1+η)]`; principal strain má
mez `1−sqrt(1−η)`. Použije se menší ze dvou **prokázaných** mezí této strain
(Gram a ||J−Q||). Při nedoložené regularitě/rozpočtu zůstane UNRESOLVED.

Injektivita není nahrazena vzorky: v collar zaveď `v=relief*(y−f)/(relief−f)`,
pak α=1−v/relief a `P=Rr0+x t0+v dφ+α[B−Rr0−x t0]`. Před koncem ohybu z
určí jednoznačně v, tečná souřadnice je přísně rostoucí v x. Ve finální rovině
kladnost výslovné dolní Jacobian meze zajišťuje radiální monotónnost po konstantní
tečné souřadnici. Collar je radiálně nad `R−relief`, rigidní část pod touto mezí;
jejich interiéry se nezdvojí. Jde o kusově hladký materiál, s crease na relief,
nikoli tvrzení o pružnosti nebo fyzické tloušťce deformovaného papíru.

## Celý ohyb: body, sousedé, cap

Pro rigidní část mimo relief se porovná G s radiální referencí
`F=(R+y aφ)rθ+y bφ z`. Od generátorového těla vzdáleného směrem zpět je F
nejméně y h; |F−G|≤Ra²/2+T+depth*a. Dolní mez body distance je proto
`relief*h−Ra²/2−T−depth*a`. Platí pro **celý** φ interval, ne jen φ=0 a β.
Požadovaná separace zahrnuje thickness+clearance+2*bend_radius. Těsnější
nedoložený výsledek se neprohlásí za kolizi ani volno: je UNRESOLVED.

Při všech nezávislých fázích má G radiální složku≥R−depth. Tečná úhlová
odchylka celé skutečné triangle/arc oblasti je nejvýše
`max(xe/(R−|fe|),|apexOffset|/(R−depth))`: poměr lineárních funkcí na stranách
trojúhelníku nabývá maxima v koncích; přidaný curved segment leží v base pásmu.
Použití |fe| zahrnuje i negativní flat y, kde počáteční radiální složka může klesnout.
Pro různé sektory a jejich skutečný periodický odstup Δ je vzdálenost G alespoň
`2 rmin sin(Δ/2)`. Odečte se Dmax obou collar a použije dolní Taylor mez sinu.
Každý unordered aktivní pár má vlastní výsledek. Off není materiál; neztrácí ID.
Pohyb jedné chlopně a ostatní folded je podmnožinou tohoto nezávislého proof scope.

Cap přijímající materiál leží v z≤0, tab contact face při ohybu v z≥0; u rigidní
části se kontroluje také jednostranný thickness envelope pro úvodní fáze cone.
**Výslovně povolená hinge/body/cap kontaktní oblast je celý nelepený relief collar.**
Není to důkaz jeho fyzického průchodu, pružnosti nebo potřeby tloušťkové kompenzace.
Zbytek materiálu touto výjimkou nelze zakrýt. Celá sestava stále potřebuje kontrolu
ostatních skutečných překážek a P3 ověření collar konstrukce.

## Skutečná lepicí plocha a konečné rozpočty

Průnik řezu y=relief se stranami dává přesný rovinný triangle; jeho plocha se
počítá racionálně, nikoli base×depth po odříznutí neznámé části. Větve contact
rekurze klasifikují celé trojúhelníkové buňky proti skutečnému disku a kruhovým
otvorům. Souřadnice rotovaných vrcholů jsou uzavřené intervaly; venek určuje
prokázaná vzdálenost od bbox, vnitřek konvexního disku všechny vrcholy. Děti mají
přesně aditivní plochy. Neurčené buňky přispívají do horní, nikoli dolní meze.
Jakákoli prokázaná chybějící lepicí plocha je INVALID; nejisté pokrytí UNRESOLVED.
MinGlue ani materiálový otvor nejsou potichu oříznuty nebo upraveny.

Sqrt používá celočíselné isqrt s outward racionalizací. Atan je alternující
racionální řada s omezeným počtem členů a doloženým zbytkem, π Machinovou identitou.
Trig rotace používá racionální intervalovou Taylor řadu a Lipschitz mez chyby úhlu.
Hloubka, počet buněk, párů a velikost vstupu mají explicitní konečné budgety.
Vyčerpání není pozitivní důkaz. Nepodporované/neplatné vstupy nesmějí vrátit PASS.

## Konkrétní použitelné digitální volby

Široký experiment b2/depth2/relief0,5, minGlue1 mm², max position0,08 mm,
max principal strain0,25, thickness0,2/clearance0,01 prochází jako omezený
APPROXIMATE pro cylinder a oba cone rims. Limit0,25 je pouze technická hypotéza;
nelze jej číst jako dovolenou deformaci běžného papíru.

Užší volba b0,24/depth9,5/relief0,6, stejný minGlue1 a thickness/clearance,
max position0,01 a **max principal strain0,01** prochází pro cylinder, oba cone
rims±1/3 a near-cylinder±1e−20. Je dlouhá a úzká; přístup, manipulace a pevnost
jsou fyzicky neověřené. Dvanáct slotů je zachováno a povinná ruční úprava/off
musí ještě projít budoucí doménou, skutečným UI a výrobním výstupem.

Matematické testy zahrnují analytickou cylinder plochu9/8, užší volbu s plochou
nejméně1, přesné native circle identity obou cone znamének, přechod/contiguity
oracles, principal-strain oracle, libovolné mezifáze, otvory, nenulový contact gap,
overlap, source seam/gap, off/UUID/custom, neznámou tloušťku/překážku a finite budget.
Automat není nový modelář a tento soubor nezakládá produktové přijetí C.
