# PC-007A — nezávislé review úzké V4 alokace rezerv

Reviewer `/root/authoring_independent_review`, 11.11.2026. Není autorem komponenty, opravy ani diagnostiky. Přesný source **`7ee42b397e0491bff87a0f76b7c07850ef5b56c3`**, izolovaný worktree `papercraft-loft-coalescing`. Východisko je jiným reviewerem [schválené730cb28](PC007A_LOFT_COALESCING_REVIEW.md); toto review neposouvá jeho schválení na celé B nebo interoperabilitu.

**Verdikt: APPROVED_IN_V4_COALESCING_ALLOCATION_DELTA_SCOPE.** Žádný otevřený zásadní nález. Schválený je konkrétní delta interních rezerv, metadata, V4 staleness a read-only diagnostika. **LX01 jako skutečný editorový průchod zůstává PENDING; ani toto review, ani původní normativně malý error starého runu z něj nedělá PASS.** Nový integrovaný native/editor výsledek, celé PC-007A/P2, novice a P3 mají samostatné přejímky.

## Source a opakované ověření

[Izolovaný Git archiv/bytes](evidence/pc007a-loft-coalescing-v4-review-source.json), [skutečné importy a SHA-256](evidence/pc007a-loft-coalescing-v4-review-imports.json). Běhy importují právě archive7ee, ne sdílený editable checkout. Vykonatelná merge/reverse/restriction/cap matematika se vůči730 nezměnila: rozdíl v produkci jsou2 default reserve hodnoty,4 popisná metadata pole a V4 capability string. Předchozí review-only commit a3ef3d6 má samostatně zachovanou evidenci.

- **138 cílených autorových regresí PASS/37.12s**, [JUnit](evidence/pc007a-loft-coalescing-v4-review-author-7ee.xml): compaction, native curves, source domain, performance a nová diagnostic jednotková orákula.
- **13 původních nezávislých orákulí předchozího review PASS/0.84s beze změny**, [JUnit](evidence/pc007a-loft-coalescing-v4-review-previous-own-7ee.xml). Zachovaly unequal intervals, exact polynomial restriction, konstruktivní globální length svědek, current-cache poison, reverse a fallback.
- **14 nových vlastních případů PASS/16.94s**, [skript](evidence/pc007a-loft-coalescing-v4-review-own.py), [JUnit](evidence/pc007a-loft-coalescing-v4-review-own-7ee.xml), včetně skutečného B1 replay. Ruff4 dotčených source/test souborů PASS; live text je ověřeně totožný s přesným archivem po výhradně LF/CRLF normalizaci. Počty nejsou vydávané za další unikátní full-suite testy.

## Proč větší merge rezerva nezvětšuje původní rozpočet

Default merge position je nyní0.001 paper mm a **globální délka každé celé profile side**0.006mm. Původní total source→coarse position i global-side length limit zůstává0.008mm. Skutečné operace používají přesné Fraction hodnoty dodaných binárních čísel:

`effective_position=min(.001,total_position−source_to_fine_position)`

`effective_global_side_length=min(.006,total_length−source_to_fine_length)`

Poziční merge chyba je maximum nad bloky. Délka je součet všech příspěvků přes fine intervaly, coarse bloky a patche dané strany; každá lokální alokace má disjunktní podíl z globálního fine-count počtu. Nadále se přičítá původní source→fine chyba, nic se nezamění za menší coarse-only údaj. Závěrečné ven zaokrouhlené published totals se znovu porovnají s původním celkovým limitem. Pole effective allocation jsou popisné float hodnoty, nikoli nové matematické upper boundy nebo nový per-patch limit.

Obě celé profile side mají vlastní globální limit; sumář obou stran zůstává zvlášť a není tímto nepravdivě označen za jednu další0.008 rezervu. Toto je původní contract schválené komponenty, nikoli změna jeho významu. Actual topology, intrinsic-source area a následná serializace zůstávají další nezávislé kontrolní povinnosti calleru.

