# PC-008 — nezávislá revize domény segmentované odvozené varianty

11.11.2026. Reviewer `/root/commands_review` není autorem domény, numerického jádra ani persistence změn. Přesný source **`95fa2c7c0e5a5d50f0763ae2a461a4e5e2821872`**, izolovaný worktree `papercraft-segmentation-domain`. Živé navazující bulk-placement změny jiného autora do revize nejsou zahrnuté.

**APPROVED_IN_LINE_SEGMENTED_VARIANT_DOMAIN_AND_PERSISTENCE_COMPONENT_SCOPE,0 otevřených BLOCKER / MAJOR.** Schválení pokrývá omezený LINE↔LINE derived-generation producent, v5 registry/load/save, výběr materiálu/referencí a jeho napojení do doménové validace. **Není schválena bulk API, nové UI, finální výrobní writer, actual D/B3 průchod, celé P2, nový uživatel ani fyzická stavba.** ARC/C vstup zůstává v tomto řezu pravdivě UNRESOLVED. Celý AC-AU12 vyžaduje následný skutečný UI→save/reopen→layout→APPROXIMATE SVG/PDF/editor důkaz.

## Přesný zdroj a provedené zkoušky

Znovu načteny AGENTS, všechny4 projektové skills a v1.2 D/AU12/AU15 i průřezové AC. [Runner](evidence/pc008-domain-review-archive.py) vytvořil fresh `git archive`, explicitní `PYTHONPATH` do jeho `src` a fresh subprocess. [Manifest](evidence/pc008-domain-review-archive-95fa2c7.json) dokládá skutečné importy `project`, `segmented_surface`, `paper` a Git text SHA-256, s výslovnou LF/CRLF konverzí. Offscreen prostředí bylo nastavené, žádný native desktop se nepoužil. Souběžně měněná produkce ve worktree se neimportovala.

- Původní domain/math/interior/material sada: **92 PASS /31.43s a1 reviewer harness FileNotFoundError**, [JUnit](evidence/pc008-domain-review-original-95fa2c7.xml). Archiv při prvním běhu neobsahoval historickou diskovou fixture `pc006a-desktop-7da2403-run04/own-model.apcraft`; nejde o produktovou regresi. Exact fixture Git blob byl doplněn a **jen tento neprovedený případ znovu prošel:1 PASS /.65s**, [raw a hash](evidence/pc008-domain-review-legacy-replay-95fa2c7.json), [JUnit](evidence/pc008-domain-review-legacy-replay-95fa2c7.xml). Původní FAIL se nepřepisuje a celý soubor se kvůli němu zbytečně neopakoval.
- [Vlastní případy](evidence/pc008-domain-review-own.py): **19 PASS /6.38s**, [JUnit](evidence/pc008-domain-review-own-95fa2c7.xml), plus jediný přidaný nezávislý normal-field test **1 PASS /.80s**, [raw](evidence/pc008-domain-review-own-normal-95fa2c7.json), [JUnit](evidence/pc008-domain-review-own-normal-95fa2c7.xml). Jde o20 různých vlastních případů ve dvou cílených bězích, nikoli full-suite nebo native/human důkaz.

## Nezávislá racionální předloha

[Spustitelný witness](evidence/pc008-domain-review-witness.py), [raw](evidence/pc008-domain-review-witness-95fa2c7.json), vytváří jiný původní cíl **`S(u,v)=(16u,8uv,12v)`** než povinná40/20/30 fixture. Analytický determinant je−1536 a pole normál plyne přímo z `S_u×S_v=(96v,−192,128u)`. Expected nevolá segmentační generátor ani jeho helper pro dosazení bodu nebo normály.

Při limitu.26 paper mm vzniklo8 buněk,16 samostatných trojúhelníků a18 paired cut seam. Raw celoplošná mez je přesně1/4mm; skutečný finite material-frame reserve ji zvýší na přibližně **.25000000000000177mm**, stále pod.26. Původní cíl po potvrzení zůstává **REJECTED**, tisková generace má **APPROXIMATE**. Snapshot má16 materiálových dílů a17 konstrukčních ploch včetně původní reference, rozložených ručně8+8 na dvou stránkách.

