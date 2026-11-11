---
name: papercraft-construction
description: Navrhuj a posuzuj konstrukci papírových modelů při změně ploch, profilů, spojů, chlopní nebo montáže v Papercraftu.
---

# Papercraft konstrukce

Před konstrukční změnou načti dotčený rozsah [kontraktu](../../../docs/p2/v1.2/P2_IMPLEMENTATION_CONTRACT.md), [produktové situace](../../../docs/p2/v1.2/PRODUCT_ANALYSIS.md) a příslušná [AC](../../../docs/p2/v1.2/ACCEPTANCE.md). Specifikace má přednost; skill ji nenahrazuje.

Ujasni si, co autor vystřihne, ohne a přilepí, ke kterému materiálu a v jaké sestavené poloze. Odděl zamýšlený prostorový tvar, vystřihovaný díl a stránku. Změnu posuzuj také na otevřené konstrukci; uzavřený objem není výchozí požadavek.

U spoje uvnitř plochy zachovej skutečný obrys a přesah. Sleduj zdrojový interval, cílovou stopu/oblast, stranu a skutečně dostupný materiál. Příklad: stěna pod přesahem potřebuje připojení uvnitř střechy; oříznutí střechy na hranu stěny by změnilo návrh autora. [Spike vnitřního připojení](../../../docs/p2/v1.2/GEOMETRY_SPIKES.md) je geometrický podklad, ne důkaz slepitelnosti.

Při úpravě chlopně zahrň její tvar, ohyb a příjemce, nikoli jen překryv na stránce. V ticketu dolož konkrétní konstrukční rozhodnutí a dotčený fixture/AC. Fyzický závěr podlož skutečným výtiskem podle akceptace.

Při dělení zdrojové hrany prověř všechny její spotřebitele, také ohyb existující chlopně a3D náhled spoje. [Nativní LINE průchod](../../../docs/p2/implementation/PC008_LINE_SUBDIVISION_DELIVERY.md) nalezl spotřebitele, který stále hledal zaniklé ID mezi aktuálními zobrazovanými hranami, přestože doména už uměla zachovaný celý zdroj. Příklad: rozděl hranu stěny s existující chlopní k základně při vybraném spoji, zachovej celý původní hinge a porovnej kontakt i kontrolu ohybu. První dítě ani nejbližší bod nejsou náhradou původní reference; přenos opravy na jiný typ spotřebitele musí mít vlastní důkaz.

Pro doložený problém oprav produkt a zapiš úzké zlepšení postupu podle [smyčky v AGENTS](../../../AGENTS.md#projektové-skills-a-poučení). Neověřený přenos do dalšího použití zůstává pending.
