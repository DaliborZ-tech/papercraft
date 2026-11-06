# Kestřanské tvrze — konstrukční čtení referencí

6. 11. 2026. Autor analýzy: agent `authoring_export`; jde o čtení podkladů, nikoli nezávislé schválení vlastní implementace. Projektové skills **papercraft-construction** a **papercraft-verification** byly před prací skutečně načteny. Výklad navazuje na [produktovou analýzu](../v1.2/PRODUCT_ANALYSIS.md), [kontrakt](../v1.2/P2_IMPLEMENTATION_CONTRACT.md) a [AC](../v1.2/ACCEPTANCE.md); nemění jejich rozsah ani tolerance.

## Zdroj a metoda

Přesný existující adresář je `C:\zaloha_telefon_fotky\zaloha_telefon_fotky\modely\Krestřanské tvrze`. Název adresáře obsahuje `Krestřanské`; vlastní titul na obálce a v návodech je **Kestřanské tvrze**. Obálka uvádí Richarda Vyškovského, ERKOtyp, katalog ER-28 a měřítko 1:200. Pro návrh editoru je podstatná konstrukce, nikoli přenos výtvarného zpracování.

Bylo skutečně otevřeno všech **20 různých listů** `IMG_20210715_0001.jpg` až `IMG_20210715_0020.jpg` nástrojem `view_image`: obálka s fotografiemi sestavených modelů, další fotografie, návody, prostorové návodné kresby, půdorysy a dílové listy. Původní soubory mají 2480 × 3507 pixelů; prohlížeč je v tomto průchodu zobrazil zmenšené na 1334 × 1888. Čitelné konstrukční poznámky byly porovnány s rozloženými díly a prostorovými kresbami. Z fotografií ani z pixelových vzdáleností nebyly odvozovány výrobní rozměry nebo přesné úhly.

Zdrojové obrázky nebyly změněny, zkopírovány do repozitáře ani převáděny na nové výtvarné podklady. Níže je vlastní rozbor a identifikace zdrojů. `VIDĚNO` znamená přímo pozorovatelný obsah; `ODVOZENÍ` je návrhový závěr pro Papercraft. Ověření aplikace těmito obrázky neproběhlo.

## Co bylo skutečně prohlédnuto

V tabulce označuje číslo koncovku souboru `IMG_20210715_NNNN.jpg` v uvedeném adresáři. Čísla dílů jsou lokální pro Horní nebo Dolní tvrz; nejsou globálně jedinečná.

