# Rozhodnutí vlastníka: konkrétní P2

> Aktualizace 6. 11. 2026: tento dokument zachov?v? stav p?vodn?ho P0/P1 a v1.1. V1.1 byla skute?n? p?ijata vlastn?kem, potom byl c?l roz???en. Aktivn? n?vrh [P2 v1.2](../p2/v1.2/README.md) a jedin? queue ur?uj? nyn?j?? rozsah/stav; review a baseline piny z?st?vaj? historick?. Povinn? mixed-part testy se neru??. Push n?vrhu nen? jeho produktov? p?ijet?.

P0/P1 přináší skutečně spuštěnou a proměřenou baseline, diagnostické reprodukce a návrh obnovy. Nevznikla ještě nová použitelná vystřihovánka. Technický verdikt a přesný review pin jsou v [REVIEW_REPORT.md](REVIEW_REPORT.md); PO akceptace a release jsou samostatné a zůstávají čekající.

Nezávislé review: **APPROVED_IN_SCOPE**, CODE `5b01bb26e6b4c3da8d75afdca19cad5d6b43d576`. Dva drobné nálezy opraveny a uzavřeny, žádný zásadní otevřený nález v P0/P1. Všechny dostupné nezávislé části prvního balíku jsou technicky dokončené.

**Doporučení:** přijmout variantu B a [P2_IMPLEMENTATION_CONTRACT v1.1](P2_IMPLEMENTATION_CONTRACT.md): zachovat Python/PySide6 a nahradit geometricko-papírovou pipeline parametrickými panely a explicitními spoji. Verze 1.1 na žádost vlastníka stanovuje [kotvu společného dílu stěna–střecha](MIXED_PART_LAYOUT_CONTRACT.md): zachovat body ukotvené stěny, invalidovat celý změněný díl a nevydávat pohyb závislých ploch za zachovaný stav. [Srovnání A/B/C](ARCHITECTURE_DECISION.md), [UX návrh](UX_CONTRACT.md) a [šest klikacích stavů](ux-prototype.html).

Co P2 dodá:

- Rozměrově správný panelový dům a propojený klikový výběr 3D ↔ 2D.
- Ruční cut/fold, chlopně A/B/off/šířka/zkosení a undo/redo.
- Ruční více A4 stránek, odkládací plocha, posun/rotace myší i číselně, snap, samostatné zámky.
- Zachování nedotčené autorské práce při změně střechy, viditelný stale stav a bezpečný save/open.
- SVG všech stránek se skupinami celých dílů a rolemi, vektorové PDF, český font, 100mm kalibrace a skutečný editor proof.
- Windows demo, nezávislé review a konkrétní balík pro následný fyzický výtisk P3.

Konkrétní tradeoff: první nový model je dům z rovinných panelů bez děr, ne obecný CAD. Starý sample s bání/gotikou se zachová v odděleném read-only legacy pohledu; úplná migrace těchto typů není slíbena v P2. Nejasná data se nesmějí tiše přepsat. Válce/kužely/báně, okna/ostění, materiálové kompenzace, grafika a návod zůstávají v roadmapě všech16epic. Automatický packing a dlaždice nejsou nutné pro první ruční editor.

Plánovací rozsah 24–40 soustředěných člověkodnů včetně review/oprav, s přiznanou nejistotou. Je to pracovní odhad lidské pracnosti, nikoli doba běhu agentů; po PC-006 se přepočítá podle skutečných výsledků. Rozpad a podklady v kontraktu; nejde o slíbené datum. Původní213PASS nevylučuje závažné vady: cílených6testsFAIL, 10geometrických reprodukcí, mimo jiné měřítko sample ×1000 a stale rozvin. [Baseline a jak ověřit](BASELINE_REPORT.md), [nálezy](FINDINGS.md), [Windows repro](WINDOWS_REPRO.md).

Jediné požadované produktové rozhodnutí po uzavření revize: **Přijímáte tento P2 kontrakt v1.1 včetně vymezené kompatibility a doporučené varianty B?** Přijetí autorizuje produkční P2 v tomto rozsahu a dosud neproběhlo. Samostatná oprava realizačního mandátu z 5. listopadu 2026 již autorizuje integraci a push dokončených, ověřených a nezávisle schválených balíků v autorizovaném rozsahu na `master` bez další rutinní žádosti. Integrace P0 + P1 tuto produktovou otázku neuzavírá. Produkční release zůstává samostatný. Fyzickou sestavitelnost přijme člověk až po měřeném výtisku a stavbě v P3; žádný agent ji nyní neprohlašuje za hotovou.

Záznam: `PO verdict = PENDING`, `GATE-P2 = NOT_ACCEPTED`, `release = NOT_READY`.
