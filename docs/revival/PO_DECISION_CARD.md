# Rozhodnutí vlastníka: konkrétní P2

P0/P1 přináší skutečně spuštěnou a proměřenou baseline, diagnostické reprodukce a návrh obnovy. Nevznikla ještě nová použitelná vystřihovánka. Technický verdikt a přesný review pin jsou v [REVIEW_REPORT.md](REVIEW_REPORT.md); PO akceptace a release jsou samostatné a zůstávají čekající.

**Doporučení:** přijmout variantu B a [P2_IMPLEMENTATION_CONTRACT v1.0](P2_IMPLEMENTATION_CONTRACT.md): zachovat Python/PySide6 a nahradit geometricko-papírovou pipeline parametrickými panely a explicitními spoji. [Srovnání A/B/C](ARCHITECTURE_DECISION.md), [UX návrh](UX_CONTRACT.md) a [šest klikacích stavů](ux-prototype.html).

Co P2 dodá:

- Rozměrově správný panelový dům a propojený klikový výběr 3D ↔ 2D.
- Ruční cut/fold, chlopně A/B/off/šířka/zkosení a undo/redo.
- Ruční více A4 stránek, odkládací plocha, posun/rotace myší i číselně, snap, samostatné zámky.
- Zachování nedotčené autorské práce při změně střechy, viditelný stale stav a bezpečný save/open.
- SVG všech stránek se skupinami celých dílů a rolemi, vektorové PDF, český font, 100mm kalibrace a skutečný editor proof.
- Windows demo, nezávislé review a konkrétní balík pro následný fyzický výtisk P3.

Konkrétní tradeoff: první nový model je dům z rovinných panelů bez děr, ne obecný CAD. Starý sample s bání/gotikou se zachová v odděleném read-only legacy pohledu; úplná migrace těchto typů není slíbena v P2. Nejasná data se nesmějí tiše přepsat. Válce/kužely/báně, okna/ostění, materiálové kompenzace, grafika a návod zůstávají v roadmapě všech16epic. Automatický packing a dlaždice nejsou nutné pro první ruční editor.

Plánovací rozsah 24–40 soustředěných člověkodnů včetně review/oprav, s přiznanou nejistotou. Rozpad a podklady v kontraktu; nejde o slíbené datum. Původní213PASS nevylučuje závažné vady: cílených6testsFAIL, 10geometrických reprodukcí, mimo jiné měřítko sample ×1000 a stale rozvin. [Baseline a jak ověřit](BASELINE_REPORT.md), [nálezy](FINDINGS.md), [Windows repro](WINDOWS_REPRO.md).

Jediné požadované produktové rozhodnutí po uzavření revize: **Přijímáte tento P2 kontrakt v1.0 včetně vymezené kompatibility a doporučené varianty B?** Přijetí autorizuje lokální produkční P2 v tomto rozsahu. Neautorizuje push, PR, merge ani release. Fyzickou sestavitelnost přijme člověk až po měřeném výtisku a stavbě v P3; žádný agent ji nyní neprohlašuje za hotovou.

Záznam: `PO verdict = PENDING`, `GATE-P2 = NOT_ACCEPTED`, `release = NOT_READY`.
