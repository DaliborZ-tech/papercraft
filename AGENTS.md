# ArchPapercraft Studio — aktivní pracovní instrukce

Komunikuj česky, kód a identifikátory piš anglicky. Produktový mandát je v `02_CODEX_MANDATE.md`, roadmapa v `03_EPICS_AND_ROADMAP.md`, normativní AC v `04_ACCEPTANCE_AND_VERIFICATION.md` a jediná aktivní fronta v `05_WORK_QUEUE.json`.

## Dokončení autorizovaného pracovního balíku

Vlastník 5. listopadu 2026 výslovně autorizoval integraci a push dokončených ucelených balíků na `master`. Po přiměřeném ověření, nezávislé revizi konkrétního commitu a uzavření jejích zásadních nálezů proveď integraci a push bez další rutinní žádosti. Toto pravidlo platí pouze v již autorizovaném produktovém rozsahu.

Před integrací ověř lokální stav, remote a načti aktuální `origin/master`. Pracuj na izolované větvi, zachovej cizí práci i vzdálené změny. Použij fast-forward, je-li možný, jinak standardní merge. Konflikty a věcnou změnu výsledku znovu ověř a nech nezávisle zkontrolovat v potřebném rozsahu. Reviewer musí být jiný agent než autor změny; při dostupné delegaci mu zadej samostatné review. Pokud nezávislá revize chybí, balík není připravený k rutinní integraci.

Nepoužívej reset, clean, force-push, přepis historie ani nevratnou migraci. Po běžném pushi `master` ověř shodu lokálního a vzdáleného SHA a předej GitHub commit i odkazy na výstupy. Pokud push odmítne novější vzdálený stav, znovu jej načti a bezpečně integruj; nepřepisuj jej.

## Produktová brána a meze autorizace

**Aktuální upřesnění 6. 11. 2026:** vlastník následně zásadně rozšířil cíl o vlastní tvorbu z profilů, otevřené konstrukce, přesahy, vnitřní připojení a zakřivené pláště. Před stabilizací domény/persistence připrav, geometricky prověř a nezávisle zreviduj [P2 v1.2](docs/p2/v1.2/P2_IMPLEMENTATION_CONTRACT.md). Autorizovaný aktuální balík je **PC-012 návrh + spiky + review + integrace/push**, nikoli dokončení užšího presetového editoru jako celého P2. Dřívější přijetí v1.1 zachovej jako historické; nové `GATE-P2` v1.2 je do skutečného přijetí `PO_PENDING`, `accepted_by_owner=false`. Review/push návrhu není PO přijetí v1.2. Nezakládej schvalování běžných technických kroků.

První použitelná autorská verze musí umět ručně vytvořit model A bez domu-presetu; úplné P2 zahrnuje A/B/C/D a skutečné UI→save/reopen→rozvin→ruční layout→SVG/PDF pro podporované řezy. Presety používají tutéž doménu jako ruční konstrukce; otevřený objem je platný. Povinné mixed-part kotvy z v1.1 zůstávají. Produkční schema se neuzavírá na house-only modelu. Rozpracovaný prototyp je zachován v `revival/p2` a v ověřitelném [bundle](docs/p2/archive/p2-v11-prototype.bundle); jeho evidence nedokazuje nové AC. Aktivní zdroje v1.2 mají přednost před omezením rozsahu ve starších v1.0/v1.1 dokumentech. Fyzický proof zůstává P3.

Integrace a push nejsou produktová akceptace ani release. P0 + P1 jsou technicky schválené. **Historie: vlastník 6. listopadu 2026 výslovně přijal kontrakt P2 v1.1, variantu B i mez kompatibility starých projektů a autorizoval PC-006 až PC-010.** [Záznam přijetí](docs/p2/ACCEPTANCE_RECORD.md) rozlišuje přijetí tehdejšího kontraktu od budoucího digitálního předání. Následný výše uvedený opravný mandát mění cílový rozsah na v1.2; historický souhlas není falešné přijetí nového návrhu. Přepočet odhadu po prototypu PC-006 je v `docs/p2/v1.2/ESTIMATE_AND_RISKS.md`; další přepočet po PC-006A/B. Ověřené a nezávisle schválené ucelené balíky v autorizovaném rozsahu průběžně integruj a pushuj podle pravidla výše. Fyzické sestavení a jeho přijetí zůstávají v P3.

Původní baseline/review a jejich source SHA jsou historické důkazy; neměň je zpětně kvůli novým instrukcím. Aktuální stav a doplňující integrační review eviduj samostatně v `docs/revival/`.
