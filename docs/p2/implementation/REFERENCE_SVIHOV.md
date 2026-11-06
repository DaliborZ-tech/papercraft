# Švihov — čtení konstrukce pro autorský Papercraft

6. 11. 2026. Cílená analýza agenta `authoring_export`, nikoli schválení vlastní implementace. Před prací byly skutečně načteny skills **papercraft-construction** a **papercraft-verification**. Rozhodné jsou [kontrakt v1.2](../v1.2/P2_IMPLEMENTATION_CONTRACT.md), [produktová analýza](../v1.2/PRODUCT_ANALYSIS.md) a [AC včetně závěrečného modelu AU19](../v1.2/ACCEPTANCE.md). Tento dokument zaznamenává konkrétní referenční pozorování; specifikaci nenahrazuje.

## Co a jak bylo prohlédnuto

Přesný místní adresář je `C:\zaloha_telefon_fotky\zaloha_telefon_fotky\modely\Hrad Švihov`. Obsahuje 25 JPEG souborů `Svihov_1.jpg` až `Svihov_25.jpg`. **Všech 25 různých listů bylo skutečně otevřeno přes `view_image`**, včetně celkové fotografie na listu 10, celkových prostorových kreseb, textových pokračování návodu a dílových listů. Číslování souborů řadím numericky, nikoli lexikograficky `1,10,11…`.

Číslo souboru není číslem tištěné stránky. Například `Svihov_1.jpg` má dole tiskové označení D6 a `Svihov_5.jpg` D14; `Svihov_24.jpg` D12. Sestavy `a1/a2/a3` a `b1/b2/b3` jsou části modelu. Podle návodu na listu 16 bylo původní jádro `a` číslováno společně, zatímco části `b1/b2/b3` mají vlastní číslování rozlišené zeleným/růžovým/žlutým podkladem. Samotné číslo dílu tedy není globálně jednoznačný odkaz.

Zobrazené obrázky byly podle potřeby nástrojem zmenšeny; původní rozlišení se liší. Prohlídka nesloužila k měření milimetrů z pixelů ani k přebírání tvarů. Zdrojové soubory nebyly měněny nebo kopírovány do repozitáře. Rozlišuji **VIDĚNO** v podkladu od **ODVOZENÍ** pro produkt. Výsledek není důkaz ovládání aplikace, použitelnosti s novým člověkem nebo fyzického sestavení.

## Evidence po jednotlivých listech

