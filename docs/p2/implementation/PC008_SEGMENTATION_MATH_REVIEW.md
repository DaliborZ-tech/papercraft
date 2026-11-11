# Nezávislá revize matematické segmentace D

Reviewer `bend_adapter_review`, autor nové komponenty `geometry_analysis`, 9. 11. 2026. Exact source **`ad0cfa36559cc7c475e617c94dd04613d96d55f5`** ve worktree `papercraft-segmentation-math`. Předmětem je pouze nový `segmented_loft.py` a jeho kontrakt; reviewer je autorem dřívějšího loftového modulu a **tento vlastní modul zde nezávisle neschvaluje**. Jeho nezávislé revize patří jiným agentům.

**CHANGES_REQUIRED — SM01 MAJOR / OPEN: kolidující zdrojové reference.** V pokryté matematice odchylky, normál, délek a UV pokrytí nebyl nalezen další zásadní nález. Samotný tento report není dokončený řez D, doménová/persistenční integrace, použitelný autorský pattern ani fyzický proof.

## SM01 — dvě různé geometrie se shodným profile ID dostanou certifikát

Vstupní kontrakt vyžaduje explicitní zdrojové identity, ale nová komponenta nekontroluje, že `first.profile_id != second.profile_id`. Dva různé záznamy s rozdílným lokálním tvarem a prostorovou rovinou mohou uvést tutéž identitu. Výpočet vrátí `CERTIFIED`, zatímco `source.first_profile_id` a `source.second_profile_id` odkazují na jediný identifikátor, který nemůže současně označovat obě různé geometrie.

Vlastní reprodukce ponechá první přímku `(0,0)→(40,0)` v z=0 a druhou `(0,0)→(40,20)` v z=30; druhému profilu pouze nastaví identitu prvního. Výsledek je stále certifikovaných 64 trojúhelníků. Jde o vadu referenčního kontraktu, **nikoli prokázané podhodnocení matematické meze**. Integrační owner potvrdil, že odmítnutí kolidujících source refs patří do požadovaného rozsahu pure komponenty.

Požadovaná oprava: při validaci zdrojů odmítnout kolidující profile identity dříve, než vznikne kandidátní síť; vrátit `UNRESOLVED` s konkrétním důvodem a bez `triangles/edges`. Zachovat původní profily a jejich reference. Není potřeba vytvářet novou identitu nebo automaticky přepárovat zdroje.

[Samostatný vlastní test](evidence/pc008-segmentation-review-own.py), [raw rozšířené sady: 15 PASS / 1 FAIL / 1,07 s](evidence/pc008-segmentation-review-ad0cfa3-own-expanded.xml). Jediné produktové selhání je SM01; původní [14 PASS / 1 FAIL](evidence/pc008-segmentation-review-ad0cfa3-own.xml) zachováno. Zdrojový projekt ani produkční kód reviewer neměnil.

Po doplnění explicitního porovnání obou komplementárních UV polovin a formátování zůstává [finální samostatný běh 15 PASS / 1 FAIL](evidence/pc008-segmentation-review-ad0cfa3-final-own.xml); jediná chyba je stejný SM01.

## Nezávislé matematické očekávání

Vlastní očekávání vychází z **`S(u,v)=(40u,20uv,30v)`**, nikoli z produkčního evaluatoru. Jeho `B=(40,0,0)`, `C=(0,0,30)`, `D=(0,20,0)` dávají determinant `B·(C×D)=−24000`. Hladký cíl tedy není přesný rozvinutelný povrch. Nový výstup zůstává **APPROXIMATE** i pro nulovou odchylku u případné rovinné rodiny; certifikace segmentace z něj nesmí udělat EXACT původního cíle.

