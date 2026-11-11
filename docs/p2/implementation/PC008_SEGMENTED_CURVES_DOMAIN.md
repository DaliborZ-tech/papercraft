# B3/D — zakřivený zdroj a skutečný materiál v téže doméně

Komponentový pin `518b91a9ce68706d872ee20c5765e3b2cbbda30e` spojuje původní
LINE doménu `95fa2c7` s nezávisle zrevidovanou křivkovou matematikou `3a0355f`
(review `548027a`, merge `731d12f`). Generická produkční doména nepotřebovala
další větev podle typu profilu. Samostatná oprava no-op scalarů `65159f8`
byla nezávisle ověřena reviewerem; tato zpráva není schválením curved bridge.
Nezávislá revize tohoto propojení je v okamžiku zápisu **PENDING**.

Veřejnými příkazy vznikly dvě nezávislé gotiky: poloviční šířka/výška
20/30 a18/25, vzdálenost profilů10, scale1. Každá má dvě původní ARC a rovnou
základnu. Původní loft zůstává `REJECTED` v přesném režimu; potvrzení náhledu
vytvoří96 samostatných rovinných materiálových dílů a96 párovaných švů.
Původní profily, explicitní korespondence i cíl zůstávají v témže projektu.
Rodina certifikátu je `INTERVAL_CURVED_RULED_TRIANGLE_ISLANDS`; nevkládá falešné
bilineární koeficienty. Surová celoplošná mez je0.1865948501209102 paper mm,
mez včetně skutečných konečných materiálových frames0.18659485012091598mm,
pod autorem zadaným0.25mm. Důkaz globálního RAW grafu používá přesnou projekci
`(x,y+z/8)`,4560 párů a konečný budget200000; scope a perturbace jsou ve snapshotu.

Nové testy počítají body obou kružnic přímo z nezávislého vzorce pro střed
`(h²-w²)/(2w)` a rotaci. Kontrolují skutečné profilové roviny, vrcholy i několik
vnitřních bodů každého materiálového trojúhelníku proti konzervativní mezi.
To jsou doplňující regresní orákula; celoplošný certifikát pochází ze samostatně
zrevidované intervalové matematiky, konečné vzorky jej nenahrazují.
Náhled odpovídá skutečným později vytvořeným world vertices. Stejné API
zachová nativní CUBIC profil a po jeho potvrzení jej nepřepíše polygonem.

Explicitní hromadné ruční umístění dalo48+48 dílů na dva listy. Save/reopen
zachovává totožnost projektu a APPROXIMATE/reference pokrytí. Změna živé roviny
zdroje ponechá starý layout a přepne výsledek na STALE; běžný recompute jej
necertifikuje znovu. Přísný nedosažitelný limit skončí UNRESOLVED bez částečného
materiálu. Historický uložený LINE projekt z95fa2c7 se stále otevře a tiskový
snapshot má původních32+32 dílů.

Evidence [probe a raw](evidence/pc008-curved-domain-518b91a/raw/results.json)
uvádí skutečnou importovanou cestu, zdrojový SHA a hashe projektu/snapshotu.
Backend cold preview trval1.876s, warm potvrzení0.244s, přidání druhého listu
a explicitní batch96 umístění0.558s na tomto prostředí. Nejde o měření latence
UI ani o test nového uživatele. Cílená sada má126 PASS/50.70s; po závěrečném
doplnění invarianty detached náhledu běžel dotčený test znovu1 PASS/1.80s.
Ruff a diff check prošly. První125PASS/1FAIL je zachované: nově přidaný test
očekával chybný text role náhledu, správná produkční hodnota byla
`DETACHED_ACTUAL_MATERIAL_FRAME_PREVIEW; NOT_PERSISTENT_IDENTITIES`.

Použité skills: konstrukce drží zvlášť hladký záměr a skutečně stříhaný
materiál; verification přidává nezávislé kruhové expected a skutečné frames;
UI skill se zde uplatnil na atomický preview/confirm/undo kontrakt bez injekce
meshe; delivery odděluje schválenou matematiku, nový integrační důkaz a chybějící
přejímky. Tento backendový balík neprokazuje nativní UI průchod, SVG/PDF,
nového uživatele ani fyzické sestavení. Tyto stavy zůstávají NOT_RUN pro tento pin.
