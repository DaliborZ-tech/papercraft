# PC-007A — nezávislá revize kontaktu a ohybu ohraničeného materiálu

Následný aktuální verdikt: [finální nezávislá revize SOURCE63](PC007A_PLANAR_INTEGRATION_REVIEW.md) uzavřela V02 na skutečném nativním exportu. Původní otevřené stavy a FAIL níže zůstávají historickým důkazem svých pinů; nejde o aktuální otevřený blocker schváleného rovinného podbalíku.

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; není autorem revidované produkce. Přesný pin **`61168e0879157baba1193785b9856f24d1d1c959`**. Posouzený delta zahrnuje `2cc6ce2`, `9ba4a20`, `61168e0`, geometrický exact-line-image krok `f05c48c` a úzká poučení SK-009/010 z `60d0f01`. Produkci reviewer neměnil.

**Verdikt: APPROVED_IN_BOUNDED_PLANAR_MATERIAL_CONTACT_AND_FOLD_SCOPE.** V posouzeném numerickém rozsahu nebyl nalezen nový blocker ani major. Je to schválení uvedených materiálových/kontaktních/ohybových změn, nikoli celé PC-007A, nového loft UI, fyzikálního modelu papíru nebo kompletní digitální přejímky.

**Známá samostatná UI vada:** během koordinovaného nativního běhu `pc007a-desktop-61168e0-run01` owner reprodukoval chybu náhledu chlopně: `MaterialPreview.show_part` očekává CUT `points`, ale nový Bézier díl má CUT `commands`. Běh zůstává FAIL, oprava je rozpracovaná ownerem mimo tento zdrojový pin. Tento numerický verdikt vadu neuzavírá, nepotvrzuje funkční předání 611 ani neopravuje historický výsledek. Nový preview delta a nový nativní průchod vyžadují samostatnou kontrolu.

**Aktuální další kontrola:** preview oprava `2944c0f` je níže komponentově schválena; při auditu jejích skutečných native artefaktů však vznikl nový **V02 MAJOR OPEN — plocha PDF překračuje normativní mez**. Numerické schválení 611 ani preview schválení 2944 nejsou schválením publikace výsledného planar balíku.

Zpráva a evidence zůstávají podle pokynu integračního ownera **bez commitu a stagingu**; produkční HEAD je rezervovaný pro nativní ověřování.

## Materiálové důkazy a kontakt

Kontroly oddělují skutečný doložený materiál od proxy tětiv. Kolem každého certifikovaného tětivového úseku vzniká vnější konvexní obal zahrnující chord a native SVG odchylku, zakončení i výslovnou numerickou rezervu. `guaranteed = proxy-minus-tubes`, `possible = proxy-union-tubes`. Topologická platnost nativní hranice zůstává samostatným předpokladem kontrolovaným doménou; malá metrická chyba sama nenahrazuje topologii. Otevřená stavba není důvod doplnit materiál.

Zdroj i příjemce contactu musí mít doložený skutečný materiál. Neúspěch proxy není automaticky důkazem nepřítomnosti materiálu a proxy krytí není automaticky důkazem přítomnosti. V nejistém pásmu zůstává spoj hard CURVE_CONTACT_UNRESOLVED; žádné potvrzení varování jej nepromění v lepicí plochu. Zachovaná numerická tolerance přímé hrany se nesmí použít jako doplnění křivkového nejistého pásma.

Celý implicitní zakřivený zdroj se nepovažuje za svou zmenšenou garantovanou část. Pozitivní celý kontakt je v tomto omezeném režimu odmítnut s požadavkem na vlastní výslovnou vnitřní lepicí oblast. Pro známý negativní závěr se posuzují pouze části zdroje, které jsou skutečně zaručené; nevyplňuje se konkávní výřez falešným proxy materiálem. Samostatně doložená mezera nebo určitě chybný cíl nesmějí být přepsány na obecnější nejistotu jen kvůli vzdálené křivce.

Strana materiálu u přímé hrany zakřiveného profilu je doložena z garantovaného/possible materiálu a navazujícího průsečného úseku, nikoli ze signed area mnohoúhelníku jen z koncových bodů. To umožňuje například skutečný půldisk s nulovou plochou endpoint polygonu, aniž by se otočil směr chlopně.

## Ohyb: dolní a horní materiálový registr

`_bend_surface_bounds` zahrnuje všechny plochy, jejich skutečné otvory a všechny komponenty materiálu. Dolní triangulace nesmí vstoupit mimo garantovanou oblast; nepodmíněné odvozené slivery mohou být z **dolní** množiny explicitně vynechané, s evidencí jejich plochy. Horní registr není zmenšovaná triangulace nebezpečných sliverů: obsahuje úplný proxy a vnější tubes; před použitím se kontroluje krytí celé possible oblasti. Překryv horních trojúhelníků představuje sjednocení, nikoli dvojí materiál.

