# C — autorské ovládání kruhových chlopní

## Opravy nezávislé revize CUI01–CUI04

Zdroj oprav: **`e1c06f5b068880ac22b28516ce69c66aee32603d`**. Následující původní předání a jeho zdrojové vazby jsou historické a zůstávají zachované.

- **CUI01:** odmítnutý C05 preflight vrátí viditelnou volbu sady i checkbox do skutečného autorského stavu. Neplatný rozepsaný rozměr, dosavadní výběr a dokument zůstávají zachované.
- **CUI02:** hlavní vedení rozlišuje skutečně podporovaný kruhový plášť a aktuální veřejný stav jeho sady. Digitálně doložená aproximace již nedostane protichůdné tvrzení, že spoj nemá ověření. STALE/UNRESOLVED/vypnuté sady mají vlastní dosažitelný další krok; fyzické ověření stále patří P3.
- **CUI03:** odstraněný vlastník bezpečně zneplatní návrh, zakáže výpočet/potvrzení a nabídne zavření a opětovný výběr. Pozdní odpověď workeru se nepoužije. Jde o deterministickou komponentovou zkoušku source fence; modální dialog běžnou uživatelskou destrukci vlastníka nepovoluje, proto nejde o důkaz nativního pádu.
- **CUI04:** slot mimo snížený počet nebo ve vypnuté sadě má vysvětlenou zakázanou přepínací akci. Label nemůže slibovat opačný úkon než uložený override. Klik ani přímé volání nemění počet, zapnutí sady či uloženou individuální volbu.

[Připnutý cílený JUnit](evidence/pc007b-curved-authoring-ui-review-fixes.xml): **34 PASS / 30 deselected / 36,25 s** na uvedeném source pinu, offscreen. Běh zahrnuje 8 vlastních cílených případů, 6 beze změny převzatých kvalifikovaných případů nezávislého review a 20 existujících curve/loft/segmentation workspace regresí. Počty se nesčítají s původními 47 ani s průběžnými běhy. [Nová source/import vazba](evidence/pc007b-curved-authoring-ui-review-fixes-binding.json) patří pouze tomuto běhu. Ruff a diff-check PASS.

První vlastní CUI03 harness chybně volal neexistující metodu místo veřejné funkce `editing.delete_material_part`; jeho [raw 2 FAIL / 4 PASS](evidence/pc007b-curved-authoring-ui-CUI01-CUI03-initial-harness.xml) zůstává zachován a není produktovým nálezem. Kvalifikované cizí reprodukce se neměnily. Poslední CUI02 negativní UNRESOLVED ověřuje mapování veřejného stavu pomocí dependency stubu; pozitivní i STALE případ používají skutečný producer.

Skills se uplatnily konkrétně: UI C05/SK013 na odmítnutém přepnutí a latentním/effective stavu, konstrukce na oddělení digitální aproximace od fyzického spoje, verification na vlastním i nezměněném cizím orákulu a source/import vazbě, delivery na odděleném zdrojovém commitu a předání oprav jinému reviewerovi. Toto předání ještě neuděluje nezávislé schválení; nativní integrační průchod provede root. Nový uživatel **0 / NOT_RUN**, fyzický P3 **NOT_RUN**.

UI source freeze: **`62cb8bc3d84c5c3edf0c7faf08965ea5eef4b625`**. Samostatná větev `revival/p2-curved-authoring-ui`; integrační owner slučuje výsledek až po cizím review. Backend závislost **`80493e6e9e48cb22548b9a55c2116d850e8e73f3`** je při tomto předání provizorní a má vlastní nezávislou revizi. Autor UI tím neschvaluje C matematiku ani producer. Schema ani exporter tento přírůstek nemění.

## Funkční průchod

1. Vlastní kruhové profily a jejich umístění vytvořte existujícími kreslicími nástroji, plášť příkazem **Plocha mezi dvěma profily**. Disk příjemce musí být skutečná samostatná rovinná plocha, případně s vlastními otvory. Nevzniká zde dům ani automatické víko.
2. Vyberte plášť a **Dělené chlopně kruhového okraje…**. Okraj nese jméno původního profilu; příjemce nese jméno a číslo P. Vyberte kontaktní stranu; popisek současně vysvětlí vztah k potisku. Použitý okraj nelze znovu obsadit druhou sadou.
3. Zadejte počet a šířku nebo mezeru, hloubku a nelepivý pás. Jsou to **papírové mm**. Náhled sestavy používá **modelové mm**. Pokročilé digitální meze jsou rozbalitelné; nezaměňují se za fyzickou pružnost papíru. Známý numerický příklad: 12, šířka 0,24, hloubka 9,5, relief 0,6, min. plocha 1 mm², polohová mez 0,01 mm, geometrická deformace 1 %, výstupní rezerva 0,000001 mm. Nejde o obecné doporučení fyzické stavby.
4. Vyberte **Chlopeň 1**, vypněte ji; pro **Chlopeň 2** zadejte posun vrcholu 0,01 mm. Počet lze snížit a obnovit bez ztráty původních slotů/overrides. Existující sady používají skutečná UUID, zobrazená jako srozumitelná pořadová čísla.
5. **Spočítat aktuální náhled / Ctrl+R**. Jeden worker má oddělený projekt a veřejnými add/update/set/recompute příkazy vypočte skutečný materiál. GUI dál reaguje; čeká nejvýše poslední další požadavek. Změna hodnot, zdroje, Cancel nebo zavření zneplatní starý výsledek.
6. Vlevo jsou skutečné CUT/TABS/GUIDES a vybraná chlopeň v papírovém rámci. Vpravo skutečné zdrojové tělo/příjemce a zobrazovací hinge/lepicí oblast. Zobrazení není důkaz; ověření pochází z aktuálního produceru. Nepodložený stav nevykresluje zdánlivě aktuální lepicí plochu a nelze jej potvrdit jako ověřený.
7. **Uložit návrh chlopní** zapíše pouze autorské parametry/overrides v jednom vratném příkazu. Nová sada dostane nové živé identity; index označuje pouze konkrétní nově vytvářený slot, nikdy nejbližší geometrii. Do dokumentu se nekopíruje preview certifikát, materiál ani projektový stav. **Celý vlastník je STALE, následuje výslovný přepočet Ctrl+R v hlavním okně.**
8. Nedoložený návrh lze výslovně uchovat, opravit v UI a znovu ověřit; export zůstává blokovaný. Položka kruhové chyby vybere přímo její sadu a vlastníka. Papír lze opravit přímo v dialogu; tato globální změna je staged, zrušení nic nezmění a potvrzení ji uloží společně s návrhem jako jedno Undo.

