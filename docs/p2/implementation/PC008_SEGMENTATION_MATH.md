# D — časný numerický přírůstek: ohraničená segmentace dvou úsečkových profilů

9. 11. 2026. Izolovaný worktree `papercraft-segmentation-math`, větev
`revival/p2-segmentation-math`, základ `a1cbf920397694f3b1d3e85a08052acdc3962a7b`.
Tento základ **není** SHA nového zdroje; rozhodný zdroj je commit obsahující tento
report a níže uvedené soubory. Autor neuděluje nezávislé schválení.

API `segment_ruled_loft(first, second, correspondences, *, scale,
max_deviation_mm=0.25, max_cells=4096, max_depth=16)` vrací oddělená JSON data.
Podporuje celé explicitně orientované LINE/LINE intervaly, otevřené i uzavřené
navazující profily. Výsledek je `CERTIFIED` + `mode=APPROXIMATE`, vždy pouze
segmentační komponenta. Původní cíl se nemění. ARC/C jsou konkrétně `UNRESOLVED`,
bez nedoloženého obecného triangulačního fallbacku.

## Důkaz a skutečný výsledek

Pro skutečné světové zdroje je `S=A+B*u+C*v+D*u*v`. V lokálních souřadnicích
buňky `(t,s)∈[0,1]²`, s diagonálou 00→11, je rozdíl mezi bilineární mapou
a rovinnou interpolací `D*du*dv*s*(t-1)` pro `s≤t` a
`D*du*dv*t*(s-1)` pro `t≤s`. Obě celé trojúhelníkové oblasti proto mají mez
`|D|*du*dv/4`, včetně diagonálního vnitřního maxima. Připočítává se skutečná
největší chyba zaokrouhlení jejich výstupních vrcholů. Nejde o vzorkované maximum.

Jacobian `N=B×C+u*(B×D)+v*(D×C)` je afinní. Pro normálu **dodané**, již
zaokrouhlené triangle plane `K` se na celé buňce prokáže `min(N·K)>0`.
Pak `|N|≥min(N·K)/|K|>0` a úhel je nejvýše
`atan(max|N×K|/min(N·K))`. Dot minima jsou v rozích; konvexita normy dává
rohovou horní mez čitatele. π/atan/sqrt mají racionální vnější intervaly.
Nelze-li prokázat kladnou regularitu, výpočet zjemňuje a při vyčerpání limitu
vrací `UNRESOLVED`, nikdy částečnou schválenou geometrii.

Každá zdrojová parametrická cesta podél hrany triangle je kvadratická Bézierova
křivka. Její tětiva a řídicí polygon nezávisle ohraničují délku. Report porovnává
tento interval se skutečnou dodanou úsečkou; jde o stejné parametrické cesty,
nikoli geodetiky nebo důkaz celé vnitřní metriky.

Povinný vlastní cíl je `S=(40u,20uv,30v)` v paper mm, scale1. Ručně
`C0'·(d×d')=-24000`, takže původní hladký cíl není přesně rozvinutelný.

| Veličina | Spuštěný výsledek |
|---|---:|
| Požadovaná celoplošná mez | 0.25 mm |
| Konformní dyadický grid | 8×4 |
| Prokázaná horní mez odchylky | 0.15625 mm |
| Prokázaná horní mez normálového úhlu | 8.565670155295003° |
| Regionální dolní mez Jacobianu | >1190.7334520564 paper mm² / jednotkovou UV plochu |
| Rovinné triangle islands / počet dílů | 64 |
| Párované řezové švy | 84 |
| Vnější řezové segmenty | 24 |
| Celkem vyráběných triangle řezových segmentů | 192 |
| Největší horní mez rozdílu délky hrany | 0.021487590879710347 mm |

Hrubá jediná buňka má ve všech vrcholech nulovou chybu, ale uprostřed diagonály
skutečnou chybu5 mm: `S=(20,5,15)`, triangle interpolace `(20,10,15)`.
Limit0.25 mm s max_cells1 nebo16 se proto bezpečně odmítne. Limit0.1 mm zvýší
počet dílů; neproveditelný limit zachová původní cíl a vrátí důvod.

## Ověření a meze

Spuštěno na vlastním `src`, Python3.12.15:

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_segmented_loft.py -q
C:\Users\dalib\projects\papercraft\.venv\Scripts\ruff.exe check src/archpapercraft/authoring/segmented_loft.py tests/authoring/test_segmented_loft.py
git diff --check
```

**35 PASS /1.63 s; Ruff a diff-check PASS.** Očekávání jsou analytický vlastní
bilineární cíl, jeho determinant, skutečný vnitřní svědek, nezávislá kvadratura
diagonální délky a přesná parametrická coverage. Negativní případy zahrnují
skutečný Jacobian collapse, vyčerpané limity, neúplnou/opačnou korespondenci,
neplatné vstupy, zakřivené zdroje a ztrátu světové přesnosti při posunu1e20.
Zkoušky ověřují i společný reverse, více patchů, deklarovaný uzavřený seam,
rigidní rotaci, měřítko, měřenou rezervu zaokrouhlení a neměnnost vstupů.

SHA256 kód: `09ca6001382d149fd4d336dac351139c3be5f41291ded9e43bde9b648bd814c3`.
SHA256 testy: `21fdc2ac35e6a38aaf58fda263e5dbc55436fadd0447e7dcf86c3800cd7f5048`.

Skutečně načteny čtyři projektové skills. Konstrukční rozhodnutí zachovává
otevřený zdroj a skutečné řezy; verification skill se uplatňuje svědkem uvnitř
plochy a regionálním důkazem namísto nulových vzorků. UI/delivery meze jsou
výslovné: tato komponenta nedodává autorský náhled, přijetí varianty, persistentní
UUID/lineage, ruční layout, praktické seskupení dílů, chlopně, save/reopen,
SVG/PDF, člověka ani fyzickou stavbu. Výstupní indexy jsou jen lokální lookup;
budoucí identity vycházejí ze source IDs, orientovaných intervalů a přesných UV.
Globální 3D samo-průsečíky a odchylka plochy nejsou tímto řezem certifikované.
Celé D / AC-AU12 zůstává k dodání ve skutečném autorském průchodu; triangle
islands nejsou prohlášeny za přijatelný výchozí výrobní návrh. Nezávislé review
tohoto konkrétního přírůstku čeká na jiného agenta.
