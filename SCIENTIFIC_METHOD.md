# BAU Hibrid 2026 — metodă și validare

## Definiție

BAU Hibrid 2026 v0.10.0 păstrează o singură rulare a modelului oficial World3-03,
scenariul 2 (BAU2), cu un vector comun de șapte parametri structurali. Cele
cinci ținte calibrate și cele trei diagnostice nu sunt prognoze independente.

Parametrii rulării centrale sunt:

| Parametru World3 | Valoare centrală |
|---|---:|
| resurse neregenerabile inițiale | 1,823 × 10¹² unități World3 |
| raport capital industrial / producție | 3,127 ani |
| durata medie a capitalului industrial | 14,161 ani |
| factorul randamentului terenurilor | 1,085 |
| factorul generării poluării persistente | 1,073 |
| timpul de înjumătățire al asimilării | 1,375 ani |
| mărimea normală dorită a familiei | 3,779 copii |

Pentru populație, industrie și bunăstare se estimează transformarea de scară
dintre unitățile interne World3 și seria observată. Pentru hrană și CO₂ anual
se aplică apoi două punți de observație fixe. Puntea alimentară este o medie
geometrică ponderată între semnalul alimentar World3 (25%) și capacitatea
industrială de input pe locuitor (75%). CO₂ anual este reprezentat prin
activitatea industrială totală. Ponderile au fost alese din cinci variante
predeclarate folosind numai informație încheiată în 2018.

Punțile nu participă la selecția configurației structurale, nu introduc stocuri
și nu modifică ecuațiile sau feedbackurile World3. Generarea și stocul de
poluare persistentă continuă să influențeze rularea World3, dar nu sunt pretinse
drept observații directe ale CO₂. Nivelul fiecărei ieșiri afișate este ancorat
la ultima observație după selecția structurii.

## Selecție și testare

Au fost evaluate 128 de configurații predeclarate, construite prin eșantionare
Latin hypercube în intervalele documentate în manifest. Evaluarea are două
etape. Modelul de validare este selectat numai cu date până în 2018, iar
2019–ultimul an disponibil rămâne test recent neatins pentru acea procedură.
După păstrarea rezultatelor testului, un model de producție separat este refăcut
cu toate datele disponibile și generează linia afișată. Prin urmare,
performanța holdout nu este atribuită refitului final.

În testul recent, eroarea MAPE este:

| Indicator | BAU2 ancorat | BAU Hibrid | Schimbare |
|---|---:|---:|---:|
| populație | 0,74% | 0,44% | mai bun |
| industrie/locuitor | 1,36% | 1,15% | mai bun |
| hrană/locuitor | 4,45% | 0,54% | mai bun |
| CO₂ anual, proxy activitate | 7,35% | 6,61% | mai bun |
| bunăstare | 0,69% | 0,62% | mai bun |

Validarea multi-origin rămâne mixtă la nivelul întregului sistem: hibridul este
mai bun pentru industrie, hrană și CO₂, dar mai slab pentru populație și ușor
mai slab pentru bunăstare. Erorile multi-origin ale hranei și CO₂ scad de la
10,31% la 2,03% și de la 12,00% la 7,02%. Aceste rezultate susțin utilitatea
punților ca modele de observație; nu demonstrează superioritatea generală a
structurii World3 și nu rezolvă limitele sale cauzale.

## Plaja albastră și identificabilitatea

Plaja de sensibilitate folosește 12 dintre cele mai bune configurații finale
care nu au necesitat mapări la limitele admise și trec limitele de
plauzibilitate 2030–2035. Linia centrală este medoidul acestor rulări: o rulare
World3 efectivă, nu o medie variabilă pe indicator. Plaja arată sensibilitatea
la parametri și nu reprezintă un interval de încredere, P10–P90 probabilistic
sau probabilitatea unui colaps. P10 și P90 sunt cuantilele punctuale autentice
ale ansamblului. Medoidul nu este forțat în interval și poate apărea în afara
lui pentru un diagnostic latent care nu a participat la definirea medoidului.

