# PC-006B — digitální prostor pro ohyb přímé chlopně

Samostatný core přírůstek pro [AU07](../v1.2/ACCEPTANCE.md) a [konstrukční kontroly](../v1.2/ARCHITECTURE.md). Autor `authoring_export`; nezávislá revize čeká na jiného autora. Před prací skutečně načteny skills konstrukce a ověřování. Tento modul nemění persistence, sestavovací doménu ani UI. Základ izolované větve `revival/p2-bend-clearance`: `4bb5c436f5055cf278d756a637d1c5017ed8964b`.

## Kontrakt a hranice

`src/archpapercraft/authoring/clearance.py` nabízí čisté `check_fold_clearance(sweep, material, obstacles, *, expected_obstacle_ids, allowances=(), max_depth=12, max_intervals=4096)`.

- `MaterialProfile(thickness_mm, clearance_mm, bend_radius_mm)`: výslovné hodnoty **na papíře v mm**. Tloušťka může být `None`; gramáž se nepřevádí na tloušťku. Vůle a poloměr jsou nezáporné geometrické rezervy.
- `FoldSweep(patches_world_mm, hinge_start_mm, hinge_end_mm, angle_deg, source_id, receiver_id, initial_normal, final_normal, tab_id)`: rovná konečná osa, podepsaný úhel do 180° **včetně statického 0° spoje**, počáteční i konečná normála téže materiálové strany. Souhlas konečné normály se skutečnou rotací je kontrolovaný. Materiál leží na jedné straně crease a skutečně má nenulový hraniční interval na dané hinge; osa uvnitř materiálu nebo mimo něj není automaticky platný ohyb.
- `patches_world_mm`: **tentýž skutečný materiál** rozdělený na konvexní rovinné dílčí polygony. Root předá přesnou triangulaci konkávního autorského obrysu. Každý patch se kontroluje samostatně; nevytváří se vyplněný hull konkávního dílu. Neztriangulovaný konkávní nebo nerovinný patch je `UNRESOLVED`.
- `MaterialObstacle(id, triangles_world_mm, thickness_mm, role)`: původní materiálové trojúhelníky včetně skutečných trimů. Registry musí přesně odpovídat `expected_obstacle_ids`; source a receiver jsou vždy povinné. Root napojí **všechny sestavené plochy včetně nepřipojených**. Pole `role` je popis, nikoli oprávnění něco vynechat.
- `ContactAllowance(obstacle_id, kind, vertices_world_mm, angle_interval_deg, reason)`: konečný konvexní objem, v němž je výslovně dovolena lokální hinge nebo finální kontaktní oblast. Halfspaces se odvodí interně. Hinge permission může patřit source/receiver; final contact pouze receiver. Cizí nepřipojenou překážku tímto vyjmout nelze. Každá použitá oblast, úhlový interval a důvod jsou ve výsledku.

`ClearanceResult` vrací `status`, zprávu, dotčené `tab_id/obstacle_id`, případný skutečný úhlový/poziční svědek, počty intervalů, numerickou rezervu, materiálové hodnoty, seznam ověřovaných identit a výslovné povolené oblasti. Root z toho vytvoří konkrétní opravitelné issue; nejsou to parametry, které má začátečník zadávat jako matice/halfspaces.

## Co jednotlivé stavy znamenají

| Stav | Význam |
|---|---|
| `CLEAR` | Pro celý spojitý zadaný pohyb byla oddělena obálka materiálu s uvedenou tloušťkou/vůlí/poloměrovou rezervou od všech ostatních materiálů **mimo výslovně evidované lokální kontaktní objemy**. Není to fyzická certifikace papíru. |
| `COLLISION` | Existuje konkrétní úhlová poloha se striktním průnikem reálných materiálových prism, nebo skutečných nulových střednic při neznámé tloušťce. Vzorky mohou dodat tento negativní svědek; nikdy samy nezakládají pozitivní stav. |
| `UNRESOLVED` | Nepodporovaná/poškozená geometrie, neúplná registry, špatná normála/hinge, numerická neurčitost či vyčerpané zjemnění. Překryv konzervativních obálek není automaticky prohlášen za skutečnou kolizi, ale ani za volný prostor. |
| `UNVERIFIED` | Tloušťka alespoň jednoho materiálu není známa a nebyl nalezen striktní nulově tenký průnik. Pozitivní clearance nebyla potvrzena. **Geometrický průnik se hledá i v tomto případě**, takže unknown nikdy předčasně nepřeskočí B02. |

