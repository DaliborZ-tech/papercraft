# Kruhové spojovací prvky: doména a uzavření zdroje

Tento návrh a kód patří do autorizovaného modelu C z [P2 v1.2](../v1.2/P2_IMPLEMENTATION_CONTRACT.md) a [AC-AU07, AU10–11, AU15–17](../v1.2/ACCEPTANCE.md). Samostatně nenahrazují skutečný UI průchod, nového uživatele ani fyzický výtisk P3. Nezávislé schválení této doménové integrace je **PENDING**; schválené dílčí matematické komponenty mají užší podmíněný rozsah.

## Autorský záměr a změny

Registr `curved_connectors` ve schématu 6 drží skutečný zdrojový loft, první/druhý okraj, skutečnou kruhovou přijímající plochu, její kontaktní stranu, explicitní minimální lepicí plochu a geometrické meze. Počet, šířka/mezerování, hloubka, místní ohybová rezerva, vypnutí slotu a posun vrcholu jsou autorské údaje. UUID slotů zůstávají i při dočasném snížení počtu nebo vypnutí. Celá vypnutá sada ani sada se všemi vypnutými sloty nemá aktivní materiál; explicitní přepočet obnoví holý plášť.

Příkazy `add_curved_connector`, `update_curved_connector`, `set_curved_tab` a `remove_curved_connector` jsou atomické. Uložení záměru nepředstírá geometrické schválení. `preview_curved_connector` pracuje na oddělené kopii, přepočítá skutečný díl a vrací stav, materiálový report a možnost další opravy; nezmění projekt ani jeho historii. Změna zdroje či sestavené scény zneaktuální celý vlastnický díl; autor spustí přepočet při zachování kotvy, rozmístění a zámků.

Známé schéma 5 se načte jako kopie s prázdným registrem. `requires_save_as` brání přepsání historického souboru. Neznámý formát nebo registr vložený do starého formátu se nepřijme jako známá migrace.

## Důkazy, které se nesmějí sloučit

1. Současný zdroj: skutečné kruhové profily, uspořádané korespondence, sestavené polohy, obě strany tisku, měřítko, přijímající disk a jeho skutečné otvory. Nepodporovaný posun, neprokázaná koplanarita či nekruhový příjemce končí `UNRESOLVED`.
2. Přenos nativního okraje na zdroj: každý slot používá tytéž skutečné příkazy `M+A/L` a vrchol jako komponovaný materiál. Producent nativního grafu dokládá celou derivační rezervu, nikoli odhad derivace z polohové chyby. Přenos používá skutečné intervaly poloměru/směrnice, skutečný společný prostorový rám a nejistotu jeho polohy. Binární zdroj kužele se nesmí zaměnit za nominální přesnou směrnici.
3. Skutečný řez: oddělený composer skládá holé tělo a záložky, odstraní společný základ z `CUT` a zachová jej jednou jako `GUIDES`. Zdrojovou plochu tvoří tělo a legitimní záložky; relativní povolená chyba je podle SO01 stále odvozena pouze od těla.
4. Ostatní sestavený materiál: níže popsaná konzervativní kontrola je další nutná podmínka. Důkaz tělo–sourozenci–příjemce tuto scénu nenahrazuje.

Uložené `certificate` a `material` jsou pouze odvozená cache. Stav porovnává jejich kompaktní otisky s čerstvým přepočtem, včetně skutečných příkazů, polygonů, hran a štítků. Poškozený aktuální důkaz blokuje stav; explicitní přepočet jej opraví. Otisk skutečných vstupů nezávisí jen na revizi a neobsahuje stránkové rozmístění. Vrácené struktury jsou oddělené; interní LRU ukládá jen neměnné kanonické řetězce, s konečnými počty položek.

`source_native_strain.status=SOURCE_NATIVE_STRAIN_CERTIFIED` výslovně označuje přenos současného zdroje na tytéž skutečné nativní příkazy A/L přes celý límec. Nejde o nový derivační důkaz pozdějších PDF kubik ani fyzického chování papíru. Skutečný PDF výstup má samostatné vektorové polohové, délkové a plošné přejímky.

Veřejné `curved_connector_geometry(cid)` propojuje výběr 3D a rozvinu bez přístupu UI do soukromých matematických helperů. Vrací celý stabilní pool slotů, stav vypnutí a vlastní vrchol, stejné skutečné nativní příkazy jako composer a pouze při čerstvém kladném stavu také vykreslovací závěs/lepicí trojúhelník ve světových modelových mm. Vykreslení používá referenční θ/f/α z téhož nativního grafu a současné zdrojové R/κ, společný prostorový rám a střed podle rovnice §2 matematického source-transfer proofu. Intervalové středy a konečné vzorky jsou **DISPLAY_ONLY**, nikoli nový důkaz. Při STALE/UNRESOLVED je geometrický overlay prázdný a stav popíše opravu. Vypnuté i dočasně nepoužívané sloty zůstávají dohledatelné svým UUID.

