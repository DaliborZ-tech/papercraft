# ArchPapercraft Studio

Pracovní autorská verze **0.3.0** pro vytváření vlastních papírových modelů
architektury. Začíná prázdným modelem; vlastní plochy a profily propojuje s 3D
náhledem, spoji, papírovými díly a ručním rozmístěním na stránky.

**[Český rychlý start](docs/manual_cs.md)** vede od prvního obdélníku nebo skici
přes úpravu rozměrů a spoj až k uložení a exportu.

| Pracovní kontext | K čemu slouží |
|---|---|
| Modelování | Vlastní obrysy a otvory, výběr, názvy, body a umístění ploch; volitelná Skica |
| Spoje a rozvin | Hrany, přehyby a lepení, chlopně, přepočet papírových dílů |
| Stránky | Ruční umístění a natočení dílů na A4, zámky a rozmístění podle zadaných roztečí |
| Export | Kontrola připravenosti a společný export editovatelných SVG a vektorového PDF |

Projekt ukládá příkaz **Uložit** do `.apcraft`. Oddělený 30sekundový záložní
koncept umožňuje obnovu po přerušení práce; nepřepisuje uložený projekt.
[Rozsah obnovy a ochrana originálu](docs/manual_cs.md#uložení-a-obnova-práce).

## Instalace a spuštění

Python **3.10+**. Příklad pro Windows PowerShell v kořeni repozitáře:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m archpapercraft
```

Instalovaný vstupní příkaz je také `archpapercraft`.

## Vývojové ověření

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests -q
```

Aktuální stav dodávání je v [pracovní frontě](05_WORK_QUEUE.json) a
[záznamu pokračování](docs/revival/P2_CONTINUATION_2026-11-17.md).
Test s novým uživatelem **AC-US08: NOT_RUN (0 účastníků)**;
fyzický výtisk a sestavení **P3: NOT_RUN**. Pracovní verze ani technické
ověření nejsou závěrečnou produktovou akceptací P2.

Původní [README](docs/archive/README-before-workspace-2026-11-17.md) a
[manuál 0.2](docs/archive/manual_cs-v0.2-before-workspace-2026-11-17.md)
jsou zachované jako historické texty. Pro současné autorské UI platí rychlý
start výše.

Licence: MIT.
