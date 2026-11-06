# Geometrické spiky před stabilizací P2 v1.2

6. listopadu 2026. Autor samostatné analýzy: agent `geometry_analysis`. Vstup: [přesné upřesnění vlastníka](OWNER_CLARIFICATION.txt). Tento balík je experiment, nikoli produkční geometrické API, serializační schema, hotové UI nebo fyzická akceptace.

**Výsledek:** konstrukční doména musí uchovat původní profily, jejich korespondenci a hladké intervaly, parametrizovanou plochu s trim hranicí, vnitřní připojovací stopu a samostatný konektor. Přesné rodiny zahrnují více než rovinný dům: doloženou normálovou extruzi a homotetický kuželový loft kruhového, eliptického i gotického profilu. Obecná dvojice profilů, pootočená korespondence ani rozdělené trojúhelníkové chlopně automaticky přesný rozvin nedávají.

## Spuštění a důkazy

```powershell
.venv\Scripts\python.exe tools/spikes/p2_v12_geometry.py
.venv\Scripts\python.exe -m pytest tests/spikes/test_p2_v12_geometry.py -q --junitxml=docs/p2/v1.2/evidence/geometry-tests.xml
```

Poslední ověření: **40 PASS, 0 FAIL, 0 ERROR, 0 SKIP, exit 0**. Přesné časy runneru/testů jsou v JSON/JUnit. CPython 3.12.15, NumPy 2.5.4, izolovaná existující `.venv`, Windows 11. Checkout při původním běhu měl parent HEAD `f9507e325c479c8b703e7f52c410de6847958720`; **nejde o commit obsahující tento dosud necommitnutý spike**. Přesný zdroj běhu identifikují SHA-256 skriptu a testů v `source_files_sha256` a kontrolním manifestu. Integrační owner po přenosu do návrhové větve připne vlastní CODE SHA a experimenty znovu spustí. Spike má vlastní testy, neimportuje produkční `domain` ani starý unfolder a nemění jejich výsledky.

- [Spustitelný spike](../../../tools/spikes/p2_v12_geometry.py), [analytické a negativní testy](../../../tests/spikes/test_p2_v12_geometry.py).
- [Úplné naměřené hodnoty](evidence/geometry-results.json), [JUnit](evidence/geometry-tests.xml), [kontrolní metadata a hashe](evidence/geometry-validation.json).
- [Schéma cílových footprintů chlopní](evidence/geometry-tab-footprints.svg). Obrázek ukazuje navržené polohy na víčku, nikoli důkaz jejich bezdeformačního sestavení.

Před předáním ke kandidátnímu review byly oba zdroje pouze zformátovány přes Ruff. Následně prošlo všech 40 testů i `ruff check`; všechna data pod `results` jsou přesně shodná s předchozím během. Původní surové výsledky, JUnit, metadata a SVG jsou zachované jako `evidence/geometry-preformat-*`. Aktuální JSON a kontrolní manifest nesou nové zdrojové hashe; numerické závěry a rozsah důkazů se nezměnily.

Jednotky experimentů jsou mm. Střešní fixture používá rozměry papírového modelu 1:100: 5 mm horizontálního přesahu odpovídá 500 model mm. Jeho 7.071067812 mm podél střechy odpovídá 707.1067812 model mm, ne dalším 500 mm.

## 1. Dva oblouky: rovinná oblast a prostorový ruled loft

Rovinný příklad: dvě půlkružnice se společným středem, poloměry 20 a 30 mm, ve stejné rovině. Hranici pásu tvoří oba oblouky a koncové radiální spojnice. Plocha je `π(30²−20²)/2 = 785.398163397 mm²`. Jde o rovinný materiálový region. Samotné dvě otevřené křivky nejsou uzavřená vystřihovaná oblast a nejsou automatickým důvodem k vyplnění jejich konvexního obalu.

Druhý příklad přesune větší půlkružnici do rovnoběžné roviny vzdálené 30 mm a výslovně spáruje stejné parametry. Vznikne část kuželové plochy. Její přesnost plyne z homotetie generujících profilů, ne ze stejného počtu vzorků. Vypočtený rozvin zachoval první fundamentální formu s normalizovanou numerickou odchylkou pod `2.1e-10` v příslušných fixturech.

**Dopad na návrh:** `Profile` má otevřený/uzavřený stav a skutečné orientované segmenty, `PlanarRegion` explicitní vnější/děrové trim smyčky. `RuledLoft` nese obě profilové reference, jejich umístění a korespondenci. Přepnutí rovinného pásu na prostorový loft je významová konstrukční operace; nelze je rozlišovat pouze vzhledem výsledného meshe.

