# Nezávislá revize průřezové použitelnosti a projektových skills

6. listopadu 2026, reviewer `/root/usability_skills_review`, jiný agent než autor dodatku. Posuzovaný **CODE `9a7dc15c87dac4fe19745154f18bc77e04ee0abf`**, BASE `a2d15fb1272a3fd8f539e003a13ade645abc0dae`. **Verdikt: APPROVED_IN_SCOPE, bez otevřených zásadních nálezů.** Rozsah je doplnění pracovního kontraktu a čtyř projektových skills včetně následného výslovného UI/UX mandátu. Nejde o schválení implementovaného editoru, účinnosti poučení, uživatelského testu ani přijetí P2 v1.2.

Reviewer nepsal skills, jejich pracovní instrukce, UX, protokol ani queue a neměnil produkční zdroj. Vlastní zápisy tvoří pouze tento report a `evidence/usability-skills-review-*`. Kontrola používá pinové JSON/skill bloby; oficiální formátový validator dostal dočasné přesné kopie čtyř SKILL.md, s UTF-8 a existující oddělenou validační závislostí PyYAML. Žádná produktová závislost se neměnila.

## Výsledek obsahové kontroly

| Požadavek | Doložený výsledek a mez |
|---|---|
| Použitelnost v každém řezu | AC-US01–US07 jsou ve všech P2 ticketech včetně rodičů a hlavních průchodů PC-006A/B, PC-007A/B, PC-008, PC-009/010. Každý má implementaci a důkaz v témže řezu; odklad do závěrečného redesignu je výslovně vyloučen. Stav všech těchto produktových přejímek je NOT_RUN. |
| Šest kontrol průchodu | AC a UX pokrývají začátek/další krok, kontext výběru a akcí, výsledek a 3D↔rozvin, lokalizaci/opravu chyby, bezpečné zrušení/undo a základní práci bez znalosti interní geometrie. Ukázky navazují na skutečný příjemce chlopně a materiál, nevyměňují konstrukční správnost za snazší demo. |
| Začátečník a zkušený autor | Tipy jsou volitelné, neblokující, opakovatelné, vypnutelné i znovu zapnutelné. Vypnutí neskrývá chyby a nemění projekt či export. Přímé příkazy, přesný vstup a zkratky zůstávají dostupné bez povinného průvodce; ověření obou cest je součást řezu. |
| Skutečný novice test | USABILITY_TEST.md obsahuje cílové zadání bez sekvence kliků: vlastní díl, změna/vrácení, chlopeň, A4 layout, uložení a SVG/PDF. Účastník je skutečný nový začínající modelář, ne člen autorova/review týmu. Formulář ukládá váhání, chyby, přesnou pomoc a její dopad. Věcná pomoc se nesmí překlasifikovat na samostatné dokončení. Uměle připravená chyba na kopii je oddělena od spontánního chování. |
| Načasování člověka | PC-006A sezení připraví, PC-006B musí doložit AC-US08 pro úplné ověření první autorské verze, PC-010 kontroluje pokrytí a opravy. Bez buildu či účastníka zůstává NOT_RUN/BLOCKED; nevyvolává se nová návrhová etapa a GUI automat ani autor nejsou náhradou člověka. Zde je počet pozorovaných účastníků nula. |
| Autonomie UI/UX | Stará obrazovka ani původní tabulka panelů nejsou závazný vzhled. Autonomní změny v sjednaném cíli zahrnují samotnou interakci/strukturu, nejen nápovědu. Větší změna vyžaduje pracovní důvod a skutečný průchod před/po, s pravdivým uvedením chybějící výchozí funkce, zachovaných částí a konzistence. Zásadní alternativa způsobu práce dostane konkrétní ukázku, dopady a doporučení pro rozhodnutí vlastníka; běžný panel nevyžaduje rutinní souhlas. |
| Skills skutečně v práci | AGENTS výslovně ukládá načíst relevantní SKILL.md i bez automatické nabídky klienta. Čtyři směrované kompetence mají konkrétní spouštěče; všech17 ticketů uvádí relevantní skills a záznamy použití. Původní dokončené tickety mají HISTORICAL_NOT_APPLIED, budoucí implementace NOT_RUN; aktuální PC-012 tvrdí použití pouze na tomto dodatku a uvádí konkrétní rozhodnutí/artefakty. |
| Smyčka poučení | Ledger obsahuje problém, doloženou příčinu či výslovnou hypotézu, opravu produktu nebo její pending stav, změnu skillu, příklad, ověření, nezávislou kontrolu a další použití. SK-003 rozlišuje skutečně opravený experiment od produkční funkce; SK-002 nepředstírá pozorovaného člověka ani hotovou opravu UI. Všechny čtyři účinnosti zůstávají PENDING_NEXT_USE. |
| Specifikace a rozsah | Skills stručně odkazují na platné kontrakty/AC a nepřepisují tolerance či přejímky. Původní AC a stavy zůstaly zachované; nevznikl nový ticket, stage ani cyklus. Produktová brána, oprávnění produkční implementace a rozlišení fyzického P3 se nezměnily. |

