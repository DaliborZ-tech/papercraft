# Ověřená baseline P0

K 5. 11. 2026 lze původní aplikaci nainstalovat, spustit na Windows s OpenGL, vytvořit/editovat kvádr a projít nativní save/open a export SVG/PDF. **213 původních testů PASS však neprokazuje správnou vystřihovánku**. Cílená geometrie a integrace dokládá [zásadní vady](FINDINGS.md). Produkční P2 není implementována ani přijata.

## Checkout a ochrana práce

- Skutečný VS Code root i cwd: `C:\Users\dalib\projects\papercraft`; původně 9 souborů briefu, žádný `.git`, žádný nadřazený worktree. Lokální/rodičovský `AGENTS.md` nenalezen, žádné existující workflows/queue kromě předané fronty.
- Bezpečný staging clone do `%TEMP%/papercraft-bootstrap-…`; kompletní preflight150entries před kopírováním, žádné obsahové/type kolize, žádné symlinky. Na Windows `Test-Path` řeší case-insensitive existenci. Nic se nemazalo ani nepřepisovalo; nekolizní checkout včetně `.git` přenesen do rootu.
- `git rev-parse --show-toplevel` = otevřený root, origin `https://github.com/DaliborZ-tech/papercraft.git`, vzdálený HEAD i baseline `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`. `git diff --exit-code HEAD` po bootstrapu0. Původní brief byl untracked, bez cizích tracked změn.
- Každý původní soubor má stejný SHA256 před/po bootstrapu: [bootstrap.json](evidence/bootstrap.json). Původní fronta se až následně vědomě aktualizuje v jediném root `05_WORK_QUEUE.json`; normativní zadání a ostatní původní soubory zůstávají obsahově zachované. Předané soubory jsou vědomě součástí lokálního commitu pro reprodukovatelný kontrakt.
- Izolovaná větev `revival/p0-p1-contract`; žádný reset/clean/push/PR/merge, produkční src/tests beze změny. Dočasný staging není konečné umístění, zůstává pouze jako vratná kopie v temp.

AC-B01 využívá alternativu bezpečného neprázdného bootstrapu, ne tvrzení o prázdném rootu. AC-B02 PASS. AC-B03 v reálném rootu nenastala rozdílná kolize; preflight proběhl před jediným zápisem checkoutu. Neprováděl se destruktivní experiment v uživatelových datech.

## Prostředí, instalace a příkazy

