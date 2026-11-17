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


## Pokra?ov?n? 17. 11. 2026 ? identity spot?ebitel?

Oprava spot?ebitele: **3e6fbb636f57d394ca0e5433553dc394e1b9379e**, z?klad6064f222.
Nez?visl? review zat?m PENDING. P?vodn? checkpoint a FAIL se zachov?vaj?.

**Empty-history hypot?za potvrzena pro cel? CUBIC publisher.** Vytvo?it dva
CUBIC profily, split1/3 a inverse merge, potom loft mezi aktu?ln?mi merged ID.
V detached snapshotu odebrat `profile_subdivisions`, obnovit deklarovan? digests
a representation p?es `_bound_analysis`. Bez obnovy representation se spr?vn?
odm?tne jen nesoulad cache. S konzistentn? cache na6064 projdou
`validate_loft_snapshot` i skute?n? `export_all` v?etn? SVG/PDF, a?koli aktivn?
descriptory postr?daj? replay autoritu. Zachovan? konkr?tn? chybn? v?stup je
[evidence/core9-empty-history-reproduced-output](evidence/core9-empty-history-reproduced-output/).
Geometrie tohoto p??kladu se nezm?nila; prok?zan? chyba je neov??en? aktivn?
identita. Nejde o d?kaz libovoln? zm?ny tvaru ?i produktov?ho workflow.

P???ina je podm?n?n? validace v `_source_context`: pr?zdn? registr p?esko??
loader?v valida?n? kontrakt, zat?mco matematick? helper legitimn? um? samostatn?
analytick? descriptor. Oprava pou??v? tent?? `_validate_profile_subdivisions`
v?dy, i pro pr?zdn? registr. Matematick? helper ani legitimn? legacy profil
bez descriptoru se nem?n?; orphan historie a UNRESOLVED z?st?vaj? ulo?iteln?mi
stavy. Nov? fallback se nep?id?v?.

**LINE hypot?za rovn?? potvrzena na p?vodn?m7c61 a ji? opravena72.** Root/left/right
po split+merge se `source_reference=None` p?vodn? loader p?ijme, nov?72 odm?tne.
[?ist? source-pinned subprocess replay](evidence/core9-line-source-pinned.json)
ov??il skute?n? importovan? modul a shodu LF blob? project/profile_subdivision
s uveden?mi piny. Prvn? pytest pokus pou?il jin? zdroj kv?li tests/conftest.py;
[jeho v?sledek](evidence/core9-line-pre72-DISQUALIFIED.xml) je v?slovn? neplatn?
d?kaz p?vodn?ho zdroje. Nesm? b?t p?evzat jako p?vodn? PASS.

P?ed opravou: [4 FAIL +3 PASS](evidence/core9-empty-history-before.xml).
Po oprav?: [120 PASS/98,75s](evidence/core9-empty-history-after.xml) p?es nov?
negativy, curved provenance, loft export a loft surface v?etn? kompatibility,
orphan/UNRESOLVED, kotev a layoutu. Po p?id?n? explicitn?ho LINE None:
[7 PASS/2,14s](evidence/core9-consumers-final-targeted.xml). Ruff a diff PASS.
[Vazba a hashe](evidence/core9-consumers-binding.json). P?ekr?vaj?c? se sady
nejsou sou?tem unik?tn?ch test?. Desktop, nov? ?lov?k a P3 t?mto nejsou ov??eny.

Skills: konstrukce zachov?v? skute?n? zdroje bez nearest/first-child;
ov??ov?n? zahrnuje negativn? publisher i p??m? LINE replay; delivery p?ip?n?
konkr?tn? zdroj a p?izn?v? chybn? testovac? vstup; UI rozsah nen? t?mto backendov?m
?ezem uzav?en. P?enositeln? pou?en? pro vlastn?ka queue/skills: import assert
mus? b?t v tomt?? procesu jako pytest, nebo d?kaz mus? m?t ?pln? module binding;
spu?t?n? kontroln?ho pythonu p?ed pytestem nezabr?n? pozd?j?? zm?n? sys.path.
