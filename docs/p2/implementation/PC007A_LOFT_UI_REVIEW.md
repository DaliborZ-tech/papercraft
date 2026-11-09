# Nezávislá revize widgetu loftu PC-007A

Reviewer `bend_adapter_review`, 9. 11. 2026; autor revidovaného widgetu `curve_ui`. Exact source **`d5724115bb75ffe569ec2960aa56e7339627d891`**, worktree `papercraft-loft-ui`. Reviewer vlastní loftovou matematiku v jiné větvi; **ta zde není předmětem revize a tento report ji nezávisle neschvaluje**.

**CHANGES_REQUIRED — LUI01 MAJOR / OPEN (identity integration fence).** Nejde o závěr o chybě aktuálního geometrického backendu. Samostatný widget musí bezpečně odmítnout neočekávanou změnu autorského zadání v návratu veřejného preview API.

## LUI01 — náhled může tiše změnit pořadí, seam a již přidělené identity

`LoftProfilesDialog._show_result` kontroluje množinu correspondence IDs, počet dvojic a jejich segmentové reference/intervaly. Nekontroluje však pořadí těchto dvojic ani `seam_patch_id`; již známé `ruling_id` a `end_ruling_id` také přijme z návratu bez porovnání s požadavkem. Následně přepíše parametry určené k Apply a tlačítko povolí. Výběr viditelný v řádcích/seam tedy nemusí odpovídat potvrzovanému výsledku. Změna již vydané identity může zneplatnit navazující autorskou práci.

Vlastní čtyři testovací callbacky při jinak úspěšném preview samostatně (1) obrátí pořadí dvojic, (2) změní seam na druhou dvojici, (3) nahradí již známý ruling první dvojice, (4) nahradí již známý end ruling. Všechny čtyři varianty jsou v d572 chybně přijaty. Zdrojový projekt přitom zůstává stejný: obecný source digest tuto změnu návratových parametrů neodhalí.

Integrační owner výslovně potvrdil, že jde o přesnou autorskou mapu: pořadí, seam a již přidělené identity se musí zachovat; preview není automatické přepárování. Doporučená oprava: porovnat ordered correspondence IDs a seam s požadavkem, u existujících ruling/end IDs požadovat shodu, nová IDs přijmout jen tam, kde je požadavek dosud neměl. Chybějící či neplatné nově vydané identity bezpečně odmítnout. Použití výsledku musí zůstat zakázané a feedback nabídnout nový výpočet. Výsledek nesmí nahradit live projekt.

[Samostatné vlastní orákuly](evidence/pc007a-loft-ui-review-own.py), [raw 4 FAIL / 5 PASS](evidence/pc007a-loft-ui-review-d572-own.xml). Reprodukce používá `preview_function` seam a dvojici ručně vytvořených otevřených profilů. **Není to skutečný model B, reálné geometrické preview ani skutečný UI průchod doménou.** Nález byl ihned předán ownerovi a autorovi widgetu; reviewer produktový kód neměnil.

## Ověřené chování a použité důkazy

- Reviewer skutečně spustil autorových [32 offscreen Qt testů — PASS / 1,70 s](evidence/pc007a-loft-ui-review-d572-original.xml). Ověřují pracovní thread a odezvu časovače, poslední čekající request, zdrojový digest, zrušení/Escape, oddělený clone, veřejné preview/update dispatch, staged číselný vstup, obnovu uložených map a chybějící reference bez indexového fallbacku.
- Vlastní import oracle ověřil skutečnou cestu `ui/author_loft.py` v tomto worktree. Pět vlastních pozitivních případů prošlo: změna souřadnice živého zdroje bez zvýšení revision odmítne okamžitý Accept i bez doručení 150ms timeru; zrušení zahodí čekající request i opožděný výsledek běžícího jobu; mutace detached clone a následné Cancel zachovají původní projekt; skutečně smazaný rozepsaný výpočetní limit bez Enter zastaví veřejnou akci náhledu; správný import.
- První [raw běh 5 FAIL / 4 PASS](evidence/pc007a-loft-ui-review-d572-own-initial.xml) obsahuje navíc selhání harnessu: klávesová zkratka v krátkém testu nebyla doručena a očekávaný chybový feedback se vůbec nevytvořil. Nebyl to spuštěný výpočet se špatným číslem. Harness nyní po skutečném psaní vyvolá veřejnou `request_preview` bez Enter a explicitně očekává odmítnutí; C05 případ prošel. Původní raw selhání se zachovává a nepředstírá se jako produktová chyba nebo doklad funkční zkratky. Autorova samostatná shortcut regrese prošla v sadě výše.

