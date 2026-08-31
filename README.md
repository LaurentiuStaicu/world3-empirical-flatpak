# World3 Empirical pentru elementary OS

Aplicație Vala/GTK 4 care compară datele globale observate cu scenariile
World3-03 BAU și BAU2 originale și cu proiecția condițională
**BAU Hibrid 2026**. Interfața este nativă pentru elementary OS 8 și
funcționează complet offline după instalare.

## Ce se schimbă în versiunea 0.10.0

- păstrează neschimbată selecția structurală World3-03 și aceeași rulare
  centrală cu șapte parametri;
- adaugă două punți de observație selectate exclusiv cu date încheiate în 2018;
- pentru FAOSTAT combină în spațiu logaritmic 25% semnalul alimentar World3 și
  75% capacitatea industrială de input;
- pentru CO₂ anual folosește activitatea industrială drept proxy observabil,
  păstrând generarea și stocul persistent de poluare drept stări World3 latente;
- reduce MAPE istoric al hranei de la aproximativ 41% la 7% și al proxy-ului
  CO₂ de la aproximativ 31% la 18%;
- îmbunătățește toate cele cinci holdouturi recente și, pentru hrană și CO₂,
  validarea multi-origin;
- etichetează explicit aceste relații drept punți empirice, nu drept feedbackuri
  noi sau dovadă că structura World3 a fost validată integral.

## Schimbările introduse în 0.9.2

- separă explicit potrivirea retrospectivă in-sample de sprijinul empiric al
  proiecției;
- calculează un scor conservator 0–9 din MAPE istoric, holdoutul recent și
  validarea multi-origin;
- plafonează scorul când hibridul este mai slab decât BAU2, astfel încât o
  potrivire istorică bună să nu fie confundată cu putere de prognoză;
- clasifică sprijinul proiecției ca moderat pentru populație, industrie și
  bunăstare, limitat pentru hrană și foarte limitat pentru proxy-ul poluării;
- păstrează neschimbate traiectoriile și cuantilele v0.9.1: această versiune
  îmbunătățește evaluarea și comunicarea incertitudinii, nu acuratețea numerică.

## Schimbările introduse în 0.9.1

- P10 și P90 sunt cuantilele punctuale autentice ale celor 12 rulări și nu mai
  sunt deformate pentru a cuprinde obligatoriu linia centrală;
- cardurile avertizează atunci când medoidul cade în afara P10–P90;
- fiecare indicator observat primește o calificare retrospectivă: bună,
  moderată, slabă sau foarte slabă;
- hrana și poluarea sunt marcate explicit drept insuficiente pentru o prognoză
  autonomă, fără ajustări cosmetice ale retrospectivelor;
- validarea multi-origin spune direct dacă procedura este mai bună sau mai
  slabă decât BAU2 ancorat.

## Schimbările structurale introduse în 0.9.0

- graficul afișează numai BAU original, BAU2 original și BAU Hibrid 2026;
- observațiile sunt puncte negre independente;
- grila verticală este trasată la fiecare 5 ani, cu etichete la 10 ani;
- pointerul fixează cel mai apropiat an și afișează valorile tuturor modelelor;
- BAU Hibrid 2026 este acum o singură rulare World3-03, nu cinci ajustări
  independente ale curbelor;
- același vector de șapte parametri structurali determină simultan cele cinci
  ținte calibrate și trei diagnostice suplimentare;
- plaja albastră poate fi ascunsă și reprezintă sensibilitatea la configurații
  structurale alternative admisibile, nu un interval probabilistic.
- porțiunea retrospectivă a hibridului este albastră, subțire și întreruptă;
  proiecția este albastră, groasă și continuă;
- axele verticale folosesc valori rotunjite, iar unitatea apare în grafic;
- interfața afișează separat potrivirea istorică descriptivă, backtestul recent
  și validarea multi-origin;
- separă modelul de validare înghețat în 2018 de refitul final afișat, care
  folosește toate observațiile disponibile până în 2023–2025;
- alege linia centrală ca medoid: o singură rulare World3 reală, cea mai
  apropiată de centrul celor 12 configurații finale complet admisibile;
- filtrează plaja prin limite largi de plauzibilitate pentru 2030–2035,
  declarate în manifest și distincte de probabilități;
- producția industrială totală este ancorată exact la observația din 2025;
- resursele BAU, BAU2 și hibrid folosesc același numitor, stocul BAU din 1900,
  astfel încât diferențele de stoc inițial nu mai sunt ascunse;
- aplicația raportează explicit identificabilitatea slabă a parametrilor.

## Ce este și ce nu este BAU Hibrid 2026

BAU Hibrid 2026 pornește din scenariul 2 al modelului oficial World3-03. Un set
de 128 de configurații a fost declarat înaintea selecției. Fiecare configurație
schimbă aceiași șapte parametri pentru întregul sistem: resursele inițiale,
raportul capital/producție, durata de viață a capitalului industrial,
randamentul terenurilor, generarea și asimilarea poluării și mărimea dorită a
familiei.

