# ArchPapercraft Studio — Kompletní dokumentace

## 1. Obchodní požadavky (BRD)

### 1.1 Název produktu
**ArchPapercraft Studio**

### 1.2 Vize
> „Jedna aplikace, ve které postavím 3D model historické/moderní architektury
> a jedním klikem dostanu profesionální vystřihovánku (PDF/SVG/DXF) v měřítku,
> se značením, chlopněmi a návodem."

### 1.3 Problém trhu
- Modelování a papercraft jsou dnes oddělené (FreeCAD/Blender/SketchUp + Inkscape + doplňky)
- Zakřivené střechy (cibulky/kupole) a složitá ostění se řeší ručně s chybami
- Uživatelé chtějí: měřítko, vyrobitelnost, jasný návod, opakovatelnost, export pro tisk i plotr

### 1.4 Cílové skupiny
| Skupina | Potřeby |
|---|---|
| **Papíroví modeláři** | Detail, přesnost, chlopně, značení, textury |
| **Studenti architektury / designu** | Rychlé hmotové modely v měřítku |
| **Školy / kroužky** | Jednoduché ovládání, výukové šablony |
| **Makers (plotr/laser)** | DXF vrstvy cut/score, přesné čáry a tolerance |
| **Muzea / turistické atrakce** | Generování modelů památek (suvenýry) |

### 1.5 Hlavní přínosy
- **Papercraft-first** modelář: při modelování hlídá, co jde vyrobit z papíru
- Speciální nástroje pro architekturu: gotika/baroko (okna, ostění, cibulky)
- Automatizace: unfolding, tabs, číslování, layout, export, build guide
- Robustní projekty: knihovny prvků + presety + šablony

### 1.6 Metriky úspěchu (KPI)
- Time-to-first-export: jednoduchý dům → PDF do 10–15 min
- Úspěšné sestavení bez úprav u „hranatých" modelů > 90 %
- Počet exportů na aktivního uživatele / měsíc
- Retence D7 a D30
- NPS / spokojenost s rozkladem a návodem

### 1.7 Scope
**In scope:** 3D modelování (architektura-first), papercraft generátor, projekty/šablony/knihovny

**Out of scope (MVP):** Full CAD constraints, BIM/IFC, fotorealistické rendery

---

## 2. Produktové požadavky (PRD)

### 2.1 Platforma
- Windows + Linux (offline)
- Instalátor + portable verze
- Projektový formát: složka projektu (JSON + cache + exporty)

---

## 3. Kompletní seznam funkcí

### 3.1 Modelář (3D tvorba)

#### A) Scéna, ovládání, ergonomie
- Orbit / Pan / Zoom, focus on selection
- Pohledy: Shora / Zepředu / Z boku / Perspektiva
- Mřížka + jednotky + měřítko v projektu
- Přichytávání (Snap): na mřížku, body, hrany, osy, úhlový snap (5°, 15°)
- Gizma: Posun / Otočení / Změna velikosti
- Měření vzdáleností a úhlů (3D i 2D)
- Undo/Redo (hluboký zásobník)
- Vrstvy / Skupiny
- Strom objektů (hierarchie)
- Zamknutí / Skrytí / Izolace objektů
- Řez scénou (section cut) pro kontrolu ostění a interiéru

#### B) Základní geometrie
- Primitiva: Kvádr, Válec, Kužel, Koule, Torus
- 2D tvary: Obdélník, Kružnice, Lomená čára (pro profily a půdorysy)
- Tažení profilu (Extrude)
- Rotace profilu (Revolve) — klíč pro cibulky
- Loft (později) — pro složitější střechy
- Sweep (později) — římsy, profily, ozdoby
- Boolean: Sjednocení, Odečtení, Průnik
- Zkosení / Zaoblení (později)

