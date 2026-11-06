# PC-006A — nezávislá integrační revize

6.11.2026. Reviewer: samostatný agent `authoring_independent_review`, autor původního nezávislého CODE review, nikoli autor produkce, oprav, pracovního mandátu, queue, nového skill odstavce nebo editor harnessu. Tato zpráva je samostatná od [CODE revize](PC006A_REVIEW.md). Reviewer prováděl pouze čtení a kontrolu připnutého archivu; nespouštěl OS automatizaci.

**Integrační CODE `b66b325eabc1e5cf744a73ac58ff6cda635d3603`, schválený produkční základ `4b172e65af3cde19c865cf7594c63fa004aa1ba2`. Verdikt: APPROVED_IN_SCOPE, 0 BLOCKER / 0 MAJOR.** Níže je jedna drobná nejednoznačnost záznamu `current_delivery` k rutinnímu sjednocení. Technické schválení PC-006A a produktové meze zůstávají zachované; nejde o schválení celého P2 nebo budoucího editorového pokusu.

## Následná úzká integrační kontrola po C-06

**Pin `1d8ed8b9db95a7e225ad77fbaffe7b943ddec828`: APPROVED_IN_SCOPE, 0 BLOCKER / 0 MAJOR; I-01 CLOSED.** Tato následná kontrola ponechává původní b66 revizi níže jako historii a doplňuje nový produkční source `7da240386550039761de6861d3149ce9ee1be466`/helper `5741cf144116123b4a0cb3f1c84987443517662a`. Produkce mezi `5741` a `1d8` je beze změny. C-06 byl nezávisle uzavřen [samostatnou CODE revizí](PC006A_REVIEW.md); skutečné run04/run06 důkazy nejsou předem schválené na základě starého run03.

[Vlastní kontrola konkrétního integračního archivu](evidence/pc006a-review-integration-1d8ed8b.json) potvrzuje:

- Produktová brána, její historie a historické definice ticketů jsou datově shodné s posouzeným b66. Nové úzké editorové PASS nemění přijetí celého P2, A/B/C/D, novice, fyzické P3 nebo závěrečný vlastní model AC-AU19.
- I-01 je opraven: `current_delivery.ticket=PC-006B`, předchozí ověřený A je oddělený v `previous_verified`; nejde o zpětné dokončení B. Jeho uvedené `4b` SHA je původní úsečkové schválení; nový C-06 source a meze určuje přidaný CODE review a delivery dodatek.
- Všech **30 relativních Markdown odkazů** v novém delta směřuje na existující cíl tohoto commitu a všech **89 uložených proof hashů** ve výsledkových manifestech přesně souhlasí s Git archive bytes. Staré neúspěšné běhy zůstávají FAIL; přidané PNG/PDF jsou vlastní UI/editor výstupy, nikoli zdrojové vystřihovánky. Veřejná dostupnost přes master vyžaduje následný push a ověření vzdáleného SHA integračním ownerem.
- SK-005 správně odkazuje na skutečné b66 nezávislé schválení rady. Její další použití a účinnost zůstávají pending.
- **Nová rada SK-006: APPROVED_IN_SCOPE** na tomto přesném pinu. Příčina a produktová oprava jsou podložené vlastním nezávislým A/B a nyní uzavřenou produkční regresí. Krátký verification odstavec ukládá skutečné postupné psaní víceslovného Unicode textu a uložený readback, zachování ostatních objektů a rozlišení bezpečně odmítnutého harnessu. Neoslabuje AC ani nezaměňuje Inkscape za všechny editory nebo novice. `PENDING_NEXT_USE` a PC-009 `NOT_RUN` správně nechávají účinnost nově napsané rady neověřenou. Aktuálně pending pole jejího nezávislého review a produktu lze teď navázat na tuto revizi a CODE uzavření; nedává to PASS budoucímu použití.

Tato kontrola nezahrnuje izolované rozpracované produkční změny PC-006B. Jeho digitální AU07 nálezy zůstávají oddělené a otevřené podle B review. Nepřidává rutinní produktovou bránu.

## Zdroj a přiměřené ověření

