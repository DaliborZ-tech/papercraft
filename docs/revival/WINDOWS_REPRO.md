# Malý Windows reproduction pack

Spouštět z kořene checkoutu na izolované větvi. Původní sample a vlastní projekty se neupravují. `.venv` lokální, neinstalovat globálně. Po instalaci stačí dostupné balíčky; aplikace má fungovat offline.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e '.[dev]' pypdf==6.21.4
.venv\Scripts\python.exe tools\revival\run_baseline.py
.venv\Scripts\python.exe tools\revival\run_probe.py core_probe
.venv\Scripts\python.exe tools\revival\geometry_probe.py
.venv\Scripts\python.exe tools\revival\run_probe.py integration_probe
.venv\Scripts\python.exe tools\revival\run_probe.py desktop_probe docs/revival/evidence/windows-repeat-01
```

Pro přesné verze použít evidence freeze; originální instalace měla pypdf přidaný až po legacy baseline. Desktop output adresář musí být nový, aby se nepřepsala důkazní sada ani nevznikla nečekaná overwrite modalita. Všechny příkazy generují diagnostické soubory pod evidence. Desktop harness používá jen vlastní Windows dialogy, má procesový timeout120s a oddělené APPDATA/logy. Nespouštět současně dva native-dialog desktop probes. Exit0 experimentu znamená sběr evidence, stav produktu číst v JSON; červené diagnostiky mají podběh exit1 záměrně. Rerun baseline plné sady má smysl až po změně prostředí/kódu nebo kvůli konkrétnímu novému problému.

Pro člověka: `.venv\Scripts\python.exe -m archpapercraft`. Nový projekt mm/1:100 → Přidat/Primitiva/Kvádr → vybrat ve stromu → dx100 dy60 dz40 → Focus výběru → Uložit jako do nového testovacího souboru → zavřít/otevřít → Analyzovat → Automatické švy → Exact/Rozložit → exportovat SVG/PDF. Pak dx120: porovnat aktuální model a papercraft stale stav (dnešní vada PC-F08b). Nepoužívat export jako sestavitelný kalibrovaný výrobek.

Po implementaci P2 navíc povinně: 8krokové demo z §4 normativní akceptace včetně klikového výběru oběma směry, švu/chlopně/undo, dvou stránek a protikusu, kolize, změny střechy, save/reopen, SVG editace a PDF. Zopakovat při100/150/200%DPI, klávesnicí i myší, zapsat GPU/driver a přesné verze. Otevřít a editovat konkrétní export v reálném Inkscape, zaznamenat verzi, změnit text/barvu a přesunout celý díl jako skupinu. Ověřit český font, 100mm kalibraci a shodné souřadnice přes nezávislý XML/PDF reader. Chybějící editor/Windows proof je BLOCKED/NOT_RUN, ne PASS. Fyzická kalibrace pravítkem, papír/tloušťka a sestavení jsou samostatný P3 protokol pro člověka.