Validarea și proiecția finală sunt două etape distincte. Mai întâi, o
configurație este aleasă numai cu observații disponibile până în 2018, după
prognoze retrospective 2005–2009, 2010–2014 și 2015–2018. Intervalul
2019–ultimul an observat rămâne test neatins pentru acea procedură. Rezultatele
recent și multi-origin rămân mixte și sunt afișate fără cosmetizare.

Numai după încheierea evaluării, aplicația construiește refitul final afișat,
folosind toate observațiile disponibile. Dintre configurațiile cu mapări
admisibile și fără încălcarea limitelor de plauzibilitate, păstrează primele 12
și alege drept centru rularea cea mai apropiată de mediana traiectoriilor lor.
Backtestul nu trebuie atribuit acestei linii finale, deoarece ea a văzut datele
recente.

Populația, industria și bunăstarea folosesc o transformare de scară către
unitatea observată. Hrana și CO₂ anual folosesc suplimentar două punți de
observație fixe, alese fără date ulterioare lui 2018. Acestea transformă ieșirea
afișată, dar nu schimbă selecția parametrilor, stocurile sau feedbackurile
World3. Fiecare nivel este ancorat la ultima observație. Banda albastră este o
plajă de sensibilitate între cele mai bune configurații structurale cu mapări
admisibile; nu este un interval de încredere. P10 și P90 sunt păstrate ca
valori autentice, iar medoidul poate rămâne în exterior pentru un diagnostic
latent care nu a fost folosit la definirea sa. Limitele de plauzibilitate
folosesc reperul demografic UN WPP 2024 și praguri largi pentru hrană,
industrie și bunăstare. BAU și BAU2 originale rămân referințe nemodificate.

Modelul este experimental și condițional. Nu estimează probabilitatea unui
„colaps” și nu identifică unic parametrii adevărați ai sistemului mondial.

## Surse incluse

- World Bank WDI: populație și valoarea adăugată a industriei;
- FAOSTAT Production Indices: producția alimentară mondială pe locuitor;
- World Bank/EDGAR: emisiile antropice anuale folosite ca indicator observat al
  activității industriale; generarea și stocul persistent World3 rămân latente;
- UNDP Human Development Report 2025: HDI;
- UN World Population Prospects 2024: reper demografic extern;
- World3-03 scenario 2: traiectoria structurală BAU2.
- Energy Institute Statistical Review 2026: reper pentru viitoarea calibrare
  energetică până în 2025;
- IEA Key Questions on Energy and AI: 485 TWh în 2025 și aproximativ 950 TWh
  în 2030 pentru centrele de date, păstrate ca ancore pentru viitorul submodul
  AI, nu ca observații EROI.

Fișierul `data/scenarios/bau_hybrid_2026_manifest.json` conține metoda,
parametrii, limitele și candidații reținuți. Rezultatele testului recent și ale
validării multi-origin se află în fișierele `backtest_*.csv`, iar
`parameter_identifiability.csv` arată că șase parametri din șapte rămân slab
identificați de seriile globale agregate. `candidate_ranking.csv` documentează
refitul final și filtrele de plauzibilitate, iar
`validation_candidate_ranking.csv` păstrează selecția înghețată pentru test.
`bridge_validation.csv` păstrează căutarea predeclarată a celor cinci ponderi
pentru fiecare punte și alegerea făcută fără date post-2018.

## Construire în elementary OS 8

Din directorul proiectului:

```bash
./build-flatpak.sh
```

Sau direct:

```bash
flatpak run org.flatpak.Builder --user --install --force-clean build-dir \
  io.github.laurentiustaicu.World3Empirical.yml
```

Pornire:

```bash
flatpak run io.github.laurentiustaicu.World3Empirical
```

Validare statică înainte de construire:

```bash
python3 scripts/validate.py
```

Codul auditabil care generează scenariile EROI se află în `model/`. El nu este
executat la construirea Flatpakului, astfel încât aplicația rămâne mică și
offline; instrucțiunile de regenerare sunt în `model/README.md`.

## Limite de interpretare

- producția industrială World Bank este un proxy și include construcțiile;
- puntea alimentară este o aproximație a dependenței producției agricole de
  inputurile industriale, nu un sector agricol recalibrat structural;
- fluxul anual de CO₂ este un proxy de activitate industrială; nu observă
  generarea generică sau stocul latent de poluare persistentă din World3;
- producția industrială totală este diagnostic derivat și nu este ponderată a
  doua oară în calibrare;
- stocul persistent de poluare și resursele neregenerabile rămase sunt stări
  latente ale World3, nu observații empirice;
- HDI nu este identic cu Human Welfare Index din World3;
- agregatul BAU/BAU2 nu descrie distribuția regională, conflictele sau
  politicile ca sectoare explicite;
- EROI, apa, clima, mineralele și AI nu sunt încă feedbackuri cuplate în
  rularea centrală și nu trebuie presupus că proiecțiile le includ;
- după ultimul an observat, toate valorile sunt condiționale pe structură și
  ipoteze.

## Licențe

Codul aplicației este MIT. Seriile FAOSTAT sunt CC BY 4.0. Celelalte serii își
păstrează termenii instituțiilor-sursă. World3-03 este utilizat ca model de
referință, iar proveniența numerică este documentată în manifest.
