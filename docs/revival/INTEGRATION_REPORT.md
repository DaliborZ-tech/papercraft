# Integrace P0 + P1 a oprava pracovního mandátu

Vlastník 5. listopadu 2026 výslovně autorizoval integraci a push schváleného P0 + P1 na `master`. Stejné pravidlo platí pro budoucí dokončené ucelené balíky v již autorizovaném produktovém rozsahu po ověření a nezávislé revizi, bez další rutinní žádosti. Aktivní instrukce jsou v [AGENTS.md](../../AGENTS.md) a §6 [mandátu](../../02_CODEX_MANDATE.md).

## Vstupní ověření

- Root: `C:\Users\dalib\projects\papercraft`; pracovní strom při převzetí čistý.
- Origin: `https://github.com/DaliborZ-tech/papercraft.git`.
- Schválený analytický CODE: `5b01bb26e6b4c3da8d75afdca19cad5d6b43d576`; následné administrativní předání/review: `983fef516269eac36f28a4fa81763a7a3e184f4c`.
- Lokální `master` i `origin/master` po `git fetch origin`: `d689af67e059512fdc99e85e9eb0b8d432f4c5d4`; rozdíl `master...origin/master` = `0 / 0`.
- `origin/master...revival/p0-p1-contract` při převzetí = `0 / 4`; `git merge-base --is-ancestor origin/master revival/p0-p1-contract` skončil exit 0. Při prvním fetch na vzdáleném master nebyly nové změny. Zdrojová větev již měla vzdálenou kopii na `983fef5`.

Nynější doplněk mění pouze pracovní instrukce, pravidlo ve frontě a související popis předání. Historické baseline důkazy a [původní nezávislé review](REVIEW_REPORT.md) zůstávají zachované. Produktový rozsah, geometrické závěry a implementační AC se nemění. Nová revize tohoto dodatku má vlastní pin a výsledek v [INTEGRATION_REVIEW.md](INTEGRATION_REVIEW.md).

## Ověření a postup integrace

Pro dokumentační doplněk stačí strukturální kontrola `tools/revival/validate_delivery.py`, kontrola diffu a JSON fronty, zachování všech P2 autorizačních příznaků a nezávislá revize instrukcí. Původní full suite se bez změny produkčního kódu ani nové nejistoty neopakuje. Její původní výsledek 213 PASS a diagnostických 6 FAIL se tím nepřepisuje.

Po uzavření doplňující revize znovu načíst remote a použít fast-forward zdrojové větve do `master`, pokud nadále platí ancestor vztah; jinak standardní merge zachovávající obě historie. Případnou věcnou změnu/konflikt znovu ověřit a nezávisle zkontrolovat. Push provést běžným `git push origin master`, nikdy force. Potom porovnat `git rev-parse master`, `git rev-parse origin/master` po fetch a `git ls-remote origin refs/heads/master`. Skutečný výsledek a vzdálený commit patří do konečného předání; tento záznam popisuje vstupní důkazy a ověřovací postup, nepředstírá předem úspěch síťové operace.

## Vzdálená změna během revize a její integrace

Při závěrečném načtení remote přibyl `f789b74946b0455341b53b5adf3b97dfc05b7543` (GitHub merge PR #1, rodiče `d689af6` a `71b7dcc`). Jeho strom je přesně shodný s `71b7dcc`: `git diff --quiet 71b7dcc f789b74` skončil exit 0. Původní předpoklad přímého fast-forward zdrojové větve přestal platit; `origin/master...2c572d8` bylo `1 / 1`.

Na izolované větvi `revival/p0-p1-contract` proběhl `git merge --no-edit origin/master`, exit 0, strategie ort, bez konfliktů. Vznikl merge commit `89c0bf7b3cf17cfa0732a9e0f7a044b521e25d59`, který zachovává vzdálený merge i lokální doplněk `2c572d8`. `git diff --quiet 2c572d8 89c0bf7` skončil exit 0: výsledný strom zůstává shodný s lokálně revidovanými instrukcemi. Produkce, AC, P2 scope a brána se nezměnily.

Tento integrační záznam se následně doplní vlastním nezávislým re-review konkrétního výsledného CODE v `INTEGRATION_REVIEW.md`. Obsahující větev lze při nezměněném remote převést do lokálního `master` fast-forward; po běžném pushi je stále nutné ověřit aktuální vzdálené SHA. Historie vzdáleného PR merge se zachovává, nenahrazuje ani nerebasuje.

## Samostatná produktová brána

`GATE-P2 = PO_PENDING`, `accepted_by_owner = false`, produkční P2 nadále neautorizována. Varianta B a kompatibilita z [rozhodovací karty](PO_DECISION_CARD.md) zůstávají otevřené. Integrace/push nejsou PO přijetí ani release. Po případném budoucím přijetí P2 se ověřené a nezávisle schválené balíky v jeho rozsahu integrují podle již autorizovaného postupu.