| Soubor | Konkrétně viděný obsah a konstrukční význam |
|---|---|
| 1 | Historický úvod, legenda a začátek návodu. Rozlišuje rýhování z líce/rubu, vyříznutou oblast s červenou úhlopříčkou, prostřih a prořez v rámečku pro rubové osazení detailu. Některé zbylé plochy otvoru se po nastřižení vyhnou a přilepí na rub; nejde vždy o odstranění celé bílé plochy. Začíná rubové přenášení rysek na díly 3/13/34/25. |
| 2 | Jádro: dlouhé stěnové rozviny 3 a 94, samostatné menší stěny, obloukové/špičaté průchody a úzký obloukový pás 7 s dělenými chlopněmi. Vedle skutečně označených okenních výřezů jsou uvnitř stěny bílé přijímací stopy jiných dílů. |
| 3 | Zalomený hrázděný pás 1, velká nepravidelná plocha nádvoří 24, velké střešní plochy a malé vějířové stříšky/podhledy. Uvnitř rámu rozvinu jsou rozmístěny další samostatné díly. Prázdné místo na listu není automaticky otvor v materiálu. |
| 4 | Velké střešní díly 30/35, úzké spojovací/přehýbané díly 20/21/33, opakovaná okna a konzoly A/B. Velikost na stránce neodpovídá konstrukční důležitosti: drobná konzola má konkrétního příjemce a stranu. |
| 5 | Pokračování D14 a dvě prostorové kresby `a1`. Návod sestavuje žebro 17 do štítu/stěn před uzavřením pláště, připojuje arkýře do prořezů a osazuje střechy po etapách. Malé věžičky nemají všude předtištěnou stopu na střeše; jejich poloha je určena návodnou kresbou a vzdáleností od okapu. |
| 6 | Stěny jižního křídla 38/39, několikerý tvar střešních dílů a mnoho opakovaných otvorů s různým značením. Bílé čárkované plochy 43/45/46 uvnitř stěny slouží jako reference pro prostorové doplňky; nelze je sloučit s červenými značkami odstranění materiálu. |
| 7 | Rozvin horního hrázděného patra 37, vnitřní přesuny a rohy, střecha 90 s konkávním zářezem, vyložené části a samostatné obloukové/polygonální podhledy. Prostorové kresby `a2` ukazují střechu, nárožní věžičky, palváč a připojení nižší části. |
| 8 | Samostatný text `a2`: okna se lepí na rub před uzavřením; vyšší patro se osazuje postupně na dlouhou a krátkou stranu. Rozlišuje dvě dlouhé strany střechy. Palváč má horní a dolní díl a tři samostatné podpěry. |
| 9 | Díly kaple 62/63 mají lomené gotické otvory. Pro sedm otvorů jsou opakovány dlouhé díly 69 a 70 s dělenými chlopněmi a vlastní okenní vložky pokračují na listu 11. Stěnový pás obsahuje skutečné rohy i přijímací čáry K/L. Samostatné technické konstrukční díly 67/85/92 nejsou pohledová fasáda. |
| 10 | Fotografie sestaveného papírového celku, návod a prostorové kresby `a3`. Návod výslovně skládá sedm oken z 69/70/71, dvě výztuhy kaple 67/68 a 64/65 lepí na vnitřní rysky K/J. Střecha se připojuje na horní výztuhu a hrany kaple; spojovací zeď má vnitřní žebra a rubovou řadu detailů. |
| 11 | Okenní díly 71 s modrou kresbou skel mají vlastní obrys a chlopně; vedle jsou opakované zalomené pásy střílen 93, dveřní průchod 60, výztuhy 64/65/68 a velké střešní díly 75–78. Šikmé hrany střechy a její bílé označené místo pro další prvek nejsou automaticky díry. |
| 12 | Zelená část `b1`: hradby/obranné chodby 31/39/32/38, vnitřní podlahové pásy 50/51, dlouhé řady vyřezávaných polí a samostatné konzoly. Terén 47 je nepravidelný pás. Modrá plocha 66 s přijímacími stopami je další samostatný díl, nikoli pozadí stránky. |
| 13 | `b1`: střešní plochy 25/26 mají několik přehybů, vedle jsou oblé střešní pásy 56/57/58 a vlastní stopy pro malé věžičky. Brána má lícové díly 16/19 a vnitřní obloukové ostění 17; samotný venkovní kamenný oblouk nevytváří hloubku. |
| 14 | Rozviny vstupní věže `b1` 1/2/3 a menších navazujících dílů; nepravoúhlé konce, půlkruhové i lomené průchody, uvnitř vyznačené stopy příjemců 27/41/42. Samostatné ostění 13/14/17 má dělené záložky kolem oblouku. |
| 15 | `b1`: mnoho malých věžiček, jejich polygonální podhledy, otevřené obvodové pásy a vějířové stříšky; zároveň velký nečíslovaný potištěný materiál pro opravy. Materiálová zásoba není další konstrukční plocha hradu. |
| 16 | Dvě kresby `b1` bez střech a se střechami a začátek návodu opevnění. Výslovně rozlišuje vlastní číselné prostory částí b; doporučuje dokončovat podsestavy před spojováním. Brána/průjezd se sestavují z lícové stěny, ostění, protější stěny a konstrukčních dílů. Most, vodní hladina 66 a terén jsou alternativně sestavované součásti. |
| 17 | Pokračování `b1`, celková prostorová kresba. Hradby se uzavírají přes vnitřní chodbu a žebra, jejich volné terénní chlopně fixují spojky 64/65. Oblá bašta má dolní a horní část, podhled, více částí střechy, konzoly a palváč se skutečným otvorem/prořezem pro připojení. |
| 18 | Růžová část `b2`: dlouhé vnější a vnitřní části chodby 27/28/29, skutečná řada výřezů, mnoho opakovaných konzol, celé velké oblé střešní pásy 8/9 a malé samostatné stříšky. Modrý obvodový pás odděluje terénní/vodní okolí od pohledové stěny. |
| 19 | `b2`: dlouhý rozvin dolní bašty 1 a horní stěnové díly, hradba 19, terén 25, rámová/vnitřní konstrukce, střešní pásy a vyznačené stopy navazujících podsestav. Číslované bílé místo pro věžičku na střeše 9 není označené červeným křížem. |
| 20 | Návod a dvě kresby `b2`: na horní část bašty se lepí technické chlopně 21, oblá a rovná část se uzavírají v konkrétním pořadí. Hradby mají vnitřek, žebra a konzoly; podhled nese další prostorové prvky. Terénní spojky zajišťují vazbu bašty a dvou hradeb. |
| 21 | Žlutá část `b3`: velký stěnový plášť, vnitřní chodba s pohledovou podlahou, vyznačené příjemce a opakované podpěry. Dole nečíslované náhradní potištěné plochy a zdicí pásy, nikoli automaticky hotové díly s předepsaným rozvinem. |
| 22 | `b3`: rozvin oblé bašty 37, více rozdílných oblých střešních pásů 42/43/55/56, technické díly, podhledové obrysy, věžičky a terén. Opakované potiskové čáry šindelů neznamenají technologické přehyby. |
| 23 | `b3`: velká opakovaná políčka obranné chodby, více samostatných úseků hradeb, dlouhé vnitřní podlahové pásy a terén 28. Čárkované bílé přijímací stopy jsou různě umístěné podle navazující konstrukce, ne podle tiskového rozložení stránky. |
| 24 | Tištěná stránka D12 obsahuje vedle textu hradu také nesouvisející díly letounu. Pro analýzu hradu jsou relevantní vlastní text, schematický řez terénem a postup uzavírání hradeb: žebro 30 na vnitřní rysku C, další žebra 29/55 a terénní spojky. Celý list tedy nelze bez významového rozlišení importovat jako jednu vystřihovánku. |
| 25 | Dvě kresby `b3` s otevřenými střechami, celkový baňatý střešní tvar a dokončení celku. Návod popisuje založení na deskové podložce a volitelný příkop/polystyrenový terén, oddělené od papírových staveb. Hladká kresba báně sama neprokazuje přesný rozvin hladkého cíle. |

