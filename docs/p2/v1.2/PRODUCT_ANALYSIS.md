# Co autor skutečné vystřihovánky potřebuje

P2 v1.2, 6. 11. 2026. Normativní rozsah viz [kontrakt](P2_IMPLEMENTATION_CONTRACT.md); toto je analýza pracovních situací, nikoli důkaz hotového produktu.

| Situace | Autorova práce a problém | Nutný model/kontrola už v P2 |
|---|---|---|
| Otevřená budova bez dna | Stěny připevnit na základnu, dovnitř dosáhnout, střechu osadit později | Samostatné plochy/skořepiny; otevřené okraje platné; optional assembly grouping, žádný implicitní floor |
| Základna a terén | Vlastní půdorys, výřez pro přístup, nakreslená stopa domu, několik výškových stupňů | Rovinná plocha s dírami, lokální stopy a lepicí oblasti, výška umístění; volný reliéf terénu až rozšíření |
| Výztuha | Vlastní přepážka pod střechou, otvor pro manipulaci, pásek | Stejná skica/plocha jako stěna, identity a spoje; varování kolize při sestavení. Automatický statický návrh není součástí |
| Střecha s přesahem | Každá hrana jiný přesah, stěna končí uvnitř střechy; samostatný podhled | Vnější obrys nezávislý na připojovací stopě; dva samostatné díly/printed side, nic se nesmí automaticky oříznout |
| Okno a ostění | Vyříznout otvor, propojit přední/zadní různé obrysy s hloubkou/šikmostí | Vnitřní orientovaná smyčka, odpovídající parametry profilů, patch na interval; lom profilu vytváří skutečný díl/ohyb, nikoli náhodný triangle |
| Dva oblouky v jedné rovině | Rovinný prstenec/pás může mít díru nebo otevřené konce | PlanarRegion s vnější a vnitřní smyčkou či uzavřenými koncovkami, ne automaticky prostorový loft |
| Profily v různých rovinách | Extruze, kuželové ostění, případně nesouhlasné zakřivení | Explicitní correspondence, seam/start/direction, ruled patch a test regularity/developability; obrys nesmí být tiše změněn |
| Stočený plášť | Válec/kužel, autor určí šev a stranu potisku | Analytická plocha a přesné mapování, explicitní periodický šev, smooth bend odlišný od score/fold |
| Zakřivené chlopně | Jedna dlouhá chlopeň může při ohnutí zvrásnit nebo překážet | Jednotlivé záložky, počet/rozteč/gap/relief, trojúhelník či autorský obrys, nezávislá identita a skutečná kontaktní plocha |
| Nerozvinutelný povrch | Nezkrátit potají hrany nebo vydat triangles za hladký povrch | EXACT odmítnout, ukázat místo/důvod, nabídnout řezy a změnu konstrukce nebo explicitní segmentovanou variantu s měřením chyby |

Práce autora má tři různé geometrie: zamýšlený sestavený tvar, vyrobitelný materiálový díl a umístění na listu. Lem či chlopeň přesahuje hlavní plochu na papíře, po ohnutí má jinou prostorovou polohu. Lepicí oblast může být záměrně uvnitř jiného dílu; nejde o zakázaný překryv dvou volných vystřihovaných dílů na stránce. Chyby se proto mají hlásit podle fáze a entity, nikoli jedním neurčitým „overlap“.

Při změně profilu autor potřebuje předem vidět dopad: které otvory, ostění, připojení, chlopně, papírové díly a stránky budou stale. Ruční tvar chlopně se nezahazuje; neplatná reference se označí unresolved a export se zablokuje. Automatické „opravy“ podle nejbližšího bodu by mohly přilepit díl na jiné místo.

Základní materiálový profil uchovává tloušťku, vůli ohybu a minimální lepicí plochu jako samostatné autorské hodnoty. Gramáž neurčuje automaticky tloušťku. V P2 jsou tloušťkové kompenzace vypnuté, pokud nejsou pro konkrétní spoj navržené a ověřené. Průchod geometrickou kontrolou znamená digitální soulad s nastavenými mezemi; pevnost, manipulaci, deformaci při lepení a přístup ke spoji ověřuje výtisk.

Původní dům bez přesahu zůstává cenný pro numeriku: 100 × 40mm stěna, 42.426406871mm sklon střechy, analytické plochy a povinný společný díl při změně střechy. Nedokazuje možnost nakreslit otvor, ostění, přesah nebo plášť. Dosavadní GUI a exportní důkazy se nesmějí přiřadit přejímkám A–D.
