# Přepočet odhadu po prototypu PC-006 a změně cíle

## Aktualizace po skutečném PC-006A,6.11.2026

PC-006A má běžící generický editor, uložené vlastní profily/otvory, skutečný Windows průchod až SVG/PDF a [nezávislé schválení](../implementation/PC006A_REVIEW.md) na4b172e6. Celá sada443PASS nenahradila cílenou revizi: ta našla a nechala opravit5 konkrétních chyb včetně neuložených čísel, světové plošné metriky a deklarace PDF chyby. Základní Qt/IO/vector směr a konkávní materiál jsou nyní podložené implementací. Interiérové kontakty, obecné křivky/lofty a fyzický materiál zůstávají hlavními riziky; experimentální schema se neuzavírá.

Pro **zbývající PC-006B až010** ponecháváme odborné odhady10–17 +12–20 +10–17 +8–14 +6–10 +4–7 = **50–85 člověkodnů**, s dosavadní rezervou15–25% přibližně **58–107**. Původních9–15 za006A je odebráno ze zbývající práce, nikoli vykázáno jako skutečně odpracovaný čas. Závěrečný vlastní historický model AU19, výslovně doplněný vlastníkem, přidává vPC-010 **2–4 člověkodny** na vlastní konstrukci, celý průchod, numerická očekávání a review. Aktuální zbytek je proto **52–89**, s rezervou zaokrouhleně **60–112 člověkodnů**. Nejde o naměřenou rychlost týmu, délku agentních běhů ani kalendářní termín. Dostupnost skutečného novice účastníka se sleduje samostatně; počet účastníků je zatím0. Další povinný přepočet nastane po006B podle reálných kontaktů a autorských konektorů, poté po007A.

Zbývající rizika doplněná zkušeností006A: změna vstupu během modální operace (C-05; nyní regresně chráněno), oddělení analytické a serializační chyby vektorů (C-02), materiálová geometrie ve vzdálených souřadnicích (C-04) a průkaznost capture/souborových dialogů. Doplněné historické předlohy potvrzují význam výztuh, samostatných pásků, skutečných výřezů a vnitřních přijímačů, ne matematickou správnost našich budoucíchB/C/D. Původní návrhový rozpad níže je zachován jako historie a plánovací základ.

6. 11. 2026. Jednotka je soustředěný **člověkoden**, nikoli doba běhu agenta, údaj o dosud odpracovaných dnech nebo slib kalendářního termínu. Nová v1.2 je rozsahově větší než v1.1. Starých 24–40 člověkodnů nelze přenést na vlastní kreslení, díry, profily, vnitřní připojení a stočené pláště.

## Co skutečně víme z PC-006 prototypu

Pevný panelový dům má analytické doménové testy, atomickou IO, typed odmítnutí nepodporovaných operací, rigidní transformace a ochranu před ztrátou metriky. [Core review](../PC006_CORE_REVIEW.md) schválilo omezený core pin, ne autorskou doménu ani celé UI. Windows prototyp byl skutečně spuštěn s OpenGL a nativními dialogy. Pozdější rozpracované UI ukázalo výběr, spoje, ruční stránky, stale/recompute společného dílu a SVG/PDF i skutečný Inkscape. Důkazy jsou zachované v `docs/p2/evidence/`, interpretace v [dispozici](CODE_DISPOSITION.md).

Tato data snižují riziko základního Qt/IO/exportního směru. **Neprokazují obecnou konstrukční doménu, díry ani A–D.** Paper review na `3fcf877` mělo CHANGES_REQUIRED: RAM coverage mohla vynechat díl, deklarovaný počet testů neodpovídal pinu a extrémní scale vyvolalo raw overflow. Opravy v zachovaném prototypu nejsou bez nového review nezávislé schválení. Prototyp PC-006 tedy evidujeme jako změnou cíle přerušený experiment, ne hotový nový PC-006A/B.

## Pracovní rozpad v1.2

| Balík | Obsah odhadu včetně běžných oprav a review | Člověkodny |
|---|---|---|
| PC-012 návrh/spiky | Produktové situace, analytické spiky, návrh, nezávislá revize | 3–5 referenční plánovací rozsah, nikoli vykázaná práce |
| PC-006A | Generický sketch/polygon/holes, identity a IO, blank UI, první celý výrobní průchod | 9–15 |
| PC-006B | Assembly/interior traces/regions, přesahy, vlastní chlopně a pásek, model A, první autorská verze | 10–17 |
| PC-007A | Arc/Bézier editor, profily/correspondence, ostění, certifikované rodiny a B | 12–20 |
| PC-007B | Válec/kužel, seam, dělené chlopně, kontakt/relief a C | 10–17 |
| PC-008 | D segmentace/error bounds a varianty, změny/lineage/anchors napříč A–C | 8–14 |
| PC-009 | Konsolidace vector curves/holes, nezávislá parita, skutečný editor a platformní průchody | 6–10 |
| PC-010 | Závěrečné nezávislé review, opravy, kompletní digitální předání | 4–7 |