#### C) Parametrické architektonické objekty
- **Zeď**: délka, výška, tloušťka, segmenty, vazba na půdorysnou čáru
- **Deska podlahy**: tloušťka
- **Otvor**: obdélník, oblouk, lomený oblouk; parapet, nadpraží
- **Okno/Dveře**: rám, šambrána, dělení tabulkami
- **Gotické okno**: lomený oblouk (ogive), špalety se splay angle, multi-facet
- **Střecha**: sedlová / valbová / pultová; sklon, přesahy, tloušťka, římsa
- **Věž**: polygonální/válcový půdorys, patra, římsy, okna opakovaně
- **Cibulová báně**: profil + revolve, presety (barokní, ruská, kupole)
- **Opěrný pilíř** (gotika, později)
- **Klenby** (později)

#### D) Knihovna prvků a šablony
- Prohlížeč knihovny (drag & drop)
- Ukládání vlastních presetů
- Balíčky stylů: gotika, baroko, renesance

#### E) Kontrola vyrobitelnosti za běhu
- Min. rozměr detailu v měřítku
- Min. šířka chlopně
- Varování při překročení A4/A3
- Indikátor „papercraft readiness" ve stromu

### 3.2 Papercraft (Unfold)

#### A) Analýza geometrie
- Klasifikace ploch: flat / developable / non-developable
- Detekce: self-intersections, non-manifold hrany, příliš krátké hrany
- Kontrola měřítka: detail < X mm → doporučení zjednodušení

#### B) Dělení modelu (Švy / Řezy)
- Automatické švy: ostré hrany, max velikost dílu, pravidla pro architekturu
- Manuální editor: klik na hranu, paint mode, zamknutí švů

#### C) Režimy rozkladu
- Přesný rozvin (roviny, vyvinutelné plochy)
- Přibližný rozvin (mesh cut + flatten pro fazetky)
- Cibulka: Góry (+ segmenty + gap), Prstence, Fazety (K × M)

#### D) Chlopně (Tabs)
- Typy: rovné, zkosené, zubaté (tooth)
- Vnitřní vs vnější
- Parametry: šířka, výška, skosení rohů, tolerance dle gramáže
- Pravidla: jen na vybrané skupiny, vypnutí u krátkých hran
- Zářezy proti krabacení (relief cuts)
- Režim „jen značky lepení" (bez chlopní)

