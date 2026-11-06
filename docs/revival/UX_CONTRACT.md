# UX kontrakt P2

> Aktualizace 6. 11. 2026: tento dokument zachov?v? stav p?vodn?ho P0/P1 a v1.1. V1.1 byla skute?n? p?ijata vlastn?kem, potom byl c?l roz???en. Aktivn? n?vrh [P2 v1.2](../p2/v1.2/README.md) a jedin? queue ur?uj? nyn?j?? rozsah/stav; review a baseline piny z?st?vaj? historick?. Povinn? mixed-part testy se neru??. Push n?vrhu nen? jeho produktov? p?ijet?.

Návrh k akceptaci, ne screenshot funkční nové aplikace. [Offline klikací obrazovky](ux-prototype.html) zobrazují všech šest požadovaných stavů. Prototyp nepočítá geometrii a neukládá projekt.

## Pracovní prostor a základní průchod

Vlevo strom konstrukce/povrchů se stálými čísly dílů, uprostřed současně 3D a 2D (poměr lze změnit), vpravo vlastnosti vybraného objektu/spoje a dole problémy. Horní přepínač Konstrukce / Díly a spoje / Stránky přizpůsobí nástroje, zachová vybranou identitu. Grafika a Návod v P2 nemají prázdné aktivní záložky; SVG export a pracovní legenda plní jejich minimum.

Prázdný projekt nabídne „Vložit domeček“, jednotky, měřítko a papír. Domeček ukáže délku 10 m, šířku 6 m, stěnu 4 m a převýšení střechy 3 m s náhledem papírových rozměrů. Hodnoty se převádějí jednou na vstupu. Obě strany modelu mají slovní označení potištěné strany; samotná barva nestačí.

Klik na povrch ve 3D vybere celý související díl ve 2D i stromu; opačný klik vybere odpovídající sadu povrchů. Klávesa F zaměří výběr, orbit/pan/zoom nezasahují do konstrukce. Skrytý objekt se nevybírá ray pickingem, zamčený lze prohlédnout, editace má vysvětlený zámek. Výběr spoje zvýrazní obě hrany a ukáže „P3 / strana 1 ↔ P7 / strana 2“, tlačítko „Ukázat protikus“ posune druhý pohled bez ztráty původního kontextu. Neumístěný protikus se ukáže na odkládací ploše.

Přímo u spoje je Řez / Přehyb, Chlopeň A / B / Žádná, šířka v mm papíru a zkosení. Popisky „ohnout ven/dovnitř“ doprovází kresba mountain/valley z deklarované strany papíru. Join nepodporovaného cyklu/kolize vysvětlí „Tento spoj by uzavřel nevyrovnatelný díl; ponechte alespoň jeden řez“. Žádné tiché přepnutí strategie.

Režim Stránky: přehled A4, odkládací plocha, drag s náhledem, rotace myší a číselně, X/Y mm a úhel ve vlastnostech, přesun na vybranou stránku, přidat/odebrat stránku. Snap 1 mm lze dočasně vypnout klávesou Alt; numerický vstup se nezaokrouhluje na snap. Základní zarovnání k tiskovému levému/hornímu okraji. Poloha a rotace mají samostatný zámek. Drag je jedna undo operace při puštění; Esc ji zruší. Smazaná stránka přesune díly do odkládací plochy; undo vrátí stránku, pořadí a všechny placements.

## Požadované stavy

| Obrazovka | Viditelná informace a akce | Ověření |
|---|---|---|
| Prázdný projekt | žádné díly, vytvořit dům, výchozí měřítko, export vysvětleně nedostupný | nový projekt bez falešného „hotovo“ |
| Domeček | rozměry, společný 3D/2D výběr, stránky a odkládací plocha | AC-G02/C01 |
| Vybraný spoj | obě hrany, čísla i stránky, chlopeň A/B a undo | AC-C02/C05/C06 |
| Změněná střecha | text „Dotčené díly vyžadují přepočet“, u společného partu stěna–střecha stale celý díl, starý obrys přerušovaně a stabilní kotva ve stěně viditelná; body kořenové stěny zachované, další závislé plochy uvedené v dopadu | AC-I01/I02 včetně smíšeného fixture |
| Kolize chlopně | obrys průniku, konkrétní spoj a stránky, přesunout díl / změnit chlopeň | AC-L04, žádné schování chlopně při validaci |
| Exportní souhrn | počet dílů a stránek, neumístěné, stale, varování, font, měřítko a 100% tisk | AC-L08–L10/X01–X07 |

## Chyby, změny a export

Chyby integrity (stale, missing part/reference, NaN, neúplné pokrytí) blokují kompletní export. Překryv či přesah doporučeného tiskového okraje lze označit „Přijímám pro tuto verzi“ s důvodem, nikoli globálně vypnout kontrolu. Změna dotčené geometrie potvrzení zneplatní. Přesah fyzické stránky vyžaduje umístění/jiný formát, nebo zřetelně částečnou kopii; P2 nemá automatické dlaždice. Exportní dialog oddělí neuložený projekt od aktuálního snapshotu a neoznačí projekt jako uložený.

Změna rozměru střechy zobrazí dopad před přepočtem, dovolí undo a ponechá původní placements při jednoznačné kontinuitě. Zaniklý/split díl má seznam předchůdců a upozornění; kresba či placement se nikdy nepřidělí podle čísla v seznamu. P2 nemá interní kreslicí editor, ale struktura SVG umožní přesun celého dílu i samostatnou editaci role/textu. Externě upravená kopie se neimportuje zpět.

Společný díl ukazuje kotvu a referenční hranu; X/Y ve vlastnostech jsou jejich poloha na stránce. Join zobrazí přijímající díl, jehož kotva se zachová. Změna střechy může zvětšit obálku, ale nepřecentruje díl ani neposune ukotvenou stěnu. Pokud kotva zanikne nebo nemá jednoznačného nástupce, UI vypíše „Kotvu dílu je nutné znovu určit“, nabídne volbu s náhledem a undo, kompletní export zablokuje. Plochy připojené přes změněnou geometrii zobrazí jako dotčené, nikoli bezpodmínečně nepohnuté. Přesný příklad a pravidla jsou v [kontraktu smíšeného dílu](MIXED_PART_LAYOUT_CONTRACT.md).

Uložit/Zavřít: dirty značka a volby Uložit / Zahodit / Zrušit; neúspěšný save ponechá projekt otevřený. Chybné vstupy zobrazí konkrétní pole a zachovají předchozí hodnotu. Klíčové akce mají klávesové ovládání, fokus a tooltip; kontrast a text se zkontrolují při 100/150/200% škálování Windows. Dlouhá operace ukáže stav a při pozdějším workeru ignoruje starší výsledek. Otevření novějšího schématu nesmí tiše přepnout do editace.

## Demo a skutečné limity

P2 přejímka postupuje přes všech osm kroků v §4 `04_ACCEPTANCE_AND_VERIFICATION.md`: vytvořit dům, obousměrný výběr, šev/chlopeň/undo, dvě stránky, kolize, změna střechy, save/reopen, SVG editor a PDF. Prototyp tyto AC nemůže označit PASS. Aktuální desktop baseline a jeho chybějící interakce jsou v BASELINE_REPORT; fyzické sestavení je P3.
