# Nezávislá revize kotvy společného dílu stěna–střecha

**Verdikt: APPROVED_IN_SCOPE** pro CODE **`95be72c6de6665b98efd10c58dae941f3b91fe83`**. Schválení se týká doplněného návrhu a analytického orákula. Produkční P2, jeho GUI ani exporty tím nejsou ověřené nebo produktově přijaté.

Reviewer: samostatný agent `integration_review`, odlišný od autora dodatku. Datum: 5. listopadu 2026. BASE: `42b3d80158fda64af39a99416f2b5e52be2bc72a`; první revidovaný CODE: `ab97d72f6a4e71d2d26619793dc3d3f7587ac55c`; opravný a závěrečný CODE: `95be72c6de6665b98efd10c58dae941f3b91fe83`. Původní integrační revize a její SHA se nemění.

## Rozsah a nezávislé kontroly

Přečten devítisouborový delta kontraktu, doplněný AC-I01, ADR, UX, traceability, rozhodovací karta a queue PC-006–009. `PaperFrame` má persistovaný významový root, vertex, orientovanou osu a potištěnou stranu. Placement je polohou kotvy, nikoli obálky. Kontrakt výslovně invaliduje celý smíšený díl, uchovává rámec při jednoznačné kontinuitě a blokuje kompletní export do ověřeného přepočtu. Změna obálky nezpůsobí packing ani posun kotvy.

Závazek invariantních bodů je správně podmíněný nezměněným stěnovým rootem a nezměněnou cestou fold vazeb. Jiná plocha připojená přes změněnou střechu je závislostně dotčená. Ruční join zachovává kotvu přijímajícího dílu a ukazuje dopad; přijetí do střešního rootu neslibuje invariantní stěnu. Split zachovává původní kotvu v příslušném potomku, ostatním odvozuje rigidní mapu nebo explicitní nevyřešený stav. Chybějící/degenerovaná kotva má `ANCHOR_UNRESOLVED`, blokaci kompletního exportu a žádný automatický centroid/index fallback; nová volba je explicitní a undoable. Tyto podmínky jsou v UX i implementačním kontraktu konzistentní.

Protože se sdílený hlavní checkout během revize změnil na `master/f789b74`, první guard vlastního probe tento rozdíl zastavil. Reviewer hlavní checkout neměnil. Závěrečné kontroly proběhly v samostatném detached worktree přesně na `95be72c`, s interpreterem původní projektové `.venv`. Nezávislé orákulum používá pouze standardní knihovnu a ruční vzorce; nevolá produkční unfold/layout helpery.

Reprodukce: `.venv\Scripts\python.exe docs/revival/evidence/mixed-part-review-checks.py <detached-worktree-na-95be72c>`. Skript i [výsledky](evidence/mixed-part-review-results.json) jsou v `evidence/mixed-part-review-*`. Závěrečný běh exit 0, 3.333 s. `git diff --check BASE..CODE` a `tools/revival/validate_delivery.py` v přesném worktree také exit 0. Produkční `src/`, původní `tests/` a `pyproject.toml` proti BASE nemají změnu; full suite ani GUI se bez produkční změny neopakovaly.

## Vlastní analytický výpočet

Použit transform `p=[60,60]+R(30°)u`, s `cos30=√3/2`, `sin30=1/2`. Kořenová stěna zůstává stejným lokálním obdélníkem 100×40; nezměněný affine transform zachovává všechny její body, nikoli pouze zapsané rohy.

