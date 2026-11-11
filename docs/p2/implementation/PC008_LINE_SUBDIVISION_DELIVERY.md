# Živé dělení úseček — dílčí AU13/AU14

11.11.2026. Ověřený CODE **24e08019a711c5c7c19ca73a5ac35e5093dfb4d0**.
Zdrojová/matematická/UI komponenta i skutečné native/editor artefakty a metadata
jsou [nezávisle schválené](PC008_LINE_SUBDIVISION_REVIEW.md) v omezeném LINE
rozsahu. [Integrace](PC008_LINE_SUBDIVISION_INTEGRATION.md) doloží publikovaný stav.
Nejde o dokončené AU13, AU14, PC-008 nebo P2.

## Co autor může udělat

Ve vlastním obrysu vybere úsečku a použije **Vytvořit → Rozdělit vybraný úsek
obrysu**, případně tlačítko v části Profil a křivky. Zadá vzdálenost od začátku
v aktuálních rozměrech modelu, vidí náhled bodů a může krok zrušit. Dělení
nevytváří další šev ani chlopeň. Tvar zůstane stejný a rozvin celého dotčeného
papírového dílu se označí jako neaktuální do explicitního přepočtu.

**Spojit původní úseky** ukazuje skutečné potomky dělení. Ctrl/Shift vybere
sousední intervaly téhož nezměněného zdroje; nefitují se nové přímky. Celý krok
je jedno undo a redo obnoví stejné nové identity. Potvrzení vždy vyhodnotí i
právě rozepsanou vzdálenost bez Enter. Neplatný konec/nulová vzdálenost se dá
opravit v témže dialogu a Cancel nemění projekt.

Původní edge spoj, interior attachment, číslo a parametry chlopně si ponechají
svá ID i celý orientovaný geometrický zdroj. Nemění se na spoj první poloviny.
Kotva a směr papíru jsou historické materiálové reference: inverse merge
nepřesune root wall ani v případě, že starý split vertex byl kotvou. Layout,
stránky, rotace i oba locks patří autorovi. Nejednoznačné nebo geometricky
změněné potomky se nespojují automatickým fitem; zachovaný zdroj zůstane
explicitně unresolved, uložitelný a blokovaný pro přepočet/export do opravy.

## Skutečná doména a formát

Samostatný registr `profile_subdivisions` uchovává původní analytický zdroj,
přesné Fraction intervaly, přehratelné split/merge/edit události, incidence
a historické materiálové body. Aktivní geometrie musí odpovídat odvození;
dodaná child cache, zaměněné vrcholy, alias UUID ani znovu použité retired ID
nejsou důkaz. Nahrazení celého profilu nesmí oživit starou kotvu z odpojené
historie. Ohyb a cache zahrnují stejné source references jako papír.

Nový experimentální formát7 má známé copy/SaveAs adaptéry1–5. Původní soubor
se nepřepisuje. Formát6 vzniká v odděleném C přírůstku; jeho známý adaptér se
musí doplnit při věcné integraci C. Současná větev nepřijímá neznámý formát6
jen změnou čísla verze. Nevzniká nevratná migrace starých projektů.

Přejímka tohoto aplikačního přírůstku je **LINE**. Pure komponent umí také
algebraicky správné ARC/CUBIC restrictions, ale jejich živé canonical views,
loft trim/phi korespondence a aplikační rozhraní tím nejsou dokončené.
Jednostranně rozdělený loft nesmí automaticky získat EXACT ani první-child
náhradu; potřebuje navazující řez. Normativní AC zůstávají beze změny.

## Dosavadní ověření a nalezená chyba

- Backend/interface selection179 PASS23,04s;19 nových doménových a3 widgetové
  případy22 PASS1,77s, výběry se překrývají a nesčítají se jako201 unikátních.
- [9b celá sada](evidence/au13-line-full-suite-9b87c89-run02.xml),
  [plný log](evidence/au13-line-full-suite-9b87c89-run02.log):1447 PASS294,44s.
  To samo neodhalilo chybějícího spotřebitele níže.
- První úplná sada byla přerušena po chybném historickém testovém envelope;
  [záznam](evidence/au13-line-full-suite-run01-aborted.json). Testy rekonstruující
  schema1–4 nyní odstraňují také nové pole stejně jako segmented_variants.
  Parser se nezměkčil a testy se neodstranily;80 regresí pak PASS31,87s.
- Nativní [9b FAIL](evidence/pc008-AU13-line-desktop-9b87c89-run01/results.json)
  a [929 diagnostika](evidence/pc008-AU13-line-desktop-9290a01-run02/results.json)
  zachovávají původní selhání. Nový pozorovací wrapper pouze zaznamená a znovu
  vyhodí původní exception; nemění příkaz, výsledek nebo geometrii.
