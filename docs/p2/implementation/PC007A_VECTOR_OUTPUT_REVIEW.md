# PC-007A — nezávislá revize skutečných vektorových výstupů

Reviewer: samostatný agent `commands_review`, 9. 11. 2026; není autorem revidovaných parserů ani jejich integrace. Přesný zdroj **`820ab6672d6a3f252391807b4c2c626c51a040bb`**, větev `revival/p2-profiles`; zahrnuje PDF komponentu `4a4d59d` a navazující hook/SVG/manifest změny.

**Verdikt: CHANGES_REQUESTED — V01 MAJOR OPEN.** Skutečné PDF číselné lexémy nejsou zachované přesně a dosavadní float guard jejich ztrátu nedokáže doložit. Owner nález přijal a připraví opravu přes přesné lexémy. Tento report nesmí být použit jako schválení celé PC-007A, PDF parseru nebo publikace balíku.

Na výslovný pokyn integračního ownera zůstává tento report a jeho nová evidence zatím **bez commitu**; production HEAD je rezervovaný pro koordinovaný další postup. Reviewer produkci ani staging neměnil.

## V01 — ztráta původního PDF lexému před kontrolou přesnosti

`read_pdf_cut_regions` získá čísla přes `pypdf.ContentStream` nebo pypdf page objekty. `_number` potom používá `Fraction(str(value))`. Jeho guard porovnává `float(str(value))` a `float(value)`, tedy dvě hodnoty již **po** dekódování do pypdf FloatObject. Nemůže zjistit desetinná místa, která se ztratila už při prvním převodu.

Konkrétní původní token `1.00000000000000001` v reálně serializovaném PDF proudu je bez odmítnutí přijat jako 1. Očekávaná page-mm hodnota je `Fraction(100000000000000001,100000000000000000)*127/360`, vrácená hodnota je `127/360`. Report přitom stále tvrdí `EXACT_FRACTIONS_OF_SUPPORTED_SERIALIZED_PDF_DECIMALS`.

Vlastní nezávislé PDF s ručně vypočítanými xref offsety dále zachovává původní čísla přímo v page dictionary. Všechny čtyři varianty byly na revidovaném pinu chybně přijaty:

| Pole skutečného PDF | Původní hodnota | Chybná přijatá interpretace |
| --- | --- | --- |
| MediaBox right | `360.00000000000000001` | 360; fyzická šířka se zkrátí |
| CropBox right | `359.99999999999999999` při MediaBox 360 | 360; odlišný ořez se tváří shodně |
| Rotate | `360.00000000000000001` | 360; nepodporovaná neúplná otáčka je ignorovaná |
| UserUnit | `1.00000000000000001` | 1; nepodporované fyzické jednotky jsou ignorované |

Nejde o tvrzení, že vlastní ReportLab writer běžně vydává všechny tyto dlouhé tokeny. Jde o to, že parser tvrdí přesné čtení skutečně vydaného souboru a unsupported tokeny nerozpozná. Nezávislá raw native topology komponenta zachovává racionální sub-float průniky; tento reader by takový důkaz mohl zničit před jejím zavoláním. Malá chyba není oprávnění vydat nepravdivý přesný aritmetický kontrakt nebo předpokládat, že nikdy neovlivní dotyk/průnik.

Oprava musí získat přesné původní lexémy z decompressed streamu i relevantních page objektů a zachovat je jako racionální hodnoty, případně jednoznačně odmítnout nedoloženou vlastní podmnožinu formátu. Nestačí jiná varianta float roundtripu, přejmenování exact claim nebo mutable globální zásah do pypdf parseru. Při novém review ponechat všechny původní FAIL a ověřit skutečné CTM/operandy i MediaBox/CropBox/Rotate/UserUnit.

## Ověření konkrétního pinu

Fresh subprocessy použily přesný `git archive` src/tests/tools/pyproject plus konkrétní published-B fixture z téhož pinu. Žádný rozpracovaný soubor ve sdíleném profiles worktree nebyl vydáván za připnutý zdroj.

[Runner](evidence/pc007a-vector-output-review-archive.py), [source pin, SHA256 archivu, izolovaný adresář a raw](evidence/pc007a-vector-output-review-archive-820ab66.json):

```powershell
& C:\Users\dalib\projects\papercraft\.venv\Scripts\python.exe docs/p2/implementation/evidence/pc007a-vector-output-review-archive.py
```