Pro normalizovanou dolní polovinu buňky `0≤y≤x≤1` je rozdíl bilineární funkce a jejího lineárního interpolantu `y(x−1)`; v horní polovině `0≤x≤y≤1` je `x(y−1)`. Absolutní hodnota je na **celém** příslušném trojúhelníku nejvýše `1/4`, neboť `t(1−t)≤1/4`. Proto poziční mez činí `|D| Δu Δv /4`, nikoli nulu naměřenou ve vrcholech. Pro síť `8×4` je to **`.15625 paper mm`** při zadaném rozpočtu `.25 mm`; report má 64 triangle islands, 84 párových řezných švů a 24 segmentů vnějšího řezu. Na hrubé jediné buňce je skutečná chyba ve středu diagonály 5 mm, přestože všechny vrcholy leží na cíli.

Reportované skutečné float vrcholy byly přečteny zpět jako přesné zlomky. U posunutého zdroje `(.1,.2,.3)` vlastní test odvodil ideální vrcholy přímo ze zdrojových souřadnic a bilineární formule, porovnal je s metadaty a ověřil, že každá skutečná vrcholová chyba leží v přičtené rezervě. Konvexní barycentrická kombinace těchto chyb nepřekročí jejich maximum, takže přičtení rezervy platí uvnitř celé dodané plochy. Hrubá síť s budgetem přesně 5 mm se kvůli skutečnému zaokrouhlení správně odmítne; limit se nezměkčuje.

Nezávislé Jacobian normály jsou `N=(600v,−1200,800u)`; skutečné globální minimum normy je 1200. Reportovaný konzervativní lower bound je přibližně **1190.733 paper mm²**, max normal-angle bound přibližně **8.56567°**. Reviewer rekonstruoval normály skutečných dodaných trojúhelníkových rovin z jejich float vrcholů jako přesné zlomky. Na každé celé buňce minimum kladného `N·K` nastává v rohu a maximum konvexního `|N×K|` je ohraničené rohy; z toho plyne celý-region úhel a kladná regularita. Vlastní test přímo ověřil nerovnost `regularity² |K|² ≤ min(N·K)²` a nezávislou číselnou hodnotu úhlu. Číselná kontrola úhlu sama není důkazem; důkazem je uvedená afinní/konvexní mez.

Zvláštní negativní zdroj `S=(40u(1−3v),0,30v)` má kolaps v `v=1/3`, který **nikdy není uzlem dyadické sítě**. Komponenta přesto zůstává UNRESOLVED a nepublikuje částečnou síť. Nulové vzorky ani nenulové vzorkované normály tu nejsou vydávané za důkaz regularity.

Zdrojová diagonála hrubé buňky je `(40t,20t²,30t)` s délkou `√4100/2 +31.25 asinh(.8)`. Nezávislé Decimal očekávání s 70 číslicemi leží v reportovaném chord/control-polygon intervalu a skutečné zkrácení proti dodané tětivě `√2900` je pokryté délkou mismatch. Komponenta pravdivě označuje tuto metriku jako délku téže parametrické cesty, **nikoli geodetickou vzdálenost**. Délková a poziční chyba mají oddělená pole.

## Pokrytí, reference a rozpočty

UV trojúhelníky mají přesné racionální vrcholy, kladnou orientaci a součet ploch 1 na patch; každá `8×4` buňka má právě obě komplementární poloviny. Každá hrana má jednu nebo dvě incidence a všechny tři strany každého trojúhelníku jsou pokryty právě jednou v evidenci. U dvou navazujících patchů byly explicitně ověřeny referencované segmenty a obrácené intervaly i obrácené pořadí zdrojů. Párované řezy mají shodné skutečné světové koncové body v opačném směru; sousednost se neodvozuje hledáním nejbližšího bodu.

Chybějící/duplicitní/částečné reference, jednostranně obrácený kolabující zdroj, vyčerpaný depth/cell budget a kolaps nezanechávají publikované `triangles/edges`; původní záznamy zůstávají beze změny. Oblouky a kubiky jsou explicitně UNRESOLVED a neobdrží domnělý certifikát lineární rodiny. Výpočetní rozpočty se netváří jako přesnost produktu: nesplněná tolerance vede k odmítnutí kandidáta, nikoli k částečnému nebo falešně přesnému výsledku.