Zbývající implementace: **59–100 člověkodnů**; první autorská verze A z toho **19–32**. To je rozpad práce, nikoli počet paralelních agentodnů. Pro dosud neověřené obecné křivky, clipping a chování materiálu držíme oddělenou rizikovou rezervu 15–25 %: přibližně **68–125 člověkodnů** pro implementaci s rezervou. Návrh má vlastní referenční rozsah 3–5; fyzická P3 zde započtená není. Horní mez není garance při změně cíle nebo nutnosti nového kernelu.

## Rizika a konkrétní rozhodnutí

Spiky už doložily pozitivní homotetické kruhové/eliptické/gotické rodiny a negativní nezávisle změněné profily. Snižují nejistotu základního postupu B, nikoli práci na obecné editaci a reference modelu. U D dosáhl hrubý experiment globální meze0.004113mm až za cenu8192 triangle islands; to je nepoužitelný výchozí výrobní návrh. PC-008 proto obsahuje výběr praktického dělení a náhled jeho ceny, ne pouhé převzetí tohoto mesh výstupu. U C má24 záložek malý arc/chord mismatch0.009087mm, ale změnu boční délky0.113955mm: kontakt a ohyb jsou samostatné riziko, přesný plášť je neřeší. Riziková rezerva se po těchto výsledcích nesnižuje a nelze ji převést na „garantováno testy“.

Nezávislá revize navíc našla singularitu rovinného loftu mezi vzorky. I raný spike tedy potřebuje negativní důkazy a analytickou regularitu; samotný počet PASS nedává oprávnění uzavřít schema. Jeho oprava nemění plánovaný rozsah, ale potvrzuje potřebu review a rezervy.

| Riziko | Co už je doloženo / co chybí | Opatření a bod přepočtu |
|---|---|---|
| House-only persistence by zablokovala tvorbu | Audit identifikoval pevné plochy, hrany a default wall frame | Nezmrazit prototypové schema; PC-006A/B skutečné generické entity a připravené B/C/D fixtures před freeze |
| Ruled loft nemusí být rozvinutelný | Časné spiky oddělují certifikované rodiny a negativní případy | EXACT pouze s certifikátem; UNRESOLVED jinak, approximation s rozpočtem; přepočet po spicích a PC-007A |
| Otvory/konkávnost a curve clipping | Fan/convex cesty současného prototypu nevyhovují | Samostatné geometrické adaptéry s negativními orákuly; průchod A, nejisté průsečíky neprojdou jako úspěch |
| Vnitřní kontakt a zakřivené chlopně | Nestačí stejná délka nebo flat overlap | Source/target UV a folded contact; materiálové meze explicitní, přepočet po A a C, fyzický proof v P3 |
| Topologická jména a kotvy při editaci | Smíšený panelový fixture má důkazy, volné profily zatím nikoli | Provenance segmentů/intervalů, žádný nearest fallback; povinné mixed-part regrese pokračují |
| UI rozsah a validace křivek | Existuje ověřený Qt/OpenGL směr, nikoli vlastní sketch UI | Každý řez má skutečný widgetový průchod až export, ne model-only infrastrukturu; DPI/klávesnice průběžně |
| Neúplný export z projekční cache | Historické nezávislé review našlo vynechání dílu | Autoritativní coverage kontrola před snapshotem, fault injection, nezávislé XML/PDF; neodvozovat důkaz z RAM počtu |
| Převzetí důkazů z prototypu | Původní PASS může být zaměněn za v1.2 | Historické piny zachovat, nové AC NOT_RUN; předání vyžaduje všechny A–D a nezávislou revizi |

Po PC-006A přepočítat podle skutečné generické IO, děr a celého UI průchodu; po PC-006B podle reálných kontaktů a custom tabů. Další aktualizace po PC-007A, při změně error budget nebo výběru nového geometry adapteru. Pokud se riziko naplní, upraví se technický rozpad a odhad, ne potichu sjednané schopnosti. Výsledky spikeů z tohoto balíku jsou vstup návrhu; nenahrazují měření implementační rychlosti.

Průřezové doplnění vlastníka 6.11.2026: osvojitelnost a údržba projektových skills se plánují v implementaci, ověření a běžných opravách každého řezu. Krátké skutečné novice sezení a opravy jeho nálezů patří do PC-006A/B, nikoli do další etapy. Pracovní rozsah59–100 člověkodnů není nově naměřený údaj a tímto doplněním se neprohlašuje za jistější. Při přepočtu po PC-006A/B uvést skutečné náklady na UI opravy, další ověření a dostupnost účastníků odděleně od lidské pracnosti. Chybějící účastník představuje omezení ověření, ne důvod nahradit lidský test automatem nebo práci přesunout na závěrečný redesign.