Rozhodnutí adaptéru má samostatný smysl:

- COLLISION vyžaduje svědka v garantovaném materiálu;
- CLEAR vyžaduje průchod celého complete possible registru;
- kolize pouze s možným obalem nebo nedoložená mez zůstává UNRESOLVED;
- neznámá tloušťka necertifikuje nepřítomnost fyzické kolize ani fyzický PASS.

Jistá dolní kolize má přednost před jinou nejistotou; přidání nezávislého nejistého prvku ji nesmí vymazat. Stav jiných již ohnutých chlopní a nejistých protilehlých vrstev zůstává v registru explicitní. Prověřovaný scénář je jeden pohybovaný tab, ostatní aktivní taby již sestavené; nejde o plánování celé montáže.

Kernel má nové výslovné `lower_bound_only`. Jen tento režim dovoluje skutečnou prázdnou dolní množinu s její skutečnou registry identitou a vystaví `GUARANTEED_LOWER_BOUND_ONLY`, nikoli úplnou realitu. Výchozí complete režim prázdnou překážku stále odmítá. Dolní CLEAR není obecný závěr o volném prostoru; tento rozdíl nesmí volající zahodit.

## Prořezání výpočtu bez oslabení důkazu

Nový broad phase používá analytickou projekční obálku **všech podepsaných úhlů** celého ohybu včetně rotující normály a materiálové tloušťky. Nejsou to pouze dva koncové AABB. Trojúhelník lze vypustit, pokud je jeho obal prokazatelně disjunktní od celé obálky ohybu. Při prořezání přes povolený kontakt musí celý průnik obalů včetně numerické rezervy ležet přísně uvnitř explicitního permission volume platného po **celou** úhlovou oblast. Pozdní phase-only povolení k tomuto kroku nestačí.

Prořezané registry identity zůstávají ve výsledku a důkaz uvádí konkrétní počet i rozsah prořezání. Kontrola jen vzorkovaných poloh nebo prázdný seznam po ztrátě ID by toto schválení nesplňovaly. Naměřené zrychlení samo není matematický důkaz; pozitivní hodnocení se opírá o zachovaný intervalový kontrakt a negativní případy.

## Přesný archiv, import a testy

Zkoušky běžely v fresh subprocessu nad přesným `git archive` src/tests/pyproject pinu 611. Actual import probe výslovně zkontrolovala skutečné cesty a obsah `attachments.py`, `bend.py`, `clearance.py`, `curve_material.py` uvnitř izolovaného adresáře proti Git blobům (LF normalizace pouze pro Windows CRLF). Živý profiles worktree ani práce jiného autora nebyly používány jako připnutý zdroj.

[Runner](evidence/pc007a-material-integration-review-archive.py), [source pin, SHA256, import probe a raw](evidence/pc007a-material-integration-review-archive-61168e0.json):

```powershell
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe docs/p2/implementation/evidence/pc007a-material-integration-review-archive.py
```

- Cílené původní contact/bend/core sady: **81 PASS / 21,13 s**, [JUnit](evidence/pc007a-material-integration-review-original-61168e0.xml).
- Vlastní nezávislé případy: **14 PASS / 5,46 s**, [zdroj](evidence/pc007a-material-integration-review-own.py), [JUnit](evidence/pc007a-material-integration-review-own-61168e0.xml).

Vlastní analytický mid-fold případ změnil svědka na −60°: z tab poloměru `rho=4` plyne světová poloha `y=5−4sin60°`, `z=−2`. Kruhový výčnělek mezi tětivovými uzly zasahuje do tab materiálu, proxy jej přitom nekryje. Pro známou i neznámou tloušťku výsledek zůstal hard UNRESOLVED a horní krytí bylo úplné. Další kružnice se skutečným zaručeným průnikem dala COLLISION v dolní množině; přidání vzdálené křivkové nejistoty ji nevymazalo. To je vlastní další použití principu K01, ne opakování autorova očekávání stejným helperem.

Samostatný vlastní kernel fixture u osy X měl volné koncové polohy a skutečnou prostřední překážku; nebyla ztracena AABB prořezáním a vzdálená překážka si uchovala identitu. Phase-only permission se neprunovalo a zachovalo zakázaný průnik, zatímco stejné konečné volume povolené po celém ohybu bezpečně prošlo. Výslovná empty lower source/receiver zůstala evidovaná a complete default je nadále odmítl.