| Kontrola | Nezávislý výsledek | Význam |
|---|---|---|
| Čtyři rohy stěny | [60,60], [146.602540378444,110], [126.602540378444,144.641016151378], [40,94.641016151378] | Souhlas s opraveným kontraktem, odchylka zapsaných desetinných hodnot pod 1e-9 mm |
| Sklonová délka | `hypot(30,30)=42.426406871193`, po změně `hypot(30,35)=46.097722286464` mm | Délky ani toleranci není třeba přizpůsobovat stabilizaci rámce |
| Obálka bez chlopní před změnou | minimum [18.786796564404,60], maximum [146.602540378444,181.383362293125] mm | Hlavní fixture s kotvou [60,60] se vejde na A4 |
| Obálka bez chlopní po změně | minimum [16.951138856768,60], maximum [146.602540378444,184.562814708056] mm | Obálka se mění, kořenové body se nepohybují; úplné chlopně se validují zvlášť |
| Drift při chybné vazbě na stránkový bounding box | minimum X obálky se změní o −1.835657707636 mm | Kdyby se udržovalo minimum obálky, stěna by se posunula; placement musí patřit kotvě |
| Negativní kotva [30,60] | minimum X −11.213203435596 před změnou a −13.048861143232 po ní | Oba stavy přesahují fyzickou stránku; přijetí varování nesmí povolit kompletní PDF |
| Izolovaná nová kolize | obdélník x=10..20, y=84..85 má se starou střechou průnik 0, s novou 10 mm²; rotace plochu zachovává | Platí při vypnutých horních chlopních, jak nyní výslovně stanoví fixture |
| Závislostně dotčená druhá stěna | U jednoduchého rozvinutého řetězce stěna→dvě střešní plochy→stěna má referenční bod lokální y=`40+2s`; změna s jej posune o 7.342630830543 mm | Vlastní rozměry druhé stěny mohou být stejné a její 2D poloha přesto jiná; není přípustný bezpodmínečný slib všech nepohnutých stěn |

Poslední řetězec je samostatné analytické vysvětlení závislosti, nikoli další pozitivní A4 exportní fixture. Ztráta kotvy byla ověřena staticky proti explicitnímu kontraktu stavů/reference integrity; implementační negativní test dosud **NOT_RUN**. Numerické PASS v této revizi dokazují konzistenci příkladů, nikoli implementovanou funkci aplikace.

## Nálezy a opravy

| ID | Závažnost | Nález na ab97d72 | Podmínka uzavření / re-review 95be72c |
|---|---|---|---|
| MR-01 | major | Hlavní pozitivní fixture měl kotvu [30,60] a rotaci 30°, takže střecha přesahovala fyzickou A4. To odporovalo jeho použití pro úplný SVG/PDF pozitivní proof | CLOSED: hlavní kotva změněna na [60,60], čtyři rohy přepočítány, vlastní bounds uvnitř A4. Původní poloha zachována pouze jako explicitní negativní overflow s blokací complete PDF podle AC-L10 |
| MR-02 | minor, izolace orákula | Novou kolizi v pásu y=84..85 nelze bez podmínky odlišit od již existující kolize s výchozí 5mm chlopní na horním okraji staré střechy | CLOSED: opravný kontrakt specifikuje obdélník x=10..20/y=84..85 a vypnuté horní chlopně pro tento případ. Vlastní výpočet potvrzuje průnik 0→10 mm²; tab envelope má samostatný případ |

Žádný otevřený major/blocker v tomto dokumentačním dodatku nezůstává.

## Fronta, odhad a meze schválení

PC-006 obsahuje schema rámce a povinné přehodnocení odhadu po PC-006 před PC-007; PC-007 zachování přijímající kotvy; PC-008 oddělený i smíšený fixture, root/axis/locks, reindexaci, tab envelope, novou kolizi, save/undo, split/join a missing anchor; PC-009 soulad stejného smíšeného snapshotu v SVG/PDF. Stavy těchto implementačních kontrol zůstávají NOT_RUN. Odhad je výslovně lidská pracnost v člověkodnech, nikoli běh agentů nebo naměřené paralelní zrychlení.

Fronta stále obsahuje 12 ticketů, 16 epic a 61 explicitních AC. `GATE-P2=PO_PENDING`, `accepted_by_owner=false`, všechny dosud neautorizované execution příznaky P2/P3 false. Rozšířený AC-I01 doplňuje společný part a neruší původní oddělený případ. Doporučení varianty B se nevydává za přijetí doplněného kontraktu v1.1.

Schválení umožňuje uložit tento report a jeho vlastní evidence administrativním commitem a přidat čistý odkaz na review do queue, pokud se nemění kontrakt, gate ani execution příznaky. Autorizovanou integraci a push `master` provede integrátor se závěrečným ověřením vzdáleného SHA a případných souběžných změn. Tento report nepředstírá úspěch dosud neprovedené síťové operace. Produkční P2 a její skutečná produktová akceptace zůstávají otevřené.
