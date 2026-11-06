# C06 — mezery při skutečné editaci SVG textu v Inkscape

6. 11. 2026; agent `authoring_export`. Rozsah nálezu je konkrétní **Inkscape 1.4.4 (dcaf3e7, 2026-05-05), Windows**, nikoli obecné tvrzení o všech SVG editorech. Skutečný nový uživatel a fyzický výtisk: NOT_RUN.

## Reprodukce a zachované důkazy

Zdroj je první stránka vlastního projektu z [native run03 na 4b172e6](pc006a-desktop-4b172e6-run03/results.json): SVG `page-9891d8b0-bd54-4b13-8058-342bd40fdaf0.svg`, SHA256 `03501f7ef4ae47ecc69a7a65135cdd78758862d9da8f7457a35d5587f445d16f`. Jeho `<text>` uzly nemají `xml:space="preserve"`. Originální bundle nebyl během editorových běhů měněn; úpravy prováděl skutečný Inkscape v samostatné kopii. XML parser sloužil pouze ke čtení výsledku.

1. [Editor run02, pin 18754c1](pc006a-inkscape-18754c1-run02/editor-results.json): pozorováno vlastní okno `editor-edited.svg - Inkscape`, třída `gdkWindowToplevel`; exact HWND foreground guard prošel. F8 → Ctrl+A → skutečný Unicode vstup a VK_SPACE → Ctrl+S upravily jednotlivý label. Očekávaný text `Žluťoučký – vlastní díl` se uložil jako `Žluťoučký–vlastnídíl`. Tento běh zároveň odhalil nevhodně širokou historickou uppercase extension; změnila i původní texty footeru. Ta byla odstraněna z následného helperu, nikoli zakryta slabší kontrolou.
2. [Editor run03, pin a8ff4b3](pc006a-inkscape-a8ff4b3-run03/editor-results.json): klidný desktop, stejné vlastnictví a kontrola fokusu, obsah se mění pouze individuálním GUI vstupem. Unicode SendInput nyní zahrnoval i obyčejné mezery; výsledek byl znovu `Žluťoučký–vlastnídíl`. Diakritika i zvolená barva se uložily správně a ostatní labely/footer zůstaly původní. Čistě vstupní změna tedy problém nevyřešila.

Oba běhy skončily **FAIL / exit 1** a zůstávají zachované včetně uložených editovaných SVG. Nejsou zpětně označeny PASS. U run02 byl dodatečně oznámen možný souběh cizích Qt testů; není vydáván za prokázanou příčinu. Run03 stejnou ztrátu mezer reprodukoval bez tohoto souběhu.

## Doložená příčina a úzká oprava

