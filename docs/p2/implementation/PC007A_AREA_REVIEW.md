# PC-007A — nezávislá numerická revize ploch nativních cest

9.11.2026. Reviewer `/root/authoring_independent_review` není autorem `curve_area.py`, jeho testů ani rozpracovaných exportních/precision oprav rootu. Produkce a autorovy testy nebyly měněny. Přesný source **`60d60d114745ba72c4615d5d980376bf305a1b5d`**, scope pouze nové `authoring/curve_area.py` a `test_curve_area.py`.

**APPROVED_IN_NUMERIC_COMPONENT_SCOPE, 0 BLOCKER / 0 MAJOR pro posouzené plošné výpočty.** Jde o outward Fraction meze plochy skutečně dodaných platných L/C a kruhových SVG A smyček. **Tím není uzavřen V02, přijata celá PC-007A/P2, topologie, produkční guard, publisher, skutečné SVG/PDF, UI nebo fyzické sestavení.** Rootovy souběžné změny `precision.py`, desktop/editor harnessu a další untracked review nejsou součástí tohoto pinu ani verdiktu.

## Připnutí a ověření

Zdroj byl čten a spuštěn z izolovaného `git archive` uvedeného commitu; nic se neimportovalo z rozpracovaného worktree. [Archive záznam](evidence/pc007a-area-review-source.json), [skutečný import a runtime/Git SHA-256](evidence/pc007a-area-review-imports.json). Kontrolována cesta modulu a shoda Git textu s výhradně LF/CRLF checkout konverzí.

- Připnuté původní testy: **28 PASS / 0.70s**, [JUnit](evidence/pc007a-area-review-60d-tests.xml). Ruff source/testu PASS.
- [Vlastní nezávislé oracles](evidence/pc007a-area-review-own.py): **40 PASS / 0.66s**, [JUnit](evidence/pc007a-area-review-own-60d.xml). Expected nevolají produktový area, atan, sqrt nebo π helper. Používají nezávislý100místný π interval, pozitivní arcsin řadu s geometrickou mezí zbytku,400bit racionální `isqrt` obálku a ručně integrované polynomy.

## Matematická kontrola

Pro L je člen Greenova integrálu přesný cross-product/2. Pro skutečné binární/racionální C kontroly se převod na monomiální koeficienty provede přesně a člen `j·(xᵢyⱼ−yᵢxⱼ)/(2(i+j))` dává přesnou integraci `(x dy−y dx)/2`. Zavírací Z přidá skutečnou přímou hranu ke startu, nedoplňuje vzorkované aproximace. Sčítání zůstává racionálně přesné až po veřejné outward zaokrouhlení; velký posun se proto neruší nepřesným float rozdílem.

Kruhové endpoint A používá skutečnou délku tětivy a `r²=max(rx²,chord²/4)`, což přesně odpovídá SVG korekci kruhového poloměru. Znaménko center offsetu rozlišuje large/sweep, minor úhel plyne z `4 atan(c/(2r+sqrt(4r²−c²)))`; major doplní2π a opačný sweep obrátí znaménko. Greenův člen `1/2(cx·dy−cy·dx+r²θ)` společně s přímým uzavřením vrací skutečnou kruhovou úseč. Kružnice může ignorovat konečnou hodnotu rotace os, protože obě radius osy jsou shodné; elipsa se bezpečně odmítne.

Directed Decimal dělení a sousední sqrt hodnoty obalují racionální odmocninu. Racionální intervalové operace zaokrouhlují ven; střídavá atan řada ponechává zbytek se správným znaménkem následujícího členu. Redukce pro argument nad1/2 používá platnou atan součtovou identitu bez přechodu přes větev; Machinova identita pak dává interval π. U semicircle větve se nepoužije neprokázaná malá hodnota rozdílu pod odmocninou. Clamping q do[0,1] pouze protíná již platnou known doménu pravé hodnoty, neslouží jako svévolná změna geometrie.

Hole plocha se odečítá intervalově `[outer_lo−Σhole_hi, outer_hi−Σhole_lo]`. Outer musí být jednoznačně větší než jednotlivé hole intervaly a celý net má před veřejnou quantizací prokázaně kladné znaménko. Veřejné zaokrouhlení na grid10⁻²⁴ je také outward, nikoli midpoint nebo conversion do float. U velmi malé skutečné plochy může veřejná dolní mez po tomto zaokrouhlení být0; stále jde o platný interval, nikoli slib použitelného výrobního detailu.

## Nezávislé případy

