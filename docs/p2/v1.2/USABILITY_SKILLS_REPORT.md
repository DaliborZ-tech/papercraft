# Doplnění použitelnosti a projektových skills

6.11.2026, dodatek k existujícímu P2 v1.2 na výslovný pokyn vlastníka. Základ `a2d15fb1272a3fd8f539e003a13ade645abc0dae`, izolovaná větev `revival/p2-usability`. Nevzniká další návrhová etapa ani nový ticket. Produkční zdroj, geometrie, tolerance a platná produktová brána se tímto dodatkem nemění.

## Konkrétní výsledek

- [AC-US01–US08](ACCEPTANCE.md) a [UX](AUTHORING_UX.md) dávají šest kontrol hlavního průchodu, volitelné opakovatelné/vypnutelné vedení a přímou zkušenou cestu přímo do každého řezu. První autorská verze musí projít skutečným sezením podle [připraveného protokolu](USABILITY_TEST.md).
- Čtyři stručné skills jsou v `.agents/skills/`; [AGENTS](../../../AGENTS.md#projektové-skills-a-poučení) určuje jejich skutečné načtení, spouštěče a kontrolu použití na výsledku. Všech17 ticketů má relevantní `skills` i záznamy `skill_application`. Historické mapování neznamená zpětné použití tehdy neexistujících skills.
- [Poučení](../SKILL_IMPROVEMENTS.json) obsahuje konkrétní problém/příčinu, opravu nebo její nehotový stav, změnu postupu, příklad, ověření, nezávislou kontrolu a další použití. Počáteční účinnost všech čtyř skills je `PENDING_NEXT_USE`. Případ nerozpoznaného připojení v UI je názorný scénář vlastníka, nikoli vymyšlené pozorování účastníka.

Autor tohoto dodatku načetl všechny čtyři nové skills. Konstrukční skill vedl k zachování skutečného příjemce chlopně v novice úkolu místo obcházení validace; UI skill k začlenění použitelnosti přímo do řezu; verification skill k odděleným stavům pro dokument, člověka a fyzický proof; delivery skill k přiřazení odpovědností a připnuté nezávislé revizi tohoto dodatku. To je uplatnění na pracovním kontraktu, nikoli implementace autorského UI.

## Přiměřené ověření

[Raw validační záznam](evidence/usability-skills-validation.json): všechny4 skills prošly oficiálním `skill-creator/scripts/quick_validate.py`, exit0;11 kontrol návaznosti PASS. Kontroly zahrnují odkazy, skills každého ticketu, přiřazení usability AC všem P2 ticketům, zachování původních fází/závislostí a produktové autorizace i skutečnost, že nebyl vymyšlen nový uživatel. Původní integritní validator P2 v1.2 prošel18/18; `git diff --check` PASS. Zdroj skills identifikují SHA256 v raw záznamu; konkrétní commit doplní [nezávislá revize](USABILITY_SKILLS_REVIEW.md).

První spuštění oficiálního validatoru nemohlo běžet kvůli chybějícímu PyYAML; aplikace má prostředí vytvořené přes uv bez pip. Pro validaci byl PyYAML přes existující uv instalován pouze do samostatného dočasného adresáře, s UTF-8 režimem Pythonu. Žádná produktová ani globální závislost se neměnila. Formátová validace neprokazuje účinnost skillu. Runtime aplikace ani algoritmy se nemění, proto se neopakuje nesouvisející full suite; dřívější273 PASS zůstává historickým důkazem svého pinu.

Reviewer musí posoudit skutečné uplatnění a nedoložené závěry; rozhodovací příklady agentů nejsou sezení s novým modelářem. Nové produktové AC, skutečný novice test a účinnost po přenosu zůstávají NOT_RUN/pending. První autorská aplikace není dosud implementovaná, nikdo nebyl přizván ani pozorován. P3 stále vyžaduje skutečný výtisk. Přijetí nové P2 v1.2 zůstává samostatnou produktovou otázkou; tento požadavek jej nepředstírá.
