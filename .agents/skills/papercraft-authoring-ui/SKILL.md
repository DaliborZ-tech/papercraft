---
name: papercraft-authoring-ui
description: Navrhuj, implementuj a reviduj osvojitelné autorské UI Papercraftu v každém průchodu od kreslení po opravu chyby a export.
---

# Srozumitelné autorské UI

Načti dotčený průchod v [UX](../../../docs/p2/v1.2/AUTHORING_UX.md), průřezová [AC-US](../../../docs/p2/v1.2/ACCEPTANCE.md) a případně [test s novým uživatelem](../../../docs/p2/v1.2/USABILITY_TEST.md). Ověřování použitelnosti patří do právě dodávaného řezu.

Pro aktuální výběr určete srozumitelný začátek, další dosažitelnou akci, viditelný výsledek a návrat. Postupně odkrývej složitější možnosti bez odstranění přímých příkazů, přesného vstupu a zkratek. Vedení musí jít vyvolat znovu i vypnout; nesmí být podmínkou základní práce.

Chybu řeš u dotčeného prvku s dostupným dalším krokem. Příklad: když autor nepozná, jak připojit stěnu dovnitř střechy, nejprve prozkoumej výběr cílové plochy, označení připojovací čáry a náhled spoje. Další textová nápověda sama neopraví neobjevitelné ovládání. Příčina musí vycházet z pozorování nebo reprodukce, nikoli z dojmu autora UI.

Rozpoznej, kdy selhává samotná interakce nebo členění pracovního prostoru: opakované chybné výběry, skrytá akce, nerozpoznaný režim či přerušená vazba3D↔rozvin mohou vyžadovat změnu struktury/příkazu. Současné panely ani tabulka obrazovek v UX nejsou povinný finální vzhled. Zachovej užitečné části, větší změnu spoj s konkrétním pracovním problémem a skutečným průchodem před/po; vizuální modernizace není výsledek testu použitelnosti. Běžný rework v rozsahu prováděj autonomně, zásadní alternativu způsobu práce předlož s ukázkou a doporučením podle AGENTS. Udržuj návaznost na ostatní řezy, nepřidávej další izolovaný způsob ovládání.

V ticketu dolož rozhodnutí, skutečný průchod, nalezené váhání a opravy. Odliš technické GUI ověření od sezení s člověkem, který aplikaci nezná. Při chybějícím účastníkovi nepřiděluj lidskému testu PASS; použij stav z protokolu. Zlepšení skillu eviduj v [poučení](../../../docs/p2/SKILL_IMPROVEMENTS.json) a ověř při dalším použití.

Před přidáním nástroje určete jeho místo v celé činnosti modeláře: který
pracovní pohled má prostor, co zůstane vybrané, které vlastnosti se zobrazí
a odkud vede další krok k papíru. [PO odmítnutí workspace 17. 11.](../../../docs/revival/P2_CONTINUATION_2026-11-17.md)
vychází z trvale soupeřících tří pohledů, dlouhé lišty a opakovaných problémů,
přestože jednotlivé funkce měly testy. V jednom skutečném průchodu ověř také
přechody mezi činnostmi, čitelnost celého aktivního pohledu a přímou nápravu
seskupeného problému. Jednotnou interakční architekturu drží vlastník Product
Designu; nezávislé expertní hodnocení může odmítnout nekonzistentní celek.
Jeho závěr eviduj odděleně od testu s novým člověkem.

Na skutečném snímku ověř také výsledek běžných drobných interakcí: sbalená
skupina musí skrýt své ovladače i po změně výběru, vlastní jméno jednoduchého
dílu musí jít poznat také na papíře a příkaz Vše musí ukázat celý asymetrický
model při aktuální velikosti pohledu. Nálezy z nativního průchodu v témže
[záznamu pokračování](../../../docs/revival/P2_CONTINUATION_2026-11-17.md)
prošly původní komponentovou sadou; opravu ověř původním scénářem. Odlišný
ruční název společného dílu zachovej a nezaměňuj zaměření výběru za Vše.

Před uložením, exportním snapshotem nebo rozhodnutím o neuložených změnách vyhodnoť i právě rozepsaný viditelný vstup. [C-05](../../../docs/p2/implementation/PC006A_REVIEW.md) doložil, že Ctrl+S/E/N bez Enter ignorovalo číslo; modální dialog pak mohl změnu potvrdit až po pořízení snapshotu. Příklad ověření: napiš nový rozměr a rovnou použij zkratku, také s neplatným rozměrem. Platná změna musí předcházet ukládanému stavu, neplatná musí zastavit operaci a zachovat předchozí práci. Automatizovaná regrese není důkaz nového uživatele.

Přepnutí pracovního kontextu sjednoť s aktuálním podvýběrem, stromem, vlastnostmi a3D zvýrazněním. [DU01](../../../docs/p2/implementation/PC008_UI_REVIEW.md) ukázal novou generaci v panelu, ale stále vybraný díl staré generace. Nestačí změnit popisek; podvýběr převeď na jednoznačného vlastníka nebo jej zruš. Příklad: při volbě jiné odvozené generace se vybere její původní konstrukční cíl a uvolní stará hrana/bod, zatímco samostatná volba materiálu pro tisk se nezmění. Ověř oba vlastníky a bezpečný další příkaz; přenos na jiný přepínač zůstává neověřený, dokud není skutečně použit.

Ověř také odmítnuté přepnutí při rozepsaném neplatném vstupu. CUI01 v
[revizi kruhových chlopní](../../../docs/p2/implementation/PC007B_CURVED_AUTHORING_UI_REVIEW.md)
ponechal správně původní dokument, ale combobox nebo checkbox již ukazoval
novou volbu. Vrať dotčený ovladač k platnému kontextu bez vyvolání dalšího
příkazu; zachovej chybný rozepsaný text pro opravu. Příklad: změna sady při
prázdném rozměru nesmí ukázat cizí sadu ani smazat rozepsaný rozměr. Ověř
výsledek příkazu i skutečně viditelný stav. Agentní replay tohoto případu
nenahrazuje pozorování začátečníka.

Výchozí výrobní označení posuzuj na skutečně rozmístěných dílech. DU02 v [průběhu D](../../../docs/p2/implementation/PC008_NATIVE_PROGRESS.md) ukázal, že dlouhý konstrukční název každého z64 dílů přesáhl sousední buňky. U nově generovaných dílů použij krátké jednoznačné označení a plný kontext zachovej ve stromu/vlastnostech; existující autorská jména nepřepisuj. Příklad: P26 se musí dát dohledat z papíru v3D i ve stromu. Ověř skutečný layout i vektorový výstup; screenshot autora není nový uživatel ani fyzický výtisk a účinek na jiném typu dílů zůstává pending.