| List | VIDĚNO a konkrétní konstrukční poznatek |
|---|---|
| 0001 | Dvě fotografie sestavených modelů na obálce: oddělené stavební hmoty kolem nádvoří, hranolové věže s vyloženým horním patrem, kruhová věžička, různé střechy, most a samostatná terénní podložka. Jediný dům s jednou střechou nepopisuje skladbu modelu. |
| 0002 | Úvodní legenda rozlišuje rýhování z líce a rubu, vyřezávané plochy, rubové rysky a plochy pro přilepení jiného dílu. Začátek návodu Horní tvrze výslovně používá rubové připojení oken. U podhledu dílu 2 je pro opakované nosné prvky popsána pouze jejich osa, ne celý obrys lepení. |
| 0003 | Půdorys Horní tvrze a prostorová kresba NK1 ukazují otevřenou sestavu kolem nádvoří a průjezd. Text propojuje průjezd se stěnami na přenesené rysky; při sestavení věže upozorňuje na lichoběžníkový půdorys. |
| 0004 | Návod Dolní tvrze popisuje střechu z několika dílů, komín na označeném místě střechy, spojení ochozu s vnitřní plochou hradby a zvýšený terén. Příkop se skládá ze svahů, obvodových řezových částí, žeber a dna; následně se doplňuje most. Dole jsou fotografie obou sestavených modelů. |
| 0005 | Rozvin stěn Horní tvrze: nepravidelné konce, velké nepotištěné oblasti, pravoúhlé i lomené obloukové výřezy oken a dveří označené červeným křížem, uvnitř stěn značené přijímací oblasti, samostatně rozvinutá zapuštěná okna. Horní hrázděný pás je materiálově jiný díl než spodní stěna. |
| 0006 | NK2 Dolní tvrze ukazuje prostorové vztahy věže, ochozů, střech, studny a terénního příkopu. Značení dílů vede i na skryté/vnitřní části. Fotografie skutečné stavby slouží jako předloha; není fotografií papírového modelu. |
| 0007 | Více oddělených střešních ploch a jejich spojovacích chlopní, velká červená střecha s vnitřními bílými označenými místy pro další prvky a lomeným obrysem, průjezdové díly s obloukovým obrysem. U úzkého obloukového pásu jsou řady malých zubových chlopní. |
| 0008 | Dolní tvrz: velký členitý terénní díl 77, samostatné svahy/přechody 80 a 86, obvodové výškové řezy 78/79/87 a žebra 88. Současně jsou na stránce drobné vikýře a jednotlivé podpěry; velikost a význam nejsou totéž. |
| 0009 | Horní tvrz: dlouhé rozviny věžových stěn, samostatné rozvinuté horní pásy a mnoho opakovaných oken. Úzký obklad obloukového otvoru 94 má malé oddělené záložky podél dlouhých stran. |
| 0010 | Dolní tvrz: hradba s ochozem, sloučené rozvinuté stěny se zalomeními, dlouhý pás hrázděného ochozu, střešní plochy různých tvarů, otevřený obloukový průchod a opakované konstrukční podpěry. Kruhově působící věžový plášť 25 má dlouhou hranu dělenou do drobných chlopní. |
| 0011 | Horní tvrz: terén/nádvoří 46 má velkou nepravidelnou nepotištěnou vnitřní oblast a menší stavební stopy; samostatně je červeným křížem označen otvor pro studnu 77. Terénní doplněk T4 má další bílou stavební stopu. Více střešních dílů má odlišný tvar a řady označených protějších hran; díl 96 má obloukový průběh a dělené záložky. |
| 0012 | Dolní tvrz: dlouhé stěnové pásy 48/49, samostatné štíty s přehýbaným lemem, kombinovaná střecha 51 s bílými místy pro vikýře a menší střecha 10. Štít, tloušťka jeho lemu a střecha jsou samostatné stavební úlohy. |
| 0013 | Horní tvrz: oblé rozvinuté střechy/vějířové výseče 107/108 s dělenými chlopněmi, obvodově potištěný podhled 106, mnoho vlastních úzkých pásů a podpěr, zvlášť rozvinuté části nájezdu T6/T9. Bílý kruhový střed 106 obsahuje označení dílu a není označen křížem; bez dalšího ho nelze vydávat za vyříznutý otvor. |
| 0014 | Dolní tvrz: dolní věžová stěna a vyšší hrázděné pásy, velký střešní díl 5 a samostatné střešní plochy 6/7, vlastní vložené žebro 8, boční výřezy a vyznačené přijímací stopy uvnitř dílů. Opakovaná okna nejsou jen texturové značky: mají vlastní skládací rozviny. |
| 0015 | Horní tvrz: hradby s vnitřními přehýbanými pásy, střechy a rohové díly, samostatná okna/střílny. Na stěnách jsou přenášené rysky H–H a geometrie přijímací hrany pro jinou, přehnutou část. |
| 0016 | Dolní tvrz: nádvoří 76 s červeně označeným místem výřezu studny, oblé střechy 28/29 a obloukové podhledové díly 27/75, samostatně rozvinutá studna, zábradlí, drobné vikýře a pásy krytiny hradeb. Na konkávním oblouku terénu jsou rozdělené chlopně. |
| 0017 | Horní tvrz: návod výslovně spojuje rubovou chlopeň s ryskou uvnitř jiné stěny, krovy/střechy se osazují po předběžném srovnání sestavy na půdorys. Podpora 47 se lepí na rub nádvoří. U palácové střechy se rozlišuje vnější a vnitřní strana při osazování na stěny. |
| 0018 | Horní tvrz NK3/NK4: kruhová hláska s vyloženou palváčí, podpěrami a samostatnou střechou; hradby se kontrolně skládají k již hotové části a teprve potom fixují. Text explicitně popisuje jeden spoj palváče k věži natupo a jiné spoje pomocí podpěr. |
| 0019 | NK5 a pokračování: půdorys Dolní tvrze s příkopem; text nejprve kompletuje okna a rubové podpěry, pak uzavírá plášť. Podhled nese desítky prvků umístěných podle os; jedna chlopeň se lepí na rub do vnitřní rysky. Hradby Horní tvrze se následně fixují terénními díly T1/T11 a spojkami T2/T3. |
| 0020 | Celková NK1 Dolní tvrze a detail hradby/studny. Žebro 50 se připojuje ke dvěma stěnám na vnitřní rysky, nikoli spojením jejich vnějších hran. Pokračování řeší vikýře osazené na střechu, schodiště s podhledem a samostatné stavební podsestavy. |

