# B3/D — celointervalová segmentace zakřivených zdrojů

11. 11. 2026. Autor `geometry_analysis`, izolovaný worktree
`papercraft-segmentation-curves`, větev `revival/p2-segmentation-curves`, základ
`62248d7013ad6e2d3a9082bdc367a3bb7f940914`. Základ není pin nového kódu;
rozhodný je nový commit obsahující tento report a uvedené hashe skutečně
spuštěných souborů. Nezávislá revize tohoto přírůstku čeká na jiného agenta.

Veřejné API `segment_ruled_loft(...)` zůstává. LINE/LINE pokračuje původní,
nezměněnou numerickou cestou; test porovnává **celý** výstup s historickým raw
fixturem. ARC/CUBIC/LINE kombinace používají samostatný intervalový helper.
Výstup je pouze `CERTIFIED + APPROXIMATE` nebo `UNRESOLVED` bez částečné sítě.
Původní cíl nezíská EXACT ani tehdy, když je sám rozvinutelný. Autorita jsou
původní profily, jejich skutečné světové roviny a explicitní orientovaná
korespondence; nevytváří se aplikací vydávané UUID pro vzorek.

## Důkaz nad celou plochou

Pro skutečný parametrický cíl `F=(1-v)C0(u)+v*C1(u)` a buňku `hu×hv`:

1. V každé zdrojové křivce má lineární interpolace v témže u chybu nejvýše
   `sup|C''| hu²/8`. Konvexní kombinace v∈[0,1] dává pro bilineární interpolant
   `B` mez `|F-B|≤Muu hu²/8`, kde Muu pokrývá obě skutečné druhé derivace.
2. Smíšený rozdíl čtyř analytických rohů B je dvojitý integrál `F_uv=C1'-C0'`,
   tedy má normu nejvýše `Muv hu hv`. Rozdíl B od jeho dvou trojúhelníků má
   faktor `s(t-1)` nebo `t(s-1)` a absolutní maximum1/4. Proto
   `|B-T|≤Muv hu hv/4` v **celé** příslušné parametrické trojúhelníkové oblasti.
3. Připočítává se největší skutečná chyba dodaných vrcholů proti zdrojovým
   intervalům. Barycentrické koeficienty jsou nezáporné a dávají součet1.

Celkový hard bound je součet všech tří členů, nikoli maximum nebo vzorkované
reziduum. Report odděluje model mm od paper mm a aplikuje tiskový scale jednou.
Veřejné přesné meze se zaokrouhlují ven na racionální mřížku1e-24 příslušné
jednotky. Float meze jsou také vnější.

LINE/CUBIC zdroje používají přesné racionální světové Bernsteinovy controls,
omezené de Casteljauem na skutečný dílčí u interval každé buňky. ARC zdroje
používají skutečný center/start/signed sweep, racionální interval π a již
prokázané Taylorovy sin/cos intervaly z `loft_area.py`. Reverse mění původní
zdrojový parametr a derivaci; oblouk se nerekonstruuje z nepřesného koncového
bodu. Žádné epsilon-fitnutí na homotetii či konstantní rovinu.

Povolená malá nesrovnalost uloženého arc endpointu není přesná identita. Uzavřené
value intervaly obsahují analytický limit **i** skutečný uložený roh. Ten se
zachová ve výstupní hranici a jeho odchylka se zahrne do polohové rezervy,
Sv/Jacobianu i délkového endpoint reserve. Analytické tečny a normály se hodnotí
po hladkých patch intervalech s příslušnými jednostrannými konci; gotický roh
se nevyhlazuje. Skutečné float vrcholy se čtou zpět jako Fraction, takže
rezerva nezávisí na domnělé přesnosti writeru či rendereru.

## Regularita, normály a délky

Na celé buňce se intervalově ohraničí
`Su=(1-v)C0'+v*C1'`, `Sv=C1-C0`, `J=Su×Sv`. Pro normálu skutečně dodané
triangle plane K musí být prokázané `d=lower(J·K)>0`. Potom
`|J|≥d/upper|K|>0` a úhel je nejvýše
`atan(upper|J×K|/d)`. π/atan/sqrt jsou racionální vnější intervaly. Není-li
kladný dolní bound prokazatelný, kandidát se zjemní nebo skončí UNRESOLVED.
Nenulové normály ve všech dyadických uzlech nenahrazují tento důkaz.

Pro hranu ve zdrojovém parametrickém prostoru se integruje interval normy
`E'=du*Su+dv*Sv` přes čtyři celé podintervaly. Nezávislý chord interval
zpřesňuje dolní mez; skutečná dodaná float úsečka má vlastní interval délky.
Profilové ARC hranice navíc používají přesné Gram eigenvalue meze skutečných
světových A/B vektorů, nikoli domnělé ideální jednotkové osy. To dává těsnou
speed/length mez také po povolené float rotaci. Délkový report není geodetika,
obecný certifikát celé metriky ani hard prostorový distance budget.

## Spuštěná B3 varianta a negativní případy

Vlastní uzavřená gotika: poloviční šířka20, výška30 → nezávisle změněná
poloviční šířka18, výška25, hloubka10; dvě kruhové patche a rovná základna.
Zdrojový determinant v ručně vybraném bodě je nenulový; helper nic neodvozuje
ze své výsledné sítě.

