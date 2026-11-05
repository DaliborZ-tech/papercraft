# Poučení z P0/P1

- Správná plocha nestačí: kuželový lichoběžník má přesnou plochu a spojovací strany o13.439mm delší. Každý nový rotační princip dostane analytické délky hran/oblouků, topologii i pozdější fyzický proof.
- Délky každého trojúhelníku nestačí: uzavřená krabice bez švů má7neoznačených prasklin. Kontrolovat úplnost, explicitní hranice, non-tree closure a překryvy samostatně.
- Směr indexu není geometrická orientace: tab uvnitř materiálu a změna mountain/valley po přeznačení mají společnou příčinu. Persistovat orientované významové hrany a printed side.
- Jeden interní unit kontrakt musí platit přes sample/UI/export; deklarace mm bez odstranění unit_to_mm z pipeline vytvořila ×1000. Testovat ekvivalentní vstupy a skutečně exportovanou délku.
- Test count není produktová přejímka:213PASS/6cílenýchFAIL. Nové AC potřebují konkrétní numeriku, desktop a editor, žádné přebírání historického „funguje“.
- Stav dokumentace není stav výrobku: agentní revize P1 pouze schvaluje důkazy a připravenost implementačního zadání; P2 přijímá vlastník a P3 se musí vytisknout a postavit.