- **LINE-BEND01:** actual split existujícího tab owneru prošel doménou, ale
  následný3D refresh hledal retired edge ID jen v `world_geometry.boundary`.
  `StopIteration` způsobil prázdnou chybovou zprávu. Opravaa770 používá celý
  semantic `edge_source` a zdrojovou world mapu; clearance key nese historii
  a všechny source profily. Nové2 backendové a1 widgetové regrese skutečného
  spoje s chlopní jsou v [45 PASS16,48s](evidence/au13-line-existing-tab-bend-fix-run01.xml).
- [Nativní a770](evidence/pc008-AU13-line-desktop-a770f8a-run03/results.json)
  už prošel source axis/join/trace, tab, změnou rise3000→3500, zámky,
  Save/New/Open a exportem; poté skončil **FAIL** kvůli očekávání orákula. Driver
  předpokládal90mm tab base/144mm², ale sám zadal celý interval[0,1],100mm,
  width2,taper0.6, tedy160mm². Rozdíl16mm² je doložený v uloženém projektu.
  Není to změkčení0,01mm² AC ani nový důkaz product chyby. Před finálním PASS
  musí být fixture/orákulum explicitně sjednoceny a běh znovu proveden.

Další samostatná revize odhalila a uzavřela LS01–LS05: odchylku float bodů při
velkých souřadnicích, globální alias retired UUID, netypovaný špatný zlomek,
chybějící přímou plošnou mez a nesprávnou kvalifikaci hrany při úpravě otvoru.
Zaokrouhlení se kontroluje polohou, jednou souhrnnou délkou i přímým Green
rozdílem původní/skutečné plochy. Zdroj2mm²→actual9/4mm² se odmítne i při
úspěšné polohové/délkové kontrole. Tři skutečné díry s jednotlivým rozdílem
1/256mm² nemohou každá spotřebovat0,01: třetí krok překročí společnou mez těla.
Nezměněné zakřivené příspěvky se při rozdílu ruší; jejich relativní referenci
zde konzervativně nenahrazujeme odhadem. Fyzický whole-edge navíc vyžaduje
skutečné kolineární/monotónní potomky, ne jen ideální ancestry. Při numerické
nejistotě zůstane původní práce atomicky zachovaná a lze vybrat jinou vzdálenost.
Záměrná editace tvaru má vlastní nový zdroj a nepodléhá slibu staré plochy.

| Finální důkaz na CODE24e | Výsledek |
|---|---|
| [Celá sada](evidence/au13-line-full-suite-24e0801-run05.xml) | **1465 PASS326,23s**,0 failures/errors/skips |
| [Windows od prázdného projektu](evidence/pc008-AU13-line-desktop-24e0801-run05/results.json) | **PASS_REQUESTED_FIXTURE32,734s** |
| Inkscape [strana1](evidence/pc008-AU13-line-inkscape-24e0801-page1-run01/editor-results.json) / [strana2](evidence/pc008-AU13-line-inkscape-24e0801-page2-run01/editor-results.json) | **oba PASS15,672s /18,015s** |

Native proof vytváří skutečný společný wall–roof díl a základnu, existující
interior trace i chlopeň. Při page2/[60,60]/30°/obou locks rozdělí osu,
provede inverse merge, rozdělí skutečný fold a zdroj lepicího připojení, vrátí
a zopakuje krok a změní rise3000→3500. Původní wall vertices zůstanou na stejných
souřadnicích. Následuje skutečný3D/paper pick, native Save/New/Open, ruční
layout a SVG/PDF. Analytické očekávání těla včetně160mm² tabu je
8769,772228646mm²; skutečné SVG má8769,772229 a PDF přibližně8769,772000000mm².
Očekávání základny je13000mm². Aktuální kroky/projekty/exporty/snapshot jsou v uvedené
evidence složce. Editorové kopie změní celek, barvu a víceslovný Unicode text,
originál zůstává byte-identical.

Autorovy výběry a reviewerovy případy se nesčítají do1465. Dřívější a770
1450 PASS311,48s a694 1459 PASS293,56s jsou historické běhy před posledními
opravami; nenahrazují výše uvedený finální běh. Nezávislý reviewer
`commands_review` provedl vlastní source/math/UI případy a zkontroloval
skutečné artefakty i metadata odděleně od autora root. Nemá otevřený zásadní
nález v tomto omezeném přírůstku; širší produktové důkazy tím neuzavírá.

## Skills a další práce

Konstrukční skill vedl k zachování celého hinge a skutečného příjemce; UI ke
kontextovým příkazům, měřenému vstupu, opravě a návratu; verification k vlastnímu
whole-wall orákulu a uchování nativních selhání; delivery k omezenému LINE
rozsahu a oddělené revizi. SK015 převádí LINE-BEND01 do kontroly dalších
spotřebitelů. Účinnost na jiném spotřebiteli zůstává PENDING_NEXT_USE.

Zbývají curved/loft trim adapters a publikace tohoto
přírůstku, úplné AU13/AU14, C, PC-009 a historický PC-010. **Nový uživatel0 /
NOT_RUN; fyzické P3 / NOT_RUN.** Technický průchod ani agentní revize je
nenahrazují. Dokončený D/B3 je samostatně publikovaný; tento dokument jej
nepřepisuje na dokončené P2.
