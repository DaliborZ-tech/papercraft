# Damníkov — nezávislé konstrukční čtení reference

6.11.2026, agent `authoring_independent_review`. Read-only prohlídka tří místních souborů, nikoli rekonstrukce autorského modelu, měření skenu nebo schválení produkční implementace. Použity projektové skills konstrukce, ověřování a delivery. Vlastní číselný příklad níže upřesňuje ověření již sjednaného [B1/B2/B3](../v1.2/ACCEPTANCE.md#b--ostění-mezi-dvěma-různými-obloukovýmigotickými-profily); nenahrazuje platná AC ani další přejímací modely.

## Co bylo skutečně prohlédnuto

Základní místní adresář: `C:\zaloha_telefon_fotky\zaloha_telefon_fotky\modely\Kostel v Damnikově`.

| Soubor v tomto adresáři | SHA-256 | Účel prohlídky |
|---|---|---|
| `abc_18_1.jpg` | `ccf9cb8452a818631e01b0595d96a6186ad56a185732058ca1454d63d3652da7` | List s obvodovými stěnami, okenními výřezy a doplňkovými díly. |
| `abc_18_6.jpg` | `7cf57efbc3706037886bc7e48128f80fd9605c3b3bf147faddd8db37476fb840` | List se sestavami oken a pásy ostění, zejména 35/36 a 41/42. |
| `abc_18_2.jpg` | `8d1a975bf509b72a155387f5e58cef3cceace495dff41f7156fbe8073af5e606` | Strana návodu s fotografií a montážním schématem; čtení významu výřezů, ohybů a sestav. |

Přesné zdroje jsou uvedené touto cestou a hashem; originální obrázky nebyly kopírovány do repozitáře ani měněny. Adresář obsahuje 14 souborů, tento reviewer neprohlašuje vlastní prohlídku zbývajících 11. Počet souborů není počet unikátních tiskových listů. Z rozlišení a perspektivy skenu se neodvozuje fyzické měřítko nebo výrobní tolerance.

## Co reference dokládá a co z ní neplyne

Na stěnách jsou označené skutečné výřezy včetně špičatých oken; nejde jen o kresbu okna na celistvé ploše. Návod vysvětluje červené křížové značení výřezů. Oddělené výplně a pásy se směrovým značením a mnoha chlopněmi ukazují konstrukci hloubky a návaznost na stěnu. Návod skládá sestavu 35/36 se dvěma výplněmi 34 a následně ji připojuje ke stěnám; pro další část uvádí sestavy 41/42. To je silný důvod pro výřez jako trim hranici s vlastním ostěním a adresovatelným příjemcem. Nahrazení celku plnou stěnou s texturou nebo fan triangulací přes otvor by účel ztratilo.

Pásy mají změny směru, rohy a husté dělení chlopní. Zřetelná gotická špička je především roh obrysu: sama o sobě není důkaz dvojité křivosti. Zalomený materiál se skládá z rovinných částí s určenými ohyby; stočený plášť mění normálu průběžně na hladkém intervalu. Jednotlivé natištěné hrany nebo trojúhelníkové chlopně tyto případy nerozlišují. Pro zakřivenou hranu lze také dělit chlopně, aniž by tím byl hladký samotný nosný pás.

Ze skenu nelze spolehlivě určit, zda každý konkrétní úsek ostění autor zamýšlel plynule stáčet, prostorově zalomit nebo při stavbě lokálně přizpůsobit. Návod podporuje čtení více samostatně zpracovaných okenních sestav; neobsahuje matematický certifikát ploch mezi libovolnými dvěma profily. Fotografie a montážní schéma nejsou vlastní fyzický výtisk tohoto projektu ani měření kontaktu chlopní po ohnutí. Reference tedy nenahrazuje povinné geometrické spiky, přejímku C/D, skutečné UI ani P3.

## Vlastní numerický B-fixture

Veškeré následující rozměry jsou **paper mm**, příklad je nově zadaný, nikoli obkreslený nebo odměřený ze skenu. Při projektu 1:100 se do modelových rozměrů zadává stonásobek. Lokální roviny otvorů používají osy x/y; hloubka je z. Autor vytváří vlastní profily v UI.

### Zdrojový otvor P0

Uzavřený profil v rovině z=0, průchod proti směru hodinových ručiček:

1. Úsečka z `(-12,0)` do `(12,0)` — spodní hrana.
2. Úsečka do `(12,24)` — pravý bok.
3. Kruhový oblouk se středem `(-12,24)`, r=24, úhel 0→π/3, do špičky `(0,24+12√3)`.
4. Kruhový oblouk se středem `(12,24)`, r=24, úhel 2π/3→π, do `(-12,24)`.
5. Úsečka zpět do `(-12,0)` — levý bok.

Roh ve špičce se zachová jako dva intervaly s různými jednostrannými tečnami. Nesmí se doplnit tečné vyhlazení. Nosná stěna má vnější obdélník `[-40,40]×[-10,70]`, z=0; P0 je její otvor, ne přidaný polygon materiálu.

Nezávislá analytická očekávání:

| Veličina | Přesné zadání | Numericky |
|---|---|---|
| Výška otvoru | `24+12√3` | 44.7846096908 mm |
| Délka každého oblouku | `8π` | 25.1327412287 mm |
| Celý obvod otvoru | `72+16π` | 122.2654824574 mm |
| Plocha otvoru | `576+192π−144√3` | 929.7704731993 mm² |
| Materiál nosné stěny | `6400−plocha otvoru` | 5470.2295268007 mm² |

Plocha otvoru je součet spodního obdélníku 24×24 a horní oblasti `2∫[12,24]√(24²−t²)dt`. Očekávání tím nevyužívá triangulátor nebo loft helper produktu.

### B1 — rozdílný profil a nenulová hloubka

Zvolit O=(0,18), k=1.2 a zadat druhý profil `P1(u)=O+k(P0(u)−O)` v rovině z=6. O leží uvnitř otvoru. P1 má spodní hranu y=−3.6, boky x=±14.4, úroveň počátku oblouků y=25.2, poloměry 28.8 a vrchol y=50.1415316290. Každý původní roh a obloukový interval má explicitního partnera; korespondence není nearest-point podle výsledného meshe.

Plocha ostění je `S(u,v)=P0(u)+v(P1(u)−P0(u))`, v∈[0,1]. Na každém hladkém intervalu platí `d'=0.2 P0'`, a tedy `det(P0',d,d')=0`. Nenulová hloubka 6 zajišťuje `||S_u×d||≥6||P0'||>0`. Různé v mají různé z a kladné měřítko, takže nedochází ke kolapsu nebo křížení celého uzavřeného pláště. Špička a další rohy tvoří explicitní hranice patchů a přehyby; nejsou hladkým pokračováním přes roh. Pro vystřihovaný rozvin autor výslovně zvolí řez podél spojnice levého spodního rohu P0 s jeho partnerem v P1; uzavřený oběh ostění se nesmí tiše rozříznout na jiném místě. Ostatní mezilehlé hranice mohou zůstat přehyby, jejich dosažitelné úhly a případné překryvy rozvinu se kontrolují samostatně.

Další metrické oracle: zadní obvod je 146.7185789489 mm, zadní otvor 1338.8694814070 mm² a každá jeho oblouková délka je `9.6π`. Délka libovolné spojnice odpovídajících bodů je `√(6²+0.2²||P0−O||²)`; například ve vrcholu 8.0434204572 mm. **Hloubka 6 není všude délkou šikmé spojnice.** Každá hraniční délka se ověří i po rozvinu a exportu. Tato rodina má společný vrchol kužele `(0,18,−30)`, ale vzhledem k poloze kruhových segmentů nelze celý rozvin nahradit prostou mezikruhovou výsečí pro souosé kružnice. Důkaz rozvinutelnosti a numerická přesnost výsledného rozvinu jsou dvě různé kontroly.

### B2 — rovinný pás

Ponechat stejné P0, O a k, druhý profil přesunout do z=0. Vznikne oblast mezi dvěma vnořenými hranicemi; její plocha je `(1.2²−1)·plocha(P0)=409.0990082077 mm²`. Nejde o tloušťku zdi nebo prostorový objem. Volba vnitřního O brání shodné spodní hraně a pinchi, který by vznikl při homotetii kolem bodu na spodním okraji. Obě smyčky, jejich díra a rohy zůstanou v SVG/PDF zachované.

### B3 — skutečně negativní rozdílný profil

Druhý profil se nakreslí nezávisle v z=6: spodní šířka 20, svislé boky do y=25, výška obloukové části 18. Pravý oblouk má střed `(-11.2,25)`, r=21.2, úhel 0→α1, kde `α1=atan2(18,11.2)=1.014197008784674`; končí ve špičce `(0,43)`. Levý je zrcadlový. P0 se nemění. Párování pravých oblouků je explicitně podle stejného podílu u∈[0,1] jejich úhlových rozsahů, `θ0=(π/3)u`, `θ1=α1u`.

Na tomto intervalu má daný ruled loft analyticky

`D(u)=−6·24·(π/3)·21.2·α1·sin((α1−π/3)u)`.

V regulárním bodě u=0.5 vychází **D=53.4959213788 mm³ ≠0**. To je negativní důkaz pro zadanou plochu, nikoli screening konečné sady nul. EXACT musí být odmítnuto bez změny profilů nebo částečného uložení; nabídnout změnu návrhu/korespondence, švy nebo explicitní aproximační variantu s rozpočtem podle D. Tím není prokázáno, že neexistuje žádná jiná konstrukce z těchto vstupů.

Pouhá rozdílnost rozměrů není negativní důkaz. Zejména dvě špičaté sestavy se stejným úhlovým rozsahem obou kruhových oblouků mohou mít na každém oblouku stále přímkovou rodinu s identicky nulovým D, i když se liší výška boků. Takový případ se nesmí omylem použít jako povinný test odmítnutí.

## Připojení na vnitřní hranu otvoru a chlopně

Přední i zadní stěna zůstává samostatnou rovinnou plochou s vlastním skutečným otvorem. Konec ostění odkazuje na ID dané smyčky otvoru, segment a orientovaný interval, nikoli na nejbližší vnější hranu stěny. U B1 se zároveň určí přední/zadní příjemce a potištěná strana. Editace otvoru musí přemapovat jednoznačnou lineage, nebo ukázat unresolved reference; indexový fallback je nepřípustný.

Vlastní jednoduchý číselný spoj na pravém boku P0: zdrojový interval x=12, y=6…18, z=0. V sestaveném stavu směřuje chlopeň ven do materiálu stěny a má footprint `[(12,6),(14,7),(14,17),(12,18)]`. Autorem zvolená skutečná lepicí oblast `x=12.2…14, y=7…17` má 18 mm², celá je mimo otvor a uvnitř stěny. Hinge zůstává na hranici otvoru; odsazení lepení 0.2 mm od hinge je záměrné a nesmí se zaměnit za mezeru v materiálu nosného dílu. U zadního otvoru se odpovídající interval nachází na x=14.4, y=3.6…18, z=6.

Negativní varianta přehne stejnou chlopeň směrem dovnitř otvoru, do x<12, při y=7…17. Tam pro tento interval chybí příjemcův materiál: kladná lepicí plocha musí být odmítnuta, ne získána vyplněním otvoru nebo přestřižením cílové stěny. Další varianta změní křivku/interval a ověří invalidaci dřívějšího kontaktu a reportu. Pro obloukovou část se později použijí dělené chlopně s konkrétním příjemcem, relief a doloženou chybou kontaktu po ohnutí; přesný loft není automatický certifikát přesného zakřiveného konektoru.

## Jak se má návrh skutečně ověřit

Tento dokument je **vizuální konstrukční rozbor + vlastní analyticky zadaný budoucí fixture**, nikoli PASS B. V následujícím příslušném řezu musí vzniknout profily přes skutečné kreslicí UI, zůstat editovatelné a projít save/reopen, 3D↔2D výběrem včetně hrany otvoru, explicitním rozvinem, ručním layoutem mezi dvěma listy a oběma vektorovými výstupy. Oracle výše je nezávislý na produkčním výpočtu. Při špatné orientaci/korespondenci/receiving region musí UI ukázat konkrétní místo a opravu; undo obnoví profily, spoj i layout.

Editor musí rozlišit profilový roh, přehyb rovinných patchů a hladké stáčení; čtenář skenu je nemusí pojmenovat interními geometrickými termíny. Pomoc nenahradí chybějící nástroj pro výběr vnitřní hrany. Nový uživatel ani fyzická sestava zde nebyli testováni. Originální podklady zůstávají pouze místní inspirací a historické důkazy se nemění. Integrace návrhové poznámky neuděluje schválení produkci.
