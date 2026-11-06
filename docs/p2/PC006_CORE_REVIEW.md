# Průběžná nezávislá revize PC-006 — core

**Závěrečný scoped verdikt: APPROVED_IN_SCOPE** pro core CODE **`2a341e1e64a26d5b1b4c1cde46dfb9603f964069`**. Všechny čtyři konkrétní nálezy jsou opravené a nezávisle uzavřené. Schválení se týká pouze doménového/persistenčního základu PC-006; UI, controller, papírový engine a exporty nejsou tímto schváleny a nejde o digitální přijetí celého PC-006 nebo P2.

Datum: 6. listopadu 2026. Reviewer: samostatný agent `integration_review`, odlišný od implementátora geometrie i integračního ownera. BASE: `6eb8977011854b242ab1dac8ea929e262e3b9563`; revidovaný CODE: **`135a3a1d4fb7da1c74adf33574bde58e5fd9f0e7`**. Autorizační commit `af84120` správně zaznamenává skutečné přijetí kontraktu v1.1/B/legacy a rozsahu PC-006–010 vlastníkem. Toto přijetí se nezaměňuje za hotový digitální produkt.

## Rozsah a vlastní ověření

Přečteny `domain/model.py`, `domain/project.py`, společné chyby a nové testy domény/persistence. Importy a testy proběhly v samostatném detached worktree přesně na CODE; souběžné untracked soubory application/UI/export jiných agentů nebyly zahrnuty ani měněny. Vlastní orákulum nepoužívá produkční helper k výpočtu expected. Při jeho importech je Qt výslovně zakázáno import guardem.

- `.venv\Scripts\python.exe -m pytest tests/panel/test_domain.py tests/panel/test_project_io.py -ra --junitxml=<shared-root>/docs/p2/evidence/pc006-review-tests.xml`, cwd pinned worktree, vypnutý plugin autoload: **48 PASS / 0 FAIL / 0 SKIP**, exit 0, pytest 0.86 s. Jde o nové nezávislé spuštění existujících 48 core testů, nikoli dalších 48 unikátních scénářů.
- `.venv\Scripts\python.exe docs/p2/evidence/pc006-review-checks.py <pinned-worktree>`: exit 0, vlastní pozitivní/negativní kontroly a zvlášť pozorování reprodukovaných vad. Exit 0 tohoto sběrače neznamená zelený produkt. [Zdroj](evidence/pc006-review-checks.py), [výsledky](evidence/pc006-review-results.json), [JUnit](evidence/pc006-review-tests.xml).

| Vlastní kontrola | Výsledek |
|---|---|
| Jiný dům 12×8 m, stěna 5 m, převýšení 3 m, 1:100 | 8 povrchů, plocha bez podlahy/chlopní 34400 mm², každá střecha 6000 mm²; analytická sklonová délka 50 mm |
| Ekvivalentní jednotky | 12 m / 1200 cm / 12000 mm vždy 120 mm papírové délky |
| Dva rodiče a místní transformace | Nezávislé odvození `[x,y,z] → [z,x,y]+[84,212,333]`; největší odchylka 4.55e-13 model mm, plocha zachována |
| Neplatný rozměr | NaN, Inf, záporná/nulová délka, detail 1e-8 mm, bool a string odmítnuty; celý původní slovník projektu po každém pokusu shodný |
| Fault injection fsync/replace | Každá chyba zachovala původní bajty a odstranila pouze vlastní temp; žádný falešně úspěšný soubor |
| Legacy originál | Raw bytes zachovány a přepis novým writerem odmítnut |
| Novější schema, neznámé pole, duplicitní page ID, NaN parametr | Každý případ odmítnut jako ProjectFormatError |

Původní revival validátor s předpokladem neautorizovaného P2 a beze změny produkce nebyl použit jako P2 přejímka. Původní full suite ani GUI se v tomto cíleném checkpointu neopakovaly.

## Nálezy z počátečních checkpointů

| ID | Závažnost | Konkrétní reprodukce a zdroj | Podmínka uzavření |
|---|---|---|---|
| CR-01 | major | `PanelProject.new_house().set_transform(Transform.from_trs(scale=(1e80,1e80,1e80)))` je přijato, `validate/to_dict` projdou, avšak všech osm `world_surfaces().area` vrátí `inf`. `project.py:98–113` ověřuje finite vertices a minimální hranu, nikoli konečnost všech odvozených metrik; `model.py:64–67` povoluje determinant této transformace | Podporovaná transformace nesmí vytvořit neplatné odvozené délky/plochy/normály. Přetečení nebo nepodporovanou transformaci odmítnout typovanou chybou před mutací; regresní test zachová celý původní projekt. Pokud se P2 omezí na rigidní transformace, nepodporovaná scale/shear se musí odmítnout také při deserializaci |
| CR-02 | major | Plně pokrytý projekt s oddělenými díly: frame `part-0` se změní z wall-left na root/anchor/axis wall-right patřící `part-1`; `from_dict` jej přijme a part-0 zůstává `review_state=current`. `project.py:181–187` kontroluje pouze typ a základní formát IDs | Root musí patřit příslušnému partu, vertex a axis příslušnému rootu. Neplatný/missing rámec lze odmítnout nebo explicitně zachovat pouze v nevyřešeném/stale stavu, který downstream nemůže považovat za platný current export. Nezavést tichý náhradní root. Regrese pokryje cizí root, cizí vertex/edge a skutečně zaniklou kotvu včetně zachování draftu podle přijatého kontraktu |
| CR-03 | major před napojením papírové pipeline | `set_transform(Transform.from_trs(scale=(2,1,1)))` je přijato; místní délka wall-left je 10000 mm, world délka 20000 mm. API zatím nevymezuje, zda ne-rigidní změna musí ovlivnit papírové rozměry; set_transform navíc neinvaliduje papír. Core lokální/world rozlišení samo není chybou, ale bez závazné politiky by propojená pipeline mohla vydávat jiný fyzický model ve 3D a 2D | Zvolit a implementovat jednoznačný P2 kontrakt: buď pouze rigidní transformace a typované odmítnutí scale/shear, nebo společná konstrukční/papírová geometrie zahrnující jejich fyzický účinek s odpovídající invalidací. Testovat běžnou scale 2, shear, deserializaci a hierarchickou kompozici. Zachování lokálního rozvinu se garantuje pouze při rigidním pohybu |
| CR-04 | major | Na opravném `6d41b2b` je `set_transform(Transform.from_trs(position_mm=(1e20,0,0)))` stále přijato a autoritativní stav se změní. Kvůli floating-point rozlišení se wall-left délka 10000 mm změní na 16384 mm a plocha 40000000 na 65536000 mm². Výsledky jsou finite/nonzero, takže oprava CR-01 tuto chybu nepokrývá | Podporovaný rigidní pohyb musí zachovat lokální metriky v požadované toleranci; příliš velký posun s neudržitelnou přesností odmítnout před mutací nebo zvolit reprezentaci se stabilními metrikami. Regrese musí zachytit nekolidující finite/nonzero, ale nesprávné délky/plochy, nikoli pouze úplné zhroucení hran. Ověřit i deserializaci a běžné záporné/rodičovské transformace |