Porovnání `git diff 4b172e6 b66b325 -- src tests pyproject.toml` je prázdné. Nezměnil se schválený běžící produkt ani jeho testy/dependencies. Proto není důvod opakovat celou sadu 443 PASS nebo znovu řídit desktop; jejich konkrétní source vazba a předešlá omezení platí dál. Nové jsou dokumenty, reference, queue, úzký skill odstavec, skutečné historické důkazy a opt-in `tools/authoring/editor_probe.py`.

Z archivu konkrétního integračního commitu byly ověřeny [kontrolní výsledky](evidence/pc006a-review-integration-b66b325.json):

- Produktová brána je přesně shodná se základem: `PO_ACCEPTED`, skutečné přijetí P2 v1.2 vlastníkem, autorizace A/B/C/D a odkaz na původní záznam přijetí. `product_gate_history` i všechna `historical_definition_v1_1` zůstala datově shodná.
- **132 relativních Markdown odkazů** v přidaných/změněných dokumentech směřuje na existující soubor nebo adresář v tomto commitu. Důležité nové odkazy vedou na skutečný delivery/CODE report, normativní AC-AU19, původní přijetí a uložené důkazy. To ověřuje cíle v Git; dostupnost nové verze přes `master` nastane až po autorizovaném pushi a ověření vzdáleného SHA integračním ownerem.
- **53 výstupních SHA-256** v uložených manifestech skutečně souhlasí s archivovanými bytes, včetně native pokusů a editorového FAIL. `.gitattributes` chrání `docs/p2/implementation/evidence/**` přes `-text -whitespace`; PDF a PNG mají navíc binary režim. U těchto uložených důkazů se nepřipouští přepsání CRLF nebo „oprava“ historických výsledků.
- Úspěšný run03 zůstává navázaný na původní CODE 4b172e6. Starší neúspěšné native pokusy a první editorový pokus nejsou přepsané na PASS. Vysvětlení černého dialogového desktop snímku odpovídá skutečně posouzenému omezení.

## Stav produktu, nový závěrečný model a odhad

`PC-006A = AGENT_VERIFIED` je výslovně jen technický úsečkový řez: vlastní profil/plocha/otvor, základní vnější edge spoj a chlopeň, explicitní přepočet, stránky a vektory. `acceptance_state` rozlišuje chybějící obecnou křivkovou provenance, celé A/B/C/D, konverzi PanelProject a další exportní přejímky. `participant_count=0` a lidská osvojitelnost zůstávají NOT_RUN. Delivery report neuděluje produktové přijetí implementaci, celý model A, vnitřní spoj nebo fyzický PASS. PC-006B je označený IN_PROGRESS v izolované větvi; jeho review je stále NOT_RUN.

Výslovný následný realizační požadavek vlastníka je konzistentně přidaný do AGENTS, roadmapy, kontraktu, AC a PC-010 jako **AC-AU19**. Zachovává pořadí po A/B/C/D a PC-009, před závěrečnou nezávislou kontrolou a digitálním předáním. Vlastní menší historický model se má vytvořit od prázdného projektu přes skutečné UI, uložit/zavřít/otevřít, ručně rozmístit, upravit/vrátit a vydat v SVG/PDF s nezávislými numerickými očekáváními. Import hotové předlohy nebo backendová injekce není důkaz. Záznam je NOT_RUN a výslovně nenahrazuje A/B/C/D, skutečného novice účastníka ani fyzické P3. Nevytváří dodatečnou produktovou bránu a neruší platné přijetí kontraktu.

Odhad po PC-006A je aritmeticky konzistentní: původní zbývající řezy 50–85 člověkodnů + závěrečný model 2–4 = **52–89**, s rezervou 15–25 % zaokrouhleně **60–112 člověkodnů**. Devět až patnáct plánovaných dnů PC-006A se odečítá z budoucí práce a není vydáváno za měřenou dobu odpracovanou týmem. Dokument explicitně odmítá záměnu za agentní runtime nebo kalendářní termín a zachovává přepočet po PC-006B/007A. Dostupnost skutečného člověka se eviduje odděleně.

