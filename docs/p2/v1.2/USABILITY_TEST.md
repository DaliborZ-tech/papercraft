# Krátký test první autorské verze s novým uživatelem

Povinný v PC-006A/B, součást dodávání první autorské verze. **Stav: NOT_RUN.** Nová autorská aplikace není implementovaná a nebyl zapojen žádný účastník. Tento soubor je připravený protokol a formulář, nikoli výsledek uživatelského testu. Nezakládá novou návrhovou etapu. Normativní kritéria: [AC-US01–US08](ACCEPTANCE.md); návrh ovládání: [UX](AUTHORING_UX.md).

## Účastník a příprava

Alespoň jeden skutečný začínající modelář, který aplikaci dosud nepoužíval a není jejím autorem, členem implementačního/review týmu ani předem školeným testerem. Zapiš dosavadní zkušenost s modelářstvím/CAD a jazykem UI, bez zbytečných osobních údajů. Jedno sezení je kvalitativní zkouška, nikoli důkaz použitelnosti pro celou populaci.

Na Windows připrav čistý prázdný projekt, funkční vstupní zařízení a přístupný adresář pro soubory. Zaznamenej CODE SHA/build, OS, DPI, jazyk a výchozí stav vestavěných tipů. Ověř technickou funkčnost před příchodem účastníka; nedělej mu demonstrační průchod a nenabízej hotový projekt. Příprava zařízení nesmí zahrnovat vysvětlení, která tlačítka mačkat. Sezení plánuj přibližně na20–30 minut, nikoli jako test rychlosti člověka. Čas a případné prodloužení se zaznamenají.

Účastník může používat vestavěnou nápovědu a tipy, vracet se a experimentovat. Pozorovatel sdělí cíl, požádá o průběžné vyjádření očekávání a sleduje. Autor aplikace může mlčky pozorovat, nesmí průběžně navigovat. Žádné kontaktování či nábor bez autorizace vlastníka.

## Zadání pro účastníka — pouze cíl

„Navrhni vlastní jednoduchý díl malého papírového modelu, například stěnu s chlopní pro přilepení k podložce. Změň jeden jeho rozměr a vyzkoušenou změnu bezpečně vrať. Přidej chlopeň, připrav díl na list A4 a uprav jeho polohu nebo natočení. Ulož projekt a vytvoř SVG i PDF, které bys předal k dalším úpravám a tisku. Sám zvol tvar a rozměry.“

Konstrukčně potřebný protikus/podložku vytváří účastník běžným UI, případně zvolí dostupný obecný prvek; vlastní díl nesmí pocházet z house presetu. UI má význam příjemce chlopně vysvětlit modelářsky. Není dovoleno obejít validaci spoje jen kvůli snadnějšímu testu. Zadání neobsahuje názvy interních entit, algoritmů, souřadnic UV ani sekvenci kliků.

Po dokončení polož neutrální otázky: „Co se změnilo?“, „Které místo v prostoru odpovídá tomuto dílu na papíře?“ a „Kde najdeš výstupy?“. Při přirozené chybě sleduj, zda ji účastník najde a opraví. Pokud žádná nenastane, zadej dodatečný cíl „Díl je teď částečně mimo stránku; dostaň jej celý na list“ na kopii jeho projektu. Označ to jako dodatečný scénář, ne spontánní chování, a neprozrazuj opravu. Základní úkol nehodnoť podle znalosti interní geometrie.

## Pozorování a pomoc

Zapiš hledání začátku/dalšího kroku, výběr a akce, očekávání a skutečný výsledek, vztah3D↔rozvin, hledání/opravu chyby, undo/zrušení a užité názvosloví. Váhání eviduj podle pozorovaného hledání, opakování či vyjádřené nejistoty; zaznamenej délku, ne pouze dojem pozorovatele. Zapisuj i chybné kroky, návraty a stav projektu po nich.

Pokud účastník požádá o navigaci nebo přibližně dvě minuty nemůže pokračovat, nejprve požádej neutrálně o popis očekávání, bez zmínění tlačítka. Je-li nutná věcná pomoc, lze sezení dokončit s pomocí, ale původní průchod už není „bez navádění“. Zapiš přesnou větu a okamžik; nevymaž předchozí selhání. Při riziku ztráty práce nebo žádosti o ukončení zasáhni/ukonči a výsledek označ. Vestavěná pomoc se eviduje zvlášť od zásahu člověka.

## Záznam jednoho sezení — zatím nevyplněno

| Pole | Hodnota |
|---|---|
| Stav, datum, build/CODE SHA | NOT_RUN; doplnit při sezení |
| Účastník a předchozí zkušenost, potvrzení nezávislosti/novosti | Nezapojen; anonymní označení až při skutečném sezení |
| Windows/DPI/jazyk/vstup, stav tipů na začátku a konci | NOT_RUN |
| Čas začátku/konce, dokončené a nedokončené cíle | NOT_RUN |
| Zdrojový projekt, SVG/PDF a hashe, použitá vestavěná pomoc | NOT_RUN |
| Celkově samostatně / dokončeno s pomocí / nedokončeno | NOT_RUN |

| Čas/krok | Pozorovaný pokus nebo doslovný výrok | Očekávání → výsledek | Váhání/chyba/doba | Vestavěná pomoc / přesný zásah člověka | Dopad na úkol a data | Nález |
|---|---|---|---|---|---|---|
| — | Zatím nepozorováno | — | — | — | — | — |

Ke každému problému doplň reprodukci, důkaz a odděleně hypotézu/potvrzenou příčinu, závažnost, opravu produktu, ověření a odkaz na případné poučení ve skillu. Neodvozuj příčinu automaticky z výroku „nechápu“. Například nerozpoznané připojení stěny dovnitř střechy vyžaduje přezkoumat výběr, akce a náhled; další tooltip není automatické řešení.

## Vyhodnocení a opakování

Samostatný průchod znamená dosažení všech základních cílů s platným projektem a oběma výstupy bez věcného navádění člověkem. Použití volitelné vestavěné pomoci se nezatajuje a samo o sobě neznamená neúspěch. Ztráta práce, nutná intervence nebo nedokončení blokuje PASS tohoto průchodu. Váhání a drobné opravené chyby zůstávají nálezy i při dokončení.

Závažné problémy oprav v daném řezu a ověř. Návrat téhož účastníka může potvrdit opravu, ale jde už o zkušenějšího uživatele; po zásadní opravě nebo asistovaném prvním pokusu potřebuje samostatný první průchod nového účastníka. Neoznačuj GUI automat, autorův průchod, čtení tohoto protokolu ani simulaci agentem jako test s novým člověkem. Pokud člověk nebo build chybí, AC-US08 zůstává NOT_RUN/BLOCKED s důvodem a první autorskou verzi nelze prohlásit za úplně ověřenou.

Přímou zkušenou cestu zvlášť ověř s vypnutým vedením: stejné příkazy a přesný vstup jsou dostupné bez povinného průvodce, tip lze znovu vyvolat a vypnout. Toto technické ověření nesupluje novice sezení. Fyzická stavba modelu zůstává v P3.