## Závěry pro konstrukci a ovládání

### Vlastní plocha, prostorový příjemce a materiálová strana

**VIDĚNO:** kaple má horní i dolní výztuhu uvnitř pláště (9–11), spojovací zeď a hradby vnitřní žebra (10/16/24), palváče mají podpěry a vlastní podhledy (8/17/20). Lepení se opakovaně vztahuje k rubu a ke konkrétní rysce uvnitř jiného dílu. Příjemcem není vždy vnější hranice.

**ODVOZENÍ:** PC-006B potřebuje skutečné `SurfaceTrace`/`GlueRegion` vedle `EdgePair`; žebro nebo podpěra musí být vytvořitelné stejnou doménou jako stěna. Příjemce, strana, umístění a kontaktní plocha mají vlastní význam. Záměna rubu nebo osazení mimo materiál musí být opravitelné přímo z UI. Hodí se vlastní příklad podhledu střechy s vnitřní připojovací čarou: výběr ukáže zdrojovou hranu a cílovou stopu současně v 3D i rozvinu. Označení interního UV není řešením ovládání pro modeláře.

### Zalomení a různá stavební hloubka

**VIDĚNO:** dlouhý stěnový pás tvoří několik prostorových stěn; průjezd má dvě pohledové stěny a samostatné ostění, arkýř vstupuje do prořezu. Kaple končí polygonálním závěrem (9/10), hradba má vnější stěnu, vnitřní chodbu/podlahu a tloušťku řešenou více díly (12/16/18/23).