## 2. Přesné rodiny, regularita a odmítnutí

Pro ruled parametrizaci `S(u,v)=C0(u)+v·d(u)`, `d=C1(phi(u))−C0(u)`, platí na regulárním hladkém intervalu developability kritérium `D=det(C0',d,d')=0`. Nenulové `D` v jednom regulárním bodě je negativní důkaz; konečná sada nulových vzorků není globální pozitivní důkaz. Tento základ odpovídá [primárnímu autorskému modelu developable surfaces](https://encov.ip.uca.fr/publications/pubfiles/2013_Perriollat_etal_CAVW_developable.pdf) a [univerzitnímu výkladu diferenciální geometrie, kap. 20](https://www.cis.upenn.edu/~cis6100/gma-v2-chap20.pdf). Následující konkrétní orákula a meze jsou vlastní odvození tohoto spiku.

Z druhé fundamentální formy ruled plochy vychází `K = −D² / ||S_u × d||⁴`. Ve spiku se měří jak normalizované `|D|/(||C0'||·||d||·||d'||)`, tak Jacobian a záporná Gaussova křivost. Při konstantním `d` je normalizátor nulový, ale `D=0` analyticky; není to důvod k dělení nulou. Nulový Jacobian označuje degeneraci, nikoli úspěšnou rovinnou plochu.

| Rodina a podmínky | Důkazový status | Naměřená kontrola |
|---|---|---|
| Rovinný region | Přesná projekce do ortonormální báze; samostatně ověřit trim a materiál | Půlkruhový pás 785.398163397 mm² |
| Normálová extruze `C1=C0+[0,0,H]`, H>0 | `d'=0`; přesný zobecněný válcový rozvin `[arclength(C0), Hv]` | Gotický profil má správnou analytickou délku dvou kruhových oblouků; žádné vyhlazení vrcholu |
| Homotetie `C1=k·C0+[0,0,H]`, k>0, H>0 | `d'=(k−1)C0'`, tedy D identicky 0 na každém hladkém intervalu | Kruhový, eliptický a gotický profil: reziduum D do 2.56e-16; metrická kontrola do 2.10e-10 |
| Totéž s pootočením korespondence o 25° | NONDEVELOPABLE, ne „jiný přesný kužel“ | Normalizované D přibližně 0.688; záporné K u všech tří profilových fixturech |
| Gotika a jiná gotika: půlšířka/výška 20/30 proti 18/25, hloubka 10 | Nehomotetický příklad NONDEVELOPABLE | Reziduum 0.349970; minimum K −4.4334e-5 mm⁻² |
| Shodné křivky bez hloubky i měřítkového rozdílu | DEGENERATE_OR_SINGULAR | Nulový ruling/Jacobian, přesný režim odmítnut |
| Nulové vzorky mimo prokázaný identitní klíč rodiny | UNPROVEN | Samostatný test brání povýšení screeningu na důkaz |

Homotetický rozvin se zde skutečně počítá: vrchol kužele `A=[0,0,−H/(k−1)]`, `w=C0−A`, `rho=||w||`, `theta'=||w×w'||/rho²`. Bod rozvinu má poloměr `(1+v(k−1))rho` a úhel `∫theta' du`. Numerická kvadratura je po hladkých intervalech; její reportovaná poziční chyba ve fixturech nepřesáhla `2.3e-11 mm`. Není to certifikace libovolné Bézierovy křivky bez regularity a intervalových mezí.

Pro tyto profily v rovině z=0 máme analytickou regularitu: `||S_u×d|| ≥ min(1,k)·H·min||C0'|| > 0`. U kružnice a elipsy `min||C0'||=π·min(a,b)`; u definované gotiky jde o konstantní rychlost kruhového segmentu. Důkaz platí na otevřených hladkých úsecích, v v∈[0,1]. Gotika má u=0.5 skutečný C0 roh s různými jednostrannými tečnami: dvě patche, jejich společný ruling jako výslovný přehyb. Nesmí se prezentovat jako hladká plocha přes vrchol.

**Dopad na certifikát:** uložit důkazovou rodinu, přesnou oblast parametrů/trim, singularity, hranice hladkých intervalů, analytickou identitu a regularitu zvlášť od numerických reziduí a vzorkování. Obecná či nevyřešená korespondence zůstane `UNRESOLVED`; solver musí zohlednit také `phi'`. Změna profilu, jeho rozdělení, seam startu nebo korespondence invaliduje certifikát a reference vyžadují intervalovou lineage.

## 3. Válec, kužel a téměř válcový limit

| Fixture | Nezávislé očekávání a výsledek |
|---|---|
| Válec r=10, h=30 | Obdélník 20π × 30 mm, plocha 600π mm² |
| Kuželový pás r0=10, r1=20, s=30 | Mezikruhová výseč R0=30, R1=60, úhel 2π/3; oblouky 20π a 40π, radiální strany 30, plocha 900π |
| Celý kužel r0=0, r1=20, s=30 | Výseč R=30, úhel 4π/3, plocha 600π; singularita vrcholu výslovně na hranici |
| r0=r1=10 | Samostatná stabilní válcová větev; žádné dělení nulovým rozdílem poloměrů |
| r1=10+1e-14 | Odvozené poloměry řádu 2.8e16 mm; stabilní lokální výpočet dává koncový bod [62.83185307179593,29.99999999999993] mm |

Téměř válcový rozvin nesmí vzniknout odečtením dvou obřích blízkých souřadnic. Spike používá lokální výraz `x=(R+q)sin(theta)`, `y=q−2(R+q)sin²(theta/2)`, kde q je přímo radiální offset s·v. I při velkém R zůstává fyzická šířka s samostatným číslem. Případný přechod na přibližný válec musí mít vlastní chybu; není dovoleno tiše přepsat dva různé poloměry na stejné. Výstupní SVG/PDF reprezentaci extrémně malého úhlu tento spike necertifikuje.

Negativní testy odmítají neplatné poloměry, oba nulové poloměry, NaN, s≤|r1−r0| a parametry mimo trim. Lichoběžník se správnou plochou není kuželový rozvin; starý algoritmus se nepřebírá.

## 4. Pootočený loft a poctivě měřená aproximace

Příklad: půlkruhové profily r=20, druhý násobený 1.2, hloubka 30, korespondence pootočená o 30°. Uzavřený analytický výraz pro parametr u∈[0,1] je `D=−H·k·r²·π²·sin(30°) = −71061.15168784338`; numerika dává −71061.15168784336. Přesný režim se odmítá ještě před triangulací.

Odvozená varianta rozdělí parametrickou oblast na ploché trojúhelníky. Toto jsou **oddělené triangle islands s explicitními řezy**, nikoli hotový praktický autorský pattern. Každý plochý triangle lze přesně rozvinout pro tuto segmentovanou variantu; původní hladká plocha tím přesná není.

| u×v segmentů | Triangles | Max. vzorkovaná vzdálenost mm | Analytická globální horní mez mm | Max. vzorkovaná změna normály | Zkrácení přední profilové hranice mm |
|---|---:|---:|---:|---:|---:|
| 8×2 | 32 | 0.283866 | 1.052944 | 10.2300° | 0.402950 |
| 16×4 | 128 | 0.076609 | 0.263236 | 5.1364° | 0.100883 |
| 32×8 | 512 | 0.019860 | 0.065809 | 2.5722° | 0.025230 |
| 64×16 | 2048 | 0.005054 | 0.016452 | 1.2869° | 0.006308 |
| 128×32 | 8192 | 0.001274 | 0.004113 | 0.6436° | 0.001577 |

Vzdálenost i normály se vzorkují v pěti místech každé buňky, nejen ve vrcholech. Vzorkované maximum **není globální garance**. Příklad 64×16 je záměrný negativní případ: vzorky jsou pod 0.01 mm, ale prokázaná horní mez nikoli.

Pro tuto konkrétní analytickou kruhovou rodinu je navíc skutečná konzervativní globální mez ve stejných parametrech:

`error ≤ Muu·Δu²/8 + Muv·Δu·Δv/4`, kde `Muu=π²r·max(1,k)`, `Muv=πr·sqrt(k²+1−2k cos(twist))`.

První člen ohraničuje lineární aproximaci hladké křivky v u. Druhý ohraničuje rozdíl bilineární buňky a její lineární triangulace. Mez platí pro celou tuto parametrickou oblast v přesné aritmetice; nejde o odhad odvozený z naměřených vzorků. Pro libovolný gotický/Bézierův loft ji bez nových derivativních mezí přenést nelze. Pro normálovou odchylku zde globální mez doložená není.

Hladká plocha má numericky integrovanou plochu 2048.827645916 mm². U 128×32 je mesh plocha menší o 0.010728639 mm². Zvolený error budget proto musí rozlišovat polohovou odchylku, délky, plochu a normály; jedna zelená vzdálenost nesplňuje automaticky ostatní požadavky. Kvadratura i sampled normal metrics mají v JSON popsanou metodu.

**Dopad na návrh:** zachovat cílový loft; z aproximace vytvořit samostatnou odvozenou variantu s lineage, uživatelským budgetem a fyzickou seam/crease politikou. Certifikát odlišuje `sampled_max` a `analytic_upper_bound`, jednotky model/paper a nepokryté metriky. Tisíce oddělených triangles nejsou produktově použitelné řešení B/D; je to důkaz nutnosti řízené segmentace a náhledu nákladů před vytvořením varianty.

## 5. Stěna připojená dovnitř přesahující střechy

Stěna je samostatná otevřená plocha: x=0…100, y=0, z=0…40. Její horní hrana leží v rovině střechy se sklonem 45°. Střecha pokračuje ke štítům do x=−3…103 a k okapu do y=−5, z=35. Parametrizace používá origin `O=[−3,−5,35]`, jednotkové osy `U=[1,0,0]`, `V=[0,1/√2,1/√2]` a materiálový trim `u∈[0,106]`, `v∈[0,35√2]`.

Horní hrana stěny má v této ploše **vnitřní UV stopu** `[(3,5√2),(103,5√2)]`. Vyhodnocení mapy do 3D vrací přesně `[0,0,40]…[100,0,40]`, s numerickým kontaktním gapem pod 1e-10 mm. Vzdálenost od skutečné okapové vnější hrany je 5√2 mm, tedy nejde o totožné hrany. Střecha má stále stejný přesah i trim obrys.

Přijímající footprint chlopně široké 5 mm v kladném V má skutečně 100×5=500 mm² krytých materiálem podhledu. Šířka 50 mm se nevejde: kryto je jen `100·30√2 = 4242.640687 mm²` z nominálních 5000. Posun stěny o 1 mm po normále střechy má gap přesně 1 mm; jeho projekce do správného UV regionu **není kontakt** a dostupná lepicí plocha se označí nulou.

Změna horizontálního přesahu 5→8 mm změní UV souřadnice stopy, avšak její vyhodnocené světové body zůstanou na původní horní hraně stěny. Vnitřní stopa tedy není náhodně uložené konstantní UV nebo mesh edge. Má sémantickou/provenance vazbu a při úpravě parametrizace se znovu vyhodnotí či vyžádá opravu.

**Dopad na návrh:** `SurfaceTrace` odkazuje na UV křivku, interval, stranu a revision dependency. `Attachment` nevyžaduje druhou boundary edge. `Connector` je samostatný materiálový prvek; jeho footprint se převede do přijímající plochy a odečte se neexistující materiál, otvory a omezení regionu. T-junction sestavy nesmí automaticky znamenat non-manifold materiál nebo vynucený společný přehyb jednoho listu.

## 6. Základna a vnitřní lepicí region

Nezávislá základna má obrys [−10,110]×[−10,70]. Budova bez dna se osazuje půdorysem [0,100]×[0,60]. Její spodní stěnová hrana se vyhodnotí do vnitřní UV stopy základny; maximální 3D gap je 0. Není přidána podlaha a připojovací stopa není řez.

Čtyři výslovné obdélníkové lepicí footprinty šířky 5 mm mají celkem 1600 mm². Spike skutečně provádí polygonové průniky s materiálem a s otvorem [40,60]×[−5,5]: odečte 100 mm² a zbývá 1500 mm². Otvor přeruší také 20 mm zdrojového kontaktního intervalu. To je negativní případ neúplné materiálové podpory, ne úspěšný „celý spoj“ pouze proto, že základní roviny mají nulový gap.

**Dopad na návrh:** assembly datum, základna, výšková úroveň, skutečný materiál a lepicí region jsou různé entity. Hranice přijímajícího regionu nesmí bez autorského příkazu vytvořit CUT. Otvory se odečítají před výpočtem kontaktu a vyžadují opravu/dělení dotčené chlopně, ne skryté přemostění nebo automatické uzavření budovy.

## 7. Stočený válec a dělené trojúhelníkové chlopně

Válcový plášť r=20 mm se rozvine přesně. Chlopně kolem jeho kruhového horního okraje jsou jiný geometrický problém: přímá základna v plochém válcovém rozvinu se po stočení změní v oblouk. Její další přehnutí na ploché víčko není automaticky rigidní otáčení kolem přímky. Dělení a mezery chybu zmenšují, neodstraňují ji matematicky.

Fixture má gap 0.8 mm po obvodu, trojúhelníkovou chlopeň šířky 5 mm a ilustrativní nelepenou ohybovou zónu 0.5 mm. Poloměr cílového víčka je také 20 mm. Report rozlišuje plochý výřez, cílový footprint, deformaci a fyzicky zatím neověřenou pružnost.

| Počet | Délka základny po oblouku mm | Rozdíl oblouk–tětiva mm | Sagitta hinge mm | Změna boční délky potřebná k cílovému footprintu mm | Nominální kontakt po odečtení bend zóny mm² / tab |
|---:|---:|---:|---:|---:|---:|
| 12 | 9.671976 | 0.093973 | 0.581826 | 0.440326 | 16.640620 |
| 24 | 4.435988 | 0.009087 | 0.122861 | 0.113955 | 8.695314 |
| 48 | 1.817994 | 0.000626 | 0.020653 | 0.020375 | 3.661591 |

Všechny tři cílové footprintové sady mají nulový plošný průnik nad 1e-8 mm². Avšak při šířce 25 mm zasahují záložky přes střed a vzniká **276 kolidujících párů**, největší průnik 5.586242 mm². Chlopeň šířky 45 mm zasáhne i mimo víčko; samostatný test ořízne kontakt skutečným materiálem. Pro tuto kruhovou ořezávací aproximaci je doložená plošná mez inscribed 1024-gonu pod 0.01 mm² na jednu záložku.

Ohyb 80° místo 90° dává u ideálního rovného hinge tip gap `5 sin(10°)=0.868241 mm`. Jen přibližně 22.2 % cílové trojúhelníkové oblasti by leželo v ilustrativním 0.1mm kontaktním pásu před odečtením relief zóny. Ani velká 2D překrytá oblast proto nezaručuje skutečný 3D kontakt.

Spikové prahy 0.2 mm pro bend clearance a 8 mm² kontaktu ukazují tradeoff: 12 záložek nesplní první, 48 druhý, 24 oba. **Nejsou to přijaté produktové ani materiálové tolerance.** Už 24 záložek vyžaduje boční deformaci přibližně 0.114 mm; nelze je označit za přesně bezdeformační spoj pouze podle chyby oblouk–tětiva 0.009 mm. Dostupná lepicí plocha je zde nominální cílový footprint za předpokladu dosažené montážní polohy, nikoli změřená pevnost nebo certifikovaná fyzická plocha kontaktu.

**Dopad na návrh:** per-tab ID, zdrojový interval a skutečný hinge typ (hladký oblouk versus aproximovaná přímá úsečka), gap, outline, bend/relief, owner i příjemce se ukládají. Délkové mismatch, sagitta, kontaktní gap, plocha a kolize mají samostatná měřítka. Přesný certifikát válcového pláště se nepřenáší na konektor. Materiálová vůle bez měření zůstává `MATERIAL_CLEARANCE_UNVERIFIED`; další krok je výtisk a skutečné zkoušky ohybu/lepení.

## Co musí být v návrhu před freeze a co tento spike nedokazuje

1. Autoritativní křivky a odpovídající body, ne pouze triangle soup. Samostatná source/trim/correspondence identita a intervalová lineage.
2. Přesný rozvin pouze pro prokázanou rodinu a regulární intervaly; gotické rohy a apex nejsou hladké vnitřní body. Screening nulových vzorků zůstává nejistotou.
3. Assembly kontakt přes boundary, UV stopu nebo materiálový region; žádná falešná hrana kvůli přesahu nebo základně.
4. Konektory s vlastní geometrií, specifickým certifikátem a skutečným příjemcem. Cílový footprint, dosažený 3D kontakt a fyzická pevnost jsou různé důkazy.
5. Aproximační varianta uchová cíl, error budget, cuts/creases a report sampled versus prokázaných mezí. Přesný rozvin odvozených facets není přesný rozvin původní hladké plochy.

Spiky neřeší obecné samo-průsečíky všech možných křivek, certifikaci libovolného Bézier loftu, úplnou intervalovou aritmetiku, net optimalizaci nebo prakticky slepitelnou segmentaci tisíců triangles. Nedodávají UI průchod A/B/C/D, nový writer, interoperability proof ani fyzickou stavbu. Tyto důkazy musejí vzniknout v přijatých vertikálních řezech. Dosavadní pracovní kód a evidence zůstaly zachované; návrh již nesmí být stabilizován jako house-only doména.