Windows11 build26300, x64, Python3.12.15 z lokálního uv managed runtime, uv0.12.23. Systémový Python3.14.6 se nepoužil pro projekt. Instalace pouze `.venv`, bez globálních balíčků a bez obcházení proxy.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e '.[dev]'
.venv\Scripts\python.exe tools\revival\run_baseline.py
.venv\Scripts\python.exe tools\revival\geometry_probe.py
.venv\Scripts\python.exe tools\revival\run_probe.py core_probe
.venv\Scripts\python.exe tools\revival\run_probe.py integration_probe
.venv\Scripts\python.exe tools\revival\run_probe.py desktop_probe docs/revival/evidence/desktop-new-run
```

Instalace `.[dev]`: exit0, uv příprava30packages5m31s + instalace31packages1.01s (zahrnuje editable projekt). Přesný instalační příkaz a výsledek byl zachycen v terminálu této session; délka přípravy je údaj uv, nikoli dodatečně odhadnutý čas. Úplný freeze baseline v [packages.log](evidence/packages.log); PySide6/Qt6.12.0, NumPy2.5.4, SciPy1.18.1, ReportLab5.1.0, svgwrite1.4.3, PyOpenGL3.1.10, pytest9.2.0, pytest-qt4.5.0, ezdxf1.4.5. Nejde o minimální podporované verze.

Po baseline přidán pouze diagnostický `pypdf==6.21.4` (`uv pip install --python .venv\Scripts\python.exe pypdf`, exit0), pro nezávislé čtení PDF; není produkční závislost. Současný freeze v [diagnostic-packages.txt](evidence/diagnostic-packages.txt). Pro přesné opakování zachovat verze freeze, jejich dostupnost na budoucím indexu není garance. První import může déle inicializovat Qt; skutečně zaznamenáno19.146s.

## Výsledky bez zamlčení selhání

| Kontrola | Čas / exit | PASS / FAIL / SKIP | Důkaz |
|---|---|---|---|
| import aplikace a závislostí |19.146s /0 | import OK | environment.log |
| `uv pip check` |0.095s /0 |31 balíčků kompatibilních | dependencies.log |
| původní `pytest tests -ra` | pytest40.44s, proces41.915s /0 |213 /0 /0 | pytest-baseline.log + XML |
| core subset bez možnosti importovat Qt | pytest0.28s /0 |44 /0 /0 | core-only.xml + core_probe-run.log |
| nové explicitní diagnostické assertions |0.16s /1 v podběhu |0 /6 /0 | diagnostic-contracts.xml, core-results.json |
| samostatná geometrie |0.586s /0 |1 PASS,10 DEFECT_REPRODUCED,0 ERROR | geometry-results.json |
| integrace transformů/persistence/exportu | viz integration_probe-run.json /0 | evidence sebrána, vady potvrzeny | integration-results.json |
| skutečný entry point + Windows/QTest/native dialogs | původní11.945s /0, následný cílený běh dle JSON | Qt/OpenGL a průchod funkční, invalidace/picking vadné | desktop-results.json, desktop-followup/ |
| optional OCC dry resolve | /1 | BLOCKED: index nemá pythonocc-core | occ-resolution.log |

Full suite se po informativním průchodu neopakovala. Nové diagnostiky leží mimo původní testpaths a neskrývají původní výsledek. `core_probe` vrací core exit a **zvlášť** ukládá diagnostický exit1; jeho exit0 neznamená zelený produkt. Původní markery nejsou spolehlivé rozdělení Qt/core (`test_mvp_pipeline` má importy UI); proto samostatný core běh používá import guard. Čtyřicet čtyři je podmnožina213, nikoli dalších44 unikátních testů.

První přímý integration probe skončil chybou kódování cp1250 při tisku českého/Unicode PDF textu. Zachováno v `integration-probe.log`. Harness opraven spuštěním s `PYTHONUTF8=1` přes `run_probe.py`, bez změny produktu nebo očekávání. Následné běhy doplnily konkrétní nové metriky (PDF struktura, tab envelope, save fault, dirty), ne náhodné opakování do prvního PASS.

## Skutečný desktop proof

`desktop_probe.py` volá skutečný `archpapercraft.app.main`; hook pouze naplánuje QTest scénář po zobrazení MainWindow. Není použit `offscreen` platform plugin. `platform=windows`, viewport `isValid=True`, GL4.6.0 NVIDIA610.71, RTX5050 Laptop GPU. [Screenshot](evidence/desktop-model.png) a framebuffer byly vizuálně zkontrolovány; první záběr byl bez focus příliš přiblížený, následný cílený běh využívá skutečný focus a ukládá další záběr.

Nový projekt přes skutečný wizard → QAction přidat kvádr → QTest stromový výběr → změny dx100/dy60/dz40 → nativní Windows dialog class `#32770` Uložit jako → skutečný soubor → nativní Otevřít → analyze/seams/exact unfold → nativní export SVG a PDF a success dialogs. Automatizace nastavuje jméno souboru a potvrzuje jen dialogy vlastního procesu; nejde o mock souborových cest. Report potvrzuje vytvořený/reopened projekt, validní GL a prázdné exception pole. Výsledkem1díl se7seams pro konkrétní box; není to důkaz všech topologií.

Po změně dx100→120 se mesh změní, ale unfolded/cached objekty a aktuálně vypadající label zůstanou. [desktop-results.json](evidence/desktop-results.json) to dokládá. Click picking a ruční2D authoring dnešní aplikace neimplementuje. Automatický průchod nehodnotí lidskou ergonomii, všechny GPU, DPI ani fyzický tisk. Potřeba Windows tedy v tomto prostředí není blocker; P2 nové interakce bude nutné znovu ověřit po implementaci.

## Co zůstává ověřit

P2 všechny nové AC jsou NOT_RUN, i když izolované rozměry panelu už mají analytické proof. Skutečný Inkscape nebyl v běžných cestách/PATH nalezen; editace SVG je NOT_RUN, ne tvrzená interoperabilita. Druhý editor volitelný. OCC větev neověřená. Fyzický tisk/sestavení patří P3. Přesný malý postup opakování a zbývajících Windows kontrol je v [WINDOWS_REPRO.md](WINDOWS_REPRO.md).
