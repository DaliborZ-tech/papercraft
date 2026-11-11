# PC-008 — nezávislé review segmentace zakřivených zdrojů

Reviewer `/root/authoring_independent_review`, 11.11.2026; není autorem nového helperu, LINE implementace, D domény ani jejich oprav. Přesný source **`3a0355f42a6ef5bc710ce3bd85c6280bf7cf39fe`**, worktree `papercraft-segmentation-curves`.

**Verdikt: APPROVED_IN_CURVED_SEGMENTATION_MATH_COMPONENT_SCOPE.** Nebyl nalezen otevřený zásadní matematický nález. Schválená je ohraničená lokální aproximace původního zdroje a uvedené regionální důkazy; ne celé D/PC-008/P2, global embedding, area distortion, praktická montáž, persistence/lineage/UI nebo výrobní soubory. Výsledek CERTIFIED je výhradně v režimu APPROXIMATE, nikdy oprávnění označit původní hladký cíl EXACT.

## Přesný zdroj a skutečné běhy

[Git archiv/bytes](evidence/pc008-segmentation-curves-review-source.json), [skutečné importy a hashe](evidence/pc008-segmentation-curves-review-imports.json). Python importoval helper, dispatch i matematické závislosti z izolovaného archivu tohoto pinu, nikoli z jiného editable checkoutu. Produkční zdroje reviewer neměnil.

Nezávisle **61 autorových LINE/curved regresí PASS/16.77s**, [JUnit](evidence/pc008-segmentation-curves-review-author-3a0.xml), a Ruff4 dotčených source/test souborů PASS. Vlastní [skript](evidence/pc008-segmentation-curves-review-own.py) má rozhodný [31PASS/6.22s](evidence/pc008-segmentation-curves-review-own-3a0-final.xml); před rozšířením [26PASS/5.30s](evidence/pc008-segmentation-curves-review-own-3a0.xml). Nejde o další unikátní součet k autorově celkové sadě, full application testy nebyly opakovány.

Samostatný [audit historického LINE fixture](evidence/pc008-segmentation-curves-review-line-preservation.json) potvrzuje shodné původní Git bytes před/po3a0. Nový test zároveň porovnal celý skutečný LINE výsledek s historickým payloadem. Dříve platný test „curves unsupported“ je změněným autorizovaným rozsahem překonaný; nová podporovaná curved cesta zůstává APPROXIMATE a má vlastní pozitivní celointervalový důkaz i zachované hard-budget negativy. Toto review nepřepisuje původní LINE report či jeho historické stavy.

## Nezávislý matematický rozbor

### Celá plocha a skutečné dodané vrcholy

Pro `F(u,v)=(1−v)C0(u)+vC1(u)` se nejprve porovná F s bilineárním interpolantem jeho čtyř analytických rohů. Chyba lineární interpolace každé source křivky v témže u je nejvýše `sup|C''|*hu²/8`; v-konvexní kombinace zachová maximum obou source mezí. Smíšený rozdíl rohů je integrál `F_uv=C1'−C0'` přes celou buňku. Při rozdělení po společné diagonále má rozdíl bilineárního interpolantu od každého affine triangle faktor `s*(1−t)` nebo `t*(1−s)` na jeho příslušném parametrickém trojúhelníku, maximum1/4. Proto `Muu*hu²/8+Muv*hu*hv/4` skutečně kryje celé vnitřky, nikoli pouze uzly či střed.

K tomu se přičítá největší odchylka skutečně vráceného float vrcholu od analytického source enclosure. Barycentrické váhy affine triangle jsou nezáporné a mají součet1, takže maximum stačí nad celou plochou. `_Patch.node` čte vlastní float zpět jako Fraction; neodvozuje přesnost z rendereru/writeru. Model a paper mm zůstávají oddělené a scale se aplikuje právě jednou. Výstupní hard bound je součet tří veličin, ne maximum jejich hodnot.

### Skutečné restrikce a orientace

LINE/CUBIC používají přesné racionální world controls a de Casteljau restrikci na každou skutečnou dílčí u buňku. Derivace jsou vůči původnímu source parametru; orientovaný interval přidá správný faktor změny parametru do prvního a druhého řádu. Nezměněná pozitivní base metrika světové roviny je používána jako dodaná binární báze, nikoli idealizovaná jednotková projekce.

