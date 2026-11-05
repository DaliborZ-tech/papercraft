# Nezávislá revize přípravného zadání

Datum: 5. listopadu 2026. Rozsah: tento přípravný balík, nikoli implementace produktu.

Návrh posoudil samostatný reviewer agent. Po opravách proběhla druhá revize s verdiktem **APPROVED_IN_SCOPE**, bez zbývajících zásadních nálezů. Jde o agentní revizi zadání, nikoli PO přijetí P2 kontraktu nebo certifikaci geometrického jádra.

## Zapracované nálezy

1. Validace parametrů rozlišuje kladné konstrukční rozměry, nezáporné volitelné hodnoty a podepsané souřadnice/úhly. Nulová souřadnice nebo záporná rotace není obecně chyba.
2. Závislosti epic jsou capability-level. Skutečná ticket queue je acyklická; fyzický proof je dokončovací podmínka řezu, nikoli předchozí dokončený celý epic.
3. Mountain/valley polarita a orientace chlopní mají explicitní analytická kritéria AC-C09/C10.
4. SVG má skupiny celých dílů s vnořenými sémantickými rolemi. Přesun celého dílu v editoru ověřuje AC-X10.
5. Potvrzení autorského varování není prominutí chyby integrity ani důkaz úplného tisku při ořezu mimo fyzický formát. AC-L10.
6. Referenční dům má výslovně rozlišené dvě boční a dvě čelní stěny i štítové trojúhelníky.

Upřesnění druhé revize: PC-007 může připravit výběr protikusů, ale finální GUI důkaz AC-C02 přes dvě stránky vyžaduje PC-008. Zůstává pending do integračního demu PC-009, nikoli předčasný PASS v PC-007. Queue tento odklad výslovně eviduje.

## Mechanické kontroly

Validní JSON fronty a zdrojového manifestu, unikátní ticket ID, existující závislosti, acyklický graf, platné odkazy na akceptační ID, unikátní AC a rozsah autorizace P0/P1. Balík obsahuje 16 epic, 12 počátečních ticketů a 61 explicitních AC; epiky navíc obsahují vlastní produktové podmínky.

## Co zůstává záměrně neověřené

V této analytické přípravě se neklonovalo do uživatelova VS Code, nespouštěla aplikace ani pytest, neměnil GitHub repozitář, neověřoval konkrétní grafický editor a nestavěl fyzický model. Tyto důkazy mají své místo v P0 až P3. Odhad pracnosti a definitivní výběr geometrického řešení musí vzniknout až z provedeného discovery a spike.
