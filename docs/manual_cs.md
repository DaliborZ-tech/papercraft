# ArchPapercraft Studio — český rychlý start

Pracovní autorské UI 0.3.0, stav 17. 11. 2026. Instalace a spuštění jsou
v [README](../README.md#instalace-a-spuštění).

## 1. Modelování: první plocha a její úprava

1. Spusťte aplikaci nebo zvolte **Projekt → Nový prázdný model** (`Ctrl+N`).
2. Vyberte kontext **Modelování**. Ve **Vlastnostech → Jednotky a tvorba**
   nastavte **Rozměry modelu** na `mm`. Nabídka umí také `cm` a `m`; čtěte
   jednotku u zadávaného rozměru. **Měřítko 1 :** je samostatné nastavení
   velikosti na papíře, nový model má 1:100.
3. Pro stěnu vyberte **Nová pracovní rovina → Svisle (stěna)** a příkaz
   **Vytvořit → Obdélník z rozměrů…** (na liště **Díl z obdélníku**).
   Zadejte například šířku `5000` a výšku `3000` mm a potvrďte.
   Při 1:100 má samotné tělo tohoto dílu na papíře 50 × 30 mm.
4. Plochu vyberte kliknutím ve 3D nebo ve stromu **Model → Moje plochy a díly**.
   V horním poli Vlastností změňte její název a potvrďte Enter. U samostatné
   plochy se přejmenuje i dosud automaticky pojmenovaný papírový díl, včetně
   výstupu; odlišné vlastní názvy a složené díly upravte přes **Pojmenovat…**
   (`F2`), kde lze pojmenovat i model.
5. V části **Bod obrysu** vyberte konkrétní bod a upravte **Vodorovně** /
   **Svisle v obrysu**. Číslo potvrďte Enter. Přesný rozměr obdélníku tak lze
   změnit úpravou jeho bodů; část **Umístění v prostoru** mění posun a natočení
   celé plochy. `Ctrl+Z` vrátí příkaz a `Ctrl+Y` jej zopakuje.

### Vlastní skica a otvor

V Modelování zapněte **Skica** a zvolte **Nakreslit vlastní díl** (`Ctrl+L`).
Klikáním přidávejte body obrysu. Enter obrys uzavře a vytvoří plochu;
`Ctrl+Enter` uloží otevřený profil. Backspace vrací poslední krok kreslení,
Esc návrh zruší. Síť lze nastavit ve Vlastnostech a při kliknutí obejít Altem.

Na liště lze pro další úsek vybrat **Úsečka**, **Oblouk přes tři body** nebo
**Křivka se dvěma úchopy**. Stavový řádek říká, který bod nebo úchop je další.
Nedokončený úsek nejprve dokončete nebo vraťte Backspace.

Pro okno či dveřní otvor vyberte existující rovinnou plochu a příkaz
**Nakreslit otvor do vybrané plochy** (`Ctrl+H`). Kreslete uvnitř jejího obrysu
a potvrďte Enter. Neplatný návrh aplikace odmítne; body lze opravit nebo zrušit.

## 2. Spoje a rozvin

Vytvořte druhou plochu a přepněte na **Spoje a rozvin** (`Ctrl+2`).
Ve Vlastnostech jsou skupiny **Hrany, spoj a chlopeň** a
**Autorské spoje a záložky**.

1. Vyberte první plochu a její přímý okraj v poli **Okraj vybrané plochy**.
2. Zvolte **Spojit vybrané hrany** (na liště **Spojit hrany**) a vyberte okraj
   druhé plochy. Dialog **Umístit a připojit protikus** ukáže náhled; nastavte
   úhel mezi plochami a potvrďte jej, nebo zrušte bez použití návrhu.
3. Ve vlastnostech existujícího spoje zvolte **Řez a lepení** nebo
   **Souvislý přehyb**. Pro lepení vyberte chlopeň a její šířku na papíře.
4. Po konstrukční změně použijte **Přepočítat papírové díly** (`Ctrl+R`).
   Potom zkontrolujte tvar dílů a jejich umístění.

Připojení dovnitř plochy má samostatný příkaz (`Ctrl+J`) s náhledem.
Pokročilé profily, plochy mezi dvěma profily a dělené chlopně kruhového okraje
jsou v menu **Vytvořit** a příslušných vlastnostech výběru. Sledujte jejich
zobrazený stav; odvozené rovinné díly s povolenou odchylkou vyžadují vlastní
náhled a potvrzení, nejsou automatickou záměnou původní plochy.

## 3. Stránky: rozmístěte díly ručně

Přepněte na **Stránky** (`Ctrl+3`). Vyberte díl v papírovém pohledu nebo ve
stromu. V části **Díl na papíře** nastavte cílovou stránku v poli **Umístění**,
**Kotva X**, **Kotva Y** a **Natočení**. Tyto souřadnice a rozměry chlopní
jsou v milimetrech na papíře, nezávisle na jednotce modelu.

Díl lze také přetáhnout myší. **Alt + kolečko** otáčí vybraný díl po 5°,
pokud nemá zamčené natočení. **Zamknout polohu** a **Zamknout natočení**
chrání ruční rozmístění. Tlačítkem **Přidat A4** přidejte další stránku.

Příkaz **Ruční rozmístění více dílů…** umožní vybrat díly, cílovou stránku,
počet sloupců, kotvu a rozteče. Nejdříve stiskněte **Zobrazit zadané polohy**,
zkontrolujte náhled a potom **Umístit vybrané díly**. Rozteče zadáváte vy;
jde o ruční rozmístění do mřížky, nikoli automatické hledání volného místa.

Spodní přehled připravenosti upozorní například na díly mimo stránku,
překryvy nebo potřebný přepočet. Otevřete **Podrobnosti** (`F8` zobrazí
Problémy a připravenost), vyberte problém a použijte nabízený další krok.
**Další dotčený díl** prochází členy skupiny. Přijmout lze vybrané varování
pro aktuální stav; chyba se tím neopraví.

## 4. Export SVG a PDF

Přejděte na **Export** (`Ctrl+4`). Opravte problémy bránící exportu a použijte
**Projekt → Exportovat SVG a PDF…** (`Ctrl+E`). Potvrďte počet stránek a
měřítko a vyberte výstupní složku. Příkaz vytvoří editovatelná SVG a
vektorové PDF. Během exportu lze požádat o zrušení; výsledek dialog oznámí.

Pro tisk nastavte **100 % bez přizpůsobení stránce** a ověřte 100mm kalibrační
úsečku. Digitální výstup sám nedokládá fyzické sestavení modelu.

## Uložení a obnova práce

**Projekt → Uložit** (`Ctrl+S`) zapisuje `.apcraft`; při prvním uložení vyberete
soubor. **Uložit jako…** (`Ctrl+Shift+S`) umožňuje další kopii. Před uložením
se vyhodnotí rozepsané číslo či název hlavního inspektoru; neplatný vstup
opravte. Rozpracovaný obrys nejprve dokončete nebo vědomě zrušte. Při Novém,
Otevřít a zavření se aplikace ptá na neuloženou práci.

Každých **30 sekund** se při změnách pořizuje **oddělený záložní koncept**.
Nepřepisuje soubor modelu a neoznačí projekt za uložený. Uchovává poslední
platný model a zvlášť rozepsané číslo nebo název hlavního inspektoru a
nedokončenou skicu, včetně otvoru a jeho roviny. Časovač tyto vstupy
nepotvrzuje. Změny od posledního úspěšného intervalu ještě v konceptu být nemusí.
**Nepotvrzené ovladače v samostatných modálních konstrukčních/náhledových
dialogách se do konceptu neukládají.**

Po přerušení práce nabídne další spuštění dostupné koncepty; nabídku otevřete
také přes **Projekt → Obnovit neuloženou práci…**. Vyberte konkrétní koncept:

- **Obnovit kopii** obnoví neuloženou kopii a dostupný původní výběr/vstup.
- **Později** koncept zachová.
- **Zahodit koncept** jej výslovně odstraní.

Koncept jiného právě otevřeného okna se nenabízí. Při běžném uložení nebo
vědomém zahození a zavření se vlastní nepotřebný koncept odstraní. Chyba
zápisu je hlášena ve stavovém řádku; pokud nejde koncept odstranit, zavření
nebo výměna modelu se zastaví.

**Obnovenou kopii poprvé uložte pod novým názvem.** Pokud měla původní soubor,
aplikace při tomto uložení chrání původní cestu před přepsáním. Také starší autorské projekty
mohou být otevřeny pro úpravu kopie s požadavkem na nový název a přepočet;
jiný starý projektový formát se otevírá pouze pro prohlížení.

## Ovládání pohledů a zkratky

Ve 3D prostřední tlačítko otáčí pohled, Shift + prostřední posouvá a kolečko
přibližuje. Ve skice prostřední tlačítko posouvá a kolečko přibližuje;
na papíře prostřední tlačítko posouvá a **Ctrl + kolečko** přibližuje.

| Zkratka | Akce |
|---|---|
| Ctrl+1 / Ctrl+2 / Ctrl+3 / Ctrl+4 | Modelování / Spoje a rozvin / Stránky / Export |
| Ctrl+N / Ctrl+O | Nový prázdný model / Otevřít |
| Ctrl+S / Ctrl+Shift+S | Uložit / Uložit jako |
| Ctrl+Z / Ctrl+Y | Vrátit / zopakovat příkaz; při kreslení Ctrl+Z vrací krok skici |
| Ctrl+L / Ctrl+H | Nový obrys / otvor do vybrané rovinné plochy |
| Enter / Ctrl+Enter | Při kreslení uzavřít obrys / uložit otevřený profil |
| Backspace nebo Delete | Při kreslení vrátit poslední bod či úchop |
| Esc | Zrušit rozpracovanou operaci nebo gesto |
| Ctrl+J / Ctrl+Shift+J | Připojit hranu dovnitř plochy / přilepit plochu oblastí |
| Ctrl+R / Ctrl+E | Přepočítat papírové díly / exportovat SVG a PDF |
| F2 / F8 | Pojmenovat model a díl / Problémy a připravenost |
| F / Home | Zaměřit výběr / vše v aktivním pohledu |
| F1 | Připomenout postup a znovu zapnout tipy |

Zkratky F a Home používejte s fokusem v pracovním pohledu.
Tipy lze vypnout v **Zobrazení a pomoc → Zobrazovat tipy**; příkazy a
upozornění na problémy zůstávají dostupné.

## Stav ověření a historický návod

Test s novým uživatelem **AC-US08: NOT_RUN (0 účastníků)**.
Fyzický výtisk a sestavení **P3: NOT_RUN**. Tento rychlý start ani agentní
ověření GUI tato dvě ověření nenahrazují.

[Původní příručka 0.2 je zachovaná v archivu](archive/manual_cs-v0.2-before-workspace-2026-11-17.md).
Aktuální implementace ovládání:
[autorské okno](../src/archpapercraft/ui/author_window.py),
[pracovní kontexty](../src/archpapercraft/ui/author_workspace.py) a
[obnova práce](../src/archpapercraft/ui/author_recovery.py).