Další vlastní body zahrnují kontakt uvnitř skutečného kruhového otvoru mezi uzly, jasnou void negativní stopu a jasnou pozitivní margin stopu, zákaz implicitního celého curved source oproti podporované výslovné vnitřní oblasti, skutečnou stranu půldisku a triangulaci MultiPolygonu s otvorem. Vlastní collinear cubic má zdroj `x=3t+3t²`; přesný geometrický obraz úsečky nemění hodnotu `x(0.5)=2.25`. Již nepatrná skutečná odchylka řídicího bodu z přímky ukončí exact-image výjimku. L01 nelineární identita parametru není touto optimalizací oslabená.

## SK-009 / SK-010 a skutečné použití

Přečtena odpovídající změna skillu a ledgeru `60d0f01`, platné construction/verification skills a relevantní AC. Oba nové postupy jsou úzké, mají konkrétní doloženou příčinu i příklad a odkazují na platné produktové důkazy. Nekopírují nové AC, neoslabují tolerance ani nenahrazují nepříjemný test.

SK-009 výslovně odlišuje metriku, topologii a materiál a požaduje přenos layout chyby do kontaktu i celého ohybu. Jeho konkrétní technické uplatnění v tomto navazujícím adapter review je doložené novým −60° svědkem, nepravým kontaktovým krytím kruhového otvoru a zachováním jiné jisté kolize. Tento dílčí přenos smí být zaznamenaný jako komponentově ověřený. Neprokazuje obecnou účinnost u budoucích zakřivených plášťů, ve všech UI průchodech nebo fyzické stavbě; širší efficacy zůstává PENDING_NEXT_USE.

SK-010 zachovává původní číselné lexémy před float a zahrnuje skutečné streamy i page geometrické hodnoty. Jeho příčina a oprava jsou nezávisle doložené pěti raw V01 případy v samostatném vector-output review. Tyto regrese opravného balíku samy nejsou novým nezávislým produkčním použitím skillu nebo uživatelským testem. `PENDING_NEXT_USE` v ledgeru je pravdivý; absence dalšího použití se nesmí změnit na obecný PASS.

Samotná údržba skills ani tento report neudělují produktové přijetí, nezavírají známý nativní preview FAIL, lidskou AC-US08, celé AU09/B1/B2/B3, celý P2 nebo fyzický P3. Nový finální commit po UI opravě musí být ověřen v odpovídajícím rozsahu.

## Náhled nativních křivek — delta `2944c0f`

Přesný zdroj **`2944c0fc7bb899355d45fe1f16e49253c90560c4`**. `git diff 61168e0 2944c0f -- src` mění pouze `ui/author_connectors.py`; materiálová numerika a writery zůstávají stejné. **APPROVED_IN_CONNECTOR_PREVIEW_DELTA_SCOPE.** Tento dílčí verdikt opravuje konkrétní příčinu původního dialogového selhání, nikoli níže uvedený nový PDF nález.

Preview nyní využívá existující společný reader `_path` pro M/L/C/A/Z i staré `points`, potom aplikuje stejné Y zrcadlení jako předchozí náhled. Zrcadlí celou výslednou křivku, nikoli jen endpointy nebo samotný sweep. Výsledek zůstává pouze zobrazením; preview reader nepřebírá roli konstrukční/výrobní autority.

V přesném archivním subprocessu byla ověřena skutečná cesta/importovaný obsah UI modulu:

- **27 původních Qt testů PASS / 45,62 s**, [JUnit](evidence/pc007a-connector-preview-review-original-2944c0f.xml).
- **5 vlastních Qt testů PASS / 21,82 s**, [zdroj](evidence/pc007a-connector-preview-review-own.py), [JUnit](evidence/pc007a-connector-preview-review-own-2944c0f.xml).
- [Runner, source pin, SHA256 a actual import probe](evidence/pc007a-connector-preview-review-archive-2944c0f.json).

Vlastní případy přímo četly C řídicí body po Y flip, skutečný A→curved QPainterPath a jeho správné kvadranty, compound even-odd otvor, starý points vstup a nezměněná vstupní data. Samostatný skutečný doménový Bézier díl v dialogu prošel Cancel, následným potvrzením a přehráním na klonu; analýza skutečného kontaktu dala nezávisle očekávaných 32 mm² a původní zdroj zůstal beze změny. Jde o offscreen Qt, nikoli náhradu nového člověka nebo vlastního nativního běhu reviewera.

## Nezávislý audit skutečných nativních artefaktů `2944c0f`

Přečten výstup `pc007a-desktop-2944c0f-run02`, nikoli pouze jeho status PASS_REQUESTED_FIXTURE. [Vlastní auditní zdroj](evidence/pc007a-planar-artifact-review.py), [raw JSON](evidence/pc007a-planar-artifact-review-2944c0f.json).