Přečtený widget čitelně rozlišuje vlastní roviny profilů a prostorový výsledek; kreslí nativní obrysy, zobrazuje názvy/rozměry a explicitní směry. Neplatná mapa nedostane implicitně náhradní segment, chybějící první profil v editaci zůstává zamčený a pojmenovaný, změna druhého zachovává řádky nevybrané k výslovné opravě. Nápověda je vypnutelná/znovu vyvolatelná, ale diagnostika zůstává viditelná. `REJECTED/UNRESOLVED` vyžaduje zvláštní volbu konstrukčního cíle a netvrdí přesný tiskový díl. To je technicky ověřené chování widgetu, nikoli důkaz osvojitelnosti pro nového člověka.

## Skills a rozsah závěru

Před prací skutečně načteny `AGENTS.md`, UI, verification a delivery skills. UI skill se uplatnil na C05, srozumitelný další krok, explicitní potvrzení mapy a bezpečné zrušení; verification na vlastních negativních případech odlišných od autorových testů, skutečné importované cestě a oddělení harness FAIL; delivery na okamžitém předání LUI01 a exact-pin omezeném závěru. Specifikace a AC tím nejsou oslabeny.

Testy běžely **výhradně `QT_QPA_PLATFORM=offscreen`**. Nativní desktop je rezervovaný integračnímu ownerovi. Zde není UI→save/reopen→rozvin→layout→SVG/PDF modelu B, skutečný editor, plná PC-007A nebo digitální P2. AC-US08 má **0 účastníků / NOT_RUN**; fyzické sestavení patří P3 a zůstává **NOT_RUN**. Po opravě LUI01 je nutné nezávisle přehrát původní vlastní negativy na přesném novém pinu. Žádný commit ani merge reviewer zatím neprovedl.

## Nezávislé přezkoušení opravy — 133a2ef

Exact widget source **`133a2efb5f4a6a1ae43c42cc7b669f27b9cbd410`**, SHA256 `faeeef680b06d3540bbd1bebb32ab29b4c163ddfac73779d15c8c4af51a810f3`. **LUI01 CLOSED / VERIFIED.** Původní historický report i FAIL raw zůstávají zachované. Oprava srovnává ordered correspondence IDs, seam i existující ruling/end IDs; nové identity kontroluje na přítomnost, UUID formát a jednoznačnost včetně kolize s patch IDs. Změna seam uzavřeného profilu viditelně otočí autorské řádky ještě před odesláním požadavku; ruční přesunutí řádku s nesouladným seam nabídne konkrétní opravu a blokuje výpočet.

- [Původní vlastní orákuly beze změny očekávání a autorovy testy: 56 PASS / 1 SKIP / 2,24 s](evidence/pc007a-loft-ui-review-133a2ef-replay.xml). Vlastních devět případů nyní všech prošlo. Jediný SKIP je skutečné veřejné core API, které tato samostatná widgetová větev neobsahuje; nepovažuje se za PASS.
- Reviewer následně samostatně spustil skutečný veřejný API smoke proti archivu exact core `a1cbf920397694f3b1d3e85a08052acdc3962a7b` a výše uvedenému exact widgetu: [1 PASS / 0 SKIP / 0,25 s](evidence/pc007a-loft-ui-review-133a2ef-api-smoke.xml). Test provedl closed seam → preview → add, pak load původních parametrů → změnu seam → preview_update → update. Před příkazem zdroj zůstává nedotčený, výsledné ordered IDs/seam odpovídají viditelnému požadavku a end ruling zůstává původní. [Runner](evidence/pc007a-loft-ui-review-api-smoke.py) a [binding manifest](evidence/pc007a-loft-ui-review-133a2ef-api-binding.json) zaznamenávají actual import cesty/hash i oba source piny. Jde o identitu widget/API, **nikoli nezávislé schválení matematického modulu, model B vytvořený UI nebo celý workflow/export**.
- [Další vlastní response-atomicity případy](evidence/pc007a-loft-ui-review-fix.py): [2 PASS / 1 FAIL](evidence/pc007a-loft-ui-review-133a2ef-atomic.xml). Neplatné nové end UUID a nové end UUID kolidující s patch ID se správně odmítají bez adopce částečných identit. Třetí případ odhalil menší zbytkovou vadu LUI02 níže.

