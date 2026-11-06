# Ověření návrhového balíku P2 v1.2

Integrační owner `/root`, 6. 11. 2026. Zdrojový pin prvního úplného návrhu a geometrických experimentů: **`5b8f93c940b2f042852ede5de68e697a8844bd65`**, izolovaná větev `revival/p2-v1.2-design`, základ `origin/master` `6eb8977011854b242ab1dac8ea929e262e3b9563`. Pozdější opravy a nezávislé kontroly určuje [review](INDEPENDENT_REVIEW.md).

Použit stávající izolovaný interpreter `C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe`, pracovní adresář `C:\Users\dalib\projects\papercraft-p2-v12-design`. Žádná globální instalace ani produkční změna.

```powershell
<venv-python> tools/spikes/p2_v12_geometry.py --output docs/p2/v1.2/evidence/geometry-pinned.json
<venv-python> -m pytest tests -q --junitxml=docs/p2/v1.2/evidence/design-full-tests.xml
<venv-python> -m ruff check tools/spikes tests/spikes
<venv-python> tools/spikes/validate_p2_v12_design.py
git diff --name-only 6eb8977011854b242ab1dac8ea929e262e3b9563 HEAD -- src pyproject.toml
git bundle verify docs/p2/archive/p2-v11-prototype.bundle
```

- Připnutý runner: exit0,3.755s; [data včetně source SHA a hashů](evidence/geometry-pinned.json).
- Full suite: **253 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, exit0, pytest5.01s. [JUnit](evidence/design-full-tests.xml). Je to původních213 testů master +40 izolovaných spike případů. Nejde o362 případů house-only WIP, které zůstaly v archivním bundle/evidenci.
- Ruff pro nové spike/validator/test soubory: PASS, exit0. První předformátovací verze měla71 stylových nálezů; po opravě zůstala všechna numerická data přesně stejná a původní raw evidence se zachovala.
- Produkční diff `src/` a `pyproject.toml`: prázdný. Balík nemění runtime editor nebo file schema. Přítomnost archivního bundle nepovoluje jeho automatické spuštění či migraci.
- Bundle: `git bundle verify` PASS; SHA256 `9430a97e1668e3ba862ec720c8558a034034144af5d0b47c911956a1f2b5f769`, reference `revival/p2`→`f9507e325c479c8b703e7f52c410de6847958720`, prerequisite `6eb8977`.

Validator fronty kontroluje unikátní ID, zachování původních ticketů, acykličnost dependency i completion grafu, přiřazení všech18 nových AC, všech16 epic, skutečné historické přijetí v1.1 a oddělenou bránu v1.2, nepřisouzení PASS novým produktovým AC, místní odkazy a integritu bundle. První průchod před vznikem review záměrně hlásil chybějící soubor `INDEPENDENT_REVIEW.md`; finální výsledek se uloží po doplnění nezávislé evidence. Tento validator neposuzuje pravdivost algoritmu ani neuděluje produktové přijetí.

Dosavadní prototyp a jeho úspěšné i neúspěšné desktopové/editorové pokusy se nevydávají za A/B/C/D. Nové skutečné UI, nové persistence, výrobní výstupy a DPI průchody jsou **NOT_RUN**. Fyzický výtisk, lepicí pevnost a sestavení jsou P3, nikoli výsledek matematických spikeů.

## Opravy po nezávislých nálezech

Nový source pin **`d4ce76e38b3632c72964adf3e438c5632849caa9`** opravuje falešné EXACT u singulárního rovinného loftu (DR-01) a texty poškozené přenosem Unicode přes výchozí ASCII stdin PowerShellu (DR-02). Druhá oprava byla provedena přímo z UTF-8 souboru, včetně všech nových pointerů, názvů ve frontě a doplňku přijetí; validator hlídá náhradní značky. Původní raw evidence zůstává zachovaná. Přibyly regrese nesamplovaných singularit, směrů a kruhového descriptoru; celkem je nyní60 spike testů.

Root ověření na tomto source pinu: **273 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, exit0, pytest5.28s; [finální JUnit](evidence/design-final-full-tests.xml). Je to213 původních +60 nových. Ruff PASS. [Všech18 kontrol integrity návrhu](evidence/design-integrity-d4ce76e.json) PASS: nyní též explicitní původní AC přesunutá do P2 a správné UTF-8 texty. Přítomnost review souboru znamená jen existující odkaz; technický verdikt se čte z review a nelze jej vyvodit z integrity validatoru.

[Skutečná obnova archivního bundle](evidence/preservation-restore.json) do nové izolované bare databáze potvrdila SHA archivní větve i přítomnost zdrojového modelu/UI/testu/nástroje a editorového důkazu. Původní workspace zůstává na správném místě, archivní `revival/p2` se nemění. Nezávislý reviewer ověřuje nový pin zvlášť, včetně vlastních hraničních/negativních případů; zde uvedený root test není jeho schválení.
