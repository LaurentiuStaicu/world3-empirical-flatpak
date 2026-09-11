# Registru de prognoze externe — 11 septembrie 2026

## Rezultat implementat

Registrul separat `science/data/forecasts/eia-steo-2026-09-11.json` conține
patru valori transcrise manual din pagina oficială EIA STEO, verificată la
11 septembrie: vânzări de electricitate SUA 4135/4211 TWh și emisii energetice
4821/4816 Mt CO₂ pentru 2026/2027. Publicarea declarată este 9 septembrie,
iar închiderea intrărilor prognozei este 3 septembrie.

Sursa: https://www.eia.gov/outlooks/steo/

Acestea sunt prognoze instituționale, nu observații și nu consum exclusiv AI.
Emisiile sunt pentru întregul sistem energetic SUA; împărțirea lor la
vânzările de electricitate nu produce intensitatea emisiilor rețelei.
Un miliard kWh este un TWh. Vânzările, consumul total și generarea sunt
indicatori diferiți și nu se substituie unul altuia.

## Proveniență și disponibilitate

Fișierul este o transcriere verificată, nu copia brută a paginii. Nu pretindem
că am arhivat octeții ediției originale din 9 septembrie. Pagina live poate
fi corectată după publicare. Din acest motiv `available_from` este conservator
11 septembrie, data capturii, nu data nominală a ediției.

Modulul `forecast_vintages.py` validează tipul dovezii, cronologia, unitățile
declarate, valorile finite și duplicatele. Filtrarea după data originii
exclude edițiile viitoare și păstrează toate versiunile disponibile.
Selectarea ultimei ediții nu se face implicit. Funcția de acces ca observații
de calibrare refuză aceste înregistrări; pipeline-ul central nu le importă.

## Ce permite și ce nu demonstrează

Acesta este un contract de date pentru comparații prospective viitoare.
Nu există încă observații anuale finale pentru 2026/2027 cu care să calculăm
eroarea acestor prognoze. Nu s-a îmbunătățit sau recalibrat curba centrală.
Testele verifică izolarea temporală și integritatea semantică a registrului.

Pentru utilizare ulterioară trebuie arhivate documentele originale cu hash,
identificate edițiile istorice și adăugate observații cu aceeași definiție,
geografie și unitate. Eroarea se va calcula separat pe an țintă și orizont,
fără a rescrie edițiile vechi cu valori revizuite.

## Ordinea următoarelor experimente

1. Separarea energiei, emisiilor și concentrațiilor atmosferice într-un modul
   experimental, cu bilanțuri și unități explicite.
2. Verificarea articolului climatic integral și a materialelor suplimentare
   înainte de preluarea parametrilor. Rezumatul de presă nu justifică un
   multiplicator global de 20–30% în World3.
3. Testarea fiecărui feedback separat, apoi combinat, cu audit de dublă
   numărare a daunelor deja reprezentate prin poluarea persistentă.
4. Promovarea numai după comparație temporală cu un reper simplu și cu BAU2;
   originile deja consultate sunt teste de dezvoltare, nu holdout neatins.
