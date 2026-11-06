# PC-006A — vlastní úsečkové díly až do vektorového výstupu

6.11.2026. **Technicky dodáno a nezávisle schváleno v rozsahu PC-006A**, CODE SHA `4b172e65af3cde19c865cf7594c63fa004aa1ba2`. [Nezávislá revize](PC006A_REVIEW.md). Produktové přijetí implementace je samostatné; celé P2 a první kompletní autorská verze A zde ještě dokončené nejsou.

## Co lze skutečně udělat

Spuštění v připraveném prostředí: `.venv\Scripts\python.exe -m archpapercraft`. Aplikace začne prázdným projektem. Autor nakliká vlastní polygon, Enter vytvoří plochu, Ctrl+Enter uchová otevřený profil; jeho body lze později doplnit a profil explicitně uzavřít. Otvor je skutečná hranice materiálu ve skice, 3D, papíru i obou exportech. Souřadnice lze měnit v m/cm/mm nebo tažením stabilních bodů. Neplatný obrys se odmítne a rozpracované body zůstanou k opravě.

Ve3D nebo na papíře lze vybrat odpovídající plochu/hranu, připojit další vlastní plochu přes skutečný90° náhled, zvolit řez/lepení nebo přehyb společného dílu a upravit základní chlopeň. Po editaci zůstane předchozí papír zřetelně neaktuální do výslovného Ctrl+R. Ruční stránky, poloha kotvy/otočení a jejich nezávislé zámky, protikus, potištěná strana, undo/redo a save/reopen používají stejnou doménu.

SVG a PDF vznikají z jednoho validovaného snapshotu. Chybějící díl, zastaralý rozvin nebo fyzický přesah stránky se nesmí tiše vynechat. Varování o neověřené materiálové pevnosti má konkrétní text a přijetí vázané na obsah; není to fyzický PASS. Staré projekty se jen prohlížejí bez přepisování originálu. Nový formát je stále experimentální; jeho stabilizaci podmiňují další řezy a B/C/D fixtures.

## Skutečný Windows průchod a nezávislá očekávání

[Native run03](evidence/pc006a-desktop-4b172e6-run03/results.json) provedl skutečné `app.main`, Qt widgety, OpenGL a tři Win32 souborové dialogy. Od prázdného projektu naklikal vlastní konkávní L, otvor, změnu bodu, výslovný přepočet, druhou plochu, náhled spoje, fold→cut a7mm chlopeň, dvě ručníA4 stránky, oba zámky a jejich test tažením. Poté nativeSave→nový projekt→nativeOpen→nativeSVG/PDF. Projekt nebyl připraven injekcí JSON nebo vytvořen backendovým fixture místo kreslení.

| Analyticky zadané očekávání | Doložený výsledek |
|---|---|
| Vlastní L3300mm², otvor225, materiál3075 | Skutečný průchod PASS; po změně jednoho vrcholu vnější plocha3600, otvor225, materiál3375 |
| Druhá plocha300mm² + chlopeň `7×(30+18)/2=168` | SVG468mm²; nezávisle čtené PDF468.0001092mm² |
| Stejný první díl/otvor vPDF | PDF3599.9983222495 /224.9998951406mm²; vlastní22bodový audit review PASS |
| Kalibrace100mm | Skutečné PDF100.00001167mm na obou stránkách |
| Vektorový dokument a text |0 rastrových obrazů vPDF, vložený Unicode font,7 konstrukčních rolí SVG, úplné pokrytí a shodný snapshotdigest |

[Editovatelný projekt](evidence/pc006a-desktop-4b172e6-run03/own-model.apcraft), [snapshot](evidence/pc006a-desktop-4b172e6-run03/snapshot.json), [výstupní adresář](evidence/pc006a-desktop-4b172e6-run03/export), [audit výstupů](evidence/pc006a-desktop-4b172e6-output-audit.json). Reviewer navíc nezávisle otevřel skutečné XML/PDF/project, nikoli jen přijal počty exportéra. Výsledky obsahují verze, zdrojové a výstupní hashe.

První dva native pokusy zůstávají jako **FAIL**: run01 měl chybný středový klik širokého checkboxu, run02 vynechal požadovaný krok přijetí konkrétního materiálového varování. Harness byl opraven bez oslabování těchto kontrol. Černý snímek dialogu `03-assembly-dialog-desktop.png` není důkaz čitelnosti dialogových textů; platný dialogový GL framebuffer, skutečné widgetové kroky a hlavní desktopové snímky jsou doložené samostatně. Starší startup podklad vznikl při rozpracované implementaci a nenahrazuje tento připnutý průchod.

## Revize, opravy a osvojitelnost

Nezávisle **443 testů PASS,0skip**: původní baseline/spiky a170 nových autorských kontrol. Reviewer navíc provedl vlastní numerické a IO proti-příklady,6 pozitivních/negativních shortcut kontrol,4 legacy kontroly a22bodové čtení výstupů. Ruff dotčených souborů PASS; detaily a přesné raw výsledky jsou v review.

Uzavřeno C-01 zachování vlastníka chlopně, C-02 poctivá mez interpolace a skutečné serializace PDF, C-03 kontrola drobných otvorů, C-04 světová plošná přesnost a C-05 právě rozepsaná čísla před uložením/exportem/nahrazením projektu. Tato poslední chyba by při Ctrl+S/E/N bez Enter ignorovala viditelný vstup nebo exportovala dřívější snapshot; oprava především mění transakci ovládání, nepřidává další nápovědu.

Nové pracovní rozhraní řeší doložené omezení původního presetového workflow: vlastní kreslení, skica a propojené3D/papír jsou přímo v jednom pracovním prostoru. Zachována Qt/OpenGL cesta, klávesnice, nativní dialogy, tiskové role a bezpečná IO. Dostupné akce sledují výběr; prázdné kliknutí jej vyčistí ve všech pohledech, chybu lze vybrat/aktivovat i klávesnicí, draft nezmizí opakovaným příkazem, změna výběru nepřesměruje otvor. Tipy lze vypnout a opět vyvolat bez změny projektu. To dokládají technické GUI průchody; **není tím změřena srozumitelnost pro nového člověka**.

## Co pokračuje v PC-006B a dalších řezech

PC-006B přidá vnitřní čáru/lepicí oblast příjemce, zachovaný střešní přesah, vlastní obrys/dělení chlopně a samostatný pásek; celý ručně sestavený A, povinné společné kotvy a první skutečné novice sezení. AC-US08 má **0 účastníků / NOT_RUN** a [protokol](../v1.2/USABILITY_TEST.md); PC-006A připravil běžící build a technicky reprodukovatelný základ. Curves/loftyB, pláštěC, pravdivá aproximaceD, úplná interoperabilita/DPI, následný model historické architektury AC-AU19 i finální nezávislé P2 review zůstávají povinné. P3 je skutečný výtisk a sestavení člověkem.

[Konstrukční reference](REFERENCE_OBSERVATIONS.md) byly při implementaci skutečně prostudovány, originální obrázky/PDF se do projektu nekopírují. [Přepočet odhadu](../v1.2/ESTIMATE_AND_RISKS.md) vychází z dosažených schopností a nových rizik, nikoli z doby běhu agentů. Všechna čtyři projektová skills byla uplatněna na těchto konkrétních výsledcích; přenos nového poučení C-05 do dalšího řezu zůstává pending.
