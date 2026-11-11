# Review oprava — chlopně nezvětšují povolenou plošnou chybu

Produkční pin `5ad3cc0ac53ab68a09d1ff7ccd39fe90ade7f7c4`, předek `4ab07ef`
(produkce `26873c6`). Nezávislý reviewer `commands_review` při revizi268 doložil
odchylku vzorce: relativní větev brala body+TAB union místo samotného těla.
Závažnost konkrétního plného aplikačního false-SAFE není touto zprávou tvrzena;
pokusy s velkou chlopní skončily na platném BEND_UNRESOLVED a nejsou důkazem
produktové vady bend guardu. Samotný původní vzorec však nebyl normativní.

Úzká oprava používá `max(0.01mm², sourcePlaneBodyLower/1e6)`. Skutečná čistá
plocha se nadále porovnává přímo s tělem plus ověřeným net connector union;
konektor zůstává součástí materiálu, pouze nesmí uvolnit jeho přejímací mez.
Audit každé part explicitně nese `area_budget_basis` s hodnotou
`SOURCE_PLANE_BODY_ONLY_EXCLUDES_CONNECTORS` a `area_budget_source_body_lower_exact`.
Zdrojové/body/union intervaly ani jiné geometrické, bend či publikační kontroly
se nemění. Stejně se nemění původní AC ani zamýšlený rozsah produktu.

Nový test má záměrně vymezený scope **numerický comparator se skutečnými raw
SVG/PDF**, nikoli úplnou author-domain nebo nativní UI přejímku. Nahrazuje pouze
vstup již vázaného matematického zdroje a jeho plošný interval; produkční bend
gates neobchází ani neupravuje. Tělo má nezávisle určenou plochu
`200×200/2=20000mm²`, volitelná trojúhelníková chlopeň `200×20/2=2000mm²`.
Povolená chyba je v obou případech0.020mm². Posun pouze protilehlého BODY vrcholu
o0.00021mm dává `200×0.00021/2=0.021mm²`: více než správná0.020 a méně než
chybná unionová0.022mm². Hinge ani chlopeň se neposunou.

Baseline skutečných souborů projde; odděleně změněné SVG a odděleně změněné PDF
jsou přímo po přečtení skutečných tokenů odmítnuty na ploše. PDF fixture zapisuje
přesné desetinné path tokeny; její první verze omylem vložila zápis Fraction
`a/b`, který parser správně odmítl. Tento neúspěch je zachovaný a neoznačuje se
za produktovou vadu. Po opravě fixture jsou2 numerické případy PASS/0.80s na
přesném5ad pinu. Spolu se stávajícími skutečnými LINE/curved producenty a malou
legitimní chlopní prošlo5 cílených testů/24.14s. Ruff, format a diff check PASS.

[Evidence](evidence/pc008-area-body-budget-5ad3cc0/results.json) obsahuje zdrojový
SHA, skutečně importovanou cestu, hashe kódu/testu/raw souborů, oba JUnit běhy
a první chybnou numeric fixture. Poslední raw stav má správné baseline SVG a
úmyslně změněné PDF s posunutým BODY vrcholem; toto PDF je **záporný testovací
artefakt**, nikoli publikovatelný model. C77/268 evidence se zpětně nemění.

Skills konstrukce a verification zde udržují zvlášť tělo a přidaný materiál,
správný plošný normativní základ a skutečné čtení výstupů. Delivery zachovává
původní nález, úzkou opravu a přesný scope důkazů. Nezávislé uzavření tohoto
delta je při zápisu PENDING; actual nativní průchod integrované aplikace,
nový uživatel a fyzická stavba nejsou tímto testem provedeny.
