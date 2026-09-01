# Audit regional climă–agricultură — 31 august 2026

## Decizie

Extensia regională testată nu intră în proiecția centrală BAU Hibrid 2026
v0.10.0. Indicatorul prospectiv a fost mai bun în holdoutul 2019–2024, dar mai
slab pe originile de dezvoltare. Regula stabilită înaintea testului cerea o
îmbunătățire în ambele perioade.

Aceasta este o respingere a indicatorului anual pe țări, nu a mecanismului
climă–hrană. Rezultatul arată că media anuală națională este încă prea grosieră
pentru randamentele culturilor.

## Date și proveniență

- FAOSTAT, `Cereals, primary`, elementul `Production`, unitatea `t`, 1961–2024;
- anomalii anuale ale temperaturii și precipitațiilor pe țări, informații ERA5
  Copernicus prelucrate de Our World in Data;
- asociere FAOSTAT M49–ISO3 prin `pycountry`; agregatele regionale sunt excluse;
- 174 de țări în panoul rezultat;
- producția mapată reprezintă minimum 98,36% din totalul mondial FAOSTAT în
  1992–2024 și o mediană de 99,71%; 1990–1991 sunt păstrați, dar marcați drept
  tranziție de coduri post-sovietice, cu acoperire mai mică.

Fișierele brute, amprentele SHA-256 și limita de acoperire sunt fixate în
`data/processed/regional_cereal_climate_panel_2026.provenance.json`.
Checkpointul compact poate omite arhiva FAOSTAT brută; proveniența păstrează
adresa exactă și amprenta necesară pentru redescărcare și verificare.

## Indicatorul testat

La fiecare origine de prognoză s-au recalculat, fără acces la anii ulteriori:

1. ponderi naționale din producția medie de cereale a ultimilor zece ani;
2. medii și deviații standard climatice pe ultimii 20 de ani;
3. stres termic pozitiv: `max(z temperatură, 0)`;
4. stres de uscăciune pozitiv: `max(-z precipitații, 0)`;
5. media egal ponderată între căldură și uscăciune, agregată cu ponderile de
   producție.

Răspunsul hranei a fost estimat din variația anuală a reziduului logaritmic al
punții alimentare existente, cu regularizare ridge și coeficient constrâns la
intervalul `[-0,15, 0]` pe unitate de stres standardizat.

Au fost separate două experimente:

- `conditional_observed_climate`: folosește clima realizată după origine; este
  numai diagnostic de mecanism/nowcast, nu prognoză;
- `prospective_climate`: temperatura fiecărei țări este extrapolată exclusiv
  din tendința ultimilor 20 de ani, iar precipitațiile revin la media ultimilor
  zece ani. Numai această ramură decide integrarea.

## Protocol temporal

Originile sunt 2005, 2010, 2015 și 2019, cu orizont de cinci ani. Primele trei
formează dezvoltarea; 2019–2024 este holdoutul independent. La fiecare origine,
candidatul World3, scala observațională, ponderile, normele climatice,
coeficientul de răspuns și prognoza climatică folosesc numai informații până la
anul originii.

## Rezultate

| Perioadă | Punte existentă log-RMSE | Climă prospectivă log-RMSE | Schimbare față de puntea existentă | Climă observată condițional log-RMSE |
|---|---:|---:|---:|---:|
| Dezvoltare 2005/2010/2015 | 0,011991 | 0,015701 | −30,95% | 0,012597 |
| Holdout 2019–2024 | 0,005589 | 0,003564 | +36,23% | 0,012203 |
| Toate originile | 0,010754 | 0,013714 | −27,53% | 0,012500 |

Semnul `+` în coloana schimbării înseamnă eroare redusă. În holdout, prognoza
climatică simplă a ajutat, dar ramura condițională cu clima efectiv observată a
fost cu 118,34% mai slabă decât puntea existentă. Acest contrast este un
avertisment împotriva interpretării cauzale a câștigului dintr-o singură
origine.

## De ce nu se integrează

- criteriul de dezvoltare este ratat cu o marjă mare;
- câștigul holdout poate proveni din revenirea la medie a prognozei de
  precipitații, nu din identificarea robustă a daunelor climatice;
- media anuală pe țară amestecă sezoane și regiuni agricole diferite;
- producția totală reflectă irigația, fertilizanții, schimbarea suprafeței,
  compoziția culturilor și adaptarea, nu numai vremea;
- precipitația anuală nu este echivalentă cu umiditatea solului sau deficitul
  de apă în perioada de vegetație.

## Următorul test justificat

Următoarea extensie nu trebuie să ajusteze din nou aceiași hiperparametri.
Trebuie schimbată măsurarea mecanismului: temperatură și umiditate a solului în
lunile de vegetație, pe celule sau regiuni agricole, ponderate separat pentru
grâu, porumb și orez. Până atunci, BAU Hibrid 2026 v0.10.0 rămâne neschimbat.
