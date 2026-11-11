# AU13: přesné dělení zdrojové křivky a historické reference

Stav: implementovaný čistý komponent, **čeká na nezávislé review**. Nejde o hotové
AU13, doménovou integraci, UI ani splnění mixed-part AC-AU14. Výchozí commit je
`d762fc6d2c543691b8918128b6b0d3e1da59313e`; nový kód a test mají vlastní SHA-256
v [manifestu](evidence/au13-subdivision-source.json). Výchozí SHA není vydáváno za
identitu nových souborů. Integrátorem zůstává root.

## Doručená matematická část

`authoring/curve_subdivision.py` nečte ani nemění projekt. `CurveSource` uchová
oddělený neměnný descriptor LINE/ARC/CUBIC. `CurveSubdivisionHistory(profile_id,
segment_id, source)` uchovává pouze historii jednoho zdrojového segmentu:

- `split(segment_id, t, left_id, right_id)` vytvoří dva nové caller-owned ID;
  ostatní aktivní ID zachová. `t` je striktně uvnitř (0,1).
- `merge(ordered_active_ids, merged_id)` přijme jen sousední, přesně souvislé
  potomky stejného nezměněného geometrického zdroje/generace. Nefituje nový tvar.
  Při plném spojení obnoví původní descriptor; historická ID dětí zůstanou
  adresovatelná jako podintervaly nového segmentu.
- `edit(segment_id, source)` je explicitní prohlášení změny geometrie při
  zachování lokálního parametru. Zachová topologické ancestry, ale zruší oprávnění
  k inverse merge s nepozměněnými sourozenci. Další split a inverse merge této
  nové generace funguje. Neprokazuje freshness ani legitimitu změny parametru.
- `resolve(TrimReference(id, profile_id, historical_segment_id, start, end))`
  vrátí `SINGLE`, úplný orientovaný `CHAIN`, nebo `UNRESOLVED` s původní referencí
  a nalezenými kandidáty. `require_single=True` zakáže převést řetězec do legacy
  reference na jediný edge. Chybějící zdroj ani jiný profil se nehledá podle
  polohy, indexu nebo názvu.
- `resolve_point(SourcePointReference(..., parameter))` rozliší `SINGLE`,
  `SHARED_POINT` a `UNRESOLVED`. Bod přesně na řezu zachová oba vlastníky;
  `SHARED_POINT` vyžaduje totožný analytický zdroj, generaci a parametr. Po editaci
  jedné strany je dvojznačnost unresolved i při stejných rounded souřadnicích.
  Komponent nevybírá aplikaci nové vertex ID.
- `to_dict/from_dict` používá schema 1 tohoto komponentu a striktní replay událostí.
  Nepřijímá dodanou cache potomků ani deklaraci „parent“ jako důkaz ancestry.
  Původní a retired ID nelze znovu použít; replay má limit 1024 operací. Výstupy
  jsou oddělené od vstupů. Projekt musí navíc ověřit globální UUID registry.

Každá ancestry vazba je přesná afinní mapa **historický interval ↔ lokální
interval aktuálního dílu**. Oba intervaly jsou nutné: po merge zabírá původní levé
dítě pouze část nového segmentu. Pouhý seznam parent IDs tuto informaci ztrácí.
Operace clippingu a kompozice používají `Fraction`, včetně orientovaného reverse.
ID trimu je oddělené od ID segmentu a zůstává při řešení stejné. Přetrvání těchto
recordů v aplikačním souboru musí doplnit doménový owner.

## Geometrické důkazy a experimenty

LINE je afinní restrikce. CUBIC používá racionální de Casteljau. Test nezávisle
rozvíjí zdroj `x=12t²−8t³, y=12t−12t²` při `t=a+(b−a)s` a porovnává všechny
čtyři mocninné koeficienty obou souřadnic, také při reverse. Jde o identitu pro
celý interval, nikoli shodu několika vzorků.

ARC zachovává originální kružnici a přesný interval zdrojového parametru. Sweep
potomka je `parent_sweep*(b−a)`. Nový float endpoint není nový geometrický zdroj.
`point_bounds` používá již existující outward racionální π/Taylor helpery
`curve_area`/`loft_area`; čtvrtkružnice R20 má analytický endpoint (0,±20) uvnitř
vrácených mezí. Pro libovolný arc se ukládá analytická restrikce, nikoli tvrzení,
že její iracionální endpoint je přesná binární souřadnice.

