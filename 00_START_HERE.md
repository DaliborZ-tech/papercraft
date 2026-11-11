# ArchPapercraft Studio — zadání obnovy projektu

> **Obnoveno vlastníkem 11.11.2026:** pokračuje PC-007A v `revival/p2-loft-integration`. Výkonová komponenta a export na pozadí mají nezávislé review; sjednocený source `b127fc5` má 1128 úspěšných testů a celý skutečný B1 Windows průchod. Následné uložení hustého ostění v Inkscape ale překročilo polohovou i plošnou mez; tato oprava je otevřená. Aktuální stav je v jediné queue a [průběhu loftu](docs/p2/implementation/PC007A_LOFT_PROGRESS.md). Předání z9.11. níže je historické, nikoli aktivní pozastavení.

> **Pozastaveno na žádost vlastníka 9.11.2026, pokračování 10.11.:** čti [navazovací předání](docs/p2/implementation/CONTINUE_2026-11-10.md). Rovinné křivky jsou publikované na `a27cf5a`; nová lokální integrace ostění má skutečné B2/Bézier průchody, zbývá výkonová revize a B1. Dokument rozlišuje přesné lokální větve, kladné důkazy i zachované neúspěchy. Nezačínej obnovu znovu a nepovažuj celé P2 za dokončené.

> **Aktuální přírůstek 9.11.2026:** [Vlastní rovinné oblouky a Bézierovy křivky](docs/p2/implementation/PC007A_PLANAR_DELIVERY.md) mají 908 úspěšných testů, skutečný Windows průchod a oba Inkscape roundtripy na `63ab275`. [Nezávislá revize](docs/p2/implementation/PC007A_PLANAR_INTEGRATION_REVIEW.md) schvaluje tento rovinný podbalík. Celý PC-007A pokračuje prostorovým ostěním B; C/D a historický model zůstávají v rozsahu. Nový uživatel: 0 účastníků, NOT_RUN; fyzický proof: P3. Publikace tohoto přírůstku se eviduje samostatně, není přijetím celé P2.

> **Pokračování 9.11.2026:** [PC-006B — digitální předání A a společného dílu](docs/p2/implementation/PC006B_DELIVERY.md) má celý Windows→save/reopen→layout→SVG/PDF průchod, Inkscape a 630 testů na `eb08f97`; nezávislá revize je v předání. Test s novým člověkem má 0 účastníků a zůstává NOT_RUN. Následuje PC-007A, celý B/C/D a závěrečný historický model zůstávají autorizované. Historické odstavce níže nejsou pokyn začít znovu.

> **Aktuální dodání 6. 11. 2026:** [PC-006A](docs/p2/implementation/PC006A_DELIVERY.md) má běžící autorský editor a nezávisle schválenou produkci `7da2403` včetně opravy C-06. Původních 443 testů doplňuje 55 exportních regresí a nový skutečný Windows → SVG/PDF → Inkscape průchod. Pokračuje PC-006B a celý sjednaný A/B/C/D. Vlastníkův závěrečný historický model je zapsán jako PC-010 / AC-AU19, zatím NOT_RUN. Čti [AGENTS](AGENTS.md) a jedinou queue; další odstavce zachovávají historii zadání, nikoli pokyn začít obnovu znovu.

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