Ověřeno **17 skutečných souborových SHA256**, shoda project ID mezi uloženým projektem, snapshotem a manifestem, shoda všech tří part ID mezi projektem, snapshotem a skutečným PDF a dvě stránky. Source report ukazuje přesný 2944 pin, skutečný modul z profiles worktree a NVIDIA OpenGL 4.6. Log obsahuje tři skutečně potvrzené native Save/Open/Export dialogy, vlastní UI tvorbu bez presetu, 3D↔paper výběr, ruční posun, zámky, přepočet a reopen. Příslušný desktop screenshot byl nezávisle prohlédnut: skutečný otvor zůstává viditelný ve 3D i na papíře a druhá stránka obsahuje vlastní Bézier díl s chlopní a protikus. Tento důkaz se vztahuje na planar řez, nikoli celou budovu A/B1/B2/B3.

### V02 — MAJOR: skutečná plocha PDF nesplňuje původní AC

Vlastní výpočet nepoužil exportní expected helper ani číselný výsledek PASS z driveru. Z přesně přečtených **skutečných serializovaných PDF kubických polynomů** se provedl Greenův integrál v racionální aritmetice. Pro M/L/C/Z má integrand konečný polynom; integral vzniká přesnými Fraction součty jeho koeficientů. Nejde o sampled mesh ani zaokrouhlenou numerickou kvadraturu.

| Skutečná oblast | Analytické očekávání mm² | Skutečné PDF mm² | Absolutní chyba mm² | Normativní mez mm² |
| --- | ---: | ---: | ---: | ---: |
| Kruhový otvor R20 | 1256,6370614359173 | 1256,6035223018973 | 0,033539134020 | 0,01 |
| Stěna 120×100 minus otvor | 10743,362938564083 | 10743,399277698267 | 0,036339134183 | 0,010743362939 |

Původní `04_ACCEPTANCE_AND_VERIFICATION.md` výslovně požaduje zachování plochy rovinných dílů `max(0.01 mm²,1e-6×plocha)`, bez chlopní a se správným odečtením otvorů; AC-X04 vyžaduje shodnou SVG/PDF geometrii v toleranci. Nevyhovuje tedy i skutečná **net plocha dílu**, nejen izolovaný otvor. Ostatní zkoušené PDF plochy byly 2188,001909560582 a 800,000186666678 mm² a do 0,01 se vešly.

Driver pro kruhový PDF otvor místo normativní meze použil volnější odhad `perimeter*delta+pi*delta² = 0.09607577379 mm²`. Ten může být pravdivou odvozenou mezí polohové aproximace, ale nenahrazuje zvláštní přijatou plošnou přejímku. Malý poziční bound 0,0007645321 mm sám její splnění nezaručuje. Původní native status se zpětně nepřepisuje; **nezávislé artifact review je CHANGES_REQUESTED, V02 OPEN**.

Opravit je potřeba skutečný writer/rozpočet aproximace, aby předávaná geometrie splnila i oblastní toleranci, a znovu ověřit oba příslušné číselné důkazy. Nezvyšovat povolenou plochu ani vydat derived boundary tube bound za změnu normativního požadavku. Nález byl ownerovi předán ihned s přesným PDF, číselným protikladem a reprodukcí. Finální planar publikace čeká opravu a odpovídající přezkoušení nového pinu.

### Skutečné editorové artefakty a rozdíl proti harness FAIL

Nezávisle byly přečteny obě kopie Inkscape výsledků pro hole a Bézier stránku včetně skutečných souborových hashů, nikoli jen metadata. Native Unicode text v edited SVG je přesně `Žluťoučký – vlastní díl`; fyzické width/height/viewBox zůstaly stejné a původní exportní balík je bajtově zachovaný.

Vlastní reader kanonizoval absolutní/relativní M/L/H/V/C/A/Z, implicitně opakované A a skutečnou uzavírací hranu Z. U všech původních identifikovaných lokálních cest (2 na hole stránce, 4 na Bézier/protikus stránce) se geometrie před a po skutečném editoru přesně shodovala. Bézier editor run02 má stále uložený FAIL, protože `_same_path` považoval odstranění redundantního koncového `L 0 0` před `Z` za změnu počtu segmentů. Skutečný Inkscape ale stejnou hranu uzavřel `z`; vlastní geometrická normalizace potvrzuje shodu. Tento konkrétní FAIL je potřeba opravit ve srovnávacím harnessu a výsledek pravdivě zopakovat; není doloženým odstraněním hmoty produktem. Historický FAIL zůstal zachovaný.

Editorové úpravy a preview oprava neuzavírají V02. Celé P2, celý PC-007A, všechny další loft řezy, nový uživatel a P3 zůstávají samostatné nedokončené přejímky. Tento dodatek je nadále bez commitu dle instrukce ownera.