## Konzervativní kontrola celé scény

Souřadnice a parametry jsou v tiskových mm. Plocha cizího materiálu je uzavřena přes skutečný zdroj, nikoli vykreslovací síť: úsečky přes krajní body, Bézierovy křivky přes všechny Bernsteinovy řídicí body a oblouky přes celý obsahující kruh. Afinní zobrazení profilové roviny a skutečné sestavené polohy se provedou racionálně z uložených binárních čísel. Rovinný vnitřek a přímkově interpolovaný loft leží v konvexním obalu těchto zdrojových bodů. Otvory se pro tento horní obal bezpečně ignorují.

Celý pohyb jedné C záložky je v kouli kolem skutečného středu okraje. Poloměr je horně omezen součtem zdrojového poloměru, celé tangenciální půlšířky a hloubky a prokázané polohové rezervy límce/zdrojového přenosu, násobeným horní singulární mezí skutečného prostorového rámu. Přičítá se nejistota středu a publikační rezerva. Osově zarovnaný obal této koule dále rozšíří půltloušťka papíru, vůle a poloměr ohybu. Cizí materiál dostane vlastní půltloušťku a ohybovou rezervu. Přísně kladná vzdálenost těchto uzavřených obalů dokládá oddělení pro všechny nezávislé fáze; překryv obalů je pouze **UNRESOLVED**, ne důkaz kolize ani volného prostoru.

Registr pokrývá všechny materiálově vybrané plochy včetně nepřipojených, všechny starší přímé záložky a další aktivní C sady. Pro starší záložku je celý pohyb uvnitř obalu zdrojové plochy rozšířeného o celou šířku nebo L1-poloměr vlastního obrysu vůči závěsu. Žádné ID není plošně ignorováno. Vlastní tělo/příjemce C jsou výslovně řešeny matematickým přenosem a skutečným přijímačem; jejich případné starší dodatečné záložky se kontrolují zvlášť.

Opačný spotřebitel je také chráněn: starší přímý ohyb nezíská `CLEAR`, pokud u něj zůstává nedoložený blízký C/nerovinný materiál. Podporovaný rovinný zbytek scény stále hledá skutečné negativní svědky; již prokázaná kolize má přednost před další nejistotou. Neznámá tloušťka znamená `UNVERIFIED_MATERIAL`, nikdy kladný materiálový certifikát.

Záměrně jde o konzervativní podporovanou podmnožinu. Blízké jiné objekty, dotýkající se sousední pláště nebo složitější sestava mohou zůstat nedoložené, i když by jemnější důkaz uspěl. Stav to uvádí přímo; žádná obecná mechanika papíru se z tohoto geometrického oddělení nevyvozuje.

## Uzavření před publikací

`curved_connector_inputs` obsahuje všechny skutečné autorské zdroje, materiálový profil, rámy a úplný vybraný svět, bez odvozených geometrií/certifikátů a bez layoutu. `rebuild_curved_material_binding` vytvoří omezený zdrojový kontext, ověří skutečné vlastní profily, feature, rám, UUID coverage a všechny zdvojené vazby příjemce. Tento pomocný kontext nelze uložit ani vydávat za úplný autorský projekt.

Snapshot navíc nese úplný skutečný autorský projekt. `validate_curved_snapshot_binding` jej znovu načte a odvodí celý snapshot: obyčejné chyby, tiskový výběr, coverage, každý materiálový díl, umístění a C report musí přesně souhlasit. Nevolá exportní validator zpět. Rozměrové/plošné testy pak čtou skutečné serializované SVG/PDF v oddělené komponentě; tento doménový fence není náhradou jejich měření.

## Konkrétní ověření a meze

- `test_curved_connector_sources.py`: skutečné disky/otvory, první/druhá kontaktní a potištěná strana, nesouhlas sestavené polohy, nativní packet a přenos pro válec, kužel oběma okraji a téměř válec; rekonstrukce z přesných zdrojů.
- `test_curved_connector_scene.py`: nezávislý vzdálený objekt přesunutý dovnitř pohybu; Bézierova křivka s dalekými konci a blízkým vnitřkem; zachování původního skutečného svědka B-02 při neznámé/známé tloušťce i blízké C nejistotě; nezávislost uloženého důkazu na pořadí JSON registrů; poškozená cache; vypnutí všech slotů a opětovné zapnutí vlastního vrcholu.
- `test_curved_connector_geometry.py`: nezávislý poloměr závěsu, podobnost lepicího trojúhelníku a správné modelové jednotky při prvním/druhém okraji a dvou měřítkách; shoda skutečných příkazů, oddělené návratové struktury, vypnuté/uchované sloty a skrytí zastaralého overlaye.
- `test_curved_connector_persistence.py`: copy/Save-As, striktní formát, stabilní sloty, příkazy a undo/redo; tento záměrně nekruhový fixture sám není kladný výrobní důkaz.
- Navazující composer testy jsou samostatnou závislostí a zahrnují skutečný backend save/reopen→SVG/PDF. Jejich úspěch není nativní UI, člověk ani fyzická sestavitelnost.