- Původní cílené PDF/guard/profile/curve-workspace testy: **56 PASS / 8,62 s**, [JUnit](evidence/pc007a-vector-output-review-original-820ab66.xml).
- Vlastní nezávislé případy: **10 PASS, 5 FAIL / 1,02 s**, [zdroj](evidence/pc007a-vector-output-review-own.py), [JUnit](evidence/pc007a-vector-output-review-own-820ab66.xml). Všech pět FAIL je stejná V01 příčina v proudu a čtyřech page polích, nikoli pět nesouvisejících produktových nálezů.

První archive běh omylem vynechal published-B fixture a jeden původní test skončil FileNotFoundError. Tento harness omyl je zachovaný v `pc007a-vector-output-review-original-fixture-omitted.xml` a `pc007a-vector-output-review-initial-fixture-omitted.json`. Není to produktová regrese, po zahrnutí přesné fixture prošla celá cílená původní sada. Původní V01 FAIL zůstal reprodukován i v opraveném review prostředí.

## Pozitivní výsledky v omezeném rozsahu

Vlastní skutečné PDF očekávání ověřilo nesymetrický složený CTM s translací, shear a nerovnoměrným měřítkem, fyzické `127/360 mm/pt`, top-left Y převod a q/Q obnovu před dalším dílem. Parser zachoval skutečnou díru a dovolil samostatný díl v jejím prázdném prostoru; report hash odpovídal skutečným PDF bajtům a šel serializovat bez NaN. Chybějící CUT role, neuzavřený řez, skutečný cubic crossing, clipping, singular CTM a podtečený graphics stack bezpečně blokovaly.

Vlastní SVG s přesnými dlouhými desetinnými `1±1e-20` a skrytým cubic crossing byl odmítnut. Tento reader správně pracuje přímo s textovými Fraction souřadnicemi a nemá výše uvedený pypdf float mezikrok. Skutečný vlastní arc→PDF-cubic export v otočeném dílu zachoval dva CUT obrysy včetně otvoru a manifest obsahoval odlišné, pravdivě pojmenované rozsahy PDF a SVG důkazů.

Staticky zkontrolována publikace staged souborů: vlastní writer označuje part/role v PDF, po zápisu validuje skutečné PDF a SVG a teprve potom připraví manifest/přesun balíku. CurveOutputError je zachovaný jako konkrétní výrobní chyba. Původní testy skutečného ztraceného SVG otvoru a PDF CUT role ověřily bajtové zachování předchozího balíku a odstranění pouze vlastního stage adresáře. Neznamená to obecnou ochranu proti libovolnému vnějšímu pozměnění platného souboru po předání.

## Rozpočty a nutné rozlišení rozsahů

Review sledovalo source→native SVG bound, SVG-arc→PDF-cubic interpolační bound a serializační bound skutečně emitovaného CTM/control bodů. Publisher nyní sčítá tyto odlišné členy proti 0,01 mm a uvádí je v manifestu; jeden zelený topologický certifikát nenahrazuje metrický bound. V01 stále brání tvrzení, že výsledné parserové page souřadnice byly přesné původní desetinné hodnoty.

SVG reader kontroluje **skutečné lokální CUT podcesty**, jejich přímou strukturu a podporované pevné umístění. Výslovně nevydává přesnou page separation ani fyzické page bounds z rotovaných serialized SVG koordinát. Integrace rezervuje konzervativní output obálky v page layoutu včetně 0,01 mm na obou sousedních dílech. Tento report nezaměňuje tento source-envelope postup za přesné parsované SVG page vzdálenosti. Pokud se změní writer umístění nebo jeho vazba na snapshot, musí být přiměřeně ověřena znovu.

Relevantní construction/verification skills byly použity při rozlišení skutečného materiálu a otvorů, strict topology proti pouhé geometrii vzorků a raw serializovaných hodnot proti source surrogate. Použitelnost a delivery rozlišují konkrétní opravitelné výrobní chyby, rollback a přesný commit. Žádná nápověda ani oslabení AC nemohou opravit V01.

Skutečný desktop/editor, lidská použitelnost, celý loft průchod B1/B2/B3, celé PC-007A a P2 ani fyzický P3 nejsou tímto review schválené. Oprava a nové nezávislé review přesného finálního pinu jsou povinné před publikací tohoto balíku.
