# ArchPapercraft Studio — Uživatelská příručka

**Verze 0.2.0** · Česky

---

## Obsah

1. [Instalace a spuštění](#instalace-a-spuštění)
2. [Rozhraní aplikace](#rozhraní-aplikace)
3. [Nový projekt](#nový-projekt)
4. [Přidávání objektů](#přidávání-objektů)
5. [Editace objektů](#editace-objektů)
6. [Workflow: Od modelu k vystřihovánce](#workflow-od-modelu-k-vystřihovánce)
7. [Export do PDF / SVG / DXF](#export-do-pdf--svg--dxf)
8. [Měřítko a jednotky](#měřítko-a-jednotky)
9. [Klávesové zkratky](#klávesové-zkratky)
10. [Nastavení](#nastavení)
11. [Formát projektu](#formát-projektu)
12. [Tipy a řešení problémů](#tipy-a-řešení-problémů)

---

## Instalace a spuštění

### Požadavky

- Python 3.11 nebo novější
- Operační systém: Windows, Linux, macOS

### Instalace

```bash
# Klonování repozitáře
git clone https://github.com/DaliborZ-tech/papercraft.git
cd papercraft

# Vytvoření virtuálního prostředí
python -m venv .venv

# Aktivace (Windows)
.venv\Scripts\activate

# Aktivace (Linux / macOS)
source .venv/bin/activate

# Instalace závislostí
pip install -e ".[all]"
```

### Spuštění

```bash
python -m archpapercraft
```

### Volitelné závislosti

| Balíček | Účel |
|---------|------|
| `pythonocc-core` | CSG operace (otvory ve zdech) |
| `ezdxf` | Export do formátu DXF |

```bash
pip install pythonocc-core   # CSG
pip install ezdxf             # DXF export
```

---

## Rozhraní aplikace

Hlavní okno se skládá z těchto částí:

```
┌──────────────────────────────────────────────────────┐
│  Menu  │  Nový │ Otevřít │ Uložit │ Zpět │ Znovu    │
├────────┼──────────────────────────────┼───────────────┤
│        │                              │  Vlastnosti   │
│ Objekty│      3D Viewport             ├───────────────┤
│ (strom)│    (orbita / posuv / zoom)   │  Vystřihová-  │
│        │                              │  nce           │
│        │                              │  (workflow)    │
├────────┴──────────────────────────────┴───────────────┤
│  Stavový řádek                                        │
└──────────────────────────────────────────────────────┘
```

### Panel Objekty (vlevo)
Zobrazuje hierarchii scény — všechny přidané objekty s názvem a typem.
Kliknutím vyberete objekt pro editaci ve panelu Vlastnosti.

### 3D Viewport (uprostřed)
Interaktivní 3D náhled scény.

- **Střední tlačítko myši** — orbita (otáčení pohledu)
- **Shift + střední tlačítko** — posuv (pan)
- **Pravé tlačítko** — alternativní posuv
- **Kolečko myši** — přiblížit / oddálit

### Panel Vlastnosti (vpravo nahoře)
Zobrazuje transformaci (pozice, rotace) a parametry vybraného objektu.
Změny se aplikují okamžitě.

### Panel Vystřihováníka (vpravo dole)
Čtyřkrokový workflow pro vytvoření papírové vystřihováníky:
1. **Analýza ploch** — klasifikace povrchů (ploché / rozvinutelné / nerozvinutelné)
2. **Švy** — automatické umístění řezů
3. **Rozložení** — rozvinutí do 2D
4. **Export** — uložení do PDF / SVG / DXF

---

## Nový projekt

1. **Soubor → Nový projekt** (`Ctrl+N`)
2. Vytvoří se prázdná scéna s výchozím nastavením:
   - Jednotky: metry (`m`)
   - Měřítko: `1:100`
   - Papír: A4, gramáž 160 g/m²

---

## Přidávání objektů

Menu **Přidat** nabízí dvě kategorie:

### Primitiva
| Objekt | Popis |
|--------|-------|
| Kvádr | Základní box |
| Válec | Cylinder |
| Kužel | Kónus |
| Koule | Sféra (rozloženo na gore / kroužky) |
| Torus | Prstenec |

### Architektonické objekty
| Objekt | Popis |
|--------|-------|
| Zeď | Plochá stěna s nastavitelnou výškou a tloušťkou |
| Otvor (okno/dveře) | Booleovský výřez ze zdi (vyžaduje pythonocc-core) |
| Střecha (sedlová) | Dvousklonná střecha |
| Gotické okno | Lomený oblouk s ostěním a středovým sloupkem |
| Cibulovitá kopule | Cibulovitá kopule pravoslavného typu |
| Podlaží / deska | Vodorovná podlažní deska |
| Věž | Válcová věž |
| Opěrný pilíř | Gotický opěrný pilíř |

### Gotické okno — parametry
| Parametr | Výchozí | Popis |
|----------|---------|-------|
| `width` | 1.2 m | Šířka otvoru |
| `height` | 2.8 m | Celková výška včetně oblouku |
| `depth` | 0.35 m | Hloubka ostění |
| `splay_angle` | 10° | Úhel rozevření ostění |
| `arch_segments` | 16 | Rozlišení oblouku |
| `frame_width` | 0.10 m | Šířka kamenného rámu |
| `mullion` | Ano | Přidat středový sloupek |
| `mullion_width` | 0.06 m | Šířka sloupku |

---

## Editace objektů

1. Klikněte na objekt v panelu **Objekty** (strom)
2. V panelu **Vlastnosti** upravte:
   - **Pozice X / Y / Z** — posunutí v prostoru
   - **Rotace X / Y / Z** — otočení (stupně)
   - **Parametry** — specifické pro typ objektu (rozměry, segmenty, …)
3. Změny se projeví okamžitě ve viewportu

---

## Workflow: Od modelu k vystřihovánce

### Krok 1 — Analýza ploch

Klikněte **Analyzovat** v panelu Vystřihováníka.

Systém klasifikuje všechny povrchy modelu do tří kategorií:
- **Ploché** — rovné plochy, ideální pro papír
- **Rozvinutelné** — zakřivené plochy, které lze rozvinout bez deformace (válce, kužely)
- **Nerozvinutelné** — koule, torus — vyžadují aproximaci (gore / kroužky)

### Krok 2 — Švy (řezy)

Klikněte **Automatické švy**.

Algoritmus umístí řezy na optimální hrany tak, aby:
- Části se vešly na papír (A4 v daném měřítku)
- Bylo minimum švů
- Řezy šly po přirozených hranách objektu

### Krok 3 — Rozložení

Vyberte strategii a klikněte **Rozložit**:

| Strategie | Použití |
|-----------|---------|
| **Exact** | Ploché a rozvinutelné povrchy — přesné rozvinutí |
| **Gores** | Koule / kopule — svislé pruhy (poledníky) |
| **Rings** | Koule / válce — horizontální kroužky |
| **Facets** | Trojúhelníkové výseče — nejuniverzálnější |

**Segmenty** — počet dělení pro zakřivené plochy (4–64).

### Krok 4 — Export

Klikněte **Exportovat PDF** (nebo SVG / DXF) a zvolte umístění souboru.

Export obsahuje:
- **Řezací čáry** (plné) — stříhat nůžkami / řezákem
- **Ohybové čáry** (čárkované) — přehnout
- **Chlopně** (šedé) — nanést lepidlo
- **Značky párování** — která chlopeň kam patří
- **Měřítko** — uvedeno v záhlaví stránky
- **Číslo stránky** — „Strana X / Y"

---

## Měřítko a jednotky

### Jak funguje měřítko

Model se vytváří v **metrech** (výchozí). Při exportu se přepočítá na papír
podle zvoleného měřítka:

| Měřítko | 1 metr modelu → na papíře |
|---------|---------------------------|
| 1:100 | 10 mm |
| 1:50 | 20 mm |
| 1:25 | 40 mm |
| 1:10 | 100 mm |

**Příklad**: Gotické okno 1.2 × 2.8 m v měřítku 1:100 → výstřižek cca 12 × 28 mm.
V měřítku 1:25 → 48 × 112 mm.

### Změna měřítka

Měřítko se nastavuje v `ProjectSettings.scale`. Výchozí hodnota je `"1:100"`.
Podporovaná měřítka: `1:1`, `1:10`, `1:25`, `1:50`, `1:100`, `1:200`, `1:500`.

### Jednotky

Podporované jednotky: `mm`, `cm`, `m`. Výchozí: `m` (metry).
Interně vše pracuje v milimetrech.

---

## Klávesové zkratky

| Zkratka | Akce |
|---------|------|
| `Ctrl+N` | Nový projekt |
| `Ctrl+O` | Otevřít projekt |
| `Ctrl+S` | Uložit |
| `Ctrl+Shift+S` | Uložit jako |
| `Ctrl+Z` | Zpět |
| `Ctrl+Y` | Znovu |
| `Delete` | Smazat objekt |
| `Ctrl+D` | Duplikovat objekt |
| `Ctrl+A` | Vybrat vše |
| `Numpad 7` | Pohled shora |
| `Numpad 1` | Pohled zepředu |
| `Numpad 3` | Pohled z boku |
| `Numpad 5` | Perspektiva |
| `Numpad .` | Zaostřit na výběr |
| `G` | Přepnout mřížku |
| `S` | Přepnout přichytávání |
| `Ctrl+E` | Export |
| `Alt+F4` | Ukončit |

---

## Nastavení

Nastavení se ukládá do `~/.archpapercraft/settings.json`
(Windows: `%APPDATA%\archpapercraft\settings.json`).

### Kategorie

**Obecné**: jazyk, jednotky, téma, interval autosave, hloubka undo.

**Viewport**: barvy pozadí / mřížky / výběru / švů, citlivost myši.

**Přichytávání (Snap)**: mřížka, vrcholy, hrany, osy, úhlový krok.

**Export**: výchozí formát, papír, gramáž, tvar chlopní, rozlišení PNG.

**Klávesové zkratky**: viz tabulka výše.

---

## Formát projektu

Projekty se ukládají s příponou `.apcraft` (JSON).

Struktura:
```json
{
  "settings": {
    "units": "m",
    "scale": "1:100",
    "paper": "A4",
    "paper_margin_mm": 10.0,
    "paper_bleed_mm": 3.0,
    "paper_grammage": 160
  },
  "scene": {
    "root": {
      "name": "Scene",
      "children": [
        {
          "name": "Gothic Window",
          "node_type": "GOTHIC_WINDOW",
          "parameters": { "width": 1.2, "height": 2.8 },
          "transform": { "position": [0, 0, 0], "rotation": [0, 0, 0] }
        }
      ]
    }
  }
}
```

### Autosave

Automatické ukládání probíhá každé 2 minuty. Záloha se ukládá do:
`~/.archpapercraft/autosave/`

### Crash reporty

Pokud aplikace spadne, crash report se zapíše do:
`~/.archpapercraft/logs/crash_*.txt`

---

## Tipy a řešení problémů

### Černý viewport
Zkontrolujte, že je nainstalován PyOpenGL:
```bash
pip install PyOpenGL
```

### Export vypadá prázdný
- Zkontrolujte měřítko — v 1:100 jsou malé objekty téměř neviditelné
- Zkuste větší měřítko (1:25 nebo 1:10)
- Ujistěte se, že jste provedli celý workflow (Analyzovat → Švy → Rozložit → Export)

### CSG nefunguje (booleovské operace)
Nainstalujte `pythonocc-core`:
```bash
pip install pythonocc-core
```

### Kruhové plochy nejdou rozložit
Použijte strategii **Gores** (poledníky) nebo **Rings** (kroužky) místo Exact.

### Velké modely se nevejdou na papír
- Zmenšete měřítko (1:200, 1:500)
- Použijte větší papír (A3, A2)
- Snižte počet segmentů

### Kde najdu logy?
```
~/.archpapercraft/logs/
```

Pokud tento adresář není dostupný, logy se zapíší do dočasného adresáře
systému (`%TEMP%\archpapercraft_logs\`).

---

*ArchPapercraft Studio v0.2.0 — © 2025*
