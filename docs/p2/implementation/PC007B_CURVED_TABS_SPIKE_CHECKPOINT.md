# PC-007B / C — checkpoint konstrukce zakřivených chlopní

11. 11. 2026. Izolovaná větev `revival/p2-curved-tabs`, základ
`b127fc550fc8401a8f8c8f066ca948e81184b246`. **EXPLORATORY / UNREVIEWED**.
Práce přerušena na pokyn integračního ownera kvůli prioritní opravě skutečného
Inkscape B1 průchodu. Žádný produkční modul, schema ani UI nebyly změněny.
Tento spike není splnění C, nezávislé schválení, digitální předání ani fyzický důkaz.

Načteny všechny čtyři projektové skills, platný kontrakt, produktová analýza,
AC C, architektura, UX a geometrické spiky. Jejich konkrétní použití: skutečný
spojený výřez má přednost před hezky vypadajícím, ale odpojeným footprintem;
numerický experiment se nevydává za celointervalový důkaz ani fyzickou zkoušku.

## Dvě konkrétní varianty

1. Pravý radiální ohyb válcové chlopně
   `Fφ(s,y)=(R−y sinφ) r(s/R)+(H+y cosφ) z`.
   Bází vždy sdílí skutečný kruhový okraj. Tangenciální metrika se ovšem mění
   faktorem `1−y sinφ/R`: depth2 při R10 vyžaduje až20% zkrácení. Není to
   bezdeformační papír a samotný EXACT plášť to neřeší. Tato varianta nemá PASS.
2. Rigidní lepicí trojúhelník s výslovným deformovaným, nelepeným collar.
   Doporučený další experiment, **nikoli schválený produktový výsledek**.
   Cylinder R10,12 chlopní, source base2, depth2, relief0,5 mm. Mezery jsou
   přibližně3,236 mm; skutečná rigidní lepicí část má1,125 mm² na chlopeň.
   Samotné `Gφ=Rr0+x t0+y dφ` má odpojenou bázi. Proto se nesmí publikovat
   bez spojitého přechodu popsaného níže.

## Skutečný flat materiál a spojitost

Osa z míří ven z těla přes posuzované víčko; tělo leží pod z=H. `k` je podepsaná
radiální složka generátoru směřujícího z těla ven, `h=sqrt(1−k²)`.
Pro cone10→20/slant30 je na horním okraji k=+1/3,R20; na dolním, s obrácenou
lokální osou, k=−1/3,R10. Periodický rim a vlastnictví musí doména zachovat.

Rovinná rozvinutá báze je skutečný oblouk
`Γ(s)=((R/k)sin(ks/R), −2(R/k)sin²(ks/2R))`.
V limitě k=0 je Γ(s)=(s,0). Báze není nahrazena tětivou ani falešnou origin loop.
Zdrojový interval je s∈[−b/2,b/2]; konce Γ se přímými stranami spojí s apex(0,depth).
Flat smyčka tedy obsahuje nativní A (nebo L pro přesný válec), dvě strany a Z.
Tentýž oblouk musí být sdílenou hranicí body↔tab v materiálové unii a zůstane
odkazem na skutečný zdrojový rim. Publikace nesmí vytvořit druhý CUT v bázi.

Na krátkém oblouku lze Γ vyjádřit grafem y=f(x).
`β=atan2(h,−k)`, `dφ=(k cosφ−h sinφ)r0+(h cosφ+k sinφ)z`, φ∈[0,β].
`B(s)=Rr(s/R)+Hz`, `Dφ(x)=B(s(x))−Gφ(x,f(x))` a

`Pφ(x,y)=Gφ(x,y)+max(0,(relief−y)/(relief−f(x))) Dφ(x)`.

P na y=f(x) sedí na skutečné B pro všechny fáze a na y=relief souhlasí s G.
Materiál je ve flat výřezu spojený; collar nemá skrytý řez. Nad relief je plocha
rigidní, finálně přesně v rovině příjemce. Collar však podléhá deformaci; hodnocení
nesmí tuto konstrukční cenu skrýt za APPROXIMATE bez konkrétních mezí.

