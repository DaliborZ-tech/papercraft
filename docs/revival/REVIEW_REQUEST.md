# Vstup nezávislé revize P0/P1

Problém: obnovit produkt se skutečně správnou geometrií a editovatelnými výstupy; současný desktop se spustí a testy jsou zelené, ale diagnostika dokládá chyby. Reviduje se úplnost a pravdivost P0/P1 i připravenost konkrétního P2 kontraktu, nikoli schválení implementovaného produktu.

Normativní zdroje: root 02_CODEX_MANDATE,03_EPICS_AND_ROADMAP,04_ACCEPTANCE_AND_VERIFICATION a jediná05_WORK_QUEUE. Baseline SHA `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`. CODE SHA předá integrátor z lokálního analytického commitu; reviewer jej zapíše přesně do REVIEW_REPORT včetně případného následného opravného pinu. Diff: `git diff <baseline>..<CODE_SHA>`, produkce `src/` a původní `tests/` musí zůstat beze změny.

Ověřit bootstrap hash preservation/root/remote, oddělení core a desktopu, přesné počty/exit/time, skutečné nové/uložit/otevřít/švy/unfold/export a evidence platného GL, červené diagnostiky bez maskování. Geometrie minimálně vlastní analytický pozitivní, negativní a hraniční případ: cone lengths vs area, panel hranice/cycle coverage, nonmanifold, tab winding/polarity/permutace, tolerance. Nestačí přečíst integrátorovo PASS.

Kontrakt musí zachovat všechny16epic a61AC, P2 linked selection/manual seams/tabs/layout/SVG/PDF, konkrétní kompatibilitu, identity/revision invalidaci, neprominutelnou integritu, správný SVG grouping a PDF vektorový/tiskový význam. Ověřit lehký UX prototyp všech6stavů a přiměřenost odhadů s nejistotami. Novější schema, díry/near-cylinder a printed-side polarity nemají dostat falešný PASS. Zkontrolovat pending interoperability/fyzický proof a oddělení AGENT_VERIFIED od PO_ACCEPTED.

Doporučené příkazy: `geometry_probe.py`, `run_probe.py core_probe`, `run_probe.py integration_probe`; core runner ukládá red diagnostics exit1 zvlášť. Desktop rerun pouze do nového adresáře, souběžný native-dialog probe neprovádět. Full legacy suite už běžela a nemá se bez nové nejistoty opakovat. Reviewer může mít vlastní read-only experimenty a vlastní evidence pod `evidence/reviewer-*`; jeho výhradní zápis je REVIEW_REPORT + tyto evidence, ostatní opravy provádí integrátor.

Verdikt APPROVED_IN_SCOPE / CHANGES_REQUIRED / INCOMPLETE_EVIDENCE; každá vada severity, důkaz, dopad a přesná podmínka uzavření. Produkční vady ponechané pro P2/E11 nejsou automaticky blokující vadou P1, pokud mají věrnou reprodukci, mez a kontrakt. Chybějící povinný P1 výstup je problém této revize. Neudělit PO ani release approval.
