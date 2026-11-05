# ArchPapercraft Studio — aktivní pracovní instrukce

Komunikuj česky, kód a identifikátory piš anglicky. Produktový mandát je v `02_CODEX_MANDATE.md`, roadmapa v `03_EPICS_AND_ROADMAP.md`, normativní AC v `04_ACCEPTANCE_AND_VERIFICATION.md` a jediná aktivní fronta v `05_WORK_QUEUE.json`.

## Dokončení autorizovaného pracovního balíku

Vlastník 5. listopadu 2026 výslovně autorizoval integraci a push dokončených ucelených balíků na `master`. Po přiměřeném ověření, nezávislé revizi konkrétního commitu a uzavření jejích zásadních nálezů proveď integraci a push bez další rutinní žádosti. Toto pravidlo platí pouze v již autorizovaném produktovém rozsahu.

Před integrací ověř lokální stav, remote a načti aktuální `origin/master`. Pracuj na izolované větvi, zachovej cizí práci i vzdálené změny. Použij fast-forward, je-li možný, jinak standardní merge. Konflikty a věcnou změnu výsledku znovu ověř a nech nezávisle zkontrolovat v potřebném rozsahu. Reviewer musí být jiný agent než autor změny; při dostupné delegaci mu zadej samostatné review. Pokud nezávislá revize chybí, balík není připravený k rutinní integraci.

Nepoužívej reset, clean, force-push, přepis historie ani nevratnou migraci. Po běžném pushi `master` ověř shodu lokálního a vzdáleného SHA a předej GitHub commit i odkazy na výstupy. Pokud push odmítne novější vzdálený stav, znovu jej načti a bezpečně integruj; nepřepisuj jej.

## Produktová brána a meze autorizace

Integrace a push nejsou produktová akceptace ani release. P0 + P1 jsou technicky schválené. Kontrakt P2, varianta B a vymezená kompatibilita nadále čekají na skutečné přijetí vlastníkem. `GATE-P2` zůstává `PO_PENDING`, `accepted_by_owner=false`; nezačínej produkční P2 pouze kvůli integraci na `master`. Budoucí přijetí P2 otevře jeho produktový rozsah; dokončené a nezávisle schválené balíky v něm se pak integrují a pushují podle pravidla výše.

Původní baseline/review a jejich source SHA jsou historické důkazy; neměň je zpětně kvůli novým instrukcím. Aktuální stav a doplňující integrační review eviduj samostatně v `docs/revival/`.