## Kontext a bezpečný návrat

Výběr jiné sady vybere jejího skutečného vlastníka, strom/vlastnosti/3D i papír; stará hrana a vztah se uvolní a bod se převede na profil nového vlastníka. Volba tiskového materiálu se nemění. Při výběru jiného samostatného profilu či plochy se kontext sady zruší. Přepnutí aktuální chlopně používá její skutečný slot. Vypnutí je samostatný Undo příkaz; neaktuální materiál ihned ztratí 2D/3D overlay, Undo vrací původní identitu a platný výsledek.

SK013/DU01 se uplatnil na dvou nezávislých vlastnících. Zkouška odhalila, že `_sync_selection` mohl po surface vybrat ještě source-profile child ve stromu. Oprava upřednostní surface, je-li vybraný; samostatný profil zůstává samostatným kontextem. Není to nový vizuální redesign.

C05 se uplatnil na pending numeric input včetně focus-out automatické korekce Qt: neplatný raw vstup se neztratí, platný se vyhodnotí před preview/apply. Rozepsaný vrchol při změně slotu patří původnímu slotu. Tipy jdou vypnout i obnovit; diagnostika a fyzické omezení zůstávají viditelné.

## Ověření a meze důkazu

Všechny běhy jsou **`QT_QPA_PLATFORM=offscreen`** s vlastním `PYTHONPATH`. [Závěrečný JUnit](evidence/pc007b-curved-authoring-ui-targeted.xml) a [source/import binding](evidence/pc007b-curved-authoring-ui-binding.json) dokládají přesný source SHA, hashe a skutečně importovaný checkout. **47 PASS / 0 SKIP / 43,40 s**, z toho 27 vlastních C widget/host případů a 20 regresí curve/loft/segmentation workspace. Ruff a diff-check PASS. Počty se neagregují s překrývajícími historickými běhy; `own.xml` je zachovaný dřívější dílčí vývojový běh, nikoli nový důkaz finálního pinu.

Vlastní skutečné producer průchody: první/druhý okraj válce, první/druhý okraj kužele 10→20 s H=√800, téměř válcový 10→10,000001, off0/custom-tip1, explicitní přepočet, Undo/Redo, save/open, oprava neznámého papíru. Negativy: nesprávná kontaktní strana, velká šířka, neznámý papír, source/draft změna, Cancel, zavření, source fence po přijetí, chybná odpověď a bounded pending queue. Unit dependency callbacky slouží jen k cíleným concurrency/response negativům, nikoli k důkazu C geometrie.

Plný komponentový řetězec command→recompute→Undo/Redo→save/open prošel pro první válcový okraj s off0/tip1. Ostatní uvedené tělové varianty prošly skutečným výpočtem náhledu přes dialog. Tato rozlišení nenahrazují níže čekající celý nativní C průchod.

Použité skills: konstrukce — skutečný příjemce/strana/materiál a otevřený plášť; UI — kontext, čísla, oprava, volitelná pomoc a Undo v právě dodaném řezu; verification — skutečný producer oddělený od stubů a 3D display, import/source binding; delivery — izolované vlastnictví, přiměřené regrese, zdrojový freeze a předání jinému reviewerovi.

**Čeká:** nezávislé review UI commitu a backend consumeru, rootův skutečný native UI→save/reopen→rozvin→ruční stránky→SVG/PDF a editor pro celý C. Tyto offscreen testy nezačínají celé kreslení C od prázdného modelu. Nejsou ani testem nového uživatele: **AC-US08 0 účastníků / NOT_RUN**. Fyzická sestavitelnost/pevnost je **P3 / NOT_RUN**. Zdrojová native strain, pozice/délka/plocha skutečných SVG/PDF a fyzický výtisk jsou odlišné důkazy. Tento balík není předání celého P2 ani jeho přijetí.