Téměř koplanární překryv uvnitř numerické nejistoty je `UNRESOLVED`, nikoli tiché přijetí pod P3 varováním. Skutečný export musí nalezený průnik a nerozhodnutelnou geometrii zablokovat. Obecnou material uncertainty může UI vysvětlit samostatně podle platného kontraktu; checker jí nevydává `CLEAR`.

## Spojitý pozitivní důkaz

Po odečtení počátku hinge označme jednotkovou osu `h`. Pro každý vrchol `p` základního konvexního patche se známou normálou `n` nejprve vytvoříme **skutečné normálové tloušťkové vrcholy** `p ± n·t/2`. Ty rotují společně s materiálem. Tloušťka se tedy nerozšiřuje všesměrovou koulí, která by přidávala falešný materiál vedle konečného footprintu.

Rodriguesovo rozložení každého takového vrcholu je

`q(θ) = h(h·p) + (p − h(h·p)) cos θ + (h × p) sin θ`.

Pro libovolný pevný jednotkový separační směr `a` jde o skalární funkci `c + A cos θ + B sin θ`. Na celém úhlovém intervalu se vyhodnotí oba konce **i všechny vnitřní kritické úhly** `atan2(B,A) + kπ`. Minimum a maximum přes všechny vrcholy pokrývá také každou jejich konvexní kombinaci, tedy celý rotující konvexní materiál, nikoli pouze jeho rohy. Konkávní materiál je sjednocením přesně dodaných patchů.

K projekčnímu intervalu přičteme `clearance_mm + bend_radius_mm` a numerickou rezervu. Poloměr je zde konzervativní maximální geometrická rezerva/deformující obálka mimo tuhý pohyb, **ne výpočet pružnosti ani automatická délková kompenzace**. Pokud actual kinematika nejde tímto obálkovým předpokladem popsat, tento checker ji nemá přijmout jako ověřenou.

Každý statický materiálový trojúhelník je extrudován o jeho skutečnou tloušťku na konvexní prism. Z jeho vrcholů se vypočte projekční interval. Jakýkoli pevný směr se striktní mezerou dokazuje oddělení celého průběhu tohoto intervalu. Směry zahrnují světové osy, normály překážky, normály a hrany rotovaného patche v krajních/střední poloze a součiny hran. Výběr směrů ovlivňuje, zda se podaří důkaz nalézt, nikoli platnost nalezeného oddělení.

Pokud se oddělení nepodaří, interval se půlí. Před půlením se zkouší skutečná poloha na koncích a uprostřed jako případný **negativní** svědek. Při známé tloušťce je použit úplný konvexní SAT (normály obou těles a všechny součiny jejich hran). Při neznámé tloušťce se svědek počítá z původních nulových polygonů/trojúhelníků: striktní průchod uvnitř obou polygonů nebo přesný koplanární překryv nenulové plochy mimo permissions. Uměle tenké proxy prisms v tomto režimu pouze konzervativně omezují hledání; nesmějí být zdrojem údajné materiálové kolize.

Žádný konečný počet prázdných úhlových vzorků proto nevede k `CLEAR`. Neúspěšně zjemněný interval vede k `UNRESOLVED`, při unknown materiálu absence svědka stále necertifikuje clearance.

Nulový fold není prázdný seznam intervalů: výslovně se zkontroluje jedna statická poloha `[0,0]` a stejně jednopolohové kontaktní permissions. Nezměněná normála je povinná, skutečný cizí materiál se nadále testuje. Bez neznámé tloušťky se může prokázat statický `CLEAR`; s unknown zůstává absence průniku `UNVERIFIED`.

## Povolený kontakt není plošné ignorování plochy

Konečný konvexní permission objem se odečítá z **tlustých materiálových prism**, ne jen z jejich středu. Rozdíl se rozloží pomocí clippingu na konvexní kusy. Numerická rezerva permission mírně zmenšuje, aby neodstranila cizí materiál za svou hranicí. Při striktním nulovém kolizním svědku se naopak používá opatrné rozšíření permission, aby hraniční kontakt nebyl falešně vydáván za průnik. V přesné fázi kontaktu se u svědka zohlední všechny permissions aktivní **v tom bodě**, nikoli jen ty platné v celém větším intervalu.

Root z autorské hinge, skutečného footprintu a výslovného materiálového profilu odvodí tyto lokální geometrie. Nesmí z testu vyjmout celé source/receiver IDs ani automaticky zvětšovat rezervu, aby vyšel zelený stav. `crease_zone_mm` / „Místní pás ohybu“ popisuje lokální deformující se oblast mimo rigidní aproximaci; není to neprovedený výřez. Kontakt se publikuje jako výjimka s konkrétním rozsahem a důvodem, ne jako tvrzení, že papír může libovolně pronikat jiným materiálem.