## Dopad na konstrukci Papercraftu

### Materiálový díl není uzavřená budova

**VIDĚNO:** rozvinuté pláště v 0005/0009/0014, výřez pro studnu označený křížem v 0011, rubové osazení oken před uzavřením a postupné připojování podsestav 0017–0020. Návod používá uzavření pláště v půdorysu jako pracovní operaci; fotografie spodní stranu staveb neukazují. Z podkladů tedy nelze poctivě tvrdit, že každá věž je bez dna, ani z nich vyvodit povinnost dna.

**ODVOZENÍ:** jednotlivá stěna, otevřený pás, žebro s výřezem, prstenec i otevřená sestava musí být platné samy o sobě. Případné uzavření, podhled a podložka jsou autorem vytvořené díly. Kontrola nesmí odmítnout otevřený okraj nebo jej automaticky uzavřít. Vazba na AC-AU02/03 a model A; uzavřený manifold není obecné validační pravidlo.

### Terén je konstrukční sestava, nikoli pouze obrázek pod domem

**VIDĚNO:** příkop Dolní tvrze tvoří díly 77–89 v 0004/0008; je zde dno, svahy, výškový obvod, tři žebra 88 a most. Nádvoří Horní tvrze 46 má nepotištěnou stavební stopu a rubovou podpěru 47 (0011/0017); skutečný výřez pro studnu je od bílé stopy rozlišen červeným křížem. Návod v 0019 fixuje části hradeb terénními spojkami.

**ODVOZENÍ:** už rovinná doména musí umět konkávní obrys, otvory, samostatnou výztuhu, rubovou lepicí stopu a umístění nad/pod jinou plochou. Toto není požadavek na automatický generátor reliéfu: popsaný terén lze autorsky složit z vlastních rovinných dílů. Jeden obdélník základny není reprezentantem všech takových situací. PC-006B musí vyzkoušet lepení výztuhy do vnitřku podložky a odlišit lepicí překryv při sestavení od zakázaného překryvu volných dílů při tisku.

### Střecha má svůj obrys, podhled a různé přijímače

**VIDĚNO:** nepravidelné střešní díly, vlastní štíty a bílá označená místa pro vikýře (0007/0012), samostatné podhledové díly (0013/0016), přesah viditelný na fotografiích (0001/0004), rozlišení vnějšího a vnitřního osazení střechy v 0017. Půdorys jedné věže je podle 0003 lichoběžník.

**ODVOZENÍ:** obrys střechy, připojovací stopa stěny, poloha vikýře a potisková strana jsou různé informace. Připojení nesmí zkrátit přesah ani přetvořit lichoběžník na pravoúhlý preset. Střecha rozdělená na několik ploch může být jedním materiálovým dílem přes skutečný ohyb nebo několika lepenými díly. Fotografie sama nedává numerickou velikost přesahu; tu musí určit autor a ověřit analytický fixture A. Případy s otvorem nebo samostatným podhledem nesmí být nahrazeny pouhou změnou textury.

### Vnitřní spoj potřebuje stranu, stopu a orientaci

**VIDĚNO:** rubové rysky pro průjezd, žebro mezi dvěma stěnami, rubový příjemce na nádvoří a umístění podpěr podle os (0002/0003/0017/0019/0020). Kromě chlopní text 0018 používá i spoj natupo. Číslo protějšího dílu na hraně není úplný popis takového spojení.

**ODVOZENÍ:** kromě hrana–hrana jsou nezbytné hrana–čára uvnitř plochy a lepicí oblast. Editor má ukázat obě spojované entity v 3D i rozvinu, stranu líc/rub, orientaci a skutečnou dostupnou plochu. „Osa pro podpěru“ může být vstupem pro umístění, avšak sama neprokazuje kontaktní plochu. Rozhraní musí umožnit autorské určení šířky materiálu/kontaktu, případně říci, že jde o omezený spoj natupo. Spoj nesmí tiše převést na velkou plochu lepení jen proto, že jsou entity blízko. AC-AU05/07 zůstávají rozhodné.

### Chlopeň je navržená geometrie a má výrobní smysl

**VIDĚNO:** velké zkosené chlopně u přímých hran, krátké sousední záložky okolo oblouků (0007/0009/0013/0016), jednotlivé konstrukční pásky a chlopně na různých stranách. Rýhování líce/rubu má v návodu 0002 jinou značku. Otevřené obloukové pásy jsou odlišné díly od kruhového podhledu s bílým středem; samotná bílá barva neznamená odstranění materiálu.