#### E) Značení a instrukce
- Řezné / přehybové čáry (mountain / valley / rylka)
- Číslování dílů (Part ID) a hran (Edge match ID)
- Orientační značky (šipky, „tato strana nahoru", přední/zadní)
- Generátor stavebního návodu: legenda, seznam dílů, tabulka párování, pořadí

#### F) Rozmístění / Packing
- Auto packing: min. stránek, rotace 0/90/180/270, okraje + bezpečná zóna
- Manuální editor layoutu: drag & drop, zámek pozice
- Formáty: A4 / A3 / Letter
- Dlaždicový tisk (velký díl přes více A4)
- Optimalizace pro plotr (min. přejezdů, později)

#### G) Export
- **PDF**: přesné měřítko, vrstvy (cut/fold/tabs/labels)
- **SVG**: vrstvy jako groups, kompatibilita s Inkscape
- **DXF**: layers CUT / SCORE / ENGRAVE / LABEL
- **PNG**: náhled pro sdílení

### 3.3 Textury / vzhled (volitelné)
- Barevné výplně dílů (základ)
- Fasádní skiny (později)
- Jednoduchý editor materiálů
- Import bitmapy / UV mapping (později)

### 3.4 Projekt a produktivita
- Ukázkové projekty (domeček, kaple, kostelní věž)
- Šablony: „1:100 A4 quick build", „1:72 detail"
- Verzování projektu: save points / snapshoty
- Autosave + recovery
- Hlášení pádů + prohlížeč logů
- Exportní balíček projektu (zip)

### 3.5 QA / Debug / Developer
- Geometrický inspektor (normály, non-manifold, švy overlay, heatmapa deformace)
- Deterministický export (stejný vstup → stejné ID dílů)

---

## 4. Nefunkční požadavky

| Oblast | Požadavek |
|---|---|
| **Kvalita** | Stabilita, jasné chybové hlášky, deterministické číslování |
| **Výkon** | Plynulý viewport do ~200k tri, unfold+packing do 30–60 s |
| **Kompatibilita** | Windows + Linux, exporty pro Inkscape/Illustrator/CAD |
| **Bezpečnost** | Offline, žádný cloud, čitelný projektový formát |

---

## 5. Roadmap

### MVP
- **Modelář**: Zeď, Otvor (rect + gotický), Střecha (sedlová), Cibulka, Deska, Věž
- **Mřížka/Snap**, strom objektů, transformace, Undo/Redo
- **Analýza** + švy (auto + manuální)
- **Rozklad**: flat + góry pro cibulku
- **Chlopně** + číslování + jednoduchý stavební návod
- **Packing** A4 + export PDF + SVG + PNG

### V1
- Střecha: valbová/pultová; Prstence pro cibulku
- Manuální editor layoutu; DXF export
- Dlaždicový tisk; Knihovna a presety (gotika/baroko)
- Lepší stavební návod (tabulka hran, pořadí)

### V2
- Fasádní skiny / textury
- Fazetový mesh unfold pro obecné tvary
- Klenby, opěrné pilíře, římsy (sweep)
- Heatmapa deformace
- Plugin export pipeline

---

## 6. Architektura modulů

### core_geometry
Primitiva (MeshData), operace (extrude, revolve, boolean), validace meshe.
Fallback na numpy mesh když OpenCascade není dostupný.

### scene_graph
Strom uzlů (SceneNode), transformace (pozice/rotace/škálování),
vrstvy, skupiny, zamykání/skrytí objektů.

### arch_presets
Parametrické generátory: zeď, otvor, střecha, gotické okno,
cibulová báně, deska podlahy, věž.

### paper_analyzer
Klasifikace povrchů (BFS flood-fill dle dihedrálního úhlu),
detekce non-manifold a self-intersections, kontroly měřítka.

### seam_editor
Graf švů na meshu, automatické švy, manuální editor,
zamykání švů, paint mode.

### unfolder
Přesný BFS edge-unfolding, góry (vertikální pásy), prstence
(horizontální pruhy), fazetový rozklad.

### tabs_generator
Rovné/zkosené/zubaté chlopně, přehybové čáry (mountain/valley),
číslování, orientační značky, generátor stavebního návodu.

### layout_packer
Shelf-packing algoritmus, dlaždicový tisk, rotace dílů,
manuální editor rozmístění.

### exporter
PDF (reportlab), SVG (svgwrite), DXF (ezdxf), PNG (Pillow).

### project_io
JSON formát .apcraft, autosave, recovery, snapshoty,
exportní balíček (zip).

### commands
Undo/Redo systém (Command pattern) s hlubokým zásobníkem.

### preferences
Globální nastavení aplikace (zkratky, snap, UI škálování, jazyk).

### ui
PySide6 — hlavní okno, 3D viewport (OpenGL), strom objektů,
panel vlastností, papercraft panel, průvodce projektem,
knihovna prvků, geometrický inspektor, měření.

---

## 7. Epiky a backlog

| # | Epika | Stav |
|---|---|---|
| 1 | Core App & Projekt | MVP |
| 2 | Viewport & UI | MVP |
| 3 | Geometry Kernel Integration | MVP |
| 4 | Modeling Basics | MVP |
| 5 | Architektonické nástroje | MVP |
| 6 | Papercraft analýza | MVP |
| 7 | Švy / Řezy | MVP |
| 8 | Unfold Engine | MVP |
| 9 | Chlopně & Značení | MVP |
| 10 | Layout & Packing | MVP |
| 11 | Export | MVP |
| 12 | Generátor stavebního návodu | MVP |
| 13 | Knihovna & Presety | V1 |
| 14 | Textury / Skiny | V2 |
| 15 | QA & Tooling | Průběžně |

---

## 8. Definice „hotovo" (DoD)

- Funkce má acceptance criteria + testovací scénáře
- Export sedí v měřítku (kontrola referenčním pravítkem v PDF)
- UI neobsahuje dead ends (průvodce dokončitelný)
- Crash log při pádu
- Ukázkový projekt, který jde reálně vystřihnout a slepit
