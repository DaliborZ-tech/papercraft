# Krátký test první autorské verze s novým uživatelem

Povinný v PC-006A/B, součást dodávání první autorské verze. **Stav: NOT_RUN,0 skutečných účastníků.** [PC-006A](../implementation/PC006A_DELIVERY.md) nyní poskytuje běžící build a technicky ověřený průchod vlastním dílem; celéA a první autorskou verzi s vnitřními přijímači dokončí PC-006B. Tento soubor je připravený protokol a formulář, nikoli výsledek uživatelského testu. Před sezením připnout skutečný použitý build a uvést, které dílčí schopnosti již obsahuje. Nezakládá novou návrhovou etapu. Normativní kritéria: [AC-US01–US08](ACCEPTANCE.md); návrh ovládání: [UX](AUTHORING_UX.md).

## Účastník a příprava

**Skutečný stav dostupnosti 6. 11. 2026:** vlastník na konkrétní dotaz k zajištění nového člověka pro 20–30minutové sezení odpověděl „Teď takový člověk není k dispozici“. Účastník tedy není zajištěný; AC-US08 zůstává **NOT_RUN / účastník nedostupný**, počet skutečných účastníků 0. Nejde o zamítnutí produktu ani zrušení autorizace. Implementace a nezávislé technické části pokračují. Žádný dosavadní průchod autora, agenta nebo GUI automatu tuto chybějící lidskou přejímku nenahrazuje.

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

## Expertní agentní průchod a přenosné vzory — 17. 11. 2026

Na výslovné nové zadání vlastníka provedl nezávislý agent průzkum místních
AUTHORING_UX/PRODUCT_ANALYSIS, této úlohy a manuálu0.2, primárních webových
návodů a vlastní UI průchod. Není autorem testovaného UI. Toto je expertní
kontrola s toolkit introspekcí a native Qt automatizací; **není to nový člověk,
spontánní objevování ovládání ani AC-US08 PASS**. Původní lidský protokol zůstává.

Pět vzorů pro hobby modeláře (doporučení jsou expertní přenos, ne změřené
zlepšení našeho produktu):