Fázi finálního kontaktu nelze obecně odvodit z `asin(contactBand/největší_šířka)`: nejdříve se vrstvě přibližují body těsně za crease-zone. Použije se doložená **nejmenší radiální vzdálenost materiálu mimo povolený hinge objem**, případně konzervativní explicitní interval. Nedostačující lokální rezerva má zůstat problémem konstrukce, ne skrytě větší permission.

## Numerická oblast použití

Operace používají konečné IEEE double vstupy a SciPy convex hull/planární clipping; nejde o univerzální symbolický intervalový kernel pro libovolné extrémní souřadnice. Výsledek zveřejňuje numerický guard odvozený od velikosti souřadnic, dosahu, délky hinge a kondice vstupních polygonů/trojúhelníků/permission objemů. Guard má dolní mez `1e-9 paper mm`; přesáhne-li `1e-4 mm` nebo absolutní souřadnice `1e6 paper mm`, je geometrie mimo podporovaný přesný režim a vrací se `UNRESOLVED`. Separační test vyžaduje kladnou mezeru i po přidání této rezervy. Degenerace, neplanarita a nesoulad skutečné konečné normály se nepromění v prázdnou překážku.

Numerické mantinely i konzervativnost odečtení permissions jsou součástí nezávislé revize; analytický mechanismus nesmí být zaměněn za měřený počet vzorků nebo za fyzický proof. Pro velmi blízké dotyky může checker odmítnout rozhodnout místo falešného `CLEAR`.

## Nezávislá očekávání a provedené core regrese

`tests/authoring/test_clearance.py` má **30 úspěšných core případů** (bez skutečného desktopu). Expected jsou explicitní souřadnice, ručně určené vzdálenosti, úhly, plochy a ortogonální invariance, nikoli volání téhož helperu pro výpočet očekávání.

- **B02 z nezávislé revize:** hinge `[20,5,0]→[60,5,0]`, počáteční chlopeň směrem dolů do `z=-5`, podepsaný fold `−90°`. Cizí nepřipojená stěna má `x∈[25,55], y=3, z∈[-2.5,-1.5]`. Pro poloměr `√8` a úhel `−45°` plyne přímo `y=5−2=3, z=−2`, tedy bod `[40,3,-2]` uvnitř obou materiálů. Ploché i konečné polohy jsou volné. Test je `COLLISION` také pro unknown chlopeň, unknown překážku i všechny unknown materiály.
- **Mezi vzorky:** tenká překážka kolem analytické polohy `−17°` není zasažena počátečními koncovými/středními testy. S nulovým zjemněním zůstává `UNRESOLVED`; po adaptivním zjemnění vznikne konkrétní `COLLISION` svědek. Prázdné vzorky tedy nedávají falešný pozitivní důkaz.
- **Pozitivní 90° a 35°:** kompletní source/receiver registry se známou tloušťkou, vůlí a rezervou, lokálními hinge/kontaktními objemy a analyticky volným pohybem. Bez těchto výslovných oblastí se vlastní materiál skutečně zablokuje; neignoruje se automaticky.
- **Konkávní vlastní tab:** skutečný L-materiál má plochu `40·3 + 30·2 = 180 mm²`. Překážka leží v chybějícím rohu `x>50, radial>3`: plný původní obdélník je `COLLISION`, stejné místo proti přesným patchům L je `CLEAR`. Bounding hull by dal chybný výsledek.
- Nezávisle zadaný celý svět rotovaný přesným ortogonálním přeznačením os a posunutý zachovává výsledek. Změna tloušťky/vůle/poloměru změní prostorovou obálku. Neúplná registry, nepatřičné vyjmutí cizí překážky, chybná normála nebo neplatná hinge nemají `CLEAR`.
- **Statický rovinný spoj 0°:** zdrojová stěna a příjemce jsou sousední rovinné materiály. Pozitivní případ má skutečně jeden ověřený interval, ne prázdnou smyčku. Přidaný cizí materiál dává `COLLISION` pro známou i unknown tloušťku; při unknown a bez tohoto průniku zůstává `UNVERIFIED`.

Příkaz: `C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe -m pytest tests/authoring/test_clearance.py -q` z worktree `papercraft-bend-clearance`. Běh před finálním freeze: **30 PASS / 6,34 s**; aktuální přesný CODE SHA připne lokální commit vlastníka těchto souborů, následně jiný reviewer. Root integrace úplné registry a skutečný UI průchod ještě nejsou tímto core důkazem provedeny. P3 mechanika/tisk a nový uživatel zůstávají oddělené; neuzavírají chybějící digitální AU07.