**ODVOZENÍ:** rozlišení zdrojové plochy, materiálového dílu a místa na stránce je nezbytné. Jedna obrysová plocha fasády s dekorativně nakresleným obloukem nenahrazuje průjezd ani prostorové ostění. Stejně tak nelze do jedné plošné triangulace tiše schovat zamýšlený ohyb. Vlastní gotický otvor se nejprve vytvoří jako skutečný trim a připojené ostění musí samostatně zachovat hloubku, vrchol a korespondenci obou profilů podle B.

### Grafika, výřez, přehyb a pomocná stopa jsou různé věci

**VIDĚNO:** legenda na listu 1 odlišuje odstranění materiálu, prostřih, prořez pro rubový detail, rýhování z různých stran a vyhnutí zbylých záložek do rubu. Červené plochy střech a černé čáry šindelů jsou potisk, zatímco bílá označená plocha často přijímá jiný díl. List 24 obsahuje i cizí model; listy 15/21 obsahují zásobu potištěného materiálu.

**ODVOZENÍ:** role `CUT/FOLD/TABS/GUIDES/ARTWORK/LABELS` musí vycházet z autorsky určené technologie, nikoli z barvy nebo z OCR čísla. Otevřený řez vytvářející záložku není uzavřená díra; obrysový trim je jiná operace. Při rekonstrukci/reference se proto nejprve popíše „co odstřihnout, co zůstává, co ohnout, kam přilepit“. Pouhé přidání nápovědy nevyřeší nástroj, který tyto operace zaměňuje. P2 není automatické rozpoznávání starých scanů; zkušenost chrání vlastní kreslení a export před chybnou interpretací role.

### Střecha není parametr jediné krabice

**VIDĚNO:** velké nepravidelné střešní plochy mají více úžlabí, hřebenů a napojení, někdy je určeno postupné osazení na různé chlopně stěn. Malé věžičky mohou být osazeny podle vzdálenosti od okapu bez předtištěné stopy (5/8). Oblé střechy jsou rozdělené do více vytištěných pásů/výsečí (13/18/22), podhledy jsou samostatné konstrukční prvky.

**ODVOZENÍ:** vlastní konstrukční obrys musí zůstat nezávislý na připojovací stopě, přesahu a lepicí oblasti další věžičky. Přesah se při spojování nesmí odříznout. Graficky hladká baňatá kresba na listu 25 neurčuje přesnou matematickou plochu ani důkaz, že se dá hladká baň EXACT rozvinout. U vlastního P2 modelu lze volit podporovanou přesnou kuželovou/válcovou část nebo explicitní odvozenou segmentaci s doloženou chybou podle D. Jednotlivé rovinné dílky mohou být přesně rozvinuté, zatímco aproximují původní hladký cíl; tato dvě tvrzení musí zůstat oddělená.

### Konstrukční identita a změny

**VIDĚNO:** stejné číslo označuje jiné díly v částech a/b1/b2/b3; malá okna se opakují ve více stěnách; terénní spojky některých dřívějších etap se použijí až při spojování celku. Potištěné náhradní plochy slouží jako rezerva pro fyzické opravy, ne jako automatický důkaz geometrické správnosti.

**ODVOZENÍ:** stabilní ID a konkrétní vazba přijímače musí přežít dělení dílu, změnu střechy a ruční stránkový layout. Viditelné „Spoj J1 / protikus na stránce 2“ je užitečná modelářská navigace, ale interní identita nesmí záviset na tom, jak autor očísluje sestavu. Při ztrátě reference se vyžaduje konkrétní unresolved chyba a oprava; nejbližší hrana nebo podobné číslo není oprávněná náhrada. Povinný společný díl a invariant kořenové stěny podle AC-AU14 zůstávají.