CR-01 a CR-02 byly integračnímu ownerovi předány ihned po běhové reprodukci. CR-03 je konkrétní požadavek na vymezení API před závislou implementací, nikoli žádost o obecný CAD či změnu produktové varianty. Tyto vady nelze uzavřít pouze přidáním dalšího počtu zelených testů; opravný pin vyžaduje cílené re-review.

## Re-review opravného core checkpointu

CODE `6d41b2beac72d7f229dee22df78962abc5965626` zavádí rigid-only transform policy, kontrolu konečnosti odvozené world geometrie a kontrolu příslušnosti rámce. Vlastní běh dvou core test modulů v novém pinned worktree: **56 PASS / 0 FAIL / 0 SKIP**, exit 0, pytest 0.71 s. Autorův záznam 60 zahrnuje ještě čtyři controller testy, které v této samostatné core revizi nejsou započteny ani schváleny.

Vlastní [recheck script](evidence/pc006-review-recheck.py) a [výsledek na 6d41b2b](evidence/pc006-review-recheck-6d41b2b.json) potvrdily typované odmítnutí uniform/nonuniform scale, shear i obrovské scale, vždy bez změny projektu a také při deserializaci. Cizí root/vertex/axis, zaniklá osa a špatná orientace se nesmějí deserializovat jako current; výslovně ANCHOR_UNRESOLVED + stale + shodně označený placement se zachová bez fallbacku, včetně save/reopen.

CR-01 **CLOSED** na 6d41b2b: původní overflow scale je odmítnuta, podporované world metriky mají explicitní finite guard. CR-02 **CLOSED** na 6d41b2b: current reference integrity a zachování nevyřešeného draftu doloženo pěti vlastními případy. CR-03 **CLOSED** na 6d41b2b: P2 dovoluje jen rigidní rotaci/posun; rozměry jsou parametry, modelové měřítko je samostatné. CR-04 byl na tomto mezilehlém pinu ještě **OPEN** a následně vyžádal další opravu.

## Závěrečné re-review přesnosti a schválení core

CODE `2a341e1e64a26d5b1b4c1cde46dfb9603f964069` přidává porovnání skutečných world a lokálních délek/ploch v paper mm vůči přijaté toleranci `max(0.01, 1e-6 × reference)` a guard konečnosti škálovaných metrik. `set_transform` stále validuje celý kandidát před změnou autoritativního stavu.

Vlastní [recheck na 2a341e1](evidence/pc006-review-recheck-2a341e1.json) potvrzuje, že rigidní posun 1e20 je odmítnut typovaným `TRANSFORM_PRECISION`, původní projekt zůstává beze změny a totéž platí při načtení ručně upraveného souboru bez jeho přepsání. Znovu prošly všechny čtyři ne-rigidní případy v API i deserializaci a všech pět vadných frame případů; explicitně nevyřešený draft se přes save/reopen zachová přesně. Samostatný běh trval 0.132 s, exit 0.

Nezávislý cílený pytest na finálním pinned worktree: **57 PASS / 0 FAIL / 0 SKIP**, exit 0, pytest 1.05 s; [finální JUnit](evidence/pc006-review-final-tests.xml). Nepřidávají se k tomu controller testy ani souběžně rozpracované UI soubory. CR-04 **CLOSED** na 2a341e1; dřívější CR-01–03 zůstávají CLOSED. Ve vymezeném core checkpointu nezůstal otevřený blocker/major.

## Zbývající přejímka

Core je nyní technicky schválený v popsaném rozsahu. PC-006 potřebuje následně aplikovaný UI průchod, bezpečné save/open v aplikaci a kompletaci scope; PC-007–009 navíc mixed-part anchor/unfold/layout/export a své AC. Fyzická stavba zůstává P3. Přijetí kontraktu a oprávnění k implementaci zůstává platné; implementační digitální PASS se nesmí odvozovat z této autorizace.

Administrativní uložení tohoto reportu a jeho vlastních důkazů nemění schválenou produkci a je zahrnuto do tohoto scoped schválení. Změna doménového/persistenčního chování nebo integrace jiného věcného obsahu vyžaduje příslušné cílené review; výsledné ucelené PC-006 předání musí mít vlastní pin a nezávislé posouzení celku v potřebném rozsahu.