Vlastní hraniční případy ověřily zbývající exact dyadické rezervy2^-30,2^-20,2^-10 a1/4. Metadata effective limits odpovídala přesně očekávanému min; total proof nikdy nepřekročil skutečný původní budget. Při přesném vyčerpání position nebo length rozpočtu zůstal celý původní proved native objekt s NOT_APPLIED. Při candidate/comparison cap1 také zůstal kompletní původní objekt. Opakovaný merge již sloučeného reportu neutrácí reservy znovu; požadavek slabšího/nevyhovujícího certifikátu skončil odmítnutím.

Pro nový default global length byl použit samostatný8patch svědek: skutečné64 malé cubic humps na každé straně mají zvětšenou y-variaci. Pokud by všechny patche byly sloučené na jedinou rovnou C, nezávislá dolní mez skutečné změny délky je **12072·2^-20mm≈0.0115128mm**, větší než celých0.006mm. Algoritmus proto nesloučil vše do jedné C na patch; přesné sečtení patch reportů odpovídalo globálnímu field a zůstalo≤0.006. Nestačilo max lokálních chyb ani0.006 pro každý patch.

## V4 a zachování autorovy práce

Sdílený paper contract končí `BOUNDED_COALESCED_CUT_V4`; nadále používá dříve nezávisle přezkoumanou PF-01 load/stale cestu. Vlastní V2 i V3 soubory se otevřely se STALE, nezměněným původním CUT a blokovaným snapshotem. Výslovný recompute zachoval source profiles/surfaces, part identity, frame, placement a oba locks; původní bytes souboru zůstaly. Není prováděna tichá migrace, změna měřítka nebo přesun autora.

Pod aktuálním V4 se stejně velký posunutý CUT nevydává za pouhou starou reprezentaci: po reload zůstane current vzhledem ke zdroji, ale actual geometry comparison jej označí INVALID_CACHE a snapshot odmítne. Nespoléhá se na digest nebo plochu samotnou. Přezkoumané138 regrese zachovaly source/C/ruling/provenance kontroly předchozího730.

## Vlastní backend replay skutečného B1

[Raw](evidence/pc007a-loft-coalescing-v4-review-actualB1.json) načetl původní native73f3437 soubor SHA **`5e183f24424eebc0ce33c9fddf99e37cee7af8ac9d596c3bba1b4fac6dcd3f35`** pouze přes archive7ee. Backend replay není nový UI nebo editorový důkaz.

| Kontrola | Nezávislý výsledek |
|---|---|
| Před/po explicitním recompute |69→21 CUT commands, z toho16C; křivky nejsou nahrazené tětivovým meshem |
| Source/frame/layout/identity/čítače |beze změny; původní soubor byte-for-byte zachovaný |
| Total source→coarse position |0.0004685390077743519mm <0.008mm |
| Total source→coarse global-side length |0.0035289474937882856mm <0.008mm |
| Actual native topology a frame area |VALID / CERTIFIED, validate_layout issues[] |
| Vlastní exact Fraction-Green plocha actual CUT |1364.046989175902mm² |
| Vlastní intrinsic source očekávání |interval≈[1364.04639361918,1364.04639362232]mm² |
| Nezávislá horní mez actual area rozdílu |≤0.0005955568mm² < původní0.01mm² |
| Uložení kopie/reopen |přesná shoda aktuálního projektu |
| Current V4 equal-area poison |INVALID_CACHE; snapshot blocked |

Actual native area byla spočtena vlastním power-polynomial Green integrálem dodaných binary controls, nikoli produkčním area helperem nebo číselným expected z manifestu. Vlastní source očekávání používá half-angle integrál gotických R32.5/c12.5/H10/k6/5 profilů s80digit Simpsonem4096 a celointervalovým fourth-derivative remainderem; skutečný model100× a binární scale0.01 jsou aplikované jako přesný racionální faktor. Přidaná angle/rounding rezerva je mnohem menší než0.01, nezvětšuje normativní limit. Širší caller certifikát source area dává konzervativní maximum≈0.000645137mm² a také zůstává pod původní mezí.

## Read-only diagnostika a neuzavřený LX01

Nový `test_loft_editor_diagnostic.py` nic nepublikuje ani neřídí editor. Normalizuje původní decimal path tokeny stávajícím exact relative parserem a počítá samostatný Green integrál. Známý obdélník a polynomial arch mají vlastní analytická očekávání; test zachovává i rozdíl `1.00000000000000001`. Otevřené FOLD paths jsou správně označené pouze jako open-path integral a nemají material-area PASS.

