# PC-007A — nezávislá revize ohraničeného slučování nativních křivek

11.11.2026. Reviewer `/root/commands_review` není autorem komponenty, jejího volajícího ani testů. Přesný source **`730cb28f2e3f221e03e7df174bf194ff577d6c3c`**, izolovaná větev `revival/p2-loft-coalescing`. Scope3 produkční/testové cesty: nový `loft_curve_compaction.py`, úzká integrace `loft_surface.py` a `test_loft_curve_compaction.py`.

**APPROVED_IN_BOUNDED_NATIVE_LOFT_COALESCING_COMPONENT_SCOPE,0 otevřených BLOCKER / MAJOR.** Source→fine meze zůstávají započtené a coarse→fine důkaz kryje celé nerovnoměrné intervaly i globální délkový součet. **LX01 není tímto reportem uzavřen jako skutečná interoperabilita:** nový native/editor důkaz musí teprve potvrdit výsledek aktuálního integrovaného zdroje při nezměněných AC a harness tolerancích. Nejde o schválení celého B/C/D, PC-007A/P2, nového uživatele nebo P3.

## Přesný zdroj a nezávislé testy

[Runner](evidence/pc007a-loft-coalescing-review-archive.py) vytvořil fresh `git archive` připnutého source/tests a fresh subprocess s explicitním `PYTHONPATH`. [Manifest](evidence/pc007a-loft-coalescing-review-archive-730cb28.json) zaznamenává skutečné importy `loft_surface` a `loft_curve_compaction` do archivu, hash archivu a shodu Git text SHA-256 s výslovnou LF/CRLF normalizací. Živý worktree se nespletl s připnutým zdrojem. Žádný skutečný desktop nebo editor reviewer nepoužil.

- **126 původních PASS /39.90s**, [JUnit](evidence/pc007a-loft-coalescing-review-original-730cb28.xml): nové coalescing testy a existující native loft curves/domain regrese. Jde o zde skutečně spuštěný výběr, nikoli přeznačení autorových134 testů nebo celého projektu.
- **13 vlastních PASS /.79s**, [vlastní oracles](evidence/pc007a-loft-coalescing-review-own.py), [JUnit](evidence/pc007a-loft-coalescing-review-own-730cb28.xml). Expected využívají nezávislou přesnou monomiální substituci, analytické derivace a konstruktivní délkovou dolní mez, nikoli produkční restriction/norm helper.
- První vlastní aritmetický test omylem vynechal faktor2 pro y-variaci přes midpoint; tato chyba reviewerova expected byla opravena podle analytického odvození. [Původní raw](evidence/pc007a-loft-coalescing-review-harness-arithmetic-730cb28.json) a [JUnit](evidence/pc007a-loft-coalescing-review-harness-arithmetic-730cb28.xml) zůstávají zachované; nejde o produktový FAIL nebo změkčení rozpočtu.

## Matematické posouzení

Kandidát používá skutečné původní binary endpoints a globální-u endpoint derivace první/poslední fine kubiky. Odvozené handles se jednou převedou do skutečných binary float hodnot a důkaz následně ověřuje **tyto vracené controls**, nikoli ideální nevytištěný polynom. Řetězec L zůstává L, C zůstává C.

Pro každý původní interval `[u,v]` se skutečný coarse polynom přesně racionálně restrikuje na tento interval. De Casteljau po rozdělení v b a následně v a/b dává stejný lokální polynom jako substituce globálního parametru; pracuje se skutečným nerovnoměrným u, ne pořadovým číslem vzorku. Vlastní odlišné expected převedlo původní Bernstein controls na monomiální koeficienty a dosadilo `u=a+(b−a)t`; přesná rovnost platila na nerovných racionálních intervalech včetně velmi krátkého koncového intervalu.