Existující `Curve` připouští uložený ARC endpoint odlišný od analytického limitu
do 1e−7. Test `(−20,1e−8)` versus nominální `(−20,0)` tento rozdíl zachovává:
historie nezahladí authored údaj a bodové meze ho neprohlásí za analytický bod.
Budoucí native-output adaptér musí explicitně nést tuto rezervu. Prosté vytvoření
nového ARC descriptoru z float počátku dítěte by změnilo poloměr a není přijatelný
zdroj pro exact-family certifikát.

Konkrétní rámcový protipříklad: horní půlkruh R20 má původní chordu z (20,0) do
(−20,0), ale levé dítě po půlení chordu do (0,20). Náhrada axis segmentu prvním
dítětem otočí rámec o **45°**. Původní celointervalový trim má pořád stejné dva
semantic konce; jeho plný řetězec nesmí být nahrazen prvním dítětem. Další test
ověřuje všechny čtyři body stejné stěny při půlení a znovupůlení osy, měřítku .01,
page transform [60,60]/30°. To je čistý frame experiment, **není to UI ani celé
smíšené wall/roof AC**; page ID a locks nevlastní tento komponent.

Testy dále ověřují partial merge, reference vytvořené na zaniklých dětech,
opakované dělení po merge, nepozměněný zdroj, nevratnou záměnu ID, různé profily,
jednostrannou editaci, neznámé schema/pole/události, pokus o vložení falešné cache,
hranici replay budgetu a JSON reopen bez ztráty exact racionálních parametrů.

## Konkrétní integrační pořadí a hooks

1. **Project/model owner:** atomický `split_profile_segment(profile_id, segment_id,
   t)` a `merge_profile_segments(profile_id, ordered_ids)` přes čistý komponent.
   Vložit split vertex a dvě nová segment ID; ponechat profile ID i všechny
   nezasažené vertex/segment IDs. Nepoužívat `AuthorProject.update_profile`
   (`project.py:209`), který nyní nahrazuje veškerou topologii. Před mutací připravit
   kompletní reference/remap plán, ověřit geometrii a až poté jeden transaction.
   Neztrácet uživatelské parametry spojů, connector/tab overrides, placements,
   čísla, locks ani staré cache. `_profile_surfaces` a `_touch` již poskytují
   dependency/stale propagaci celé části.
2. **Persisted source/trim registry:** ke konkrétnímu profilu uložit původní source
   a historii, stabilní trim/point recordy a explicitní unresolved stav odkazů.
   Nejde o obecný graph. Současné schema 5 nemá ancestry; pokud budou tato pole
   přidána, schema 6 s ověřeným copy adaptérem 5→6 a beze změny původního souboru.
   Legacy celé edge reference dostanou plný orientovaný trim [0,1]. Samotný pure
   record neověří, že aktivní Profile cache odpovídá historii: load/recompute to
   musí nezávisle porovnat, nebo odvodit cache z canonical source.
3. **Planární boundary owner:** `profile_curves.source_curve` (:188),
   `profile_native_path` (:88) a source contour/material consumers musí umět
   canonical restricted source. LINE/CUBIC cache zaokrouhlit pouze s výslovnou
   rezervou; ARC nikdy neregenerovat jako nový exact source z rounded počátku.
   Vnější obrys/otvory si zachovají profile ID a oblast materiálu. Merge odstraní
   jen ověřený vnitřní split vertex, ponechá jeho historickou point referenci.
4. **Joint/attachment owner:** rozšířit `attachments.edge_source` (:15) a
   `interval_points` (:38) o resolver stabilního trimu. Přesný souvislý řetězec
   LINE potomků téhož zdroje lze použít jako **jeden virtuální geometrický edge**:
   jeden joint/connector, stejné seam/fold role a tab čísla/overrides, žádné falešné
   další spáry. Attachment source_interval se přesně skládá přes ancestry;
   target UV/region a glue direction zůstávají. Pokud consumer složenou referenci
   neumí nebo je změna nejednoznačná, zachovat původní edge/interval/joint data,
   nastavit unresolved a blokovat recompute/export s konkrétním repair. Již nyní
   Joint/Attachment validation dovoluje uchovat takto označený chybějící edge.
   Neoznačovat celý AU13 za „jen unreferenced“ ani CHAIN za automaticky current.
5. **Paper/anchor owner:** `_frame_map` (`paper.py:82`) a loft `_local_frame`
   (`loft_surface.py:943`) potřebují persisted semantic axis trim a anchor point,
   ne jen aktivní `axis_segment_id`. Zachovat původní authored endpoint/chord při
   beztvarové změně topologie. Smíšená část si ponechá part/frame/placement ID,
   page 2, [60,60], 30°, oba locks; `_touch` ji celou označí stale až do explicitního
   recompute. Povinné integrační orákulum porovná **všechny body stěny**, seam/fold
   a tab reference před split, po recompute, undo/redo a reopen. Zaniklý vertex
   nesmí dostat nearest náhradu; ověřený source material point lze zachovat
   explicitně. Jiné geometrické editace neposkytují slib zachování všech bodů.