Vlastní orákulum rekonstruovalo skutečné generované body přesně racionálně z uložených binary plane origin/u/v a skutečných2D profile bodů. Barycentra i midpointy triangulací byly porovnány s analytickým S ve stejném UV; squared distance je uvnitř reportovaného actual material bound. Chyba je prokazatelně nenulová, nesmí se přejmenovat na exact původní plochu. Nezávislé skutečné material-plane normály mají kladný přesný dot se source normálou a jejich vertex/centroid úhly jsou pod reportovanou mezí. Tato bodová normal zkouška je regresní orákulum; nenahrazuje celointervalový důkaz základního matematického komponentu.

## Doména a skutečný finite material frame

Preview je detached a nealokuje application UUID. Potvrzení neadoptuje předaný mesh nebo callerem změněný certificate; znovu odvozuje candidate z aktuální source binding a parametrů a porovnává digest potvrzeného náhledu. Kandidát přebírá pouze podporovaný, CERTIFIED LINE↔LINE matematický výsledek a nepovýší neEXACT zdroj na EXACT. Přísnější/nesplnitelný limit a nepodporovaný source nezanechají částečně vytvořené děti.

Každý actual material child má vlastní planar profil/rovinu, surface, paper frame a part. Konstrukce jeho finite plane se porovnává se skutečnými raw3D triangle vertices, ne s idealizovanou dokonale kolmou bází. Racionální reconstruction reserve se přes common-pose operator přičte k source→raw deviation; raw-edge versus actual-flat length reserve je samostatná. Normal offset používá skutečné rekonstruované hrany a kladnou orientaci; common pose condition reserve kryje změnu úhlů. Původní rovinné/number/layout guardy se nevypínají.

Source fingerprint zahrnuje actual geometry, scale, korespondence, source UUID a prostorové umístění. Změna revision nebo názvu bez změny geometrie sama nezruší potvrzení, skutečná změna bodu/roviny/pózy/scale jej zruší i bez zvýšení revision. Vlastní kombinace benigní name/revision versus skutečný bod prošla odpovídajícím APPROXIMATE→STALE výsledkem. Stale zdroj se neregeneruje automaticky pod existujícími autorskými stránkami.

## Uzavřený registr a neměnné generace

v5 zavádí explicitní `segmented_variants`; vlastní variant UUID, triangle UUID, profile/surface/part/vertex/edge identity a provenance jsou kontrolované proti znovu vytvořenému kanonickému candidate. Pouhá shoda uloženého hashe není autorita. Vlastní útočník po změně certificate, child geometry/hash, seam edge, duplicate UUID, generation-cycle nebo extra mapping field přepočetl generation digest; **všech6 případů loader stále odmítl**.

Variant source binding/fingerprint a generation digest zůstávají detached. Každý child key a parameter-UV mapping je jednoznačně svázaný se skutečným původním patch/source. Vlastní kontrola všech seam uses našla skutečné stabilní profilové edge UUID a přesně opačné UV orientace obou použití. Změněný child profil po recompute nezískal falešnou potvrzenou chybu: status zůstal UNRESOLVED a snapshot se odmítl. Materiálová vazba nesmí podvrženým novým hashem sám sebe potvrdit.

Aktualizace tvoří novou generation s vlastními identitami a odkazem na předchozí; staré generace a jejich ruční polohy/zámky se zachovávají. Print selection se mění odděleně od source/certificate. Cyklus historie, neplatná předchozí vazba nebo více selected generací jednoho cíle se odmítá. Existující autorovy testy této aktualizace a následného návratu byly skutečně spuštěny, nejde jen o analytické přečtení.

## Tiskový výběr nepřekrývá jiné chyby

Úplný projekt se validuje **před** vytvořením tiskového pohledu. Selected generation nahradí pro tisk pouze vlastní původní target; původní konstrukce zůstává reference a inactive generation nejsou coincidentní dodatečný materiál. Snapshot výslovně deklaruje expected material part/surface IDs, selected variant IDs, reference targets, všechny konstrukční plochy a inactive variant surfaces. Na každém odvozeném partu je APPROXIMATE režim vůči targetu a samostatně EXACT_PLANAR_TRIANGLE pro vystřihovaný core.

