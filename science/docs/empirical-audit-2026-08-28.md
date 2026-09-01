# Audit empiric preliminar — snapshot 28 august 2026

Acest audit verifică modelul înainte de recalibrare. Seriile observate sunt
normalizate la 2010=100, iar perioada 2019–2024 este păstrată ca test temporal.
Rezultatele nu reprezintă validarea BAU2 și nu sunt folosite încă drept
prognoză.

## Acoperirea datelor

| Concept | Serie observată | Ani | Utilizare curentă |
|---|---|---:|---|
| Populație | World Bank `SP.POP.TOTL` | 1960–2025 | calibrare și testare, provizoriu până la integrarea UN WPP |
| Producție industrială | World Bank `NV.IND.TOTL.KD` | 1992–2025 | proxy provizoriu; include construcțiile și valoarea adăugată |
| Hrană pe locuitor | World Bank `AG.PRD.FOOD.XD` / populație | 1961–2020 | exclusă momentan din calibrare |
| Emisii CO2 | World Bank `EN.GHG.CO2.MT.CE.AR5` | 1970–2024 | indicator observat auxiliar; nu calibrează direct stocul de poluare World3 |

## Rezultatul testului necalibrat

În intervalul 2019–2024, modelul tehnic World3 din 1974 are o eroare procentuală
medie absolută de aproximativ 3,3% pentru populație și 35,4% pentru proxy-ul
producției industriale. În 2024, indicele populației observate este 116,3 față
de 111,0 în model, iar indicele industrial observat este 150,1 față de 78,7.

Acest contrast este important: apropierea populației nu compensează ratarea
traiectoriei industriale. Modelul nu trebuie declarat „validat” printr-o medie
agregată a seriilor.

Proxy-ul alimentar are numai două observații în fereastra de test și o ruptură
metodologică vizibilă în seria lungă. Până la reconstruirea indicatorului din
FAOSTAT pe bază fizică și cu metadate de revizie, seria este marcată
`excluded_from_calibration`.

Pentru modelul oficial World3-03, pe aceeași bază 2010=100, scenariul BAU2 are
în holdout o MAPE de 2,5% la populație și 9,9% la proxy-ul industrial, față de
4,0% și 28,2% pentru BAU. Acest rezultat compară forma și ritmul seriilor după
normalizare; nu validează nivelurile absolute și nu demonstrează că traiectoria
viitoare BAU2 este cea corectă.

Comparația dintre fluxul anual de CO2 și stocul agregat de poluare persistentă
este conceptual neomogenă. CO2 poate alimenta un modul climă-carbon sau o
ecuație explicită flux–stoc, dar nu poate fi folosit ca observație directă a
indicelui latent World3.

## Ce este verificat acum

Fișierul oficial Vensim `World3_03_Scenarios.mdl` este păstrat integral în
proiect. Scenariul 1 reproduce BAU World3-03, iar scenariul 2 reproduce BAU2,
cu stocul inițial de resurse neregenerabile mărit de la 1×10^12 la 2×10^12
unități. Aceste rulări sunt o bază de referință, nu o recalibrare empirică.

În fereastra 2025–2035, BAU-ul oficial reduce producția industrială pe locuitor
cu 36,8%, hrana pe locuitor cu 22,0% și indicele bunăstării cu 25,9%, în timp ce
populația scade cu 2,1% față de 2025. BAU2 menține încă producția industrială pe
locuitor în creștere cu 10,8%, dar hrana pe locuitor scade cu 12,9%, poluarea
persistentă crește cu 49,5%, iar bunăstarea scade cu 2,8%. Aceste valori sunt
ieșiri condiționale ale modelului nerecalibrat, nu prognoze cu probabilitate
atribuită.

## Următorul prag de calitate

Calibrarea va începe numai după înlocuirea proxy-ului alimentar, adăugarea unui
registru energetic și material și definirea unei ecuații de observație pentru
poluarea latentă. Parametrii vor fi estimați pe un interval istoric și evaluați
pe ani ținuți complet în afara ajustării.
