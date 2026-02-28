# ArchPapercraft Studio

**Architektura-first 3D modelář s exportem vystřihovánek (PDF/SVG/DXF)**

> *Jedna aplikace, ve které postavím 3D model historické/moderní architektury
> a jedním klikem dostanu profesionální vystřihovánku v měřítku, se značením,
> chlopněmi a návodem.*

---

## Hlavní funkce

| Oblast | Popis |
|---|---|
| **3D Modelář** | Parametrické architektonické objekty (zdi, okna, střechy, cibulky, věže) |
| **Analýza povrchů** | Klasifikace ploch (rovinné / vyvinutelné / nevyvinutelné) |
| **Automatické švy** | Inteligentní dělení modelu na díly podle ostrých hran a velikosti |
| **Rozklad (Unfold)** | Přesný rozvin pro roviny, góry/prstence pro cibulky |
| **Chlopně & značení** | Oušky, horní/dolní přehyby, číslování dílů, párování hran |
| **Rozmístění** | Automatické balení dílů na listy papíru (shelf-packing) |
| **Export** | PDF (přesné měřítko), SVG (vrstvy), DXF (pro plotr/laser), PNG (náhled) |
| **Stavební návod** | Legenda, seznam dílů, tabulka párování hran, doporučené pořadí |

## Instalace

```bash
# Vytvoření virtuálního prostředí
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux

# Instalace projektu (vývojový režim)
pip install -e ".[dev]"

# (Volitelně) OpenCascade back-end pro přesná B-Rep tělesa
pip install pythonocc-core
```

## Spuštění

```bash
archpapercraft          # přes entry-point
# nebo
python -m archpapercraft
```

## Spuštění testů

```bash
pytest tests/ -v
```

## Architektura projektu

```
src/archpapercraft/
├── app.py                   # Vstupní bod aplikace
├── core_geometry/           # Primitiva, mesh operace, validace
├── scene_graph/             # Transformace, hierarchie uzlů, scéna
├── arch_presets/            # Parametrické arch. prvky (zeď, střecha, okno…)
├── paper_analyzer/          # Klasifikace povrchů, kontrola vyrobitelnosti
├── seam_editor/             # Graf švů, automatické švy, zamykání
├── unfolder/                # Přesný rozvin, góry, prstence, fazetový rozklad
├── tabs_generator/          # Generátor chlopní a značení, stavební návod
├── layout_packer/           # Balení dílů na stránky, dlaždicový tisk
├── exporter/                # PDF, SVG, DXF, PNG export
├── project_io/              # Projektový formát (.apcraft), autosave, snapshoty
├── commands/                # Undo/Redo systém (Command pattern)
├── preferences/             # Nastavení aplikace (zkratky, snap, UI)
└── ui/                      # PySide6 GUI (viewport, panely, průvodce…)
tests/                       # Testovací sada (pytest)
samples/                     # Ukázkové projekty
docs/                        # Dokumentace
```

## Technický stack

* **GUI** — PySide6 (Qt 6)
* **CAD jádro** — OpenCascade (pythonocc-core) pro B-Rep tělesa, booleany, revolve
* **Triangulace** — OpenCascade mesh + numpy fallback
* **Export** — reportlab (PDF), svgwrite (SVG), ezdxf (DXF), Pillow (PNG)

## Cílové skupiny

- **Papíroví modeláři** — detail, přesnost, chlopně, značení, textury
- **Studenti architektury / designu** — rychlé hmotové modely v měřítku
- **Školy a kroužky** — jednoduché ovládání, výukové šablony
- **Makers (plotr/laser)** — DXF vrstvy cut/score, přesné čáry a tolerance
- **Muzea / turistické atrakce** — generování modelů památek (suvenýry)

## Licence

MIT