`print_material_view` zachovává validaci úplného closed registru a filtruje jen výslovný materiálový výběr. Stale/unresolved selected variant se nejprve promění v blokující issue. Direct bend/clearance panel používá stejný selected material jako snapshot, nikoli navíc původní reference. Spoj tiskového dílu s netisknoucí referencí je zakázán; external vazby vyžadující neprokázané přemapování na novou generaci se odmítnou.

Vlastní původně platný derived snapshot byl doplněn jiným neEXACT loftem: druhý loft zůstával materiálem a snapshot se správně odmítl. Nejde tedy o obecný flag „ignorovat neEXACT“. Návrat k původnímu targetu rovněž nedělá z jeho REJECTED stavu hotový exact díl. Vyřazení z tisku je skutečná autorova volba konkrétní generace, nikoli globální potlačení chyb.

## Konečný embedding proof

Podporovaný pozitivní důkaz hledá jednu skutečně nedegenerovanou přesnou racionální projekci raw triangle graphu. Pair separation zahrnuje pozitivní průnik, nechtěný dotyk i soulad deklarovaných společných UV nodes. Vlastní16triangle witness používá skutečnouXZ projekci a120 párů. Dvojice duplicitních triangles nebo dotyk bez společné UV identity se ve vlastních negativních případech neproměnily v CERTIFIED; správně společná UV hrana se připustila.

Párů/projekcí je konečný globální rozpočet200000 a doména nejvýše512 triangles; vyčerpání nevrací částečný úspěch. Vlastní nulový limit přímého embedding vstupu vrátil typed UNRESOLVED, nikoli free. Pokud žádná podporovaná projekce nestačí, jde o konzervativní odmítnutí; neprohlašuje se obecný3D intersection solver.

**Scope pozitivního embedding důkazu je pravdivě omezen na raw triangle graph před common pose.** Actual finite material-frame perturbace má samostatné metrické/normal/deviation bounds. Tato certifikace nenahrazuje physical thickness/clearance, skutečné lepení ani globální slib fyzické sestavitelnosti. Žádný takový physical PASS zde není udělen.

## Uložení, undo a staré projekty

Vlastní generace prošla ručním dvoustránkovým layoutem, snapshotem, save a load s přesnou shodou stavu. Controller Undo/Redo zachoval původní target i potvrzenou generaci; neplatné následné potvrzení nevymazalo redo ani neposunulo původní state. Starší schema4 se načte jako chráněná copy a původní soubor nelze přepsat ani po příkazu/undo. Vlastní unknown top-level registry, vložená v5 variant capability do v4 a nedeklarovaný triangle parametr ve starém formátu byly odmítnuté, původní bytes zůstaly stejné.

To je komponentová persistence kompatibilita, nikoli hotový nový UI copy/SaveAs průchod nebo uzavření všech migračních AC. Norma a původní důkazy nejsou měněné; žádná nevratná migrace se neprovedla.

## Skills a předání

Construction skill se projevil zachováním původního cíle a skutečných samostatných dílů/paired cuts; verification v jiném racionálním source orákulu, exact finite-frame rekonstrukci, forging/pair-budget negativech a import pinu; UI skill v požadavku na opravitelný stale/UNRESOLVED zdroj a budoucí skutečný průchod; delivery v oddělení komponenty od celého D a nezávislé revizi jiného autora. Dosud neprovedený novice/physical/digital end-to-end důkaz zůstává NOT_RUN.

Reviewer vytvořil pouze tuto zprávu a vlastní raw evidence. Žádná produkční změna, staging, commit, merge/push nebo desktop. **Bulk placement není v95fa2c7 a toto schválení se na něj nepřenáší.** Sjednocený UI/writer přírůstek a actual D/B3 přejímka vyžadují vlastní připnuté ověření a nezávislou revizi.
