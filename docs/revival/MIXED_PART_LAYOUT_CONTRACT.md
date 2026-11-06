# PC-008 — kotva společného dílu stěna–střecha

> Aktualizace 6. 11. 2026: tento dokument zachovává stav původního P0/P1 a v1.1. V1.1 byla skutečně přijata vlastníkem, potom byl cíl rozšířen. Aktivní návrh [P2 v1.2](../p2/v1.2/README.md) a jediná queue určují nynější rozsah/stav; review a baseline piny zůstávají historické. Povinné mixed-part testy se neruší. Push návrhu není jeho produktové přijetí.

Normativní doplněk kontraktu P2 v1.1 na žádost vlastníka z 5. listopadu 2026. Rozšiřuje provedení AC-I01/I02/I03/I05 a AC-X04 o společný díl; není to implementace ani PASS budoucího produktu. Všechny zde popsané implementační kontroly jsou **NOT_RUN**. Produktová brána zůstává PO_PENDING.

## Identita a souřadnicový rámec

Jeden `PaperPart` může obsahovat stěnu i střechu. Změna kterékoli z jeho ploch invaliduje **celý díl**, jeho chlopně a příslušné kontroly; nedotčenou stěnu uvnitř dílu nelze použít jako důvod k označení starého dílu za aktuální. Při nezměněném členství povrchů a jednoznačné kontinuitě se zachová part ID a placement, zvýší se obsahová/source revision a díl je stale až do ověřeného přepočtu.

`PaperFrame` obsahuje persistované `root_surface_id`, `anchor_vertex_id`, `axis_edge_id`, orientaci hrany a potištěnou stranu. Jde o významové reference konstrukce, nikoli index trojúhelníku nebo seřazený vertex index. Kotva je počátek lokálního rozvinu a orientovaná hrana určuje kladnou osu X. Rozvin se vždy koření ve stejném panelu a stejné orientaci; nemění počátek podle centroidu či minima aktuálního bounding boxu.

Při prvním vytvoření společného dílu se preferuje stěna před střechou; mezi způsobilými stěnami se vybere deterministicky podle stabilního významového klíče. Kotvou je pojmenovaný dolní roh a osou pojmenovaná spodní hrana této stěny. Volba se uloží a po přepočtu se znovu nevybírá. Při ručním join autor vybírá přijímající díl: výchozí kotva a umístění se berou z něj, UI ukáže dopad před potvrzením. Pokud autor přijímá do střešního dílu, zachovává se jeho explicitní kotva; UI neslibuje nepohnutou stěnu v takto jinak ukotvené sestavě.

`Placement(page_id, x_mm, y_mm, rotation_deg, locks...)` umísťuje **kotvu**, ne levý horní roh obálky. Pro lokální paper souřadnici bodu `u` je jeho poloha na stránce `p = [x_mm,y_mm] + R(rotation_deg)·u`. Papírové mm jsou již po převodu měřítka. Bounds se počítají až z této geometrie včetně chlopní; změna obálky nevyvolá posun ani packing. Save/reopen musí zachovat frame i placement.

## Co změna střechy zachová

Je-li kořenovou plochou nezměněná stěna a její kotva i osa zůstávají platné, změna výšky/sklonu střechy zachová na stránce **všechny body této stěny**, nejen hodnoty x/y/rotation. Stejně se zachovají další nezměněné plochy připojené ke kořeni pouze přes nezměněnou geometrii a nezměněné fold vazby. Změní se obrys střechy, příslušné spoje/chlopně a obálka celého dílu; vzniklé kolize/přesahy se hlásí, díl se neposune.

Pokud cesta jiné plochy ke kořeni vede přes změněnou střechu, její 2D poloha se může geometricky změnit, i když její vlastní rozměry zůstaly stejné. Taková plocha je **dotčená závislostí**, nikoli nedotčená stěna krytá slibem invariance. UI ji zahrne do přehledu dopadu a celý díl vyžádá kontrolu. Není možné současně garantovat libovolně fixované polohy všech panelů a zachovat změněné spoje; aplikace nesmí problém vyřešit jejich roztržením nebo nepravdivým tvrzením „stěny beze změny“.

Poloha, rotace i oba zámky zůstávají uložené. Zámek polohy/rotace omezuje změnu placementu, nikoli konstrukční deformaci střechy. Potištěná strana se nesmí tiše prohodit, přepočet nesmí použít zrcadlení. Potvrzení předchozích varování se pro změněný snapshot zneplatní.

Zmizí-li root/anchor/axis, zdegeneruje-li osa nebo není-li kontinuita jednoznačná, uložený frame/placement se zachová jako nevyřešený stav `ANCHOR_UNRESOLVED`; kompletní export je blokován. Žádný fallback na centroid, bounding box, první trojúhelník ani jiný stejně dlouhý edge. Autor zvolí novou kotvu s náhledem a jedním undoable příkazem. Jednoznačný sémantický nástupce je přípustný pouze s uloženou lineage mapou a ověřenou orientací.

