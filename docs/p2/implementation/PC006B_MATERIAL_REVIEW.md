# Nezávislá revize PC-006B — materiál, průběh ohybu a export

Reviewer: samostatný agent `bend_adapter_review`, nikoli autor adaptéru ani geometrické opravy. Datum 9. 11. 2026. Výchozí WIP `4e9956bc8fdb8a91af5cd5a4aa62de481e3eb657`, následný produkční registr `f27d51802ef77472bbefc2b93f20a50b6156959e`; `95482c5e69cb4f6768494a7f5d00e6b571ea2064` mění proti f27 pouze queue. Pozdější finální pin a jeho ověření se doplní samostatně níže.

**Finální verdikt: APPROVED_IN_SCOPE pro technický balík PC-006B na `eb08f97f3ced9c547bd818f97e47d29f9b73a548`: skutečný model A a společný stěna–střecha díl, R01 a B02 v tomto digitálním rozsahu CLOSED.** Skutečný novice test má stále 0 účastníků / NOT_RUN, fyzický P3 je NOT_RUN a celé P2 A/B/C/D není dokončené. Technické schválení se nesmí vydávat za produktové přijetí nebo doklad celé použitelnosti. Průběžné nálezy a jejich původní důkazy níže zůstávají historicky zachované.

## Nález R01: nejistá vrstva oslabila skutečné blokování

`bend.py` v novém registru po kontrole jádra přepsal každé původní `UNRESOLVED` na `UNVERIFIED`, pokud existoval protilehlý tab a tloušťka nebyla známa. Z geometrické/numerické chyby tak vzniklo přijatelné obecné varování. Přidání nejistoty nesmí oslabit nezávisle existující negativní stav.

Vlastní reprodukce obsahuje stěnu `x=20..60,y=5,z=0..20`, příjemce `100×100`, chlopeň šířky 5 a navíc samostatnou plochu u `x=10⁷ paper mm`. Jádro výslovně podporuje magnitude nejvýše `10⁶ mm`: bez další chlopně vrací `UNRESOLVED / Coordinate conditioning exceeds the supported digital precision`. Přidáním vzdálené chlopně `x=70..90` na protilehlé straně téhož příjemce se výsledek změnil na `UNVERIFIED`, se zcela prázdným `checked_obstacle_ids` a neprázdným očekávaným inventářem. To není prokázaná geometrie.

[Původní raw důkaz](evidence/pc006b-material-review-R01-unresolved-downgrade.json), [samostatná reprodukce](evidence/pc006b-material-review-R01.py). Požadavek opravy: kombinovat závažnost monotónně, zachovat původní `UNRESOLVED` i důvod, `COLLISION` má nadále přednost. Doplnit negativní regresi a nezávisle zopakovat původní reprodukci na přesném opravném pinu. Stav: **OPEN**, než je uvedeno uzavření níže.

## Ověření před opravou R01

- [Původní cílené testy](evidence/pc006b-material-review-original-tests.xml): 26 PASS; pozdější [sada včetně geometrického jádra](evidence/pc006b-material-review-final-tests.xml): 68 PASS. Tyto zelené testy R01 původně nepokrývaly.
- [Vlastní reprodukovatelný skript](evidence/pc006b-material-review-oracles.py) a [výsledek](evidence/pc006b-material-review-oracles.json): 28 PASS, samostatná očekávání bez odvození výsledku produkčním generátorem.
- Vlastní devadesátistupňový ohyb má hinge `x=10..70,y=7,z=0`, tab šířky 6 a překážku `y=4,z=-3.5..-2.5`: bod `[40,4,-3]` při −45° leží uvnitř obou materiálů, zatímco koncové polohy jsou volné. Známá i neznámá tloušťka dávají `COLLISION`.
- Jiný skutečný tab je v rovině `y=4,z=-6.3..-0.3` a jeho přijímač má skutečný otvor. Výpočet jej hlásí jako překážku uprostřed pohybu; vypnutí odstraní pouze jeho materiál a zachová ID i ostatní plochy. Výsledkem je známý `CLEAR` nebo neznámý `UNVERIFIED`.
- Protilehlá deklarovaná strana je explicitně v odděleném nejistém inventáři, nesmí předstírat nulu fyzického offsetu. Známý profil vede k `UNRESOLVED`, neznámý k `UNVERIFIED`. Vlastní třetí určitá kolize zůstala `COLLISION`; předcházející R01 ukazuje, že tato vlastnost samotná nestačila pro ostatní typy tvrdého selhání.
- Schema 1 a 2 načtená ze skutečného disku vyžadují kopii. Po změně materiálu, undo/redo, neúspěšné operaci a Save As jsou původní bajty stejné. Schema 3 bez materiálu, s neznámým materiálovým polem nebo schema 4 se odmítají.
- Ruční stránka ani nepoužitá skica nemění assembly digest; materiálová změna digest změní a zneplatní odvozené díly. Neplatné materiálové hodnoty jsou atomicky odmítnuté.
- Writer samostatně odmítl i vnořený blokovaný tab pod jinak povoleným rodičovským reportem. Dřívější celý výstupní bundle zůstal bajtově shodný. Původní exportní test nezávisle čte shodný digest a obsah konstrukční kontroly v SVG, PDF Keywords i manifestu.

