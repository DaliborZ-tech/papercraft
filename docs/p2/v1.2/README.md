# P2 v1.2 — návrhový balík pro skutečnou autorskou tvorbu

**Dodání PC-006A6.11.2026:** [běžící úsečkový editor a nezávislé ověření](../implementation/PC006A_DELIVERY.md); pokračuje PC-006B. Dokumenty níže zachovávají návrhový základ, celá implementace A/B/C/D ani novice a fyzické přejímky zatím dokončené nejsou. Závěrečný historický model je nově zapsán v PC-010 / AC-AU19.

**Aktuálně přijato vlastníkem 6.11.2026.** [Přijetí a autorizace celého A/B/C/D](ACCEPTANCE_RECORD.md). Implementace začíná PC-006A a navazuje PC-006B; níže je podklad návrhového balíku, nikoli tvrzení dokončeného editoru.

Aktuální produktový cíl: od prázdného projektu kreslit vlastní profily/obrysy, konstruovat otevřené i zakřivené plochy, spojovat je včetně vnitřních stop a lepicích oblastí, vytvářet vlastní chlopně a připravit ručně rozmístěnou vystřihovánku SVG/PDF. Referenční domeček je numerický test, ne základní omezení editoru.

Tento balík obsahuje **analýzu, spustitelné geometrické experimenty a návrh implementace**, nikoli hotovou novou autorskou aplikaci. V1.1 byla vlastníkem skutečně přijata, následný opravný pokyn rozšířil cíl. Nový návrh v1.2, technická revize, implementační ověření, produktová akceptace a fyzická P3 jsou oddělené stavy. Aktuální normativní stav je v [jediné queue](../../../05_WORK_QUEUE.json).

| Dokument | Co rozhoduje nebo dokládá |
|---|---|
| [Přesné upřesnění vlastníka](OWNER_CLARIFICATION.txt) | Úplný podklad včetně A/B/C/D, zachovaný UTF-8 text přílohy |
| [Produktová analýza](PRODUCT_ANALYSIS.md) | Otevřené stavby, základny, výztuhy, přesahy, ostění a chlopně |
| [Kontrakt P2 v1.2](P2_IMPLEMENTATION_CONTRACT.md) | První autorská verze A a celý sjednaný digitální rozsah |
| [Architektura a persistence](ARCHITECTURE.md) | Skici, křivky, trim plochy, assembly vs material, certifikáty a identity |
| [Skutečné geometrické spiky](GEOMETRY_SPIKES.md) | Plochy mezi profily, vnitřní připojení, tabs; důkazy, negativní případy a limity |
| [Autorské UX](AUTHORING_UX.md) | Cesta od prázdného projektu až po layout/export a řešení problémů |
| [Test s novým uživatelem](USABILITY_TEST.md) | Připravený krátký protokol a formulář; skutečné sezení NOT_RUN |
| [Dispozice kódu](CODE_DISPOSITION.md) | Konkrétní reuse/adapt/replace, žádné automatické vyhození dosavadní práce |
| [Akceptace A/B/C/D](ACCEPTANCE.md) | Povinná skutečná UI, IO, rozviny, layout a oba výstupy; nové AC NOT_RUN |
| [Roadmapa](ROADMAP.md) | Zvládnutelné vertikální řezy a zachování všech 16 epic |
| [Odhad a rizika](ESTIMATE_AND_RISKS.md) | Přepočet po prototypu PC-006, širší rozsah, člověkodny a body dalšího přepočtu |
| [Zachování prototypu a evidence](PRESERVATION.md) | Přesný WIP pin, archivní bundle, význam PASS/FAIL a neúplných pokusů |
| [Nezávislá revize](INDEPENDENT_REVIEW.md) | Reviewer odlišný od autorů, konkrétní pin, vlastní reprodukce a opravy |
| [Ověření balíku](VERIFICATION.md) | Přesné source piny, příkazy, výsledky, integrita fronty a obnova archivu |
| [Integrace a publikace](INTEGRATION_REPORT.md) | Kontrola master/remote, bezpečné zachování WIP a skutečný stav push |
| [Dodatek použitelnosti a skills](USABILITY_SKILLS_REPORT.md) | Průřezové AC, čtyři skills, uplatnění a pending účinnost |

První použitelná autorská verze (PC-006A/B) musí sama vytvořit A bez domu-presetu. Celé P2 přidává B ostění mezi profily, C stočený plášť s dělenými chlopněmi a D pravdivé odmítnutí přesného režimu plus použitelnou odvozenou segmentovanou variantu. Přesné rozviny se neslibují pro libovolný loft. Změna střechy společného dílu stále musí zachovat všechny body kořenové stěny na stránce.

Původní produkční aplikace na master se tímto návrhovým balíkem nemění. House-only prototyp je bezpečně uložen v `revival/p2` a v přenosném Git bundle; jeho důkazy jsou uchované v `docs/p2/evidence/`. Pozdější implementace cíleně převezme ověřené transakce, jednotky, kotvy/layout, export a Qt zkušenosti, ale neuzamkne nový formát podle čtyř rozměrů domu. Skutečná fyzická sestavitelnost zůstává předmětem výtisku v P3.
