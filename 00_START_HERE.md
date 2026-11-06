# ArchPapercraft Studio — zadání obnovy projektu

> **Aktuální dodání6.11.2026:** [PC-006A](docs/p2/implementation/PC006A_DELIVERY.md) má běžící autorský editor a nezávisle schválenýCODE4b172e6;443testů a skutečný Windows průchod kSVG/PDF. Pokračuje PC-006B a celý sjednanýA/B/C/D. Vlastníkův závěrečný historický model je zapsán jako PC-010 / AC-AU19, zatím NOT_RUN. Čti [AGENTS](AGENTS.md) a jedinou queue; další odstavce zachovávají historii zadání, nikoli pokyn začít obnovu znovu.

> Vlastník 6.11.2026 výslovně přijal P2 v1.2 včetně UI/UX, skills a použitelnosti a autorizoval celé A/B/C/D. Aktuálně realizuj PC-006A, následně PC-006B a další řezy podle AGENTS a jediné queue. [Záznam přijetí](docs/p2/v1.2/ACCEPTANCE_RECORD.md). Předchozí pending odkazy níže zachycují historickou přípravu.

> Aktuální stav 6. 11. 2026: P0/P1 jsou na master. Vlastník přijal P2 v1.1 a následně zásadně upřesnil cíl. Aktivní návrh je [P2 v1.2 — vlastní autorská tvorba](docs/p2/v1.2/README.md), aktuální návrhový balík PC-012; jeho review/push není PO přijetí nové v1.2. Starší přípravné instrukce níže jsou historický vstup, nikoli pokyn znovu klonovat nebo omezit produkt na dům. Čti nejprve AGENTS a jedinou queue.

Verze 1.0 · 5. listopadu 2026 · vlastník produktu: Dalibor Zálešák.

Aktuální oprava realizačního mandátu: po ověření a nezávislé revizi dokončený ucelený balík v autorizovaném rozsahu integruj a pushni na `master` bez další rutinní žádosti. Podrobný bezpečný postup je v [AGENTS.md](AGENTS.md) a §6 mandátu. Integrace sama není přijetím kontraktu. V1.1/B/kompatibilita byly následně přijaty; nové rozšíření v1.2 se eviduje odděleně.

## Jak balík použít

Otevři VS Code v adresáři, který má být přímo kořenem projektu, a v něm novou Codex session. **Repozitář si naklonuje agent přímo do tohoto otevřeného adresáře, bez další podsložky `papercraft`.** Přilož celý tento balík nebo jej předem umísti do `docs/revival/brief-v1/`; agent musí zvládnout i takto neprázdný adresář bez ztráty souborů. Vlož prompt z `01_START_PROMPT.md`. Agent musí číst také hlavní mandát, epiky a akceptační matici; krátký prompt je pouze vstupní bod.

Balík definuje celou cílovou vizi. První realizační mandát je P0 + P1: skutečná diagnostika produktu, ověření kritických algoritmů, varianty obnovy, konkrétní architektura, UX a připravené implementační zadání P2. P2 má produktovou bránu: po předložení konkrétního kontraktu jej přijme vlastník. Není dovoleno vydávat dokončené dokumenty za oživenou aplikaci. Po přijetí kontraktu se realizuje P2 bez dalšího potvrzování běžných technických kroků.

## Soubory

| Soubor | Úloha |
|---|---|
| `01_START_PROMPT.md` | Text ke vložení do nové session |
| `02_CODEX_MANDATE.md` | Samostatný produktový, technický a ADLC mandát |
| `03_EPICS_AND_ROADMAP.md` | Celá vize v 16 epicích, závislosti a etapizace |
| `04_ACCEPTANCE_AND_VERIFICATION.md` | Přesná akceptační kritéria, numerické kontrakty a demo scénáře |
| `05_WORK_QUEUE.json` | Počáteční fronta úkolů s rozsahem autorizace a podmínkami pokračování |
| `06_SOURCE_MANIFEST.json` | Připnuté zdroje a omezení této přípravy |

Nejprve čti tento soubor, potom prompt, mandát, epiky a akceptaci. Fronta není druhý tracker: v repozitáři se zvolí jediná evidence stavu a tyto položky se do ní převedou bez ztráty ID a kritérií.

## Důležité rozlišení

- V této ChatGPT session byla provedena statická analýza vybraného kódu. Nebyl spuštěn produkt ani testy a nebyl změněn repozitář.
- Základ při přípravě: `master`, `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`. Agent ověří novější stav; nesmí checkout vrátit na tento commit.
- Odhad na hodiny nebo slib dokončení za den by bez runtime baseline byl nepodložený. P0 má dodat skutečné podklady pro odhad práce.
- Předání tohoto balíku k realizaci uděluje níže popsaný pracovní mandát. Samotná žádost o posouzení balíku implementaci neautorizuje.