## Nezávislé uplatnění skills na rozhodnutích

Tyto čtyři případy posuzují konkrétní výsledek a hranice tvrzení; nejsou sezením s novým uživatelem ani dokladem účinnosti při budoucím produktovém dodávání.

| Skill a zvolený podklad | Přijaté rozhodnutí a důvod |
|---|---|
| Konstrukce: raw `geometry-dr01-results.json`, vnitřní střešní připojení | Zachovat přesah a vnitřní stopu: od skutečného okraje ji dělí7.071mm. Při gapu1mm leží UV projekce stále uvnitř střechy, ale skutečná lepicí plocha je0. Nestačí pozitivní půdorysný překryv ani oříznutí střechy. Novice protokol správně zachovává potřebný protikus, místo zrušení validace. Otevřená základna nepřidává podlahu budovy. |
| UI: historický `p2-desktop-attempt3/results.json` proti novému protokolu | Záznam nativních dialogů, výběru, undo a exportu neobsahuje důkaz práce nového člověka; nesmí uzavřít AC-US08. Příklad nerozpoznaného připojení v ledgeru je označená hypotéza z požadavku vlastníka. Skutečným výsledkem dodatku je pozorovací protokol, návaznost příjemce a šest kontrol, nikoli údajné zlepšení již přepracované obrazovky. Výběr/příkaz/náhled je nutné vyšetřit před další nápovědou. |
| Ověřování: vlastní nový analytický případ `k=1.8`, `twist=70°`, `depth=0` | Nezávislý vzorec dává singularitu `v=(1-k cosφ)/(1+k²-2k cosφ)=0.1277496031`, mimo staré vzorky0,0.5,1. Výpočet Jacobianu je1.14e-13; spike vrací DEGENERATE_OR_SINGULAR. Toto doložilo použití pravidla „konečné vzorky nejsou pozitivní důkaz“ na jiném případu než původní DR-01. Nejde o nový obecný důkaz rozvinutelnosti všech ploch. |
| ADLC: připnutý `paper-review-tests.xml` a současný diff | XML obsahuje90 případů s jedním selháním, tedy89 PASS. Zelený necommitnutý pracovní strom neopravňuje schválit tento historický pin. Současný dodatek nemění runtime, geometrii ani testy, proto je přiměřené nové formátové/obsahové ověření a review konkrétního pinu, nikoli tvrzení nového runtime nebo fyzického proof. Historický verdikt se nemaže. |

## Reprodukce a raw důkaz

```powershell
.venv\Scripts\python.exe -X utf8 docs/p2/v1.2/evidence/usability-skills-review-checks.py
```

[Vlastní skript](evidence/usability-skills-review-checks.py), [výsledky](evidence/usability-skills-review-results.json). Exit0; všech20 provedených integritních a rozhodovacích kontrol PASS. Čtyři aktuální skills prošly oficiálním `quick_validate.py`, každý exit0. Záznam obsahuje jejich pinové SHA256: změněné UI/delivery skills jsou zkontrolované znovu a nejsou jim připsané starší hashe z8826. Kontrola zahrnuje striktní JSON, zachování původních AC/stavů/ticketů/závislostí, mapu a skutečná tvrzení o použití, pending účinnost a odkazy. Vlastní full suite ani živý GUI test se zde neopakovaly, protože runtime zdroje a testy nemají diff.

Po vytvoření tohoto reportu původní integritní validator prošel18/18, exit0; [raw výstup](evidence/usability-skills-review-validator.json). Chybějící review na samotném source pinu nebylo tajně označeno za PASS. Žádný nový člověk nebyl testován, žádný model fyzicky sestaven, žádná účinnost po dalším produktovém použití potvrzena.

## Meze závěru a administrativní dokončení

Schváleno je zavedení postupů do instrukcí, ticketů a přejímek. Aktuální dokumentační použití čtyř skills má konkrétní oporu ve výsledku; tím se nemění NOT_RUN skutečného produktu a člověka ani PENDING_NEXT_USE účinnosti. První autorská verze musí teprve naplnit produktové AC a skutečný novice protokol. P2 v1.2 stále čeká na produktové přijetí vlastníkem, P3 na výtisk a sestavení.

Následující administrativní commit může uložit tento report/raw důkazy a odpovídající review stav tohoto dodatku/ledgeru. Zkontrolována je také zamýšlená jediná přidaná atributová direktiva `.agents/skills/** text eol=lf`, která chrání konzistentní zdrojové bajty skills při Windows checkoutu a nemění jejich text ani chování produktu. Smí se potvrdit pouze formát, obsahové rozhodovací ověření a schválení pracovního kontraktu; nesmí se změnit účinnost na ověřenou, vymyslet účastníka, produktový PASS nebo přijetí v1.2. Po zaslání konkrétního administrativního SHA reviewer ověří omezený diff před rutinní integrací/pushem dle AGENTS; nový návrhový nebo reportovací cyklus se tím nezakládá.
