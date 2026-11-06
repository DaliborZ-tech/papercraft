# P2 v1.2 v celé produktové roadmapě

P0/P1 zůstávají dokončenou diagnostikou a návrhem původního řezu. Historické P2 v1.1 se zachovává jako prototyp, ne cílový produkt. P2 v1.2 předchází stabilizaci nové domény; [jediná queue](../../../05_WORK_QUEUE.json) zachovává původní ID a přidává podřezy, nikoli další tracker.

| Pořadí | Přínos a závislost | Co už nesmí čekat na další etapu |
|---|---|---|
| PC-012 | Produktová analýza, geometrické spiky a nezávisle revidovaný návrh | Konstrukční model pro autorské profily/interior attachments před schema freeze |
| PC-006A → PC-006B | Blank sketch → vlastní díl s dírami → celá budova A | Vlastní kreslení, přesahy, základna/výztuha, vlastní chlopně, UI/IO/ruční layout a oba výstupy |
| PC-007A → PC-007B | Oblouky/Bézier, ostění B → stočené pláště C | Profily, korespondence, certifikace rozvinu a dělené chlopně |
| PC-008 | D, varianty a robustní změny A–C | Vysvětlené odmítnutí EXACT i použitelná měřená alternativa, lineage a mixed-part invariance |
| PC-009 → PC-010 | Všechny modely, interoperability a závěrečné review/předání | Žádný model-only PASS, žádné vynechané stránky/role/otvory |
| P3 / PC-011 | Skutečný výtisk, měření a stavba A/B/C a schválené varianty D | Fyzická akceptace konkrétního exportu; screenshot ji nenahrazuje |
| P4–P6 | Rozšiřování komfortu, pokročilé konstrukce a grafika/návod | Zachovat všechny níže uvedené epiky, bez návratu k preset-only tvorbě |

Každý implementační podřez je end-to-end, včetně ručního švu, chlopně, layoutu a obou výstupů v rozsahu svého typu geometrie. Pozdější konsolidace PC-009 není první chvíle, kdy lze z programu exportovat vlastní díl. Žádný cyklus závislostí: rodičovské PC-006 se dokončí po svých dětech, děti nezávisejí na rodiči; PC-007A závisí na dokončeném PC-006, PC-007B na PC-007A a rodič PC-007 se uzavírá po obou. `completed_by` je agregační pravidlo, nikoli dodatečná opačná závislost.

## Zachování a posuny všech 16 epic

| Epic | P2 v1.2 | Další rozsah, který zůstává v produktu |
|---|---|---|
| E01 Obnova/ADLC | PC-012, skutečné spiky, důkazy, review a poučení | Průběžná diagnostika, žádný procesní orchestrátor |
| E02 Konstrukční model | Sketch/curves/trimmed surfaces/assembly, otevřené skořepiny | Pokročilé konstrukční operace, ověřený import/CSG podle potřeby |
| E03 Propojené prostředí | Výběr profilů/povrchů/spojů ve 3D↔2D, kreslení a editace | Rozšířené pohledy, měření, izolace a sekce |
| E04 Švy/rozvin | Ruční cut/fold/smooth bend, přesné rodiny a přiznaná aproximace | Automatické návrhy a složité sítě |
| E05 Spoje/chlopně | EdgePair/SurfaceTrace/GlueRegion, vlastní a dělené tabs, pásek | Pokročilé zámky, nasazovací a odnímatelné spoje |
| E06 Materiál | Papírové mm, tloušťka/vůle a lepicí plocha, varování | Fyzicky ověřené kompenzace a materiálové profily, směr vláken |
| E07 Ruční stránky | A4 obě orientace, tray, drag/numerika/rotace, snap, oba locks | Další formáty, multi-select, rezervované oblasti |
| E08 Validace/automatika | Plný materiálový footprint, physical overflow, kontakt/clearance | Volitelný packing, dlaždice a pokročilé kontroly |
| E09 Výstupy | Editovatelné SVG s křivkami/dírami, vector PDF z téhož snapshotu | DXF/PNG, dlaždicování, další výrobní adaptéry |
| E10 Architektonické prvky | Ručně vytvořená základna, otvory, výztuhy, přesahy, ostění | Knihovna, schodiště, pokročilý terén a hotové styly |
| E11 Zakřivené plochy | Vlastní profily, válce/kužely, doložené loft/extruze, D alternativa | Báně a složitější přesné/aproximační rodiny se samostatným proof |
| E12 Identity/změny | Feature provenance, dependency revisions, frames a varianty aproximace | Produktové varianty, exportní diff a pokročilé mapování |
| E13 Projekty/desktop | Atomická IO, read-only legacy, generický formát po proof, Qt/Windows | Autosave, recovery, balíček assets a distribuce |
| E14 Ověření/stavba | Analytika + skutečné UI + externí editor + pinned review | P3 fyzická stavba každého nového principu a opravy |
| E15 Grafika | Role ARTWORK a oddělené konstrukční cesty v exportu | Potisk, návaznost textur, interní grafika a ověřený round-trip |
| E16 Návod/podsestavy | Názvy dílů, spojů, stránek a ruční montážní poznámky | Obrazový návod, kroky/animace, explicitní model přístupu |

P5 už neodkládá celou vlastní tvorbu ani základní válce, kužely, otvory nebo ostění. Zůstávají v něm pokročilé architektonické rodiny a širší komfort. Nejde o odstranění dalších epic kvůli rozšíření P2.