| Veličina | Naměřený výsledek / prokázaná mez |
|---|---:|
| Autorův hard budget | 0.25 paper mm |
| Grid na patch | 16×1 |
| Patche / buňky / triangle islands | 3 /48 /96 |
| Párované řezy / vnější řezy | 96 /96 |
| Celoplošný horní bound | 0.1865948501209102 paper mm |
| Regionální normal-angle horní bound | 35.48826220500793° |
| Kladná Jacobian lower mez | >277.9786238014494 paper mm² / UV |
| Horní mez rozdílu celého obvodu | 0.033885436943237236 paper mm |
| Největší interní edge length bound | 0.5017700219909262 paper mm |
| Cold numerický běh | 1.32 s |

Interní délkový bound je konzervativní horní mez, ne naměřené maximum a ne
splnění distance limitu jinou veličinou. Stejný zdroj zvětšený100× v rovině XZ
při scale0.01 dává stejné96 díly a bound18.659485012091075 model mm /
0.18659485012091076 paper mm; následný běh0.65 s. Časy jsou lokální evidence,
nikoli obecná garance odezvy nebo UI důkaz.

Nezávislá očekávání pokrývají skutečnou půlkružnicovou sagittou, celý analytický
obvod `20π+60`, parabolickou kubiku s přesným `C''=(0,60,0)`, skutečné kubiky
třetího stupně, všechny kombinace LINE/ARC/CUBIC kromě již pokryté LINE/LINE,
ostré gotické patche, reverse, XY/XZ a skutečnou float bázi/posun. Nelineárně
parametrizovaná kolineární kubika nesmí dostat nulový same-parameter bound jen
proto, že geometricky leží na tětivě.

Dva záporné cíle mají singularitu mimo **každý** dyadický vertex:
`Cx=9u³-9u²+3u`, `Cx'=3(3u-1)²` kolabuje v u=1/3; planar arc halfturn
`S=(1-2.4v)C0` kolabuje v v=5/12. Oba zůstávají UNRESOLVED. Stejně tak
vyčerpaný cell/depth budget, ztráta float world přesnosti u1e20, kolidující
profile IDs a neúplná/duplicitní korespondence. Zpřísnění autorova limitu zvýší
počet dílů nebo bezpečně odmítne ověřenou variantu; nevymění původní cíl.

## Připnutí a ověření

Python3.12.15, skutečný import z
`C:\Users\dalib\projects\papercraft-segmentation-curves\src`:

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_segmented_loft.py tests/authoring/test_segmented_loft_curves.py -q
C:\Users\dalib\projects\papercraft\.venv\Scripts\ruff.exe check src/archpapercraft/authoring/segmented_loft.py src/archpapercraft/authoring/segmented_loft_curves.py tests/authoring/test_segmented_loft.py tests/authoring/test_segmented_loft_curves.py
git diff --check
```

**61 PASS /17.79 s; Ruff a diff-check PASS.** Historická reviewerova numerická
LINE sada má14 PASS /1.07 s s výslovným `-k 'not curved_sources'`; dvě původní
negativní přejímky „curves unsupported“ jsou záměrně nahrazené novou podporou,
její pozitivní numerikou a zachovanou negativní hard-budget regresí. Reviewerův
soubor se neměnil. Jeho starý binding test zapisuje historický manifest;
po replay byly původní bytes manifestu obnoveny z tohoto základního commitu.
Žádná historická FAIL ani binding evidence není součástí změn.

SHA256 skutečně spuštěných souborů:

- `segmented_loft.py`: `2b44a56acdee4f796f0f76d97ee203d2634133099d069d1751a0b10f9e0da472`
- `segmented_loft_curves.py`: `81878c9075522f59b2050eb942e7fa227f9637895dd10458e2ca233cff91644d`
- `test_segmented_loft.py`: `fa5ed8644c10da78c89d48897b72cb17421fd28aecc53604ea680c7d98897406`
- `test_segmented_loft_curves.py`: `cd9c53945382ea048dcb93278b9414e852a1bcd3e5446207dded25017fd23bb2`

Skutečně načteny aktuální AGENTS a čtyři projektové skills. Konstrukční skill
se projevil zachováním skutečných source profilů/rohů a přiznanými náklady96
samostatných dílů; verification skill celointervalovým důkazem, nezávislou
analytikou a singularitami mimo vzorky; delivery/UI skill přesným rozlišením
čisté numeriky od autorské varianty a jejího předání.

Veřejný rozsah zůstává plné source segmenty právě jednou, s orientací [0,1]
nebo[1,0]. Omezení uvnitř adaptivních buněk jsou skutečné intervalové restrikce;
veřejný trim/partial correspondence kontrakt se tímto neotevírá. Globální
embedding/samoprůniky, odchylka plochy, praktické seskupení/švy, chlopně,
projektová persistence/lineage, UI/save/reopen/layout/SVG/PDF ani fyzická
sestavitelnost nejsou tímto komponentovým certifikátem schválené. Celý B3/D
průchod zůstává k ověření v navazující doméně a skutečné aplikaci.