Split: potomek s původní kotvou zachová frame. Jiný potomek dostane vlastní frame a přesnou rigidní mapu z dosavadního rozvinu, pokud existuje; placement se odvodí tak, aby se jeho dosavadní body na stránce nepohnuly. Nejednoznačný potomek přejde do explicitního stavu k rozmístění/kontrole. Join/split i změna kotvy mají atomické undo/redo; žádné přiřazení podle pořadí dílů.

## Povinný fixture a ověřovací kontrakt PC-008

Referenční dům 1:100, stěna 100 × 40 paper mm, střecha bez přesahu. Eave spoj stěna–střecha je **fold**, obě plochy tvoří jeden part se stěnovým rootem. Spodní levý roh stěny je lokální `[0,0]`, spodní hrana kladná X; stěna zabírá `[0,100] × [0,40]`, střecha pokračuje od y=40. Placement kotvy `[60,60]` paper mm na druhé A4 stránce, rotation=30°, oba zámky zapnuté. Tento hlavní fixture se vejde na fyzickou A4 i po změně střechy; úplná obálka s případnými chlopněmi se navíc validuje samostatně. Triangulační pořadí není součást expected.

Změna převýšení střechy 3000→3500 model mm při neměnné šířce domu 6000 mm změní lokální sklonovou délku `sqrt(30²+30²)=42.426406871...` na `sqrt(30²+35²)=46.097722286...` paper mm. Maximum lokálního y dílu se změní z 82.426406871... na 86.097722286... bez chlopní. Čtyři rohy stěny po placementu zůstávají:

| Lokální roh stěny | Bod na stránce v mm |
|---|---|
| [0,0] | [60,60] |
| [100,0] | [146.602540378...,110] |
| [100,40] | [126.602540378...,144.641016151...] |
| [0,40] | [40,94.641016151...] |

Expected vychází z analytické rotace/posunu, nikoli z helperu testovaného unfold/layout algoritmu. Použij stávající délkovou toleranci `max(0.01 paper mm, 1e-6 L)`; neměň ji kvůli stabilizaci identity.

| Případ | Očekávání a důkaz | AC / ticket |
|---|---|---|
| Změna střechy ve společném partu | Celý part stale a complete export blokován; po přepočtu stejné ID/frame/page/x/y/rotation/locks, všechny uvedené rohy stěny stejné, střecha má novou délku | AC-I01/I02; PC-008 |
| Rotace, jiné pořadí triangles a větší tab envelope | Žádná změna kotvy ani bodů kořenové stěny; nová kolize/přesah se hlásí bez automatického posunu | AC-I01/C10/L04; PC-008 |
| Nová kolize | Malý sousední materiál při x=10..20, y=84..85 v původním lokálním rámci leží mimo starou střechu a uvnitř nové; pro tuto izolovanou kontrolu jsou chlopně na horním okraji střechy vypnuté. Po transformaci se odhalí nová kolize, placement zůstane. Chlopně mají vlastní doplňující obálkový případ | AC-L04/I02; PC-008 |
| Save/reopen, undo/redo | Persistovaný frame a page souřadnice, undo obnoví starou source revision i geometrii; redo vrátí nový tvar bez driftu | AC-I05/I01; PC-008 |
| Kotva smazaná/neplatná, nejednoznačný split | Explicitní ANCHOR_UNRESOLVED/kontrola, žádná náhradní kotva bez příkazu, žádný kompletní export | AC-I03/I02; PC-008 |
| Stěna připojená přes změněný střešní panel | Zahrnuta do dopadu a ke kontrole; žádný falešný příslib její původní 2D polohy | AC-I01/I02; PC-008 |
| Tentýž smíšený part v SVG/PDF | Zachované kotvy i rohy stěny a změněný rozměr střechy ze stejného snapshotu; kontrola nezávislými čtečkami | AC-X04; PC-009 po PC-008 |
| Negativní overflow varianta s kotvou [30,60] | Při stejné rotaci má bod [0,ymax] x=-11.213203436... před změnou a -13.048861143... mm po změně: oba stavy přesahují fyzickou stránku, complete PDF je blokován. Přijetí varování nesmí tuto chybu obejít; hlavní pozitivní exportní fixture používá [60,60] | AC-L10; PC-008/009 |

PC-008 se nesmí uzavřít testem pouze oddělených stěn a střech. PC-006 zavede reference rámce/persistence; PC-007 nesmí joinem tyto reference zahodit; PC-008 ověří celý přepočet/layout a PC-009 exportní soulad. Původní AC se neruší: tento fixture doplňuje běžný případ oddělených dílů.