### LUI02 MINOR / OPEN — neplatný text výsledku se ověří až po adopci nových IDs

Injected preview vrátí jinak platnou odpověď s novými UUID a `message=None`. `_show_result` zkontroluje identity, adoptuje je do draftu, poté při skládání feedbacku nastane `TypeError`. Handler správně zahodí preview a zakáže Apply, live projekt zůstane nezměněný; **draft však již obsahuje nové ruling/end IDs z odmítnutého výsledku**. Existující identity jsou novým fence chráněné, proto jde o MINOR malformed-response atomicity, nikoli znovuotevřený LUI01 nebo prokázanou chybu skutečného core.

Požadovaná úzká oprava: validovat typ/připravit feedback a všechny převzaté hodnoty před jakoukoli adopcí draftu, případně bezpečně normalizovat zobrazovaný text bez výjimky. Původní test očekává, že **odmítnutý** výsledek nezmění `_parameters()`; nesmí se pouze smazat nepohodlná regrese. Nález i reprodukce byly okamžitě předány integračnímu ownerovi a autorovi. Žádná produkční změna, staging ani commit reviewera.

Aktuální závěr: **LUI01 opraven; celkový widget report čeká na cílené uzavření LUI02.** Všechny výše uvedené meze digitálního/nativního/lidského/fyzického důkazu beze změny; UI/verif/delivery skills byly pro přezkoušení znovu načteny a použity na konkrétních výsledcích.

## Finální cílená revize LUI02 — 6efd70a

**APPROVED_IN_SCOPE — widget/API identity a atomické převzetí odpovědi. LUI01 i LUI02 CLOSED / VERIFIED.** Exact widget source **`6efd70a33f377298a267b4a91214e5383eb548f5`**, SHA256 `09b1cef95cbf65439b65dfc34f014d0ad814862f15c5dbb85ae899e840132d85`. Starší OPEN závěry výše popisují historické piny; raw se nepřepisuje.

Přečtená úzká oprava nyní před jakoukoli adopcí připraví převzaté parametry, ověří neměnnost druhého profilu a explicitních výpočetních parametrů, ověří textové prezentační hodnoty, vytvoří celý feedback a kopii určenou k publikaci. Teprve potom zveřejní úspěšný náhled a převezme nové draft IDs. `message=None` je tedy bezpečně odmítnut před mutací.

- Reviewer skutečně přehrál **všech 12 vlastních případů** z původních souborů beze změny očekávání: [12 PASS / 0,82 s](evidence/pc007a-loft-ui-review-6efd70a-own.xml). To zahrnuje původní čtyři LUI01 negativy, source fence, clone/cancel/C05 a všechny tři atomicity případy LUI02 včetně původně selhávajícího `message=None`.
- Cílené autorovy identity/presentation/staging regrese: [16 PASS / 1,03 s](evidence/pc007a-loft-ui-review-6efd70a-targeted.xml). Neprováděla se nová široká testovací etapa.
- Změněné kontroly skutečné odpovědi mohly ovlivnit veřejný API kontrakt, proto reviewer zopakoval [actual core create/edit smoke: 1 PASS / 0 SKIP / 0,26 s](evidence/pc007a-loft-ui-review-6efd70a-api-smoke.xml) s exact archivem core a1cbf92 a final widgetem 6efd70a. [Samostatný runner](evidence/pc007a-loft-ui-review-api-final.py) a [binding manifest](evidence/pc007a-loft-ui-review-6efd70a-api-binding.json) zaznamenávají oba piny, skutečné importované cesty a ověřený hash widgetu. Historický 133a runner i jeho raw zůstávají beze změny.

V pokrytém widgetovém rozsahu nebyl nalezen další zásadní nález. Jde výhradně o **offscreen Qt a veřejný API input/output identity smoke**, nikoli schválení reviewerovy vlastní loftové matematiky, aktuálního integračního desktop buildu, úplného modelu B nebo celé PC-007A/P2. Nativní desktop nebyl použit. AC-US08 má nadále 0 účastníků / NOT_RUN a P3 fyzický proof je NOT_RUN. Reviewer neměnil produkci, Git staging ani neprovedl commit.
