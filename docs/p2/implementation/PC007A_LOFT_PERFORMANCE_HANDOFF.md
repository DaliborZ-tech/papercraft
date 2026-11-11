# Předání výkonové opravy loftu

Runtime pin: `2e4212388caef05adef42a4301bf367e7a6cb7f0`, izolovaná větev
`revival/p2-loft-performance`, základ `10a21ac`.

Na skutečném uloženém stavu neúspěšného B1 průchodu byla odstraněna opakovaná
kopie úplného analytického reportu a nové generování stejné sítě. Omezené LRU
pro síť a kanonický materiál ukládají neměnné JSON hodnoty. Klíče zahrnují skutečné
oba zdrojové záznamy, scale, feature/transformaci a pro materiál také identitu,
kotvu, tiskovou stranu a konstrukční schopnosti. Veřejné výsledky jsou oddělené.
Validace stále kontroluje skutečná data; shoda revize ani plochy nenahrazuje
porovnání úplného skutečného cache payloadu. Writerové privátní signatury zůstaly.

Přesná racionální kolinearita a podmínka bodu mezi sousedy odstraňují pouze
nadbytečné L uvnitř jednoho zdrojového úseku. Zdrojové rohy a rulingy zůstávají,
C se nezplošťuje a podrobná parametrická provenance zůstává mimo CUT nezměněná.
Bézierova normálová extruze má skutečný obdélníkový CUT s pěti M/L/Z příkazy.

| Operace na stejné předloze | Před [s] | Po [s] |
|---|---:|---:|
| Opakovaná veřejná síť | 1.046 | 0.087 |
| Validace | 1.698 | 0.151 |
| Backend příkaz rozmístění | 6.880 | 1.054 |
| Qt obnovení | 13.170 | 2.344 |
| Qt příkaz rozmístění a obnovení | 18.481 | 3.237 |
| Nejdelší mezera Qt heartbeat | 18.490 | 3.239 |

[Před](evidence/pc007a-loft-performance/before.json),
[dílčí první oprava](evidence/pc007a-loft-performance/stage1.json),
[dílčí druhá oprava](evidence/pc007a-loft-performance/stage2.json),
[po na runtime pinu](evidence/pc007a-loft-performance/after.json).
Záznamy obsahují SHA předlohy i skutečně importovaných runtime souborů.
Předloha nebyla změněna; po běhu je loft EXACT, plocha CERTIFIED a layout bez issues.
Jde o jednotlivé lokální běhy, nikoli laboratorní statistiku. První načtení
nebylo zrychleno (8.34 s před, 10.11 s po); první dotaz statusu může dopočítat
dosud nepoužitý certifikát rámu. Náročný první výpočet patří nadále do existujícího
asynchronního náhledu s možností zrušení.

Ověření: **56 cílených loft/integrity regresí PASS**, následně **7 výkonových
integrity regresí PASS** přímo na runtime pinu; Ruff a diff-check PASS. Regrese
pokrývají oddělené návratové hodnoty, změnu obou skutečných profilů a pózy bez
změny revize, změnu kotvy a poškození CUT se stejnou plochou. Celá sada ani nový
nativní B1 průchod se po tomto přírůstku nespouštěly. Nezávislé review je PENDING.
Offscreen automat není test nového uživatele, editoru ani fyzického modelu.

Reprodukce (PowerShell, sdílený venv a výslovně tento checkout):

```powershell
$env:PYTHONPATH='C:\Users\dalib\projects\papercraft-loft-performance\src'
$env:QT_QPA_PLATFORM='offscreen'
& 'C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe' tests/authoring/test_loft_performance.py --source 'C:\Users\dalib\projects\papercraft-loft-integration\docs\p2\implementation\evidence\pc007a-loft-B1-desktop-a9d155a-run01\FAIL-partial-observed-state.json' --output 'C:\Users\dalib\AppData\Local\Temp\papercraft-loft-recheck.json' --label independent-recheck
```

Další sezení: nezávislé review tohoto pinu, integrace podle ownera a skutečný B1
UI průchod. Zbývá zhruba třísekundové synchronní rozmístění; další doložené náklady
jsou opakovaná validace, kopie part_geometry a dirty serialization. Nebyly zde
řešeny UI async/debounce ani nové D práce. Příčina původního číselného vstupu
40 místo44 zůstává neprokázaná; produktový numeric vstup nebyl měněn.