První vlastní fixture chybně očekával volnou koncovou polohu při horním okraji otvoru `z=.1`: papír tloušťky `.25` v konečné rovině `z=0` sahá do `z=.125`, proto korektně narazil do přijímače. [První FAIL](evidence/pc006b-material-review-oracles-initial-fixture-fail.json) je zachován. Opraven byl skutečný otvor na `z=.3`, nikoli produktová tolerance nebo očekávaná kontrola.

## Uplatnění skills a omezení důkazu

Reviewer skutečně načetl všechny čtyři projektové skills a dotčený kontrakt, analýzu, UX a AC. Konstrukce: rozlišil původní plochy, materiál jiné chlopně, přijímací otvor a sestavenou polohu. UI: kontroloval rozepsaná čísla, raw přesnost, zrušení materiálového dialogu a srozumitelnost názvu kolizní překážky. Ověřování: vlastní záporný úhlový svědek, zachování selhání R01, samostatné IO/rollback případy a oddělení omezeného hledání od pozitivního důkazu. Delivery: přesné piny, průběžný nesouhlas při zásadním nálezu a požadované přezkoušení opravy.

Drobné UI zjištění: nová překážka `tab:<UUID>` původně vedla k obecné hlášce „plocha modelu“ bez doplnění dílu majitele překážky. Root dostal konkrétní návrh mapovat stabilní tab na connector a jeho owner; oprava a nezávislá kontrola budou uvedeny ve finálním dodatku.

SK-007/SK-008 v `d072aa8` jsou úzká relevantní poučení: nezávislá nejistota nesmí odstranit známý negativní důkaz a skutečně importovaný modul musí patřit ověřovanému worktree. Jejich text nemění AC ani nevydává automatizaci za člověka. Aktuální přenos je nutné doložit konkrétní další reprodukcí/průchodem; R01 rozšiřuje důvod kontrolovat také nezávislé tvrdé selhání, nejen již nalezenou kolizi.

Tato revize sama neprovedla skutečný nativní Windows průchod, externí editor ani test s novým uživatelem. Účastníků AC-US08 je stále 0; fyzický P3 není proveden. Celé A/B/C/D a závěrečný historický model nejsou tímto komponentovým přezkoušením dokončené.

## Nezávislé přezkoušení opravy R01 a finálního adaptéru

Opravný produkční commit **`022e9fa543865b5edffe8243c1973700a269b74a`**, obsažený ve finálním zdroji **`d2a3b735ce2fcffcddbea6ca32d7449a1609b0c5`**. Přírůstky po f27 jsou skutečně přečtené: monotónní kombinace stavů, explicitně nevyhodnocený inventář, diagnostika 9097e61, dva guards nativního harnessu, review sousední komponenty a evidence/queue/skills. Dřívější 68 PASS se nevydává za nový běh pozdějšího commitu.

[Vlastní přesná R01 reprodukce na opravě](evidence/pc006b-material-review-R01-fixed.json) nyní vrací `UNRESOLVED` před přidáním i po přidání nejisté vrstvy. Původní conditioning message je zachovaná a nevyhodnocené plochy jsou vyjmenované v `not_evaluated_obstacle_ids`, odděleně od skutečně předaných a od neurčených layer dvojic. **R01 CLOSED**. Původní špatný výsledek se nemění zpětně.

Vlastní hlavní skript byl znovu spuštěn na tomto finálním pinu: **30 PASS**, tj. původních 28 a dvě nové nezávislé kontroly konkrétního názvu/majitele překážející chlopně. Záporné svědky, unknown stavy, atomické IO a writer rollback nezhoršily. Nová diagnostika nepíše interní tab UUID do uživatelské hlášky, pojmenuje skutečný papírový díl/plošný materiál a zahrne díl překážky do issue. Drobnost o neurčité „ploše modelu“ je v tomto rozsahu uzavřená.