ARC používá původní center/start/signed sweep, racionální π a dříve přezkoumané Taylorovy sin/cos intervaly. Reverse přemapuje skutečný parametr; nevyrobí nový oblouk z přibližného stored end. Analytický endpoint limit a uložený roh jsou uzavřeně zahrnuty do value bounds, Sv/Jacobianu, skutečné vertex rezervy i délkového endpoint reserve. Derivace/normály jsou po jednotlivých hladkých patch intervalech a jejich jednostranných koncích; neslibuje se hladká normála přes gotický roh nebo přes případný stored endpoint rozpor.

### Regional regularity a normal-angle

Intervalové `Su=(1−v)C0'+vC1'`, `Sv=C1−C0` kryjí celou buňku. Pro skutečný binary triangle plane K se prokazuje kladný dolní bound `d=lower((Su×Sv)·K)`. Potom `|J|≥d/upper|K|>0` nad celou buňkou. Kladný dot navíc vylučuje obrat normály; `atan(upper|J×K|/d)` je bezpečný horní úhel. π, atan a sqrt mají vnější racionální intervaly, nikoli libm vzorky. Omezení výsledku na90° je při prokázaném kladném dot bezpečné.

Neprokázaná pozitivita nutí zjemnění nebo UNRESOLVED. To se nesmí nahradit testem pouze nad dyadickými vrcholy. Vnější výstupní float směry byly zkontrolovány i proti přesným string mezím; paper Jacobian má jednotky mm²/UV a scale². Číselné enclosure se nezaměňují za skutečný velikostní/distance hard limit.

### Délky skutečných source cest

Hrana má původní parametrickou cestu `(u(t),v(t))`; její derivace je `du*Su+dv*Sv`. Čtyři uzavřené subintervaly normy této derivace dávají integrální dolní/horní mez. Chord zpřesňuje pouze dolní mez; není dosazen jako očekávaná source délka. Actual delivered binary edge norm a endpoint consistency reserve jsou samostatné.

U ARC hranic je rychlost ohraničena přes vlastní Gram matici skutečných world A/B vektorů: eigenvalue lower používá horní discriminant root, eigenvalue upper také horní root. Po vnější sqrt a násobení skutečným sweepem to zahrnuje i povolenou neideální float bázi. Boundary součty jsou přes všechny hrany, ne maximum lokálního rozdílu. Tyto délky jsou délky stejných UV cest, **ne geodetiky** a ne certifikát zachování celé intrinsic metriky.

## Vlastní nezávislá orákula

