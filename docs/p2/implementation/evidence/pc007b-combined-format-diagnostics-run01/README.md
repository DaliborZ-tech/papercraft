# Kombinace C a LINE — zachovaná diagnostika

11.11.2026, root, izolovaný `papercraft-c-integrated-authoring`, vlastní
`PYTHONPATH=.../src`, Qt offscreen. Tyto iterace předcházely finálnímu připnutí;
nejde o finální celkový JUnit ani o nový uživatelský test.

- `merge-targeted-run01`: 117 PASS, původní oba registry spojené do schema8.
- `c-and-line-run01`: žádné testy; autor zadal neexistující název testového
  souboru. Chyba spuštění, žádné tvrzení o produktu.
- `c-and-line-run02`: 103 PASS / 1 FAIL. Historický schema5 fixture pocházel
  z aktuálního formátu, ale ponechal nový C registr. Doplněno odstranění
  skutečně tehdy neexistujícího registru; parser nebyl oslaben.
- `combined-run01`: 3 PASS / 1 FAIL, skutečný integrační nález: zdrojový
  kontext C obsahoval historii rozdělené vzdálené plochy, ale kontrola jejího
  rámu stále vyžadovala aktivní ID hrany. Oprava používá sémantické rozřešení
  původní celé osy a kotvy; první dítě ani nejbližší bod se nepoužívá.
- `combined-run02`: 2 PASS / 1 FAIL. Opravený produkt již přešel až k poslednímu
  očekávání; autor zaměnil stav materiálového reportu
  `CANONICAL_NATIVE_MATERIAL_COMPOSED` za stav jednotlivého spoje
  `CERTIFIED_APPROXIMATE`. Test nyní ověřuje obě skutečné veřejné vrstvy.
- `combined-run03`: 50 PASS / 0 FAIL, včetně opraveného historického fixture,
  kopírovacího načtení obou formátů6/7, ochrany původních bytů a skutečného
  pozitivního C s rozdělenou osou vzdáleného materiálového dílu.

Plné původní logy jsou zachované v této složce. Výběry se překrývají a jejich
počty se nesčítají. Nové finální ověření musí být navázané na vydávaný zdroj;
tyto historické běhy jej nenahrazují. Nový člověk0/NOT_RUN, fyzické P3/NOT_RUN.