**ODVOZENÍ:** potřebujeme souvislou i dělenou chlopeň, upravitelný obrys, vlastní ID, určený ohyb a přijímače. Zubový tvar v obrázku není sám o sobě průkazem přesného ohybu nebo dostatečného lepicího kontaktu. U válce/kužele musí příslušný řez C odděleně ověřit dělení, mezeru, kolizi a kontakt po ohnutí. Tvar záložky nemá zakrýt otvor. Řez a base hinge nesmějí při exportu vzniknout dvakrát. P2 nemusí reprodukovat konkrétní vystřihovánku; má umožnit stejný druh autorského rozhodnutí.

### Sestavení není totéž co rozvin ani rozmístění na listu

**VIDĚNO:** díly jednoho stavebního celku jsou rozptýlené po stránkách; drobné opakované díly sousedí s velkým terénem nebo střechou. Návod opakovaně požaduje osadit detaily z rubu před uzavřením, porovnat sestavu s nádvořím a teprve pak fixovat. Palváč má podpěry a stranu zábradlí podle polohy v modelu (0018/0019).

**ODVOZENÍ:** samostatně uchovávat konstrukční polohu, materiálový díl a ruční tiskový layout. Výběr musí od dílu na listu dovést k jeho místu v sestavě i příjemci. Začátečníkovi mají akce odpovídat výběru („Připojit k ploše“, „Upravit chlopeň“, „Ukázat příjemce“); interní UV ani číslo algoritmu nesmí být nutná znalost. Pomoc může vysvětlit stranu spoje, ale nenahradí chybějící interakci pro její volbu. Tato inference není provedený test AC-US01–08.

## Konkrétní použití v navazujících řezech

Jde o podněty pro implementaci a nezávislé fixtures; současná specifikace má přednost. Nejsou tímto označeny jako implementované nebo PASS.

| Řez / existující AC | Malý vlastní fixture bez kopie předlohy | Co musí nezávislé očekávání rozlišit |
|---|---|---|
| PC-006A, AU01/02/03 | Konkávní podložka s velkým vnitřním výřezem a samostatná otevřená stěna | Materiálová plocha = vnější plocha minus otvory; výběr a oba exporty otvorem propouštějí; žádné doplněné dno. Dosavadní technické testy nelze vydávat za provedení celého modelu A. |
| PC-006B, AU04/05 | Stěna pod delší střechou, samostatná plocha podhledu a žebro připojené rubem do vnitřní čáry základny | Přesah a kořenové body stěny po editaci zůstávají; přesun tiskového dílu neposouvá konstrukci. Mimo materiál nebo do otvoru musí spoj konkrétně selhat; neztotožnit vnější hrany. |
| PC-006B, AU06/07 | Jeden zkosený pásek, tři individuální záložky a autorsky vypnutá prostřední | Příjemce, strana, kontaktní plocha a mezera jsou skutečné hodnoty, undo obnoví obrys i přiřazení. Export bez dvojitých řezů. |
| PC-007A, AU08/09 | Vlastní lomený gotický profil a samostatné ostění, navíc rovinný prstenec | Ostění je hloubkový spoj dvou profilů; prstenec je plocha s dírou. Fotografie oblého tvaru nenahradí korespondenci a test rozvinutelnosti. |
| PC-007B, AU10/11 | Vlastní kruhový plášť, samostatný prstenec/podhled, dělené záložky | Přesnost pláště zvlášť od konektorů; intervaly, kolize a skutečný kontakt vůči příjemci. Obloukové záložky nejsou automaticky EXACT. |
| PC-008/009, AU13/14/15/17 | Změnit šířku příjemce společného dílu s rubovým attachmentem a potom znovu otevřít projekt | Stabilní reference/kořenová kotva, stale dopad, zachování ručního layoutu, unresolved při zániku příjemce; stejná geometrie SVG/PDF a pravdivá metadata. |

Povinný test společného dílu stěna–střecha, přesné rozměry modelu A, odlišné profily B a negativní případ D se tímto nezmenšují. První autorská verze má nadále umožnit vlastní díl, úpravu, chlopeň, ruční layout a export z prázdného projektu. Reference ukazují, proč toto nemá být workflow omezené na house preset.

## Meze důkazu a otevřená práce