- **Parabola a celý triangle:** `C0=(6u,6u²,0), C1=(6u,6u²,5)`. Pro každé u pásmo má affine interpolation přesnou chybu `6(u−u0)(u−u1)`, tedy celé maximum `3hu²/2`. Forward i reverse endpoints a všechny vrcholy byly porovnány racionálně. Celý source obvod má nezávislý90digit interval `6√5+3ln(2+√5)+10`; obsahují jej skutečné source length meze.
- **Skutečně nerozvinutelný dvou-C fixture:** `C0=(6u,6u²,0), C1=(9u,3u²+3u³,5)` má v u=1/2 exact triple determinant225/2. Vlastní J je explicitní polynomial `(60u−30uv+45u²v,−30−15v,−54u²+18u³+9u²v−18u³v)`. Reviewer jej nezávisle převedl do přesných restricted Bernstein controls na každé actual cell a obou v koncích. Minimum všech dot(K) controls je kladné; convex hull poskytuje vlastní whole-cell cross norm horní mez. Vlastní240bit integer-isqrt a samostatný90digit Taylor tan lower potvrdily každou publikovanou regional regularity i normal-angle mez. Toto je vlastní pozitivní důkaz nad celou buňkou, nikoli převzatý interval helper ani pouze vzorky. Racionální barycentrické sanity checks jsou navíc, nejsou vydávané za celý důkaz. [Úplný raw příklad](evidence/pc008-segmentation-curves-review-polynomial-report.json):16 triangle islands, hard bound≈0.2158852160mm≤0.25mm, regional regularity>29.373 paper mm²/UV.
- **Skutečná kruhová metrika:** quarter circle r4,H6 má obvod `4π*q+12` pro dodané U,V zvětšené faktorem q. Případy q=1 a1±2^-42, v obou orientacích, použily vlastní100digit π interval. Výsledky při q≠1 výslovně vylučují idealizovanou unit-basis délku. Celá source normal cone má přesnou krajní úhlovou odchylku `45hu` stupňů od skutečného chord plane; report ji pokrývá. Source druhá derivace musí pokrýt `q*π²`, nikoli nulový chord residual.
- **Dílčí source intervaly:** vlastní extrema hodnoty, první i druhé derivace paraboly nad[1/5,4/5] jsou obsaženy v exact native source bounds při forward/reverse. Veřejná partial correspondence zůstává nepodporovaná a vrací UNRESOLVED; interní restrikce neslouží jako falešné schválení nového trim API.
- **Nondyadické kolapsy:** vlastní kubika `x=25u³−30u²+12u` má `x'=3(5u−2)²` a singularitu v u=2/5. Arc pár r4/r10 v opačných osách má faktor `1−3.5v` a kolaps v v=2/7. Ani jeden není dyadický vertex; oba při velkém position budgetu bezpečně skončí UNRESOLVED bez triangle/edge payloadu.
- **Stored endpoint gap:** velmi malý .01° source arc s endpoint rozdílem≈9e−8 má explicitní vertex rezervu. S odpovídajícím loose budgetem vznikne APPROXIMATE varianta; tight1e−9mm se odmítne, i když samotný analytický curvature term je menší. Rozpor není vydáván za exact endpoint identity.
- **Jednotky, float a limity:** scale1/8 mění position jednou, Jacobian scale², ponechá stejnou skutečnou modelovou síť při úměrném autorově budgetu. Cell/depth cap, podlimitní1e−25 budget, boolean vstupy, source origin2^60 s nedostatečnou float přesností, missing/duplicate/partial refs a kolidující profile identity nedostávají částečný pozitivní výsledek. Parametrické triangle areas mají kladnou orientaci a celkový součet1; vrácený report lze změnit bez zásahu do příštího výsledku/source.

Autorových61 testů navíc skutečně zopakovalo nonhomothetic gotiku20/30→18/25,H10 při hard budgetu0.25, XY/XZ/model100×scale0.01, twist25°, všechny LINE/ARC/CUBIC kombinace a jeho u=1/3,v=5/12 negativy. Vlastní31 nejsou kopiemi všech těchto fixtureů; doplňují jiná matematická očekávání a independent whole-cell metodu.

## Přesné meze schválení a navazující práce

Návratová pole pravdivě uvádějí `global_embedding=NOT_CHECKED` a `source_area_distortion=NOT_CERTIFIED_BY_THIS_COMPONENT`. Lokální regularita nevylučuje vzdálený samoprůnik, překryv jiného patch nebo kolizi při montáži. Zdejší interval obvodu také může být konzervativně široký: vlastní fixture uvádí boundary difference bound≈0.266mm. To není tvrzení, že původní target splnil .01mm exact-mode metriku; hard limit tohoto APPROXIMATE řezu je samostatná odchylka celé plochy0.25mm. Normativní přesnost později vydaných rovinných dílů a SVG/PDF tím není zvětšená.

Veřejný scope je úplná explicitně orientovaná source segment coverage právě jednou. Výsledkové indexy jsou lokální, nikoli persistentní UUID; samostatný domain autor musí navázat skutečné variant/feature IDs a source digest/revisions, zachovat původní odmítnutý cíl a správně invalidovat po změně zdroje. Potřebuje rovněž embedding/material kontroly v požadovaném rozsahu, srozumitelné vyčíslení počtu dílů/švů a souhlas ke konkrétní odvozené variantě. **Toto review tyto čekající povinnosti neschvaluje ani nezakrývá výsledkem CERTIFIED helperu.**

Skutečně načtené skills: konstrukce zachovala source rohy/otevřený plášť a materiálový smysl jednotlivých dílů; verification vyžadovalo nezávislé celé integrály/hulls a singularity mimo vzorky; UI/delivery odlišují numerický certifikát od autorského preview, editace, opravy a předání. [D akceptace](../v1.2/ACCEPTANCE.md) vyžaduje přijetí konkrétního náhledu, save/reopen, manual layout a oba vektorové výstupy; ty zde nejsou provedené. UI/QTest, OS desktop, nový člověk a fyzický model nebyly spuštěny. Novice0/NOT_RUN a P3 zůstávají beze změny; scope celého A/B/C/D ani AU19 není zúžený.