Použití skills: konstrukce určila skutečný příjemce a materiálové role; ověřování zachovalo známý negativní B-02 i po přidání nejistoty a oddělilo zdrojový certifikát od skutečné publikace; UI vedlo k opravitelnému detached preview a vypnutí bez ztráty slotu; delivery vyžaduje připnutý zdroj a nezávislou revizi před integrací. Účinnost na novém uživateli a fyzickém modelu zůstává **NOT_RUN**.

## Připnuté výsledky

Doménové opravy a veřejný výběrový packet jsou v `104f292ee157ffb4d1b85329493ad01611f55fde` a `c5b86aa113aceec24092028f8bc12c688e2ec7a4`. Aktuální integrace s final composerem `67c44ae` a jeho důkazy `9eec5e5` je v `c680f8090782f90010b48b3e29589d28196178f5`. Na tomto runtime zdroji prošlo **187 vybraných regresí za 138,34 s**: registry/zdroje/scéna/veřejná geometrie, skutečný composer a callback save/reopen, kritické GUIDE/TABS výstupy, starší přímé ohyby, writer, async export/cancel a rollback, přesnost stránky a starší persistence. [Původní JUnit](evidence/pc007b-domain-c680f80-targeted.xml) je zachován. Není to úplná sada P2. Ruff a kontrola whitespace diffu prošly.

Samostatný [reprodukovatelný backendový průchod](evidence/pc007b-curved-domain-probe.py) je připnutý na `511805ce03b09be29766028958b84f081cf45bbd`; `src`, `tests` a `tools` jsou proti výše testovanému `c680f80` totožné. [Výsledek](evidence/pc007b-domain-511805c-run01/results.json) a [editovatelný projekt](evidence/pc007b-domain-511805c-run01/authored.apcraft) obsahují skutečný válec r10/h30, příjemce, 12 stabilních slotů, jeden vypnutý slot, vlastní posun vrcholu jiné záložky o 0,01 mm a další samostatnou vzdálenou materiálovou plochu. Ručně zadaný layout používá tři listy a zachované zámky původního pláště. Jde o volání veřejných backendových příkazů, **nikoli průchod přes UI**. Uložené původní bajty se během publikace nezměnily.

Nezávislé analytické očekávání skutečného materiálu pláště je `600π+11×0,24×9,5/2 mm²`. Skutečný serializovaný PDF má vůči source plošnou chybu pod `9,8e−14 mm²`; SVG pod `1,1e−12 mm²`. Poziční a celkové délkové chyby CUT, GUIDE a hranice fill TABS jsou všechny pod `1e−12 mm`, proti nezměněné explicitní rezervě `1e−6 mm`. Výsledek nese zvlášť `SOURCE_NATIVE_STRAIN_CERTIFIED` a vektorové skutečné PDF/SVG metriky; nedokládá nový derivační ani fyzický model PDF kubik.

V tomto konkrétním procesu trvala počáteční konstrukce 1,47 s, autorské změny/přepočet/layout 0,96 s, save 0,068 s, open 0,107 s, první/opakovaný snapshot 0,457/0,548 s, readonly výběrová geometrie 0,092 s a první/opakovaný export 1,116/0,432 s. Názvy `cold`/`warm` v raw JSON znamenají první a následné volání v tomto procesu; nižší závislosti mohly být zahřáté tvorbou modelu. Tyto časy nejsou měřením skutečné odezvy UI ani nového uživatele.

Skutečné velikosti v raw soupisu: projekt 641092 B, snapshot 1314766 B, společná exportní metadata 1318316 B, PDF 46323 B, jednotlivé SVG 743344–747491 B (každé obsahuje společná metadata). Source-only kontext má limit 32 MiB, registr 64 sad, pool 1000 slotů, privátní source LRU 4 a canonical snapshot LRU 2 položky; topologický composer má konečný budget 400000. Velikost důkazových metadat není odhadnuta jako nulová a tyto omezené cache neopravňují k tvrzení stálé interaktivity.

Nezávislá revize této doménové integrace, skutečný C UI průchod, externí SVG editor C, nový uživatel a fyzické sestavení zůstávají v příslušném rozsahu **PENDING / NOT_RUN**.