Rozdílové Bernstein controls `D_i` popisují coarse-minus-fine ve stejném parametru. Convex hull dává celointervalovou poziční mez `max ||D_i||`. Pro kubiku je derivace rozdílu `3Σ(D_(i+1)−D_i)B_i²`; integrál každého `B_i²` na[0,1] je1/3. Proto `∫||difference'|| ≤ Σ||D_(i+1)−D_i||`. Z trojúhelníkové nerovnosti rychlostí plyne stejná mez pro absolutní rozdíl obloukových délek. U L platí odpovídající lineární případ. Není nutné znovu přidávat délku globálního u intervalu: obě restrikované křivky už používají stejný lokální parametr a tento fyzikální integrál je invariantní vůči shodné reparametrizaci.

Normy se obalují ven z přesných rational squared hodnot; `*_bound_exact` ukládá přesnou racionální hodnotu konzervativní horní meze, nikoli tvrzení o přesné iracionální normě. Poziční chyby lze vzít jako maximum, ale délkové příspěvky se skutečně **sčítají přes všechny fine intervaly, coarse bloky a patche dané strany**. Poměr `fine_count/global_side_count` alokuje jednotlivým blokům disjunktní podíly globálního length limitu; jejich celkový podíl nepřesáhne1. Obě strany mají oddělený globální součet a společná mez obou stran sčítá oba.

Závěrečný source→coarse rozpočet přičítá chybu merge k původní source→fine chybě. Outward publikované float souhrny jsou ještě porovnány s původním limitem; překročení způsobí návrat původní reprezentace. Neprovádí se nahrazení source chyby menším merge číslem ani max místo součtu délek.

## Vlastní případy, které kontrolují podstatné vady

- Nerovnoměrné dyadické parametry0,1/128,3/16,7/8,1 přesně rekonstruovaly jedinou původní binary C. Úplné fine `source.subintervals` zůstaly zachované, včetně opačného směru původního source parametru. Reverse vrací geometry controls, všechny intervaly/direction a pořadí subintervalů; dvojí reverse vrátí přesně původní záznam. Veřejný výstup je detached.
- Vlastní řetězec64 malých skutečných polynomiálních humpů ve2 patchích má analyticky prokázanou dolní mez celkové změny délky **`183·2⁻²⁰ mm`**: délka každé fine křivky je alespoň součet svislých vzdáleností přes její midpoint, coarse délka je známá přímka. Tato skutečná dolní mez je větší než jedna celá lokální patch mez přibližně`128·2⁻²⁰`. Publikovaný **globální součet** ji kryje; implementace používající max patch/local by tento svědek neprošla. Polohové konce přitom samy chybu neodhalí.
- Large-offset controls kolem2³⁰ s malými detaily ověřily skutečnou binary quantizaci: vlastní monomiální restrikce vracené coarse C dala na všech fine intervalech rozdílové control squared normy uvnitř publikované poziční meze. Nešlo pouze o sampled maximum nebo comparison se source helperem.
- Změna source segmentu a typu C→L uvnitř patch zůstala hranicí; oddělené strany/patches se nikdy nesloučily. Oba explicitní ruling records zůstaly přesně stejné. Po sloučení měly actual coarse derivace v globálním u analytické hodnoty(12,0) a(0,2), takže recomputed jump bound²≥148 a `exact_c1=false`. Neprošlo by převzetí staré continuity nuly ani porovnání lokálních derivací bez u škálování.
- Work cap2 pro candidate/comparison vrací celý původní prokázaný objekt a explicitní NOT_APPLIED, nikoli již změněnou první polovinu s částečným certifikátem. Vyčerpaná error rezerva rovněž nevymaže původní source chybu. Tyto fallbacky nejsou schválením původní husté reprezentace pro externí editor; caller musí její výrobní proof stále provést.

## Caller, provenance a cache kontrakt

Slučování je uvnitř jediné boundary patch/side a stejné čtveřice feature/patch/profile/segment. Samotný helper vyžaduje již prokázaný fine native vstup; řetězec `status=CERTIFIED_REPRESENTATION_ONLY` není ověřovač libovolného nedůvěryhodného externího JSON. V produkčním calleru vstup vzniká z aktuálního `fit_native_loft_boundaries`, aktuálních source records a solveru. Helper netvrdí topologii, rozvinutelnost, intrinsic area nebo editorovou stabilitu.