Chování odpovídá přímo [Inkscape issue #1053](https://gitlab.com/inkscape/inkscape/-/issues/1053): při psaní na konec importovaného textu bez `xml:space="preserve"` nelze připojit mezeru pro další slovo. [Oficiální zdroj SPText](https://inkscape.gitlab.io/inkscape/doxygen/sp-text_8cpp_source.html) atribut při tvorbě vlastních textových objektů nastavuje. V [pravidlech SVG whitespace](https://www.w3.org/TR/SVG10/text.html) režim `default` odstraňuje koncové mezery, zatímco `preserve` je zachová. Primární zdroje podporují vysvětlení; lokální potvrzení opravy vyžaduje další skutečný editorový průchod.

Writer proto přidává standardní namespaced atribut `xml:space="preserve"` **všem textům materiálových dílů i oběma stránkovým labelům**. Nepřidává pro tento neověřený případ další CSS `white-space:pre`. Nemění geometrii, role, snapshot, PDF nebo fonty. Text zůstává nativní a samostatně editovatelný.

Rozšířená existující XML regrese ověřuje pokrytí všech textových uzlů na obou stranách; tento formátový guard není náhradou za skutečné psaní více slov. Po source pinu se musí vytvořit **nový export skutečnou aplikací**, se zachováním starého důkazu, a otevřít jej v Inkscape bez opravování XML. Stejný GUI vstup musí uložit přesné `Žluťoučký – vlastní díl`, zachovat ostatní texty, role, otvor, kalibraci a geometrii skupin.

Stav při přípravě opravy: **FIX_PREPARED, EDITOR_RECHECK_PENDING, INDEPENDENT_REVIEW_PENDING**. Tento dokument neuděluje vlastní nezávislé schválení ani neuzavírá celé AC-AU17 či PC-009.

## Skutečné ověření po opravě — run06

Nový [desktop/UI run04](pc006a-desktop-7da2403-run04/results.json) na produkčním pinu **`7da240386550039761de6861d3149ce9ee1be466`** prošel celým vlastním kreslením, otvorem, editací, propojením, chlopní, ručním layoutem, nativním uložením/otevřením a nativním exportem: **PASS / exit 0 / 14,219 s**. Všech 23 zaznamenaných výstupních hashů bylo znovu přečteno a ověřeno. Všech osm textových uzlů obou SVG má `xml:space="preserve"`.

Z něj byl přímo, bez úpravy XML nebo přepsání staršího exportu, použit `page-4e4eefb9-aada-4c67-b70e-a2045ffb9b27.svg`. Mezilehlé editorové pokusy zůstávají pravdivě zachované:

- [Run04 na 7da2403](pc006a-inkscape-7da2403-run04/editor-results.json): **FAIL před prvním znakem**, Windows odmítl aktivovat vlastní editorové okno a exact-HWND guard nepovolil žádnou klávesu. Nejde o záporný test whitespace opravy.
- [Run05 na ed3b50b](pc006a-inkscape-ed3b50b-run05/editor-results.json): individuální GUI edit už uložil správný více slovný Unicode text včetně mezer. Celý běh zůstal **FAIL** při následné kontrole, protože Inkscape přiřadil ID `path2` původně anonymní kalibraci. Původní dva CUT IDs, počet tří cest a geometrie byly zachované. Harness následně rozlišil přiřazení jména téže kalibraci od ztráty ID nebo přidání geometrie; všechny původní IDs a kontroly geometrie/počtu/metadat/bounds zůstaly povinné.

Celý nový [editorový run06](pc006a-inkscape-5741cf1-run06/editor-results.json) s připnutým helperem **`5741cf144116123b4a0cb3f1c84987443517662a`** a Inkscape **1.4.4 (dcaf3e7, 2026-05-05)** prošel: **PASS / exit 0 / 14,656 s**. GUI běželo v pozorovaném vlastním okně a před každou klávesou/znakem se ověřil přesný foreground HWND. Skutečné F8 → Ctrl+A → Unicode SendInput → Ctrl+S uložilo přesné **`Žluťoučký – vlastní díl`**, tj. tři obyčejné mezery, diakritiku a pomlčku. Barvu `#b43d28` a posun skupiny provedly skutečné Inkscape actions; obsah pak změnilo individuální nativní GUI. XML parser pouze četl výstup.

Read-only audit autora po ukončení editoru ověřil:

- Všechny čtyři výstupní hashe run06 a všechny čtyři původní soubory native bundle souhlasí; původní SVG/PDF/manifest nebyly měněny. Editovaná kopie má SHA256 `526f7fbc3184f9e51c15d0dd5aa33ed438ce810b6380d1753e8fdf18066c9a67`; raw report `0992482fbe7a58a515c1225a4214725ef5420f7a60a1de340e1465e882cb51ac`.
- Oba původní CUT IDs zůstaly a jejich lokální souřadnice souhlasí i po nativní reserializaci `L` na `H/V`. Plochy samostatných uzavřených obrysů jsou analyticky i z přečteného editovaného SVG **3600 a 225 mm²**, tedy čistý materiál **3375 mm²**. Otvor zůstal samostatnou prázdnou smyčkou, nepřibylo proříznutí přes jeho vnitřek.
- Přečtené Inkscape bounds obou CUT cest se posunuly přesně **10 / 15 CSS px**, tedy **2,645833333 / 3,96875 paper mm**. Jejich šířky/výšky ani velikost otvoru se nezměnily. Posun není změnou měřítka.
- Zachovalo se všech sedm role groups, ostatní texty, A4 `210 × 297 mm`, `viewBox` a geometrie kalibrace `[10,282] → [110,282]`, tedy **100 paper mm**. Celkově jsou stále tři cesty; jediné nové ID pojmenovává stejnou existující kalibraci.
- Přes `view_image` byly skutečně prohlédnuty [GUI snímek](pc006a-inkscape-5741cf1-run06/editor-gui.png) a [Inkscape render](pc006a-inkscape-5741cf1-run06/editor-final-render.png): normální obraz skutečného editoru s aktivním textovým nástrojem, červeným textem a polem, zachovaný vnitřní obrys a oddělená spodní kalibrace. Nejde o černý capture ani o kresbu napodobující editor.

Aktuální stav: **FIX_VERIFIED_EDITOR_RUN06, INDEPENDENT_REVIEW_PENDING**. Závěr je omezen na skutečně provedenou interoperability reprodukci tohoto Inkscape a uvedených zdrojů. Křivkové projekty, širší editorové/DPI přejímky PC-009, nový uživatel a P3 zůstávají oddělené. Žádný historický raw FAIL nebyl upraven; tato aktualizace není vlastní nezávislé schválení.

**Následné nezávislé uzavření:** [CODE revize](../PC006A_REVIEW.md) posoudila produkci `7da2403`, helper `5741cf1` a uložené důkazy `1d8ed8b`; C-06 je **CLOSED / APPROVED_IN_SCOPE**. Reviewer není autorem writeru, opravy nebo harnessu. Vlastních 132 kontrol a 22 kontrol nových native výstupů prošlo, stejně jako 55 exportních regresí; viz raw odkazy v review. Výše uvedené pending stavy popisují skutečné pořadí přípravy a nejsou zpětně přepsané. Nový uživatel, širší PC-009 a P3 zůstávají otevřené.
