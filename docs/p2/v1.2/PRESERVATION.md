# Zachování rozpracované v1.1 a výklad důkazů

Původní checkout zůstává v `C:\Users\dalib\projects\papercraft`, větev `revival/p2`. Jeho veškerý rozpracovaný produkční kód, testy, nástroje a dosavadní důkazy jsou zachované lokálním commitem **`f9507e325c479c8b703e7f52c410de6847958720`**. Jde o **WIP prototyp bez globálního nezávislého schválení**, nikoli vydání P2. Nic se nemaže ani nevrací resetem.

Návrhová větev `revival/p2-v1.2-design` má základ v aktuálním `origin/master` `6eb8977011854b242ab1dac8ea929e262e3b9563` a pracovní kopii vedle původního checkoutu. Není novým umístěním projektu ani opakováním bootstrapu. Na master se integruje návrhový balík bez změny produkčního entry pointu, house-only domény a její persistence.

Pro zachování **i na vzdáleném repozitáři** obsahuje balík [Git bundle prototypu](../archive/p2-v11-prototype.bundle). Obsahuje všech šest navazujících commitů od přijetí v1.1 po WIP včetně jejich ancestry; vyžaduje základ `6eb8977`, který už je v historii master. Bundle není spuštěná aplikace ani review verdict. Lze jej ověřit a načíst do nové archivní větve bez změny pracovního checkoutu:

```powershell
git bundle verify docs/p2/archive/p2-v11-prototype.bundle
git fetch docs/p2/archive/p2-v11-prototype.bundle revival/p2:archive/p2-v11-prototype
git show archive/p2-v11-prototype:src/archpapercraft/domain/project.py
```

Pokud cílová archivní větev již existuje, zvolit nové jméno; nepřepisovat ji. Bundle ověření a SHA256 je v integračním důkazu návrhu. Veřejně čitelné kopie původních reports a evidence jsou v `docs/p2/`; zdrojové soubory referenced lokálním SHA lze otevřít po načtení bundle. Historické review source SHA a závěry se nemění.

## Co jednotlivá evidence znamená

| Důkaz | Skutečný rozsah a limit |
|---|---|
| `PC006_CORE_REVIEW.md` | Nezávislé schválení omezeného core pinu `2a341e1`; ne schválení UI, paper engine ani autorské verze |
| `PAPER_ENGINE_REVIEW.md` | CHANGES_REQUIRED na `3fcf877`; 89 PASS / 1 FAIL na pinu, chybějící RAM díl nebyl blokován, extrémní overflow. Opravy jsou v WIP, review zde netvrdí, že byly nezávisle uzavřeny |
| `evidence/p2-prototype-preservation.*` | Root verification zachovávaného pracovního kódu: **362 PASS / 0 FAIL / 0 SKIP**, exit0, pytest23.37s. Nezávislá produktová revize se tím nenahrazuje |
| `evidence/pc006-desktop-final/` | Windows/OpenGL, native save/open, ochrana legacy; prototyp domu |
| `evidence/p2-desktop-attempt3/` | Skutečný prototypový dům v UI, výběr, švy, chlopně, stránky, mixed wall drift0, nativní save/open/export; úspěšný třetí pokus. Není A/B/C/D |
| `evidence/p2-desktop-attempt1*`, `attempt2*` | Zachované neúspěšné automatizační pokusy: návratová hodnota summary/kliknutí a výběr adresáře. V prvním collector vracel0 i při zapsaných errors; nelze jej interpretovat jako PASS. Třetí nástroj už vrací skutečný stav |
| `evidence/house-editor-proof/` | Skutečný Inkscape1.4.4: posun celého domu/dílu, jednotlivý text a barva, zachování source SHA a skupin. Neprokazuje nové curve/holes exporty |

Při prvních Qt testech došlo k chybě testovacího teardownu: focus vyvolal dodatečný editingFinished a dirty close dialog čekal na interakci. Opravené testy mají konkrétní before-close postup a znovu zaznamenané výsledky. Produkční formuláře následně dostaly no-op/precision kontroly a 17 widgetových regresí; ty jsou součástí 362 PASS. Žádný tento údaj nedokazuje podporu nových autorských modelů.

Časné v1.2 experimenty jsou odděleně v `v1.2/evidence/`. Jejich výstupy jsou analytika, ne produkční save schema. Všechny nové UI přejímky začínají NOT_RUN. Neprovedené DPI a fyzické průchody se neoznačují PASS.
