# Nezávislá revize měření vstupu při škálování Qt

Reviewer: `commands_review`, jiný agent než autor root. Datum: 11. 11. 2026. Rozsah je technický harness a čtení skutečných záznamů, nikoli produktové přijetí C/P2, certifikace nastavení Windows nebo test začátečníka.

Revidované zdroje: původní probe `65b6dae843fe2ec74bb76aa884c1c7afaf826828`; oprava `572514fc8c75fd1298329fad8b5d18be0e17bbb6`, začleněná do `22301faa45c8393cc127a3f117b0708cd48eea5f`. Vlastní izolovaný worktree je `papercraft-scaling-review`, větev `review/scaling-22301fa`. Aplikační `src` a `pyproject.toml` jsou proti schválenému C8 zdroji `8f1ec6382d527c719133958e7eb6f78a724ef5d5` beze změny. Reviewer nespouštěl aplikaci ani nativní vstupy a neupravoval produkci.

## Původní probe a skutečný neúspěšný běh

Event filter zavolá původní konstruktor, pouze čte události, transformaci a obrazovky a vždy vrací `False`. Nenastavuje kameru, geometrii, dokument ani výsledek příkazu. Dodatečný `scaling-observations.json` je samostatná evidence s vlastním hashem; nepředstírá zahrnutí do původního manifestu běhu.

Skutečný `pc009-C-cylinder-qt150-65b6dae-run02` zůstává FAIL. Vlastní [audit](evidence/pc009-scaling-review-65b6dae-run01.json) zpracoval 308 událostí, žádnou chybu observeru a nedosažený limit 20 000 událostí. Qt hlásí monitor PL2293H s DPR 1,5 a MNG007QX2-2 s DPR 1,875, oba logical DPI 96. Toto je změna per-process Qt scale, nikoli důkaz změny OS scale.

Poslední Ctrl+wheel dorazil do QWindow na local `[526.6667,187.3333]`, global `[526.6667,197.5556]`. Skutečný prostřední stisk měl local `[186,156]`, global `[790,296]`, z čehož plyne poloha levého horního rohu papírového viewportu `[604,140]`. Kolečko tedy dorazilo vlevo od papíru; jeho window-local souřadnice odpovídají zamýšlenému `[790,281]` dělenému 1,5. Kamera zůstala stejná. Samotný prostřední posun nemá doloženou chybu aplikace: původní probe nezaznamenával rozsahy scrollbarů ani jednoznačnou identitu cíle, a posun po fit-all může být omezen nulovým rozsahem. Záznam filtru je před obsluhou události, není přímo postcondition téže události.