- **PROVEDENO:** vizuální čtení všech 20 zdrojových listů, porovnání fotografie / prostorové kresby / dílového listu / čitelného návodu, kontrola identifikace a SHA256.
- **NEPROVEDENO:** digitalizace tvarů, měření přesných rozměrů z obrázků, implementace těchto referenčních modelů, matematická certifikace jejich oblých ploch nebo konektorů. Na základě vzhledu nelze udělit EXACT; zvláště složené oblé střechy vyžadují vlastní geometrický popis.
- **NOT_RUN:** skutečný nový uživatel, ovládání aplikace nad těmito modelářskými situacemi, výtisk a fyzické sestavení. Publikovaná fotografie hotového modelu dokládá pouze zobrazenou podobu předlohy; není naším fyzickým proofem, měřením kalibrace ani důkazem sestavitelnosti nové varianty.
- **REVIEW_PENDING:** tento dokument je výstup cílené analýzy, určený integračnímu ownerovi a jinému reviewerovi. Není produktovým přijetím ani schválením vlastního kódu.

## Identifikace čtených originálů

SHA256 byly čteny přímo z originálů, bez zápisu do jejich adresáře. Celá sekvence byla otevřena přes `view_image`; hash není náhradou prohlédnutí. Tabulka umožňuje zopakovat čtení nad stejnými zdroji, pokud má reviewer přístup do místní knihovny.

| Soubor | SHA256 |
|---|---|
| IMG_20210715_0001.jpg | `cc6362ddd280336d80fbaa1499b2c4d776c10c75576a00f8ef7996c5c0e6b911` |
| IMG_20210715_0002.jpg | `2c13582a935f930e0bfa3b05a070b79d20fabbb966ef1bd65df7fd37035acc14` |
| IMG_20210715_0003.jpg | `d62d719abfd846edc5fcd7c61edd10e473b14eac38a1cfef213055e3d1cb95dd` |
| IMG_20210715_0004.jpg | `f05615725847668a0f57b7223ce0108d5d5b37f82d5a4c0b63c6b73896da7131` |
| IMG_20210715_0005.jpg | `659d4d0c1e6ccadd595e690608046e1f69e0d0f118ee61b7493afcc886f0b18e` |
| IMG_20210715_0006.jpg | `84ac34302d9de87dc5cfa7b28faeab3b492ca526b4da4155fee07157e348a270` |
| IMG_20210715_0007.jpg | `788351b90c646bd88dec8b2ee3a8ca68b8f97024278b31cea8d9bf102497ddf4` |
| IMG_20210715_0008.jpg | `bd4ef8fe4ed3a4aadeace107127bea3255d330aed6980ee3e58409adfe5bd0c6` |
| IMG_20210715_0009.jpg | `3b0651b8d2504bc4cfe143adb620887bde296c2fcf3d7e732178878fa1a14c08` |
| IMG_20210715_0010.jpg | `2afe8a95180bd296d3d6fe9c23650e26f72e8f66858952eafbca7ad23aa6c03e` |
| IMG_20210715_0011.jpg | `add0acc92e449f79fb8708d96a7c0d5e300f99c35402291b05839b19b6f16ff5` |
| IMG_20210715_0012.jpg | `0c690da60175a9c84f71c71db72b996f4a525c8c03ec9241ced8a019ddb9741e` |
| IMG_20210715_0013.jpg | `096684b7224e89798b4d01001cc6bb6ebfa63fb42c748b2ddd51ed37e899ef38` |
| IMG_20210715_0014.jpg | `46485261757112435dfa80f945269b7b8c1424eb9c8c2fece1ee9c4a0e8b502d` |
| IMG_20210715_0015.jpg | `8c9ea7fcab8c71bd7a7a7344f23d2377eb8bc438f8d0b7839d0b61c03aa9ef71` |
| IMG_20210715_0016.jpg | `5327886d189fa130f0ac23a10d491d8b309b4a34c83c16766f41c8a5f172593e` |
| IMG_20210715_0017.jpg | `059f3fb262a190feee2cd6f68ab9b17c2470fcec3d868bb8bd6b87c9a3946e80` |
| IMG_20210715_0018.jpg | `a72e8f17c9a4f5dc606c63ccebe56927ee06963d6de5f3b7491e5f9a3f95c02e` |
| IMG_20210715_0019.jpg | `da3b38f5eb9ae6c1fc95c978b3ec8ea102d9fbad5baac16456d42978a96df244` |
| IMG_20210715_0020.jpg | `c66c3b4e0a5d388fa3b6b62acac22a7b9c33af4ef2f703c7128001034252d61d` |