6. **Loft owner:** současný `validate_loft_params` (:135) vyžaduje whole-segment
   bijekci a intervaly jen [0,1]/[1,0]. Jednostranný split profilu tedy nelze
   napravit pouhou záměnou jednoho patch edge za dítě. Zachovat patch/ruling/seam
   IDs a přesné source trimy, přidat podporu ověřených restricted source views a
   rozdělení correspondence intervalů; původní φ musí být explicitně převoditelná.
   Alternativou je explicitní atomická autorská operace na obou profilech, nikoli
   skrytý edit protějšího profilu. Do dokončení adaptéru pravdivě unresolved se
   zachovanými referencemi, ne smazání loftu či přisouzení EXACT. Platí i pro
   material-point kotvu uvnitř patch po změně parametrizace.
7. **Derived D owner:** stará segmented generation zůstane immutable a s placementy;
   změna source topology mění fingerprint, ruší její current potvrzení/print
   selection a vyžaduje explicitní nové odvození. Historická provenance se
   nepřepíše. UI pak zobrazí rozsah operace, unresolved reference a náhled opravy;
   undo/redo zachová authored data a bezpečný návrat. Toto není součást pure commitu.

Šestý krok je skutečná integrační práce, nikoli důvod odložit planar/joint/anchor
průchod. Bez něj nelze tvrdit celé AU13 hotové. Nejmenší reviewovatelný vertikální
řez po tomto helperu je společná planar boundary + již připojený line fold/trace +
semantic frame + save/reopen. Poté stejný contract pro loft trims/φ/anchors.

## Ověření a skutečné meze

Spuštěno ve Windows worktree `papercraft-au13-math`, Python ze sdílené `.venv`,
pytest používá lokální `src` (actual import path v manifestu).

```powershell
C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_curve_subdivision.py -q --junitxml=Temp/au13-subdivision-final.xml
C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_curve_subdivision.py tests/authoring/test_curves.py tests/authoring/test_curve_area.py tests/authoring/test_loft_area.py -q --junitxml=Temp/au13-subdivision-regression.xml
C:\Users\dalib\projects\papercraft\.venv\Scripts\ruff.exe check src/archpapercraft/authoring/curve_subdivision.py tests/authoring/test_curve_subdivision.py
git diff --check
```

- Nové testy: **55 PASS**, 0.68 s; relevantní pure regrese: **168 PASS**, 13.742 s.
- Ruff a diff whitespace: PASS. Původní raw výsledky jsou zachované v evidence.
- První běh měl 44 PASS/2 FAIL: arbitrární nová testovací mez šířky arc intervalů
  1e−45 byla těsnější než používaný globální Taylor bound (~4.17e−44 pro R20).
  Test nyní explicitně používá 1e−40 a stále vyžaduje enclosure analytického bodu.
  Nezměnil se produktový AC threshold, žádná chyba z evidence nebyla odstraněna.
- Skills: konstrukce vedla k oddělení skutečné křivky a display cache/endpointů;
  verification k algebraickému celointervalovému orákulu a adversarial merge;
  delivery k izolovaným souborům/replay a pravdivému incomplete stavu; UI skill
  k explicitnímu unresolved/repair bez nearest fallback a k zachování undo dat.
  Žádný průchod v UI, nový uživatel ani fyzický proof nebyl proveden.
- Z otevřených poučení v `SKILL_IMPROVEMENTS.json` se zde konkrétně přenáší
  rozdíl finite screening / celointervalový důkaz a rozdíl zelený working tree /
  přesně připnutý zdroj: polynomial identity, konzervativní trig intervaly,
  zachovaný první FAIL a per-file source hash. Poučení o cache kontraktu se
  promítá do explicitního požadavku na invalidaci staré D generation a zachování
  placementů. Účinnost v aplikačním split/reopen průchodu zůstává pending; tento
  pure test ji nenahrazuje. Sdílenou evidenci ani skills tento izolovaný commit
  nepřepisuje.
- Komponent neposuzuje jednoduchost celého profilu, kontakt, topologii oblasti,
  rozvinutelnost, export native budget ani globální UUID; to zůstává příslušným
  existujícím certifierům a aplikační transakci. Samotné ancestry není důkaz, že
  autor později nezměnil aktuální cache či zdroj mimo povolený příkaz.
