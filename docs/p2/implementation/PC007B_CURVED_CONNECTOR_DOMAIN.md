# Kruhové spojovací prvky: doména a uzavření zdroje

Tento návrh a kód patří do autorizovaného modelu C z [P2 v1.2](../v1.2/P2_IMPLEMENTATION_CONTRACT.md) a [AC-AU07 / AC-AU16](../v1.2/ACCEPTANCE.md). Samostatně nenahrazují skutečný UI průchod, nového uživatele ani fyzický výtisk P3. Nezávislé schválení této doménové integrace je **PENDING**; schválené dílčí matematické komponenty mají užší podmíněný rozsah.

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
- `test_curved_connector_persistence.py`: copy/Save-As, striktní formát, stabilní sloty, příkazy a undo/redo; tento záměrně nekruhový fixture sám není kladný výrobní důkaz.
- Navazující composer testy jsou samostatnou závislostí a zahrnují skutečný backend save/reopen→SVG/PDF. Jejich úspěch není nativní UI, člověk ani fyzická sestavitelnost.

Použití skills: konstrukce určila skutečný příjemce a materiálové role; ověřování zachovalo známý negativní B-02 i po přidání nejistoty a oddělilo zdrojový certifikát od skutečné publikace; UI vedlo k opravitelnému detached preview a vypnutí bez ztráty slotu; delivery vyžaduje připnutý zdroj a nezávislou revizi před integrací. Účinnost na novém uživateli a fyzickém modelu zůstává **NOT_RUN**.