- **Viditelný pracovní krok a výsledek.** Oddělit tvorbu, rozvin, uspořádání
  listů a vydání; ponechat přímou cestu zkušenému autorovi. Výrobce UPC takto
  vysvětluje celý [workflow](https://www.papercraft3d.com/upc/tutorial_papercraft_workflow.aspx).
- **Stejný pojmenovaný díl v prostoru i na papíře.** Výběr z obou stran,
  zvýrazněný protějšek a možnost jej najít mají přednost před znalostí ID.
  [Pepakura](https://www.pepakura.tamasoft.co.jp/pepakura_designer/helpful-features/)
  dokumentuje vzájemný výběr a záběr obou konců lepení.
- **Spoj má dva konkrétní konce a předvídatelný účinek.** Náhled směru, příjemce
  a vysvětlená nemožnost, poté upravitelná chlopeň. UPC ukazuje
  [směr a způsobilost spoje](https://www.papercraft3d.com/upc/tutorial_cutting_and_joining_parts.aspx)
  a [samostatnou úpravu chlopně](https://www.papercraft3d.com/upc/tutorial_papercraft_flaps.aspx).
- **Papír má skutečnou velikost a jasný výstup.** Stránka, tisknutelný okraj,
  ruční polohy; PDF pro tisk a SVG pro další editaci. Tuto volbu přímo popisuje
  [autor Blender add-onu](https://addam.github.io/Export-Paper-Model-from-Blender/).
- **Návrat změny a obnova práce jsou odlišné věci.** Undo i explicitní save,
  samostatná dočasná kopie s časem a dohledatelná recovery; obnovenou práci
  bezpečně uložit jako vlastní projekt. Vzor oddělených mechanismů poskytuje
  [Blender recovery manual](https://docs.blender.org/manual/en/latest/troubleshooting/recover.html).

Dva vlastní veřejné příběhy slouží jen jako anekdoty pro návrh diagnostiky:
autor [nedokáže spojit jednoduchý blok](https://www.reddit.com/r/Pepakura/comments/1ta1w02/pepakura_doesnt_allow_me_to_join_simple_shape/)
a jiný [hledal správně velké šablony místo UV map](https://www.reddit.com/r/blender/comments/1pric1a/how_do_i_make_craft_templates_on_blender/).
Neprokazují četnost problému ani použitelnost našeho UI. Manuál ArchPapercraft0.2
je popis historické aplikace, takže nebyl považován za spolehlivý návod k0.3.

Praktický baseline: runtime **f496ecf0**, vlastní harness **bc36f29**, skutečné
Windows okno1366×768/DPR1; žádná změna OS DPI. Od prázdného projektu přes
viditelné příkazy vznikla vlastní Podložka100×70 paper mm a Stěna60×40,
nakreslené vnitřní připojení,4mm trojúhelníková chlopeň, přepočet a ruční
polohy40/50 na dvou A4. Nativní Save, Nový prázdný model (0 ploch), nativní
Open a vydání obou SVG/PDF prošly. Výběr dílu na papíře ukázal Stěnu ve3D;
skutečný own-PID Win32 klik na Podložku ve3D ukázal její papírový protějšek.
Žádný projekt ani geometrie nebyly injektovány do domény nebo načteny z fixture.

[Editovatelný projekt](../implementation/evidence/first-workflow-agent/own-first-model.apcraft),
[SVG/PDF](../implementation/evidence/first-workflow-agent/export/),
[vazba a nezávislé čtení výstupu](../implementation/evidence/first-workflow-agent/results.json),
[spojený výběr](../implementation/evidence/first-workflow-agent/07-paper-to-model-selection.png).
Nezávislá aritmetika skutečných SVG/PDF tokenů dává7000+2520=9520mm² materiálu,
obě PDF stránky jsou210×297mm. Po skutečném reopen se celý uložený stav shoduje.

Konkrétní nálezy pro opravu produktu:

- V1366px úzkém pravém docku vodorovný scroll odděluje popisek od hodnoty;
  při zpřístupnění pole se ořezávají počátky popisků
  ([pozorování](../implementation/evidence/first-workflow-agent/partial-flow/03-edge-choice-before-attach.png)). Potřebuje responzivní
  formulář/zalomení, nikoli další tooltip.
- Po hotovém spoji, chlopni a přepočtu, kdy oba díly stále čekají na odkládací
  ploše, hint pořád nabízí připojení hrany a teprve následné vytvoření chlopně.
  Další krok má odpovídat skutečně chybějícímu umístění na papír.
- Cesta k jednoduché chlopni prochází dlouhou vlastnostní oblastí s pokročilými
  profily, generacemi a dvěma různými skupinami spojů. Kontexty Model/Spoje/Papír
  mají být ověřeny na témže příběhu; toto je expertní důvod volby, ne lidský test.

Meze: první offscreen rozměrové závěry a dávkování do modálních smyček byly
chyby harnessu; nativní resize po inicializaci prokázal1366×768. Zachovány jsou
raw pokusy, ne produktové FAIL. V dílčím průchodu se změnil bod4→5m a přesné
Undo obnovilo celý projekt; pokus CtrlShiftZ nebyl skutečný Redo (UI má CtrlY).
Nulová hrana byla odmítnuta, ale záznam její nativní warning narazil na
introspekci již zaniklého Qt objektu; úplná oprava chyby se tím neprohlašuje.
Checkbox klik středu širokého řádku v harnessu nepotvrdil zámky: uložené flags
zůstaly false. Žádný lock/Redo/error-UX PASS se z těchto pokusů neodvozuje.
Nové pracovní kontexty a DATA-01 recovery čekají na samostatné nezávislé ověření.
