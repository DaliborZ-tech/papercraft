# Changelog

Všechny významné změny projektu jsou dokumentovány v tomto souboru.

Formát je inspirován [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/)
a projekt dodržuje [Sémantické verzování](https://semver.org/lang/cs/).

## [0.2.0] — 2025-01-XX

### Přidáno
- **Průvodce novým projektem** — wizard s výběrem šablony, jednotek, měřítka
- **8 architektonických presetů** — Zeď, Otvor, Střecha, Gotické okno, Cibulovitá kopule, Podlaží, Věž, Opěrný pilíř
- **Gotické okno** — rozeta, ostění se špaletou (`spring_ratio`), kružba (`tracery`)
- **CAD-like UI** — strom objektů → panel vlastností, živá editace parametrů, výběr s podsvícením
- **Undo/Redo systém** — CommandStack s 7 typy příkazů, napojený na UI akce (přidat, smazat, duplikovat)
- **Dialog předvoleb** — záložkový UI dialog (Ctrl+,) pro Obecné, Viewport, Přichytávání, Export, Klávesové zkratky
- **PNG export** — rastrový export rozložených stránek
- **Sestavovací návod** — textový výstup s pořadím lepení a tipy
- **Čísloání stránek a měřítko** — v PDF exportu: „Strana X / Y" + grafické měřítko
- **Crash reporting** — bezpečný zápis crash reportu s fallback řetězcem adresářů
- **Autosave** — automatické ukládání každé 2 minuty
- **Snapshoty** — verzování projektu s časovými razítky
- **Export balíčku** — ZIP archív projektu + snapshotů
- **Kompletní čeština** — veškeré UI, chybové hlášky a docstringy v češtině
- **Uživatelský manuál** — `docs/manual_cs.md` (instalace, workflow, zkratky, řešení problémů)
- **pytest markers** — `core` a `ui` pro selektivní spouštění testů

### Opraveno
- Export měřítko pipeline — správný přepočet `paper_scale = to_mm(1.0, units) × scale_factor`
- Výchozí jednotky projektu změněny na `"m"` (metrický vstup)
- PyOpenGL kompatibilita s PySide6 6.10 (sip → ctypes pointer)
- Gotické okno: `spring_ratio` a `tracery` parametry správně čteny z dict

### Změněno
- Interní geometrie vždy v mm, UI zobrazuje v jednotkách projektu
- Geometrický backend s automatickým fallbackem (OCC → numpy mesh)

## [0.1.0] — 2024-12-XX

### Přidáno
- Základní projektová struktura (scene graph, mesh generace, unfolder, layout packer, exporter)
- 5 primitiv (kvádr, válec, kužel, koule, torus)
- Přesné a přibližné rozložení (exact unfold, facet/gore/ring strategie)
- Bin-packing rozložených dílů na stránky
- PDF a SVG export
- DXF export (volitelný, vyžaduje ezdxf)
- Generátor chlopní (straight, tapered, tooth)
- Automatické umisťování švů (spanning-tree + curvature heuristika)
- 3D viewport s OpenGL (orbita, posun, zoom)
- Nastavení aplikace (JSON, `~/.archpapercraft/settings.json`)
