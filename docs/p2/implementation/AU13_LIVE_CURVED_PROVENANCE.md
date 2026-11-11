# AU13: živé analytické zdroje ARC/CUBIC a historické reference loftu

Produkční source pin: `4f43a6427c7fbd25a87309ab31ad676ddd7794e1`, větev
`revival/p2-curved-profile-provenance`. Jde o konkrétní doménový přírůstek,
nikoli o schválení celé AU13/P2. Nezávislé aplikační review a nové skutečné UI
průchody jsou **PENDING**; původní helper review má vlastní oddělený rozsah.

## Funkční změna

`CurveSegment.source_reference` nese původní analytický `CurveSource`, přesný
racionální interval a kvalifikované identity profilu, historie, aktivního dílu
a generace. Živý profilový záznam musí přesně odpovídat replayované historii
i své kanonické numerické projekci. Radius/počáteční fáze oblouku se neurčují
z nového zaokrouhleného dělicího bodu; kubická omezení používají původní
Bernsteinův polynom. Úsečky bez descriptoru zachovávají původní LINE cestu.

`split_profile_segment` a `merge_profile_segments` nyní skutečně obsluhují ARC
i CUBIC. Opakované dělení a inverzní spojení uchovávají retired UUID a body.
Kopie s měřítkem transformuje každý původní zdroj jednou a přidělí kopii vlastní
identity; nekonstruuje nové poloměry z jednotlivých float potomků.

Existující loft může nadále odkazovat na celý původní úsek, i když autor rozdělí
jen jeden profil. Sémantický zdroj vyžaduje jednoznačné úplné pokrytí stejného
zdroje/generace. Nemění patch, ruling, šev, parametrizaci ani protější profil.
Skutečná geometrická změna potomka vytvoří novou generaci; starý smíšený trim
zůstane uložitelným `UNRESOLVED` cílem s původními referencemi a blokovaným
exportem. Nedochází k implicitnímu přepárování.

Papírové rámce rozlišují původní tětivu od prvního potomka a zachovávají
materiálový bod po odstranění dělicího vrcholu. Loft rámec vyhodnocuje **známý
zdrojový parametr dopředně v doložené bounded reprezentaci**. Není to přesná
analytická inverze, nearest picking ani důkaz fyzického přehybu;
`paper_frame_source_mapping` uvádí tuto mez a rozsah. Protikladné výskyty na
otevřeném švu se pravdivě odmítají.

Loft analytická data, nativní CUT, výstupní source replay a kruhový C receiver
nyní přenášejí příslušnou historii. C seam/radius vycházejí z celého původního
zdroje; nepoužívají zaokrouhlený první child. Zachován je C8 důkaz přesné společné
translace receiveru a odmítnutí nepodložených transformací.

## Rozhraní pro UI

```python
project.profile_segment_length(profile_id, segment_id)
# {status: CERTIFIED, lower, upper, units: model_mm}

project.profile_segment_parameter_at_length(profile_id, segment_id, distance_model_mm)
# {status: CERTIFIED, parameter: Fraction, distance_bounds_model_mm: [lo, hi],
#  actual_error_bound_model_mm, units: model_mm}
```

ARC/LINE mají doloženou konstantní rychlost; CUBIC používá konečné hledání nad
intervalově doloženou původní obloukovou délkou. Výchozí chyba je nejvýše
`0.001 / project.scale` modelových mm, bez epsilon rozšíření. Neplatná vzdálenost
nebo nedostatečný rozpočet vrací čitelnou typed chybu. Apply znovu provádí veřejný
příkaz; náhled není injekce projektového stavu. UI integraci vlastní samostatný
agent, jehož skutečné pozitivní průchody nejsou součástí zdejšího důkazu.

## Persistence a kompatibilita

Aktuální experimental formát je **schema9**,
`0.3.0-pc008-curved-source-provenance-experimental`. Pole descriptoru je v živém
záznamu current9 povinné, jeho hodnota smí být `None`. Známé schema1–8 odmítají
podstrčené nové pole v živém segmentu, i `None`; bezpečný adapter doplní výchozí
hodnotu pouze do živých objektů. Načtení staršího souboru vyžaduje SaveAs a nikdy
nepřepíše originál. Historické CUT/rámce/layout/zámky zůstávají zachované a stará
odvozená capability je explicitně stale do přepočtu.

Archivní D `source_binding`, generační certifikáty a fingerprinty se nepřepisují.
Hashování pouze na oddělené kopii známého `CurveSegment` záznamu považuje absent
legacy pole a `source_reference=None` za stejný default. Neprázdný descriptor se
hashuje celý. Nejde o rekurzivní mazání `None`, tolerování unknown fields ani
obcházení kontroly otrávené current9 cache.

## Ověření a praktické meze

[Přesná evidence](evidence/au13-live-source9-4f43a64-verification.json) a
[JUnit](evidence/au13-live-source9-4f43a64-coupled.xml): **419 PASS, 0 failures,
0 errors, 0 skipped**, 169.94 s. Soubor obsahuje příkaz, prostředí, skutečné
archivní vstupy a jejich SHA. Ruff a `git diff --check` prošly.

Nové aplikační orákuly zahrnují R20 při `t=1/3`, původní cubic délku 8 a nezávislý
prefix `L(u)=8u³−12u²+12u`, opakované dělení, jednostranný loft, retired rámec,
save/reopen, skutečné SVG/PDF, C body i receiver ARC split, smíšené generace,
poškozené descriptory a rozlišení historického defaultu od skutečného zdroje.
Plocha je přímo původní NET BODY/holes versus skutečná nativní projekce; chyba
se sčítá přes celý díl a zahrnuje skutečný world-basis Jacobian. Dílčí rozdělení
nedostává nový celý toleranční rozpočet.

Pět skutečných publikovaných archivů A/B/D/C/LINE prošlo copy→recompute→actual
SVG/PDF při zachování originálních bytes, identit, rámců, layoutu a D generací.
Navíc [tři skutečné C8 soubory](evidence/au13-live-source9-4f43a64-c8-copies.json)
(cylinder, cone se společnou translací, near-cylinder) prošly stejnou cestou;
žádná jejich výstraha nebyla nutná k obejití digitální chyby. Výstupy z tohoto
backendového opakování mají zaznamenané SHA a leží v čerstvých Temp adresářích.

Celá čistá partition může použít původní topologický důkaz. **Neúplný ARC view
sám nedává exact source-topology/hinge proof**; nepodporovaný kernel zůstává
typed `UNRESOLVED`. Povolený starý authored endpoint gap se uchová a má vlastní
metrickou mez; nepředstírá se jeho oprava ani přesná topologická shoda. Přísné
homothetické a ostatní původní family podmínky se neoslabují.

Použité konstrukční/verifikační/UI/delivery skills určily zachování otevřené
konstrukce, měřenou vzdálenost místo skrytého parametru, nezávislá očekávání,
ochranu autorovy práce a oddělení druhů důkazu. Tento backendový průchod není
nový UI test, lidský test AC-US08, externí editor ani fyzické P3. C8 a původní
publikované důkazy zůstávají historicky beze změny.
