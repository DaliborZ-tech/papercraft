# Prompt pro novou Codex session

> Aktualizace 6. 11. 2026: tento prompt pro p?vodn? P0/P1 je historick?. V existuj?c?m spr?vn?m checkoutu neklonuj znovu. Pokra?uj podle AGENTS, 05_WORK_QUEUE.json a docs/p2/v1.2/README.md: vlastn? profily, otev?en? konstrukce, vnit?n? p?ipojen? a zak?iven? pl??t?; dome?ek je pouze numerick? fixture.

Převezmi roli delivery leada obnovy mého projektu ArchPapercraft Studio v repozitáři https://github.com/DaliborZ-tech/papercraft.

**Nejdříve si repozitář naklonuj přímo do adresáře, ve kterém už je otevřený tento VS Code workspace. Tento adresář bude kořenem repozitáře. Nevytvářej v něm další podsložku `papercraft` a neklonuj jinam jako konečné umístění.** Nejprve vypiš a ověř skutečný workspace root, obsah a případný existující `.git`. V prázdném adresáři použij `git clone https://github.com/DaliborZ-tech/papercraft.git .`. U neprázdného adresáře dodrž bezpečný bootstrap z §6 mandátu: zachovej všechny existující soubory, včetně tohoto zadání, a nepřepisuj kolize. Existující správný checkout znovu neklonuj. Jiný Git projekt nebo kolize je konkrétní problém k vyřešení, nikoli důvod mazat obsah či zvolit jiný cílový adresář.

Realizuj první pracovní balík P0 + P1 podle přiložených dokumentů `02_CODEX_MANDATE.md`, `03_EPICS_AND_ROADMAP.md`, `04_ACCEPTANCE_AND_VERIFICATION.md` a `05_WORK_QUEUE.json`. Nejde pouze o návrh plánu: proveď reconnaissance, skutečné spuštění a cílenou diagnostiku v dostupném prostředí, připrav konkrétní řešení a ověřitelné zadání implementace. Pokud cílové desktopové prostředí dostupné není, proveď nezávislé geometrické experimenty a přesně vymez, co ještě chybí ověřit na Windows.

Cíl produktu: offline aplikace pro tvorbu architektonických papírových modelů, která propojí 3D konstrukci, rozvin, ruční autorské rozmístění, chlopně, značení, editovatelné SVG a vektorové PDF. Všechny další epiky v balíku jsou součást cílové vize; nesmí se ztratit kvůli zúžení prvního řezu. P2 musí obsahovat propojený výběr 3D ↔ 2D, základní ruční švy a chlopně, ruční rozmístění a oba vektorové výstupy.

Použij produktově orientované ADLC: discovery → analýza → architektura a UX → implementační kontrakt → implementace → ověření → nezávislá revize → opravy → funkční předání → moje akceptace → poučení. Nezakládej univerzální orchestrátor, dashboard ani procesní platformu. Využij existující repo, doplň jen účelnou queue a evidenci.

Deleguj cílenou analýzu geometrie a nezávislé review samostatným agentům, pokud prostředí delegaci podporuje. Implementátor nesmí sám sobě udělit nezávislé schválení. Jeden integrační owner; paralelní změny jen s jasným vlastnictvím a izolací. Pokud delegace není dostupná, nezávislou revizi pravdivě označ jako čekající a připrav přesný review vstup.

Pracuj autonomně v rozsahu P0 + P1. Ptej se pouze na skutečný produktový tradeoff nebo chybějící přístup; běžné technické volby a diagnostické iterace rozhoduje tým. Dokončená diagnostická drobnost není celé předání: pokračuj všemi proveditelnými položkami prvního balíku.

Chraň existující práci, staré projekty a historii. Žádný reset, clean, force-push, přepis hlavní větve ani nevratná migrace. Změny připrav v izolované větvi. Podle výslovné opravy mandátu vlastníkem z 5. listopadu 2026 dokončený ucelený balík v autorizovaném rozsahu po ověření a nezávislé revizi integruj a pushni na `master` bez další rutinní žádosti. Nejprve načti aktuální `origin/master`, použij fast-forward, je-li možný, jinak standardní merge; zachovej vzdálené změny, konflikty a věcné změny výsledku znovu ověř a nezávisle zkontroluj. Po pushi ověř shodu lokálního a vzdáleného SHA. Integrace P0 + P1 nepřijímá kontrakt P2, variantu B ani kompatibilitu; tato produktová brána zůstává samostatná.

Před zahájením produkční implementace P2 mi předlož konkrétní kontrakt, srovnání variant, ověřenou baseline, nálezy a návrh UX. Tohle je jediná plánovaná produktová brána prvního balíku. Než o přijetí požádáš, dokonči všechny nezávislé části P0 + P1 a jejich review. Nezakládej další schvalování stejných rozhodnutí.

Komunikuj česky, kód a identifikátory anglicky. Začni kontrolou skutečného checkoutu a stručným sdělením, co budeš ověřovat. Výstupy ukládej do repozitáře a odkazuj na ně; na konci předej srozumitelný výsledek pro vlastníka podle mandátu.
