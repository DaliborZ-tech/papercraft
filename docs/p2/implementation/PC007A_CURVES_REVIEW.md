# PC-007A — nezávislá revize numerické komponenty křivek

Reviewer: samostatný agent `commands_review`, 9. 11. 2026. Autorem revidované komponenty je jiný agent.

Zdroj: **`8074d3ef0f9168cedf686b461d5f002cff63c2e9`**, větev `revival/p2-curve-numerics`, pracovní strom byl před revizí čistý. Rozsah: `authoring/curves.py`, zdrojové segmenty line/arc/cubic, vyhodnocení/derivace, intervalové meze délky a tětivové aproximace, konečné rozpočty a nativní SVG příkazy. Revize nemění produkci ani autorovy testy.

**Verdikt: CHANGES_REQUESTED — R01 MAJOR OPEN.** Délkové a tětivové důkazy pro zkoušené konzistentní vstupy mají pozitivní výsledky, ale téměř úplný oblouk může být jako nativní SVG vydán na jiné kružnici. Komponentu nelze schválit pro tvrzenou shodu zdroje a vektorového výstupu, dokud není nález uzavřen.

## R01 — MAJOR: povolená endpoint odchylka mění větev SVG oblouku

Vstup:

```python
epsilon = 1e-8
Curve((1, 0), (1, epsilon), "arc", {
    "center": (0, 0), "sweep_deg": 360-math.degrees(epsilon)
})
```

Analytický konec podle středu a sweep leží poblíž `(1,-1e-8)`. Deklarovaný konec `(1,+1e-8)` je vzdálen přibližně `2e-8`, takže projde absolutním limitem `1e-7` v konstruktoru. `evaluate` pracuje s deklarovaným středem a úhlem na otevřeném intervalu, ale v parametru 1 vrací výslovný konec. `certify_curve` při tolerancích 0,001 vydá **CERTIFIED** s `max_chord_deviation_bound = 0.00030121642356500044`.

`svg_commands` ovšem vydá jediný endpoint oblouk s poloměrem 1, `large-arc=1` a `sweep=1` k deklarovanému konci. Dvě možné kružnice určuje kolmice půlící tětivu; pro tyto flags jde o střed `(1+sqrt(1-epsilon²/4),epsilon/2)`, tedy přibližně `(2,5e-9)`. Střed původního oblouku je `(0,0)`. Bod v polovině dlouhého SVG oblouku je `(3,5e-9)`, zatímco původní zdroj má přibližně `(-1,5e-9)`. Rozdíl **4,0** mnohonásobně překračuje deklarovanou mez. Nejde o pouhé zaokrouhlení čáry ani změnu směru souřadnic.

Dopad: zdroj a nativní SVG mohou mít jiný materiálový tvar, přestože malá endpoint odchylka je zahrnuta jen jako malý numerický guard. To brání schválení nativní reprezentace oblouku a návazného výrobního workflow. Nález byl ihned předán integračnímu ownerovi.

Oprava má zachovat skutečný zamýšlený střed/sweep a pravdivě řešit deklarovaný konec. Možností je více stabilních nativních A úseků s mezilehlými body odvozenými ze zdrojového oblouku a kontrolou odchylky výstupu, nebo bezpečné odmítnutí nejednoznačného/nekonzistentního vstupu. Samotné zvětšení guardu o endpoint vzdálenost nestačí. Při následné revizi vyžadovat obě orientace, near-full sweep i konzistentní oblouk se stejným středem; původní FAIL uchovat.

## Ověření

Příkazy z `C:\Users\dalib\projects\papercraft-curve-numerics`, s `PYTHONPATH` na jeho `src`:

```powershell
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_curves.py -q --junitxml=docs/p2/implementation/evidence/pc007a-curves-review-original.xml
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest docs/p2/implementation/evidence/pc007a-curves-review-own.py -q --junitxml=docs/p2/implementation/evidence/pc007a-curves-review-own-initial.xml
```

- Autorovy testy: **34 PASS / 2,15 s** ([JUnit](evidence/pc007a-curves-review-original.xml)).
- Vlastní orákula: **18 PASS, 1 FAIL / 1,13 s** ([zdroj](evidence/pc007a-curves-review-own.py), [JUnit](evidence/pc007a-curves-review-own-initial.xml)). FAIL je výše uvedený produktový R01; není to důvod změkčit toleranci nebo smazat zkoušku.

Vlastní analytika: délka kruhového oblouku `r|sweep|` od 1e-6° přes obě orientace a hranici 180° do 359,9°; explicitní nativní flags; kubika `x=(3t-1)^3` se stacionárním bodem v nedýadickém parametru 1/3 a známou délkou 9; kolineární kubika s reverzemi, jejíž celkovou variaci určují nezávisle kořeny kvadratické derivace. Čtyři prudké/vracející se či malé kubiky byly porovnány s nezávislou integrací explicitní Bernsteinovy rychlosti; nepoužívá produkční `evaluate` ani `derivative` pro očekávanou délku. Kvadratura je nezávislá numerická kontrola, nikoli nový formální pozitivní důkaz.

Samostatně ověřeno, že omezení počtu segmentů či hloubky neztrácí parametrickou oblast, vrací BUDGET_EXHAUSTED a neskrývá neprokázanou toleranci. Velká translace vrací UNRESOLVED při překročení numerického guardu. Regularita kubik není povýšena z absence nalezené nulové derivace na REGULAR; i certifikovaná délka zůstává NOT_PROVEN nebo SINGULAR. Důkaz délky tudíž není důkaz regularity, jednoduchosti profilu, developability ani fyzické sestavitelnosti.

Kontrola implementace: přesné racionální de Casteljau dělení kontrolního polygonu a konvexní obálka poskytují meze pro celou kubiku; alokace délkového gapu podle velikosti parametrického intervalu a závěrečná globální kontrola brání neomezenému součtu per-leaf tolerancí. Kruhový certifikát rozlišuje přesnou délku a horní sagitta mez; úseky větší než π vyžadují dělení. Zkoušky necertifikují všechny možné extrémní vstupy nebo externí SVG editory.

## Uplatnění skills a meze výsledku

Před revizí byly skutečně načteny čtyři projektové skills a relevantní AU08/09, kontrakt a závěry geometrických spiků. Konstrukční skill zde brání záměně analytického zdroje s náhodným tessellovaným obalem; R01 ukazuje výrobně významnou změnu obrysu. UI skill vyžaduje, aby pozdější integrace nehlásila certifikát délky jako obecně regulární nebo přesně rozvinutelný profil; žádný UI průchod tato pure komponenta nedodává. Verification skill vedl k vlastnímu nepříjemnému endpoint případu a oddělení matematického důkazu od vzorků. Delivery skill vyžaduje opravu a nové review konkrétního zdroje před použitím schválení.

AC-AU08/09 nejsou touto revizí celé splněné: vlastní kreslení/editace oblouku a Bézier, rohy, B1/B2/B3, extruze, IO, skutečné UI, ruční layout a oba exporty musí projít navazujícími řezy. Uživatel a P3 jsou NOT_RUN. Reviewer neuděluje vlastní produktové přijetí ani schválení celé PC-007A.