Reviewer read-only přehrál diagnostiku přímo z archivu7ee na zachovaných actual native73 editor input/output: [raw](evidence/pc007a-loft-coalescing-v4-review-old73-diagnostic.json). Původní69command CUT má skutečný maximum coordinate drift **`92610227/2000000000000 =0.0000463051135mm`**, tedy stále FAIL vůči původnímu strict2e-5 same-path check. Green area změna je≈0.00000975636mm². Menší hodnoty než0.01 nejsou důvod přeznačit strict FAIL na PASS. Tato triage porovnává vstupní/uložený editorový path; sama nenahrazuje celý source→actual area důkaz.

[Git audit](evidence/pc007a-loft-coalescing-v4-review-acceptance-unchanged.json) potvrzuje byte-for-byte shodu `tools/authoring/editor_probe.py`, normativní akceptace v1.2 a původního verification dokumentu mezi730 a7ee. Žádná editor preference, AC ani harness tolerance se neměnila. Reviewer pouze četl zachované soubory; žádný desktop, Qt okno nebo skutečný Inkscape proces nebyl při tomto review spuštěn.

**LX01 musí uzavřít nový skutečný native→save/reopen/layout→SVG/PDF→editor průchod integrovaného V4 zdroje.** Menší command count a platný mathematically bounded fit tuto další serializaci negarantují. NOT_APPLIED fallback navíc znamená zachování původního proved fitu, nikoli automatické splnění nově zadaného přísnějšího total nebo editorového checku. Root má tyto následné důkazy nadále PENDING mimo tento komponentní verdict.

Všechny4 skills a AGENTS byly skutečně čteny: konstrukce chrání source/C/ruling a author frame; verification používá jiné global-length/area očekávání a přesný archive import; UI ponechává opravitelné staré soubory a skutečný editor jako samostatný průchod; delivery uzavírá jen připnutý ověřený scope. Nedochází k oslabení plného A/B/C/D, AU19, novice0/NOT_RUN nebo fyzického P3. Produkce, staging a Git historie zůstaly reviewerem beze změny; vlastní report/raw nejsou commitované.

## Dodatek — úzké review SK-012 a jeho skutečného dalšího použití

Reviewer skutečně načetl poslední odstavec verification skillu a celý SK-012 ledger z aktuálního `papercraft-loft-integration`, metadata source **`4f738c4e660a30e4027af71025cd939213712cc9`**. [Záznam zdroje textu a review](evidence/pc007a-loft-coalescing-v4-review-SK012.json) potvrzuje shodu skutečně čteného skill textu s tímto Git pinem po výhradně EOL konverzi. Starší kopie skillu v samotném coalescing branchi není vydávaná za tuto novou radu.

**SK-012 text: APPROVED_IN_SCOPE.** Rada správně požaduje verzovat změněnou certifikovanou kanonickou reprezentaci/capability a odděleně ověřit old-cache staleness i current-cache poison. Zachovává původní source, kotvu/layout a explicitní přepočet, neoslabuje normy ani nedovoluje přijmout stejnoplochou vadnou cache. Tento význam se týká změny algoritmu/formátu/garancí odvozené reprezentace; není to požadavek zvyšovat verzi programu při každé běžné editaci parametru modelu, kterou již pokrývá actual-source digest.

**Další použití na V3→V4: NARROW_TECHNICAL_TRANSFER_VERIFIED.** Autor doložil načtení rady a její uplatnění; tento reviewer následně nezávisle zopakoval obě old-V2/V3 STALE negativní cesty, current V4 poison, skutečný uložený B1 a zachování jeho identity/frame/layout i save/reopen. To je konkrétní provedený technický přenos z PF-01 do nové změny capability, nikoli pouze formální seznam skillů. Původní ledger stav NOT_RUN/PENDING před tímto review je historický; integrační owner může nyní navázat tento úzký důkaz.

Obecná účinnost rady, původně plánovaný další transfer do **PC-008 persistence**, nový uživatel, native/editor interoperabilita a physical proof tím nejsou prokázané. Tyto širší stavy zůstávají pending/NOT_RUN podle jejich vlastních důkazů. Reviewer skill ani ledger neměnil a tento dodatek nezakládá další produktovou bránu.