Reviewer skutečně spustil také autorových [35 testů — PASS / 1,70 s](evidence/pc008-segmentation-review-ad0cfa3-original.xml). [Binding manifest](evidence/pc008-segmentation-review-ad0cfa3-binding.json) dokládá skutečnou cestu modulu a SHA256; [samostatný raw analytický fixture report](evidence/pc008-segmentation-review-ad0cfa3-fixture.json) zachovává numeriku/triangles/edge coverage. Jednorázový nepytest Python shell nejprve zjistil sdílenou editable instalaci bez tohoto modulu; následné explicitní `PYTHONPATH=worktree/src` a vlastní pytest import oracle svázaly reprodukci s požadovaným zdrojem. Toto není produktová regrese ani falešný PASS jiného checkoutu.

## Skills a nepokrytý produktový důkaz

Před prací skutečně načteny `AGENTS.md`, konstrukční, verification a delivery skills, dotčená AC-D/AU12/AU13, kontrakt, produktová analýza a spike D. Konstrukční skill: 64 samostatných trojúhelníků a 84 párových švů jsou náklady odvozené varianty, nikoli důkaz praktické slepitelnosti. Verification: explicitní důkaz celé vnitřní oblasti, skutečně zaokrouhlené vrcholy, kolaps mezi uzly a vlastní kolidující reference. Delivery: zásadní nález ihned předán ownerovi, původní FAIL evidence zachována a oprava vyžaduje nový exact-pin re-review.

Tento pure přírůstek **necertifikuje source area distortion, globální embedding/samoprůniky, persistentní feature lineage, doménovou integraci, UI, stránky, export nebo celé D**. Tyto meze jsou v jeho výstupu označené. APPROXIMATE geometrie nemění původní editovatelný cíl; způsob této produktové vazby musí ověřit následující doménový řez. Žádný nativní desktop nebyl použit. AC-US08: 0 účastníků / NOT_RUN; P3 fyzická sestavitelnost: NOT_RUN. Žádný commit, merge nebo změna produkce reviewera.

## Cílené přezkoušení SM01 — eeaf081

**APPROVED_IN_SCOPE — nová bounded LINE/LINE segmentační komponenta. SM01 CLOSED / VERIFIED.** Exact source **`eeaf08182977d89dac0a6a989a8a1076255d343e`**, SHA256 `86dd159ef96883dc0efaea5987bccbad9f3e70ebbcf2454c8ffff820ebf3916e`. Historický CHANGES_REQUIRED a negativní raw výše zůstávají pravdivé pro ad0cfa3 a nemažou se.

Reviewer zkontroloval přesný diff od původního review pinu: produkčně přibyla pouze čtyřřádková validace odlišných profile IDs před přípravou párování/kandidátů; matematické důkazy, chyby, UV/normal/length výpočet se nezměnily. Proto se neopakovala široká matematická sada. Samostatně znovu spuštěn původní vlastní SM01 negativ **beze změny očekávání** a autorova cílená regrese s kontrolou `examined_cells=0`, chybějících `triangles/edges`, nezměněných zdrojů a obnovení platné varianty po opravě reference: [2 PASS / 35 deselected / 0,82 s](evidence/pc008-segmentation-review-eeaf081-targeted.xml). Platný odlišně identifikovaný cíl má opět determinant −24000, 64 triangles a mez .15625 mm; kolidující reference se automaticky nepřejmenovává.

[Binding manifest](evidence/pc008-segmentation-review-eeaf081-binding.json) ověřuje skutečně importovanou cestu, exact pin a hash modulu. V pokrytém rozsahu nezůstává otevřený zásadní nález. Všechny výše uvedené meze zůstávají: **nejde o nezávislé schválení reviewerovy dřívější loftové matematiky ani source area/global embedding/domain/persistence/UI/layout/export nebo celého D**. Výstup cíle zůstává APPROXIMATE. Nativní desktop, nový člověk a fyzická stavba nebyly součástí této kontroly. Reviewer neměnil produkci, staging a neprovedl commit.
