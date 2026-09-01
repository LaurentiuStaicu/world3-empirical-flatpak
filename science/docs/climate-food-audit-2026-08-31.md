# Auditul legăturii climă–hrană — 31 august 2026

## Decizie

Temperatura medie globală nu intră deocamdată ca feedback alimentar în BAU
Hibrid 2026. O legătură climatică simplă a fost puțin mai bună în originile de
dezvoltare, dar a eșuat clar în perioada independentă 2019–2024. Versiunea
Flatpak 0.10.0 rămâne neschimbată.

Această respingere nu înseamnă că încălzirea nu afectează agricultura. Înseamnă
numai că media termică globală, fără distribuția regională a căldurii, secetă,
umiditatea solului, irigații și comerț, nu îmbunătățește robust proiecția
agregatului alimentar mondial folosit de aplicație.

## Date

- Temperatura: NASA GISTEMP v4, indicele global combinat uscat–ocean,
  1880–2025, anomalie față de media 1951–1980.
- Hrană: FAOSTAT, `World / Food / Gross per capita Production Index`, până în
  2024.
- Reper structural: puntea alimentară existentă BAU Hibrid, alcătuită din 25%
  semnalul alimentar World3 și 75% capacitatea industrială, în spațiu logaritmic.

Snapshotul GISTEMP este fixat prin SHA-256
`6cfa44e7bbacd9b12cb10bdd64b3182c2735fa3f3a95688e1f7bc8e5dfcece93`.
NASA poate revizui anii istorici când sosesc observații întârziate, de aceea
hashul și data accesului sunt păstrate în fișierul de proveniență.

## Controlul informației din viitor

La fiecare origine 1995, 2000, 2005, 2010, 2015 și 2019:

1. candidatul World3 este selectat numai cu observațiile disponibile atunci;
2. răspunsul rezidualului alimentar la schimbarea temperaturii este estimat
   numai pe cei 20 de ani anteriori;
3. temperatura viitoare este extrapolată din tendința celor 20 de ani
   anteriori;
4. temperaturile efectiv observate după origine nu sunt folosite ca predictori;
5. sunt evaluate următoarele cinci observații alimentare.

Coeficientul climatic este regularizat și limitat la intervalul −0,15…0 per
grad Celsius. Această restricție conservatoare împiedică modelul să transforme
o corelație pozitivă accidentală într-un presupus beneficiu climatic.

## Rezultat

| Perioadă | Puntea existentă, log-RMSE | Puntea climatică, log-RMSE | Schimbare |
|---|---:|---:|---:|
| origini de dezvoltare 1995–2015 | 0,01163 | 0,01137 | +2,27% |
| holdout independent 2019–2024 | 0,00559 | 0,00872 | −56,09% |
| toate originile | 0,01086 | 0,01097 | −1,02% |

Semnul `+` indică reducerea erorii, iar `−` deteriorarea. Criteriul predeclarat
cerea îmbunătățire atât înainte de 2019, cât și în holdout. Criteriul nu este
îndeplinit.

## Interpretare

Agregarea globală atenuează șocurile regionale: un eșec de recoltă într-o zonă
poate fi compensat de condiții mai bune, stocuri sau importuri în alta. În plus,
temperatura medie nu măsoară direct zilele peste pragurile biologice, deficitul
de apă, umiditatea solului ori sincronizarea stresului cu fazele de creștere ale
culturilor. Aceste variabile sunt mai apropiate de mecanismul agronomic.

Prin urmare, un feedback alimentar central nu trebuie construit prin aplicarea
unui multiplicator la temperatura globală. Următorul test trebuie să folosească
un indicator regional agregat și ponderat cu suprafața sau producția culturilor,
care să combine:

- extreme termice în sezonul de creștere;
- umiditatea solului și deficitul de precipitații;
- apă disponibilă pentru irigații;
- suprafață recoltată și randament pentru culturile principale;
- compensarea prin comerț și stocuri.

Codul este în `scripts/evaluate_climate_food_link.py`, iar rezultatele în
`outputs/climate_food/`.