- Minor/major a oba sweep směry: vlastní horizontal chord případy pro r1/c1, r7/c2 a téměř přímý oblouk r10⁸/c1. Očekávání používá jinou identitu `A_minor=r²(asin x−x sqrt(1−x²)), x=c/(2r)`, a pro major `πr²−A_minor`. Pozitivní arcsin řada má poměr sousedních členů menší než x²; horní zbytek je tedy ohraničen následujícím členem/(1−x²). Celý tento nezávislý interval je obsažen ve vrácených mezích.
- Velký přesný posun zakřivených cest o10²⁰ a−10⁷⁰ zachovává kruhovou plochu; cubic Green integrál byl ověřen také při posunu10¹⁰⁰. Posun se zadává přesně, ne jako již ztracené `float(large+small)` číslice.
- Radius correction: deklarované r=1/10 a chord6 musí znamenat skutečný r3 semicircle s plochou9π/2, pro všechny čtyři large/sweep kombinace. Vrácený interval obsahuje nezávislý π interval.
- Vlastní cubic arch má `x=w(3t²−2t³), y=3h(t−t²)`, tedy skutečnou plochu `3wh/5`. Pro w7/h5 je přesně21mm² v obou směrech. Outer50×40, tato C díra a kruhová r2 díra dávají net `1979−4π`; pořadí i winding se mění, data zůstávají beze změny.
- Skutečná čtyřkubiková kružnice r3 s přesnými decimal handles `k=0.55` má plochu `9(2+12k/5−3k²/5)=28.2465mm²`. To je **jiná plocha než9π**; rozdíl je přibližně0.0278338823mm², tedy více než normativní0.01mm² pro tento vzor. Helper správně vrátí skutečný cubic výsledek, ne nominální kruh. Tento negativní vzor je relevantní k V02 a nesmí se přijmout jen proto, že jiná volnější odvozená obálka dovolí větší chybu.
- Malé racionální souřadnice, Fraction/Decimal vstupy, neuzavřené nebo prázdné smyčky, chybné C arity, NaN, nepodporovaná elipsa, nesprávné flags, bool, omezení čísel a global command budget. Iteratorový vstup s10 příkazy neprojde budgetem9 a nedostane částečný certifikát, budget10 vrátí správný výsledek. Empty/ambiguous outer se odmítne; dva skutečné otvory se správně odečtou bez ohledu na pořadí a winding.

## Co zůstává volajícímu

Předpoklad API je **jedna již ověřená jednoduchá outer smyčka a uvnitř ní disjunktní díry**. Largest-area pravidlo toto uspořádání samo neprokazuje. Různě velké disjunktní outer regiony, samopřekřížení nebo špatně položená díra nemají tímto helperem schválenou topologii. Jejich validaci a případné rozdělení na samostatné regiony musí provést caller. Neznámé neiterovatelné objekty či jiné tvary mimo API rovněž nepředstavují ověřený path vstup.

Helper předpokládá, že dodané souřadnice už vyjadřují skutečné nativní geometry v paper mm. Neaplikuje původní CTM, jednotky stránky ani transformaci source profilu. Parser/caller musí zachovat původní číselné tokeny a správně dodat všechny skutečné controls; `Fraction` nad již zaokrouhleným floatem neobnoví ztracené číslice. Nekruhové A po nerovnoměrné transformaci nelze předat jako kruh. Stroke/raster/text a role či provenance tohoto výstupu také helper neověřuje.

Tento výpočet **neurčuje přejímací toleranci** a nenahrazuje normativní `max(0.01 paper mm²,1e−6·A)`. Produkční guard musí porovnat meze skutečného výstupu s platným source area intervalem v tomto rozpočtu; široký interval nebo poziční/perimeter tube není důvod ho zvětšit. Konzervativní maximální rozdíl dvou intervalů se kontroluje přes jejich krajní kombinace, nikoli jen midpointy. Area chyby otvoru a outer se nesmějí skrytě kompenzovat v jediném net čísle. Fresh skutečný export, jeho čtení a nové nezávislé uzavření V02 zůstávají nutné.

Skutečně načtené konstrukční, verification a delivery skills vedly ke skutečnému odečítání děr, přesným tokenům, jinému matematickému orákulu, přísnému oddělení polohového a plošného důkazu a source pinu. Report neuděluje UI, novice nebo fyzický PASS a neuzavírá skill účinnost jen na základě zelené sady. Žádný commit, změna produkce, nativní OS průchod nebo zásah do rootova WIP nebyl proveden.