`loft_surface` poté znovu ověřuje actual coarse native topologii a intrinsic-source versus actual-native area v původním rozpočtu; nikde se tyto přejímky nevynechaly. Rebinding aktualizuje feature/patch UUID nejen v coarse source, ale i ve všech fine subintervals a reverse closed kopii. Fine parametrická provenance a source model nejsou nahrazené pouhou hrubou obálkou.

Nový paper contract **V3** mění cache digest a po načtení starého V2 označí paper stale, nikoli automaticky přesune či přepíše autorovu práci. Vlastní starý soubor zůstal beze změny a snapshot se před recompute odmítl. Po recompute zůstaly profily, plochy, frame, layout a zámky. Pod aktuálním V3 se stejně velká přeložená CUT cache neoznačí jen za starou/neaktuální: je hard `INVALID_CACHE` a snapshot se odmítne. Obojí bylo přehráno na malé nezávislé předloze i na skutečném B1 níže.

## Nezávislý backend replay skutečného B1

[Vlastní replay](evidence/pc007a-loft-coalescing-review-B1.py) načetl skutečný uložený native b127 B1 projekt, fixture SHA-256 **`22ffa3e1386dd37b1963435bb09d0f0d0e548f59db8052b37a493717c235709a`**, pouze přes archivovaný source730. [Raw](evidence/pc007a-loft-coalescing-review-B1-730cb28.json), **15.09s**, výslovně BACKEND, nikoli nový native/editor/human důkaz.

| Kontrola | Vlastní skutečný výsledek |
|---|---|
| CUT hustota |9049→69 příkazů:1M,64C,3L,1Z; nikoli nahrazení křivek mesh tětivami |
| Nová merge pozice |2.1640806468e−6 paper mm |
| Globální merge délka first/second |3.1059122944e−5 /3.7270950470e−5 paper mm |
| Úplný source→coarse position/length bound |.000309015910909 /.001536842156786 paper mm, obě pod.008 |
| Intrinsic versus actual native area |maximum error bound.000132860690969mm² < původní.01mm² |
| Source/frame/layout/čítače |přesně zachované, původní soubor byte-for-byte nezměněný |
| V2 load a V3 poison |stale/snapshot blocked před recompute; current equal-area poison hard INVALID_CACHE |
| Save/reopen |přesná shoda nového stavu |
| Feature/patch binding |18230 kontrolovaných source records včetně forward/reverse kopií odpovídá skutečným UUID; nejde o počet unikátních intervalů |

Authorův [backend záznam](evidence/pc007a-coalescing-730cb28/B1-backend.json) a targeted JUnit jsou samostatná evidence, nebyly vydány za vlastní běh reviewera. Jejich shodné počty/meze nejsou náhradou výše provedeného nezávislého archive replay.

## LX01 a další digitální důkaz

Motivující historický actual Inkscape loft run na b127 zůstává FAIL; tento reviewer jej při komponentové revizi znovu nespouštěl ani neopravoval. Bounded coalescing odstraňuje konkrétní nadbytečnou hustotu bez změny tolerancí, editor preferences nebo odhození C/ruling/source identity, ale **matematická mez sama nezaručuje chování další serializace v Inkscape**. Root musí na novém sjednoceném pinu provést skutečný native save/reopen/layout/SVG/PDF a actual editor roundtrip s původními geometrickými, plošnými, topologickými a calibračními kontrolami. Teprve tak lze uzavřít LX01 a odpovídající digitální řez; v tomto reportu je actual editor výsledek nové reprezentace NOT_RUN.

Čtyři projektové skills byly skutečně načtené: construction chránil source rohy/rulingy a autorský frame, verification vedl k jinému exact-polynomial orákulu a globálnímu length svědkovi, UI k zachování opravitelného starého souboru a pravdivého NOT_RUN editoru, delivery k přesnému pinu a zachování chyb místo změkčení AC. Žádný novice ani fyzický test nebyl proveden. Reviewer nezměnil produkci, staging, Git historii ani native desktop; vytvořil pouze vlastní review/evidence bez commitu.