| Nález | Závažnost / stav | Konkrétní dopad a doporučení |
|---|---|---|
| I-01 | MINOR, předán integračnímu ownerovi | `current_delivery` stále obsahuje `ticket=PC-006A`, `status=IN_PROGRESS`, ale `then=PC-007A` a nově `next=PC-006B`. Samotné tickety A/B jsou správně. Starší čtenář pořadí `ticket→then` může B přeskočit nebo znovu začít A. Sjednotit aktuální ticket na B a předchozí technicky dokončený A uvést samostatně. Jde o metadata, bez dopadu na schválenou produkci nebo autorizaci. |

## Skills a doložené poučení

Reviewer načetl nový odstavec `papercraft-authoring-ui` i návazné delivery/verification instrukce. **Nová rada SK-005 je na tomto pinu APPROVED_IN_SCOPE:** vychází z konkrétního C-05, vysvětluje mechanismus `keyboardTracking=False`/focusOut po snapshotu, odkazuje na správnou revizi a dává použitelný pozitivní i negativní shortcut příklad. Neřeší problém nápovědou, ale požaduje správné pořadí transakce a zastavení při chybě. Nemění AC, nepřidává oprávnění a neoslabuje testy.

Je nutné zachovat rozdíl dvou věcí: produktová oprava bbd1578 byla nezávisle ověřená šesti vlastními Qt případy a uzavřená, ale nově napsaná rada ještě nemá ověřené další použití v PC-006B. `PENDING_NEXT_USE` a `next_use.NOT_RUN` jsou tedy správné. Pole `independent_review` rady je v b66b325 ještě poctivě pending; tento report je její novou nezávislou kontrolou a integrační owner na něj může záznam navázat. Další použití ani účinnost se tím automaticky nemění na PASS.

SK-003 a SK-004 uvádějí pouze **pozorovaný úzký přenos v PC-006A**, podložený původním CODE reportem: rozlišení analytické meze a vzorkování/serializace a skutečná vazba oprav na konkrétní piny. Nejde o obecně prokázanou účinnost skillu, pozorování nového uživatele nebo fyzický důkaz. SK-001 čeká na skutečné vnitřní konstrukční napojení a SK-002 na první kompletní autorskou verzi/novice sezení; jejich pending stavy nebyly účelově uzavřeny.

## Editor harness, reference a meze schválení

Nový editor probe pracuje s novou kopií vlastního exportu, kontroluje očekávaný HEAD, čerstvý evidence adresář, vlastní process PID/HWND a foreground před globálním vstupem. První uložený `pc006a-inkscape-c390a10-run01/editor-results.json` má skutečně **FAIL**, protože nebyl potvrzen vlastní foreground; zůstávají i provedené CLI kroky a dva soubory kopie s přesnými hashi. Aktuální dokumentace ani queue neprezentuje tento pokus jako dokončený externí GUI round-trip nebo splněný celý AU17/DPI. Bezpečné odmítnutí harnessu není selhání geometrie produktu. Budoucí úspěšný běh vyžaduje vlastní nový source pin, skutečný důkaz a úzké nezávislé posouzení; tento report mu předem neuděluje PASS.

Do commitu nebyly přidané originální skeny/PDF referenčních vystřihovánek ani jejich rendery. Přidané binární obrázky jsou aplikační proof screenshoty a framebuffer; `model.pdf` a editorové SVG jsou vlastní ověřené výstupy. Referenční Markdowny obsahují pozorování, místní cesty a hashe, rozlišují inspiraci od numerického očekávání a fyzického proofu. Dříve posouzená konkrétní vizuální podmnožina je doložená v CODE reportu; tato integrační kontrola neznamená, že reviewer osobně prohlédl každou autorem deklarovanou stránku všech sbírek. Vlastní analytický Damníkov návrh reviewer sám nezávisle neschvaluje.

Integraci a push provádí jediný integrační owner podle AGENTS po načtení aktuálního remote stavu, bez přepisování historie. Tento report nemění čekající produktové přijetí celé implementace, novice/P3 ani meze technického PC-006A schválení.
