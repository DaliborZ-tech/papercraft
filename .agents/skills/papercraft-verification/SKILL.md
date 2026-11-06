---
name: papercraft-verification
description: Ověřuj geometrii, změny, skutečné UI a výrobní výstupy Papercraftu pomocí nezávislých očekávání a správného druhu důkazu.
---

# Ověřování geometrie a výroby

Načti příslušné [numerické a výrobní kontrakty](../../../04_ACCEPTANCE_AND_VERIFICATION.md), [AC v1.2](../../../docs/p2/v1.2/ACCEPTANCE.md) a relevantní [spiky](../../../docs/p2/v1.2/GEOMETRY_SPIKES.md). Tolerance a přejímky určuje specifikace, ne tento skill.

Expected výsledek odvoď analyticky, z ručně určené topologie nebo nezávislého čtení výstupu. Zahrň negativní i hraniční případ. Shodné očekávání vypočtené stejným helperem není nezávislé orákulum.

Příklad: konečné nulové vzorky neprokazují regularitu celého loftu. [DR-01](../../../docs/p2/v1.2/INDEPENDENT_REVIEW.md) našel kolaps mezi vzorky; kontroluj oblast platnosti pozitivního důkazu a odděluj vzorkované maximum od prokázané meze. Podobně přesný válcový plášť necertifikuje ohyb jeho chlopní.

Připni zdroj ověřovaného výsledku a uveď důkaz: numerika, UI automatizace, skutečný editor, nový uživatel nebo fyzická stavba. Jeden druh nenahrazuje druhý. Chybějící důkaz zůstává NOT_RUN/BLOCKED s důvodem. Selhání neskrývej odstraněním testu či změkčením AC.

Reviewer ověří také, zda důkaz pokrývá právě vydávaný commit a skutečně požadovaný výsledek. Zjištění přenes do produktu a cíleného postupu přes [smyčku poučení](../../../AGENTS.md#projektové-skills-a-poučení).