Aplicația clasifică potrivirea retrospectivă după MAPE: bună până la 5%,
moderată între 5% și 15%, slabă între 15% și 30% și foarte slabă peste 30%.
Clasificarea este un avertisment descriptiv, nu o probabilitate și nu modifică
selecția modelului. În versiunea actuală, hrana este plafonată la sprijin
moderat deoarece folosește o punte fără feedback structural propriu, iar
proxy-ul CO₂ rămâne limitat.

Separat, sprijinul empiric al proiecției primește un scor conservator 0–9.
Potrivirea istorică primește 0–3 puncte la pragurile 30/15/5%, holdoutul recent
0–3 puncte la pragurile 10/5/2%, iar validarea multi-origin 0–3 puncte la
pragurile 15/7/3%. Dacă procedura pierde față de BAU2 în validarea multi-origin,
scorul este plafonat la 5; dacă pierde și recent, și multi-origin, este plafonat
la 2. Calificativele sunt: ridicat 8–9, moderat 5–7, limitat 3–4 și foarte
limitat 0–2. Acest scor este o regulă de comunicare transparentă, nu o
probabilitate și nu înlocuiește un interval predictiv.

Intervalele celor 12 configurații acoperă peste jumătate din domeniul prior
pentru șase parametri din șapte. Numai mărimea dorită a familiei este ceva mai
restrânsă. Datele globale agregate nu identifică unic resursele, capitalul,
terenul sau mecanismele de poluare.

## Diagnostice suplimentare

Producția industrială totală este observată și ancorată exact în 2025, dar nu
primește o pondere separată în calibrare deoarece este algebric redundantă cu
populația și producția pe locuitor. Stocul persistent de poluare și resursele
neregenerabile rămase sunt stări latente World3 fără serii observate direct
echivalente. Resursele folosesc un numitor comun, stocul BAU din 1900 = 100;
BAU2 pornește astfel de la 200, nu de la un procent propriu resetat la 100.

PySD avertizează când o rulare solicită unui tabel lookup World3 valori în
afara domeniului tabulat și extrapolează cu valoarea de capăt. Aceste
avertismente nu sunt suprimate global. Generatorul le capturează exclusiv pe
cele provenite din `pysd/py_backend/lookups.py`, păstrează vizibile toate
celelalte categorii și exportă pentru fiecare dintre cei 128 de candidați
numărul total, împărțirea sub/peste domeniu și numărul mesajelor distincte în
`lookup_extrapolation_audit.csv`. Fișierul este un diagnostic de validitate a
domeniului, nu o măsură directă a erorii de prognoză; versiuni viitoare trebuie
să testeze explicit dacă respingerea candidaților cu extrapolări structurale
materiale îmbunătățește validarea în afara eșantionului.

În release-ul actual, rularea centrală (candidatul 114) produce 1.273 de
evenimente de avertizare, aparținând la 21 de mesaje distincte; cele 12 rulări
admise au între 884 și 1.693 de evenimente. Numărul mare confirmă că domeniul
tabelelor lookup trebuie tratat ca limită metodologică explicită înainte ca
modelul să poată fi prezentat drept prognoză robustă.

## Limite

- Puntea alimentară nu este un sector agricol structural nou și nu modelează
  explicit apa, solul, clima sau îngrășămintele.
- CO₂ anual este un proxy al activității industriale, nu o măsurare a generării
  generice sau a stocului de poluare persistentă World3.
- HDI este un proxy pentru Human Welfare Index, nu aceeași mărime.
- Industria World Bank include construcțiile.
- EROI, clima, apa, mineralele, infrastructura AI, conflictele și politicile nu
  sunt încă feedbackuri explicite în rularea centrală.
- Agregarea globală ascunde diferențele regionale și distribuționale.
- După ultimul an observat, valorile sunt scenarii condiționale, nu predicții
  punctuale garantate.

Parametrii compleți, intervalele, mapările și identificatorii configurațiilor
sunt în `data/scenarios/bau_hybrid_2026_manifest.json`; testele retrospective
sunt în `data/scenarios/backtest_*.csv`, iar diagnosticul identificabilității
este în `data/scenarios/parameter_identifiability.csv`.