Lokálně ověřená verze PySide6/Qt je 6.12.0. [Dokumentace QTest](https://doc.qt.io/qt-6/qtest.html#wheelEvent) požaduje window-local souřadnice, kterým původní volání odpovídá. [Přesný zdroj Qt v6.12.0](https://raw.githubusercontent.com/qt/qtbase/v6.12.0/src/gui/kernel/qwindowsysteminterface.cpp) v `qt_handleWheelEvent` předává logical souřadnice přímo do native rozhraní; mouse wrapper přitom volá `toNativeLocalPosition` a `toNativeGlobalPosition`. [Aktuální větev Qt 6.12](https://raw.githubusercontent.com/qt/qtbase/6.12/src/gui/kernel/qwindowsysteminterface.cpp) již tyto převody obsahuje i pro wheel. To vysvětluje pozorované dělení DPR v testovací cestě. Závěr je chyba doručení testovacího vstupu kompatibilní s tímto upstream rozdílem; žádný produktový wheel defect nebyl prokázán.

## Nález SO-GUARD01 a oprava

MINOR původního probe: `finally` zapisoval trace do jakéhokoli existujícího `--output`, i když původní runner odmítl existující adresář nebo nesprávné SHA. Mohl tak přepsat starší důkaz. Konkrétní běh run02 použil nový adresář a tímto nálezem není znehodnocen.

Oprava 572/223 odmítá existující cestu před importy, nastaví vlastnictví výstupu až po úspěšném původním konstruktoru aplikace a nový trace otevírá režimem `x`. Neúspěšný source guard tedy nevytvoří trace. Původní runner nadále požaduje nový adresář. Nález je uzavřen v tomto rozsahu: dva autorovy skutečné CLI testy nezávisle přehrány, **2 PASS / 2,96 s**, a tři [vlastní negativy](evidence/pc009-scaling-review-22301fa-own.py) ověřily existující obyčejný soubor, starý trace s vnořenými cizími daty a wrong-SHA se skutečným SHA vlastního worktree v chybě. Všechny **3 PASS**, žádná změna existujících bytů ani nový výstup. Testy nespouštějí QApplication ani nativní vstup.

## Nativní wheel a nové měření

Nový `native_dialogs.wheel_at` je skutečný Windows vstup Ctrl+wheel. Před vstupem kontroluje vlastní PID, foreground HWND, absenci již držených běžných modifikátorů/tlačítek, poměr native client rozměrů vůči Qt logical rozměrům a DPR a hit root HWND v naměřeném místě. V `finally` uvolní vlastní Ctrl a obnoví předchozí kurzor. Nevolá produktový wheel handler přímo a nepřepisuje kameru ani výsledky příkazu. Nevnáší verzově závislé násobení souřadnic do QTest API. Root-hit sám o sobě nedokazuje paper receiver; to musí doložit nové explicitní `target_is_paper_viewport` a případná následná změna kamery. Nový probe zaznamenává také scroll ranges, takže lze odlišit clamp od nedoručeného posunu.

Statická revize opravy a negativní kontroly: **APPROVED_IN_OBSERVABILITY_AND_NATIVE_INPUT_HARNESS_SOURCE_SCOPE** pro přesný 22301fa. Nativní běh 223 run03 byl při prvním čtení ještě RUNNING; závěr o skutečném doručení a zachování kamery je do čtení hotových artefaktů PENDING. Původní FAIL výsledky se nepřejmenovávají na PASS a shell exit code maskovaný následným PowerShell čtením není důkaz úspěšné aplikace.

Následné čtení dokončeného run03: **FAIL / 106,812 s** na `Native wheel requires this proof's foreground window`, `native_camera_inputs=[]`. Vstup tedy nebyl odeslán. Probe uchoval 294 událostí bez chyby; poslední známé scroll ranges papíru jsou `[0,0,0,0]`, což podporuje vysvětlení, proč samotný pan při fit-all nemusí změnit kameru. Záznam v místě foreground odmítnutí neobsahuje jednotlivé hodnoty own PID / foreground HWND a neprokazuje konkrétní příčinu odmítnutí. Doporučeno doplnit pouze pozorování těchto hodnot a plný ctypes podpis `GetWindowThreadProcessId(HWND, POINTER(DWORD)) -> DWORD`; původní helper zde předává obyčejný Python int a spoléhá na výchozí konverzi. Není tím prokázána chyba PID ani aplikace. Skutečný nativní průchod škálováním zůstává **PENDING**, bezpečné odmítnutí před vstupem je zachováno.

## Uplatnění skills a meze

Načteny AGENTS a čtyři projektové skills. Verification: pin zdroje, nezávislé čtení skutečných událostí a rozlišení pre/post obsluhy, negativní ochrana evidence a zachování FAIL. UI: ověřování skutečně doručeného vstupu před diagnózou ovládání, bez nahrazení změny interakce tipem. Construction: žádný nový závěr o konstrukci či výrobě z testu kamery. Delivery: úzký scope, oddělení source approval od nativního důkazu a dalšího předání. Normativní AC ani tolerance se nemění. Nový uživatel 0 / NOT_RUN, fyzická stavba P3 NOT_RUN; celé C, PC009 a P2 tímto nejsou dokončené.