Přiměřená [sada na opraveném finálním zdroji](evidence/pc006b-material-review-fixed-tests.xml) zahrnula materiál, persistence, dialog, writer, adaptér, diagnostické Qt a nezávisle dříve schválené jádro: **74 PASS / 21,05 s, 0 FAIL, 0 SKIP**. Jde o opakované cílené testy, nikoli 74 nových nezávislých orákul.

Závěr se vztahuje na jednoho pohybujícího se přímého rigidního taba při ostatních již složených tabech, s explicitními lokálními permissions a úplným inventářem. Nezavádí plán montáže, jistý offset neznámých vrstev, deformaci papíru ani fyzický certifikát. Skutečný nativní průchod a externí editor musí zůstat doložené zvlášť, před celkovým schválením B.

SK-007 i SK-008 text v d072aa8 je nezávisle schválený jako úzké poučení. R01 je skutečné další technické použití principu SK-007: přidání nejistoty neoslabí již blokovaný stav jiné části geometrie. Nejde o všeobecně dokázanou účinnost ani o uživatelské pozorování. SK-008 má správný `sys.path` guard i kontrolu skutečného `author_window.__file__`; další skutečný nativní průchod se v okamžiku tohoto komponentového závěru teprve provádí a jeho výsledek zde není předjímán.

## Následná nezávislá diagnostika nativního run05

Rootův skutečný Windows běh `pc006b-desktop-d2a3b73-run05` selhal po save/reopen při přímém Ctrl+R. Reviewer samostatně porovnal diskový `model-A/model-A.apcraft` s uloženým `FAIL-partial-observed-state.json`: [přesný diff](evidence/pc006b-material-review-native05-state-diff.json) obsahuje **pouze devět `parts/<id>/source_revision`: 82 → 121**. Materiál, geometrie, stránky, zámky, názvy ani přijetí varování se nezměnily.

Příčina je konkrétní produktové chování `build_part`: i beze změny vstupů přepíše `source_revision` na aktuální globální revizi projektu, kterou mezitím zvýšilo ruční rozmístění. Redundantní přepočet tak zbytečně změní uložený dokument a vyvolá dirty stav. Negativní nativní očekávání se nemá změkčit. Root dostal doporučení zachovat revizi zdrojového důkazu při shodném `input_digest`, nebo jinak zajistit skutečný no-op aktuálního dílu. Oprava a nový nativní průchod zůstávají v tomto checkpointu **PENDING**; komponentové schválení materiálové matematiky není schválení celého B.

**Následná oprava `eb08f97f3ced9c547bd818f97e47d29f9b73a548` nezávisle APPROVED_IN_SCOPE:** skutečný rebuild se nadále provádí, pouze zachová původní source revision již aktuálního dílu při stejném digestu. [Samostatný replay](evidence/pc006b-material-review-recompute.py), [pět nezávislých PASS](evidence/pc006b-material-review-recompute.json): skutečný uložený run05 A po load/recompute zachová přesný dokument, `dirty=False` i prázdnou undo historii; reálná změna materiálu zvedne všech devět zdrojových revizí, další redundantní rebuild je znovu stabilní; vlastní změna obrysu zvedne zdrojovou revizi. Původní projekt na disku zůstal bajtově zachovaný. Nativní opakování téhož workflow zůstává samostatným požadavkem, nikoli závěrem tohoto in-memory replaye.

## Finální skutečný průchod, výstupy a technické schválení B

**CODE `eb08f97f3ced9c547bd818f97e47d29f9b73a548`.** Přečteny také dokončené sousední [UI](PC006B_UI_REVIEW.md) a [commands revize](PC006B_COMMANDS_REVIEW.md), včetně nezávislých C05/undo/old-copy případů a uzavření C-EDIT01. Autor návrhu ani implementátor si tímto sami sobě schválení neudělují; závěr provedl samostatný reviewer po vlastní analytice a čtení skutečných artefaktů.

[Nativní Windows run06](evidence/pc006b-desktop-eb08f97-run06/results.json) prošel v 170,969 s, 15 kroků: vytvoření vlastní otevřené stavby od prázdného projektu, základna/výztuha s opravdovým otvorem, pásek a podhled, připojení dovnitř střechy a přesah, dělené trojúhelníkové záložky s off a ručně kresleným/číselně opraveným vlastním obrysem, 3D↔2D výběr, odemčené i zamčené přetažení, skutečné uložení/nový model/otevření a oba exporty. Samostatný společný stěna–střecha díl při změně výšky zachoval všechny čtyři původní souřadnice stěny, stránku 2, kotvu `[60,60]`, natočení 30° a oba zámky. Nativní kamera nyní zobrazila vše bez Home a následný zoom/pan + Ctrl+R nezměnil dokument ani kameru; tím je skutečně zopakován původní run05 FAIL.