### Terén a fyzická kompletace

**VIDĚNO:** papírové stavby mají terénní chlopně/spojky, oddělenou plochu vody a alternativní použití mostu (16/20/25). Příkop může být doplněn vnějším modelovaným terénem na desce. Návod doporučuje postupné fixování a schnutí; některé chyby se ve fyzickém modelu opravují proužky materiálu.

**ODVOZENÍ:** základna, terénní pás a stavební sestava nejsou jedno uzavřené těleso. P2 musí umožnit vlastní rovinné díly a jejich umístění; tato reference nevyžaduje zavedení automatického sochařského editoru terénu. Kontaktní geometrii lze digitálně ověřit, přístup k lepení, pružnost, zatížení a skutečnou montáž až po výtisku. Dodatečné lepidlo, posyp nebo retuš nejsou způsob, jak digitálně přijmout chybný spoj.

## Konkrétní inspirace pro PC-010 / AC-AU19

Následuje návrh testovacích situací, **nikoli kopie modelu Švihova ani změna přijatého rozsahu**. Konkrétní rozměry a numerická očekávání má ticket určit nezávisle; tento rozbor je neměří ze scanu. První vlastní model má být menší brána/věž s hradbou, členitou střechou s přesahem, gotickým otvorem a prostorovým ostěním, základnou a autorskými spoji podle již platného AU19.

| Situace vlastního modelu | Co má uživatel skutečně udělat v aplikaci | Nezávislé ověření |
|---|---|---|
| Věž a zalomená hradba | Nakreslit vlastní stěny a průchod; zvolit skutečné ohyby a lepená napojení, bez hotového house preset | Úhly, délky a otevřenost konstrukce; průchod nesmí být pouze grafika. Výběr 3D↔2D najde každou plochu i protikus. |
| Gotické ostění | Vlastní lomený profil otvoru, druhý rozměrově jiný profil, korespondence a hloubka; doplnit dílčí záložky | Analytické očekávání B, zachovaný ostrý vrchol a trim v obou exportech; neznámý či nerozvinutelný loft nezíská EXACT. |
| Podhled, žebro, přesah | Samostatný podhled a výztuha na vnitřní stopě; změnit přesah jedné střechy | Obrys přesahu nezmizí; stopa a kořenové body stěny se zachovají. Negativní příjemce skrz otvor zablokuje konkrétní spoj. |
| Oblý detail a dělené chlopně | Autorsky zvolený podporovaný válec/kužel nebo explicitní aproximovaná varianta; vlastní šev a záložky | Přesný rozvin zvlášť od kontaktu dělených záložek; režim a chyba souhlasí s uloženým zdrojem i SVG/PDF. |
| Průběžná oprava | Změnit profil, najít stale/unresolved místa přes UI, opravit příjemce, vrátit experiment | Stabilní identity, undo a invariant společného dílu; ruční layout na více listech zůstává zachován. |
| Digitální předání | Projekt uložit/zavřít/otevřít, ručně rozmístit na více listů a vydat SVG/PDF | Stejná úplná coverage, analytické rozměry a otvory po reopen, skutečný vektorový editor, kalibrace. Nový uživatel a výtisk mají vlastní oddělené důkazy. |

Vazby na řezy: PC-006B řeší především přijímače/podložky/autorské konektory; PC-007A profily a ostění, PC-007B oblé pláště a dělené záložky, PC-008 původ a aktualizace/odvození, PC-009 oba výstupy a PC-010 sestavený vlastní průchod AU19. Referenční fotografie nebo tento dokument žádný z těchto ticketů neuzavírají.

## Stav důkazu

**PROVEDENO:** 25/25 listů přes `view_image`, čtení legendy a vazeb návod → rozvin → prostorová kresba → fotografie, SHA256 originálů. **REVIEW_PENDING:** konkrétní analýzu musí posoudit jiný agent než její autor. **NOT_RUN:** vlastní historický model přes aplikaci, začátečník bez vedení autora, kalibrovaný výtisk a fyzické sestavení. Fotografie hotového historického modelu není naším P3 proofem. Žádný produktový kód, geometrická fixture ani původní soubor nebyly v tomto úkolu změněny.