## Kandidátní celointervalové meze — ještě nutná rigorózní implementace a review

Pro a=b/(2R) a krátký oblouk:

- `D0≤Ra²/2+R(1+k²)a³/6`, `|f|≤R|k|a²/2`, tedy `|Dφ|≤D0+|f|`.
- `cos(ka)≥1−(ka)²/2=c`, `|f'|≤|k|a/c`. Z derivací váhy collar plyne
  `Ex≤a/c+(1/c−1)+|f'|+|f'| Dmax/(relief−fmax)`,
  `Ey≤Dmax/(relief−fmax)`. Diferenciální porucha vůči rigidní izometrii je
  nejvýše `sqrt(Ex²+Ey²)`; nejde o fyzický materiálový zákon.
- Mimo explicitní relief je vzdálenost od otevřeného válcového/kuželového těla
  kandidátně nejméně `relief*h−D0−depth*a` pro **celý** φ interval. Před pozitivním
  verdiktem je nutné zahrnout tloušťku, vůli, skutečný trim a přesnost reprezentace.
- G leží při všech nezávislých fázích v sektoru s poloměrem≥R−depth a
  polovičním úhlem≤X/(R−depth). Úhlová mezera sousedů dává dolní mez vzdálenosti
  `2(R−depth)sin(gapAngle/2)−Dmax_i−Dmax_j`. Tím lze hodnotit pohyb jedné
  chlopně i ostatní folded; nejsou to jen konečné vzorky φ. Off se nevyhodnocuje
  jako materiál, ale jeho stabilní ID nesmí zmizet.

Kandidátní čísla jsou v JSON; plovoucí výpočet **není intervalový certifikát**.
Ve skutečné komponentě je nutné outward arithmetic, konečný budget, přesné native
endpoint semantics, vstupní validace a pravdivé UNRESOLVED při nesplněné mezi.

## Příjemce, negativní případy a pokračování

Pro rovný apex a konce báze (±xe,fe) je finální rigidní glue trojúhelník
`(R−relief, ±xe*(depth−relief)/(depth−fe))`, `(R−depth,0)`.
Jeho přesná plocha je `xe*(depth−relief)²/(depth−fe)`; celý trojúhelník musí
ležet ve skutečné cap-region po odečtení otvorů. Disk je konvexní, proto plné
pokrytí vnějšího disku lze doložit vrcholy. Otvory vyžadují samostatnou skutečnou
kontrolu a dolní/horní mez plochy; ne pouhé pokrytí středu nebo nominální plochu.

V aktuálním project/model/attachments nebyl nalezen produktový default minGlue.
Komponenta jej má vyžadovat jako explicitní materiálový vstup, nikoli tiše zvolit
nižší hodnotu, aby příklad vyšel. Numerický úspěch neslibuje pevnost, pružnost,
přístup ruky nebo sestavitelnost. Fyzický výtisk zůstává NOT_RUN v P3.

Navázání: implementovat pouze math modul `authoring/curved_tabs.py` a vlastní testy;
nejprve true-flat/source continuity, intervalové strain/position bounds a kladný
R10/12 tabs s explicitními rozpočty. Pak cone±1/3, válcový limit bez eps→EXACT,
cap holes/partial contact/minGlue, overlap/relief/owner/front/periodic IDs a finite
budget. Neznámá fyzická veličina nesmí potlačit jistý negativní výsledek. Root
rozhodne následné napojení do projektu/UI; tyto soubory jsou mimo vlastnictví agenta.

Reprodukce (numerický spike, nikoli AC test):
`python docs/p2/implementation/evidence/pc007b-curved-tabs-spike/checkpoint.py`.
Přiložený JSON má jen ilustrativní float čísla a vzorkované kontroly spojitosti.
