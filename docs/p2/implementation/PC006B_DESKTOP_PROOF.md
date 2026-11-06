# PC-006B — skutečný desktopový průchod, průběžná evidence

Autor driveru: agent `authoring_domain`. Stav 6. 11. 2026: **A i mixed dosud nedokončené**. Jde o automatizaci skutečných widgetů Windows, nikoli test nového uživatele, nezávislé schválení nebo fyzický proof. Závěrečný model AC-AU19 zůstává PC-010.

Driver [desktop_b_proof.py](../../../tools/authoring/desktop_b_proof.py) volá skutečné `app.main`, vytváří profil/plošky klikáním nebo dialogem rozměrů a sestavuje je číselnými vlastnostmi a skutečnými dialogy spojů. Nenahrává konstrukční fixture do controlleru ani JSON. `fitInView` je pouze výslovně logovaná změna kamery skici. Projektové API slouží v nativním průchodu pouze ke čtení a auditům.

Plánované A má čtyři samostatné stěny, z toho dvě štítové, dva střešní pláště se skutečným společným přehybem u hřebene, samostatnou základnu, vlastní výztuhu s otvorem, dvě skutečné materiálové poloviny pásku a samostatný podhled s vnitřní potištěnou stranou a plošným lepením. Dno nevzniká. Autor mění pouze jižní okapový přesah500→800 model mm; příčná stopa stěny i štítové přesahy400 zůstávají. Mixed je samostatný fixture se skutečným stěna–střecha foldem, nikoli lepeným attachmentem: page2[60,60],30°, oba locks, zdrojová změna výšky3000→3500 a vnitřní připojení stěny k základně.

## Provedené běhy

- [run01 výsledky](evidence/pc006b-desktop-833adec-run01/results.json), source `833adec4715f0459faedd6cf398d08f510dc515c`: **FAIL**, 33.047 s. Skutečný OpenGL 4.6 NVIDIA, vytvořený obal, základna, děrovaná výztuha, podhled a stopy střech. Selhání při kreslené lepicí oblasti základny: zamýšlená hranice oblasti se měla shodovat se stopou. Pixelový vstup ji umístil trochu dovnitř, takže správně následovalo `TARGET_GLUE_OUTSIDE`. Celý neúspěch je zachován včetně screenshotu a pozorovaného částečného stavu.
- Následná **offscreen diagnostika**, nikoli náhrada nativního průchodu, otevřela pozorovaný stav do samostatného diagnostického dialogu. Při požadovaném y 2000 skutečné body vyšly y 2010.3, zatímco stopa je přesněy 2000. Dialog má při mm grid 0.1 modelmm. To potvrdilo, že řízený klik nemůže zaručit přesnou shodu s hranicí oblasti. Oprava driveru přidala záměrnou rezervu 1 mm papír kolem vnitřního půdorysu a loguje skutečné `specification`; základna130×100mm, stěny a požadované stopy zůstaly beze změny.
- [run02 výsledky](evidence/pc006b-desktop-d83429c-run02/results.json), source `d83429c5f9374bc945202616967936746aea3fe5`: **FAIL**, 48.156 s. Všechny čtyři spodní stopy s nakreslenou oblastí byly přijaty. Vytvoření samostatného pásku šířky2mm na výztuze→jižní střeše odmítlo `TARGET_GLUE_OUTSIDE`; [skutečný dialog](evidence/pc006b-desktop-d83429c-run02/FAIL-authoring-dialog-desktop.png), [pozorovaný částečný stav](evidence/pc006b-desktop-d83429c-run02/FAIL-partial-observed-state.json).

## Přesný nález pásku předaný integračnímu ownerovi

V run02 má jižní střešní zdroj z numerického UI délku sklonu 4949.747468 modelmm. Vrchol výztuhy leží ve světových souřadnicích z 7000; jeho přijímaná stopa na střeše začíná UV [5400,4949.747468305833] a končí[5400,707.1067811865476]. Rozdíl vůči vnějšímu obrysu je přibližně3.05833e-7 modelmm, tedy 3.05833e-9 paper mm. Kontrola samotné stopy tento rozdíl přijme. Následně vytvořená lepicí oblast obdélníkové poloviny pásku šířky200 modelmm přesahuje obrys asi 6.11666e-5 modelmm², tedy 6.11666e-9 paper mm², což překročí absolutní predikát1e-8 modelmm² v kontrole oblasti. Proto zůstane OK zakázané.

Jde o reprodukci na skutečném UI a podezření na nekonzistentní toleranci generovaného kontaktu; konečné určení a oprava jsou v samostatném vlastnictví integračního ownera. Driver nesnížil přejímací toleranci, nepřesunul vrchol, nezkrátil páskový interval ani nevyřadil povinný pásek. Produkční oprava a její nezávislá kontrola jsou **PENDING**.

## Připravené kontroly, dosud bez nativního PASS

Kompilace a Ruff driveru prošly. Jeho `--oracle-only` používá vlastní Pythagorovy vztahy, plochy a transformaci kotvy, bez produkčních geometrických helperů. Nezávislé čtečky SVG M/L/Z a PDF transformačních/path operátorů prošly samostatnou rozhodovací zkouškou ručně určeného20×15mm obdélníku, plocha300mm², pagebounds [50,40]→[70,55]. Tím se netvrdí, že dosud neuskutečněný export A prošel.

Po odstranění blokace má nativní průchod doložit analytické plochy všech dílů včetně otvoru, zachování stopy při změně přesahu a undo/redo, skutečný 3D↔2D výběr a přesun, ruční tři listy, přenos dílu mezi existujícími stránkami, nativní save→new→open→export a čtení skutečného otvoru v obou vektorových výstupech. Mixed samostatně kontroluje všechny papírové body stěny a zachování stránky/kotvy/rotace/obou zámků po přepočtu a při skutečném pokusu o tah. Zdrojové SHA, hashe, runtime verze, skutečné vstupy, screenshoty a neúspěšné stavy jsou v každém čerstvém adresáři.