## SHA256 pro opakovatelné čtení originálů

| Soubor | SHA256 |
|---|---|
| Svihov_1.jpg | `5532dbc9febd081d1abac40a6a24e518af5dd1fbfdee5530fd325f287c18e3c6` |
| Svihov_2.jpg | `fba184e0bf8df9a82ae3d13c51094b707e268e64f331f52826cb809eff5ce7f6` |
| Svihov_3.jpg | `e5e0174cb88188e6878d44df1e3647841e6c06baa3bea3173dbd69f7b075bda8` |
| Svihov_4.jpg | `3a5748e24ce7c6df92b60b8f753664fc52aaf814dd2b763fbd6b9532d939eb40` |
| Svihov_5.jpg | `4004e64bde3aac03c56472af9e7ebdecdf84730e71e667c5d2903271c4247520` |
| Svihov_6.jpg | `dc3c8de3af13cb8b018ac7f76ae6f08e8c60e516f707f18245d8681fd52bfcba` |
| Svihov_7.jpg | `8b3cf8c63b2b518e4eda234ee073eba5f5a20728456974d4f27b578bf360c7d3` |
| Svihov_8.jpg | `a1a7597ce9cf5ba4ebb6c6492f287ed8f95cc0e0054ef1dbe95284f54ee666de` |
| Svihov_9.jpg | `ec85ca0c1dcad8aac7e965f9a2e302aad1de959c71690de7fa26dde8b9beb000` |
| Svihov_10.jpg | `e224b660e24cfa0c0ef8f14bcc65a3eab432508469c04029850890736da6b0e1` |
| Svihov_11.jpg | `5a01f2d209409069c5de828ab66cf3678fdb28f097991001d08b59cacb1a282a` |
| Svihov_12.jpg | `1d006cfa18b2c99795c27e28abd663cd61579beb3253f53faa96f352125db5cb` |
| Svihov_13.jpg | `042012126db5953d2a2586d0e54667c65a5ecdf861a2cef85597c21a039669b3` |
| Svihov_14.jpg | `91f261f4126bee9900d4a2770aeea4dc897646f0eff26d55de90fa5042f8058d` |
| Svihov_15.jpg | `fbde26a0c744afeafed05f50abb7fec1767ca8b1c717f48225c970c4cb92d12c` |
| Svihov_16.jpg | `95b5ec5eb8206cd0f34af5deb7dfe1202342f1363284c98609818be004a889f7` |
| Svihov_17.jpg | `1f449f2eee0d633c6b3332ca9bac853407a0176419dc3ec83b214ae28e822e6f` |
| Svihov_18.jpg | `8d5f9c350b314441c0d4a2a6049c49ddc4f257fafeaba1c89b7ea725de4f13cb` |
| Svihov_19.jpg | `2ca0b623721af6e18f1ee10540786cd2f910841faa317484de78a208fcf8b48a` |
| Svihov_20.jpg | `0f918fb41462541d65b5370693af40efe8e2559592ff60cd5002ecb51a06bc3d` |
| Svihov_21.jpg | `11a8dcc15aa3e9a48dfe8c9334ecb0fc901a88f7df649a9657ebceb37d395188` |
| Svihov_22.jpg | `099755174ef6c5e674b862246f8ff890cfd952ff5312e8ec8499df36a3833b12` |
| Svihov_23.jpg | `506915a269026907f5700961ee3dcb16bd6f5d74f635d820a4696acbbec54d1c` |
| Svihov_24.jpg | `6c44ea34a9fbbf9a3cfb2083e7673bd139c8b0485db2a60ed5785675861b94e1` |
| Svihov_25.jpg | `27a6cd38651a4933cac6e03207c9799fad0e69ff2a823b1f2c57b989fa395818` |