[Vlastní auditor](evidence/pc006b-material-review-native-audit.py), [28 nezávislých kontrol PASS](evidence/pc006b-material-review-native-audit.json):

- Samostatně přečtené a ověřené **40 hashů artefaktů a 85 hashů skutečných zdrojových souborů**, skutečný `author_window.__file__` patří připnutému integračnímu worktree. Šest nativních Save/Open/Export dialogů má samostatné `native_seen/accepted`; další čtyři záznamy jsou skutečné QMessageBox potvrzení exportu.
- Vlastní čtení SVG i PDF: úplné pokrytí 9 A dílů na 3 stránkách a 2 společných dílů na 2 stránkách, sedm oddělených SVG rolí, skutečné PDF vektorové operátory bez raster XObjects, stejný obsah konstrukční kontroly/digest v snapshotu, SVG, manifestu a PDF Keywords. Přesný režim se vztahuje na rovinné/lomené materiály, nikoli zakřivené budoucí B/C řezy.
- Jižní stěna má v opravdovém SVG CUT analyticky **`100·40 + 56 + 60 + 60 + 144 = 4320 mm²`** a jednotlivé TABS **56, 60, 60, 144 mm²**. To je nezávislé čtení výsledných cest s ručně určeným očekáváním; vypnutý tab nevytváří materiál.
- [Skutečný Inkscape 1.4.4 run01](evidence/pc006b-inkscape-eb08f97-run01/editor-results.json) nad výstupem stejného A zdroje prošel v 16,828 s. Reviewer samostatně načetl upravené XML: skutečně uložené **„Žluťoučký – vlastní díl“** včetně mezer, ostatní texty a lokální souřadnice cest zachované, původní bundle bajtově zachovaný. Skutečné nativní psaní je doložené vlastním oknem procesu a GUI capture; automatizace se nevydává za člověka.

Reviewer vizuálně prohlédl skutečné screenshoty celé stavby A, kresleného stupňového taba, znovu otevřeného třístránkového A, znovu otevřeného společného dílu a nativního Inkscape okna. Materiálový stav v důkazu je **UNKNOWN**: omezené hledání nenaznačuje prokázanou absenci kolize a rozhraní toto výslovně uvádí. P3 upozornění bylo přijato jen pro konkrétní digitální stav, žádná tvrdá geometrická chyba se nepřijímala jako warning.

Rootův [JUnit přesného finálního zdroje](evidence/pc006b-eb08f97-all-tests.xml) reviewer skutečně přečetl: **630 testů, 0 FAIL, 0 ERROR, 0 SKIP, 60,908 s**. Tento plný běh není vydávaný za nové nezávislé spuštění reviewerem; ten má vlastní výše uvedené opakování 74 cílených testů, 30 základních orákul, R01 a pět no-op kontrol. Počty se nesčítají jako unikátní testy.

První verze vlastního auditora mylně počítala všech 10 dialogových záznamů jako nativní file dialogy a porovnávala číselnou reprezentaci SVG cesty bez respektování ekvivalentních H/V příkazů Inkscape. Opraveno pouze čtení evidence: rozlišit 6 file dialogů od 4 QMessageBox a normalizovat skutečné line/H/V souřadnice. Nezměnila se data produktu ani jeho tolerance; původní produktové FAIL run04/05 zůstávají uložené.

**B02 / AU07 v dodávaném rozsahu přímých chlopní je digitálně uzavřen:** známý analytický střet uprostřed ohybu i střet s jinou aktivní chlopní se tvrdě odmítají; neznámá tloušťka/vrstva zůstává výslovně neověřená, numerické selhání se neoslabuje a pozitivní materiálový stav má přesně vymezené předpoklady. Není to obecný plán montáže, tvrzení fyzické vůle celého A ani certifikát zakřivených chlopní pro PC-007B.

SK-008 má tímto doložený úzký technický přenos do skutečného run06 s kontrolou importu; SK-007 má přenos do nezávisle odhaleného a opraveného R01. Není tím prokázaná univerzální účinnost rad ani lidská osvojitelnost. **AC-US08 zůstává NOT_RUN / 0 účastníků**, chybějící člověk se nenahrazuje tímto průchodem. PC-007A/B, PC-008–010, celé B/C/D přejímky, DPI konsolidace a závěrečný historický model zůstávají navazující autorizovanou prací.
