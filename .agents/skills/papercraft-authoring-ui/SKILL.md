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

Před uložením, exportním snapshotem nebo rozhodnutím o neuložených změnách vyhodnoť i právě rozepsaný viditelný vstup. [C-05](../../../docs/p2/implementation/PC006A_REVIEW.md) doložil, že Ctrl+S/E/N bez Enter ignorovalo číslo; modální dialog pak mohl změnu potvrdit až po pořízení snapshotu. Příklad ověření: napiš nový rozměr a rovnou použij zkratku, také s neplatným rozměrem. Platná změna musí předcházet ukládanému stavu, neplatná musí zastavit operaci a zachovat předchozí práci. Automatizovaná regrese není důkaz nového uživatele.

Přepnutí pracovního kontextu sjednoť s aktuálním podvýběrem, stromem, vlastnostmi a3D zvýrazněním. [DU01](../../../docs/p2/implementation/PC008_UI_REVIEW.md) ukázal novou generaci v panelu, ale stále vybraný díl staré generace. Nestačí změnit popisek; podvýběr převeď na jednoznačného vlastníka nebo jej zruš. Příklad: při volbě jiné odvozené generace se vybere její původní konstrukční cíl a uvolní stará hrana/bod, zatímco samostatná volba materiálu pro tisk se nezmění. Ověř oba vlastníky a bezpečný další příkaz; přenos na jiný přepínač zůstává neověřený, dokud není skutečně použit.
