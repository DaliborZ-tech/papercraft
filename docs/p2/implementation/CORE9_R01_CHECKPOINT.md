# CORE9-R01: bezpe?n? checkpoint p?ed p?eru?en?m

Source pin `72f7a168b0ecbc58ecd0f014cb1555f11d6339ba`; z?klad `7c61c7ee54233dc662420b5199e3a5d914da4441`.
Stav: **IMPLEMENTED / TARGETED PASS / REPLAY + INDEPENDENT REVIEW PENDING**.
P??r?stek nen? schv?len? k integraci. Master ani p?vodn? review d?kazy se nem?n?.

P???ina: seznam v?ech historick?ch hran obsahuje tak? retired UUID. P?vodn?
z?v?re?n? guard jej chybn? pou?il jako doklad aktivn?ho descriptoru; p?ejmenov?n?
slou?en?ho aktu?ln?ho ?seku na zanikl? root/child proto pro?lo na?ten?m.

Oprava v??e ka?d? aktu?ln? kvalifikovan? segment na p?esnou mapu **aktivn?ch
replayovan?ch pieces** (profil, historie, piece, generace, p?vodn? source a span).
Retired UUID nem??e b?t znovu aktu?ln?m segmentem; chyb?j?c? analytick? autorita
je odm?tnuta. Aktivn? LINE/legacy None cesta z?st?v?. Mapa nevy?aduje, aby v?echny
archivn? replay pieces byly ve skute?n?m profilu: v?m?na cel?ho obrysu ponech?
archiv i ulo?iteln? UNRESOLVED loft. Kanonickou projekci nad?le kontroluje
st?vaj?c? aktivn?-piece validace; reference nejsou nahrazov?ny nebo opravov?ny.

Nov? c?len? regrese: ARC/CUBIC ? retired ROOT/left/right po split+inversemerge,
strip nonNone?None a pozitivn? skute?n? whole-outline replacement s archivem.
**8 PASS / 1.79 s**, Ruff a diff check PASS. [Raw](evidence/au13-core9-R01-72f7a16-targeted.json).
P?vodn?ch 419 test? z?st?v? d?kazem p?vodn?ho pinu, nikoli tohoto opravn?ho pinu.

Dal?? p?esn? kroky jsou v raw: p?ehr?t p?vodn? nez?visl? or?kula z
`papercraft-core9-review/docs/p2/implementation/evidence/au13-core9-review-own.py`
bez zm?ny o?ek?v?n?, doplnit po?adovan? konsistentn? counterfeits, ov??it relevantn?
kompatibilitu a p?edat opravu jin?mu reviewerovi. P?vodn? ?estice FAIL d?kaz?
z?st?v? zachov?na v reviewerov? worktree. UI7ef/core4f se t?mto nep?eschvaluje;
nov? u?ivatel a fyzick? P3 z?st?vaj? odd?len?.

Vlastn?k po??dal p?ed?n? pr?ce a pokra?ov?n? p???t?. Proto neb??? ?irok? sada,
??dn? native desktop ani dal?? implementace; oprava je bezpe?n? commitnut? a
?eka na pokra?ov?n?/review, ne na rutinn? vlastnick? schv?len?.

## Pokračování 17. 11. 2026 — identita spotřebitelů

Oprava spotřebitele: **3e6fbb636f57d394ca0e5433553dc394e1b9379e**, základ6064f222.
Původní checkpoint a FAIL se zachovávají; nové review uvádí integrační report.

**Empty-history hypotéza potvrzena pro celý CUBIC publisher.** Vytvořit dva
CUBIC profily, split1/3 a inverse merge, potom loft mezi aktuálními merged ID.
V detached snapshotu odebrat `profile_subdivisions`, obnovit deklarované digests
a representation přes `_bound_analysis`. Bez obnovy representation se správně
odmítne jen nesoulad cache. S konzistentní cache na6064 projdou
`validate_loft_snapshot` i skutečný `export_all` včetně SVG/PDF, ačkoli aktivní
descriptory postrádají replay autoritu. Zachovaný konkrétní chybný výstup je
[v evidenci](evidence/core9-empty-history-reproduced-output/).
Geometrie tohoto příkladu se nezměnila; prokázaná chyba je neověřená aktivní
identita. Nejde o důkaz libovolné změny tvaru či produktového workflow.

Příčina je podmíněná validace v `_source_context`: prázdný registr přeskočí
loaderův validační kontrakt, zatímco matematický helper legitimně umí samostatný
analytický descriptor. Oprava používá tentýž `_validate_profile_subdivisions`
vždy, i pro prázdný registr. Matematický helper ani legitimní legacy profil
bez descriptoru se nemění; orphan historie a UNRESOLVED zůstávají uložitelnými
stavy. Nový fallback se nepřidává.

**LINE hypotéza rovněž potvrzena na původním7c61 a již opravena72.** Root/left/right
po split+merge se `source_reference=None` původní loader přijme, nový72 odmítne.
[Čistý source-pinned subprocess replay](evidence/core9-line-source-pinned.json)
ověřil skutečně importovaný modul a shodu LF blobů project/profile_subdivision
s uvedenými piny. První pytest pokus použil jiný zdroj kvůli tests/conftest.py;
[jeho výsledek](evidence/core9-line-pre72-DISQUALIFIED.xml) je výslovně neplatný
důkaz původního zdroje. Nesmí být převzat jako původní PASS.

Před opravou: [4 FAIL +3 PASS](evidence/core9-empty-history-before.xml).
Po opravě: [120 PASS/98,75s](evidence/core9-empty-history-after.xml) přes nové
negativy, curved provenance, loft export a loft surface včetně kompatibility,
orphan/UNRESOLVED, kotev a layoutu. Po přidání explicitního LINE None:
[7 PASS/2,14s](evidence/core9-consumers-final-targeted.xml). Ruff a diff PASS.
[Vazba a hashe](evidence/core9-consumers-binding.json). Překrývající se sady
nejsou součtem unikátních testů. Desktop, nový člověk a P3 tímto nejsou ověřeny.

Skills: konstrukce zachovává skutečné zdroje bez nearest/first-child;
ověřování zahrnuje negativní publisher i přímý LINE replay; delivery připíná
konkrétní zdroj a přiznává chybný testovací vstup; UI rozsah není tímto backendovým
řezem uzavřen. Přenositelné poučení pro vlastníka queue/skills: import assert
musí být v tomtéž procesu jako pytest, nebo důkaz musí mít úplný module binding;
spuštění kontrolního pythonu před pytestem nezabrání pozdější změně sys.path.
