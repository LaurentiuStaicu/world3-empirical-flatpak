# Istoric versiuni

## 0.10.2 — 2 septembrie 2026

- păstrează neschimbate rezultatele științifice ale modelului 0.10.0;
- compară exact structura, textele, identificatorii și ordinea rezultatelor reproduse;
- acceptă numai diferențe numerice de ordinul preciziei mașinii între platforme;
- raportează abaterea numerică absolută maximă și respinge orice modificare peste
  toleranța declarată de 1e-12;
- adaugă teste care disting variația benignă de virgulă mobilă de schimbările
  numerice, textuale sau structurale reale.

## 0.10.1 — 1 septembrie 2026

- păstrează neschimbate rezultatele științifice ale modelului 0.10.0;
- citește seriile și diagnosticele după numele coloanelor, nu după poziție;
- separă erorile de integritate de rezultatele științifice nefavorabile;
- adaugă schemă de date, manifest determinist și hash-uri SHA-256;
- generează versiunea ferestrei „Despre” direct din versiunea Meson;
- include generatorul, datele procesate, implementarea World3-03 și testele necesare reproducerii;
- descarcă arhiva FAOSTAT brută din sursa oficială și îi verifică dimensiunea și SHA-256 înainte de reproducere;
- elimină suprimarea globală a avertismentelor din simulările candidate;
- rezumă separat, pentru fiecare candidat, extrapolările tabelelor lookup World3/PySD;
- regenerează în CI auditul climatic, EROI și agricol și rulează toate cele 55 de teste științifice.

## 0.10.0 — 30 august 2026

- păstrează neschimbată selecția structurală și rularea World3 centrală;
- introduce două punți de observație alese numai cu date până în 2018;
- combină pentru hrană 25% semnal World3 și 75% capacitate industrială de input;
- tratează CO₂ anual ca proxy de activitate industrială, separat de stocul
  persistent latent;
- îmbunătățește toate cele cinci holdouturi recente și validarea multi-origin
  pentru hrană și CO₂;
- exportă căutarea ponderilor în `bridge_validation.csv` și clarifică în
  interfață faptul că punțile nu sunt feedbackuri structurale noi.

## 0.9.2 — 30 august 2026

- redenumește calificativul in-sample drept „potrivire retrospectivă după MAPE”;
- adaugă un scor transparent 0–9 pentru sprijinul empiric al proiecției;
- combină potrivirea istorică, holdoutul recent și validarea multi-origin;
- plafonează calificativul dacă procedura hibridă pierde față de BAU2;
- marchează hrana drept proiecție cu sprijin limitat și poluarea drept proiecție
  cu sprijin foarte limitat;
- nu modifică artificial curbele sau cuantilele pentru a obține calificative
  mai favorabile.

## 0.9.1 — 30 august 2026

- elimină forțarea medoidului în interiorul benzii de sensibilitate;
- păstrează cuantilele P10–P90 punctuale autentice ale ansamblului;
- avertizează în carduri când rularea centrală este în afara P10–P90;
- clasifică vizibil potrivirea retrospectivă pentru fiecare indicator;
- marchează hrana și poluarea drept insuficiente pentru prognoze autonome;
- arată direct dacă validarea multi-origin este mai bună sau mai slabă decât
  BAU2 ancorat.

## 0.9.0 — 30 august 2026

- separă configurația înghețată pentru validare de refitul final afișat;
- folosește toate observațiile disponibile numai după evaluarea holdout;
- filtrează configurațiile finale prin limite de plauzibilitate documentate;
- alege linia centrală ca medoid al celor 12 rulări finale admisibile;
- ancorează producția industrială totală exact la observația din 2025;
- compară toate stocurile de resurse cu același numitor BAU-1900;
- clarifică în interfață faptul că backtestul nu aparține refitului final.

## 0.8.0 — 30 august 2026

- îngheață selecția structurală în 2018 și păstrează 2019–ultimul an ca test;
- extinde ansamblul predeclarat de la 28 la 128 de rulări World3-03;
- construiește plaja de sensibilitate din 20 de configurații admisibile;
- respinge drept central orice candidat care cere o mapare la limita impusă;
- adaugă producția industrială totală ca diagnostic observat, fără dublarea
  ponderii sale în calibrare;
- adaugă stocul persistent de poluare și resursele rămase ca stări latente;
- exportă identificabilitatea parametrilor și arată că șase din șapte rămân
  slab restrânși de date;
- afișează explicit rezultatele mixte ale validării multi-origin.

## 0.7.1 — 29 august 2026

- separă vizual traiectoria retrospectivă a hibridului de proiecția de după
  ultima observație;
- rotunjește reperele axei verticale și afișează unitatea direct în grafic;
- adaugă MAPE și abaterea medie pentru întreaga perioadă observată, marcate
  explicit drept diagnostic descriptiv, nu holdout;
- precizează că plaja provine din patru rulări structurale și că linia centrală
  nu este mediana;
- clarifică începutul seriei industriale, diferența total/per capita și faptul
  că proxy-ul CO₂ nu reprezintă stocul persistent de poluare.

## 0.7.0 — 29 august 2026

- înlocuiește cele cinci ajustări independente cu o singură rulare comună a
  modelului oficial World3-03 BAU2;
- selectează același vector de șapte parametri structurali pentru populație,
  industrie, hrană, poluare și bunăstare;
- folosește validare temporală rulantă până în 2018 și păstrează 2019–ultimul
  an ca test recent neatins;
- îmbunătățește 4 din 5 indicatori în testul recent și eroarea ponderată totală;
- redefinește banda albastră drept plajă de sensibilitate structurală, nu
  interval probabilistic.

## 0.6.1 — 29 august 2026

- adaugă explicit biblioteca matematică `libm` la legarea executabilului;
- corectează eroarea `undefined reference to round` din SDK-ul elementary OS 8.

## 0.6.0 — 29 august 2026

- păstrează numai BAU original, BAU2 original și BAU Hibrid 2026;
- transformă observațiile în puncte independente, nu într-o a patra curbă;
- adaugă grilă verticală discretă la fiecare 5 ani și etichete la 10 ani;
- adaugă crosshair și panou sub pointer cu anul, unitatea și valorile modelelor;
- elimină ajustarea retrospectivă și alternativa BAU condiționată din legendă;
- retrage graficele EROI din selector până la cuplarea modulului în model;
- păstrează intervalul statistic ca opțiune separată.

## 0.5.0 — 29 august 2026

- adaugă un modul dinamic separat pentru EROI sistemic și energia netă;
- modelează explicit declinul calității fosile, învățarea regenerabilelor,
  povara de integrare și schimbarea mixului;
- compară scenariul central cu tranziția accelerată și blocarea fosilă;
- etichetează extensia drept necalibrată, fără backtest și fără probabilități;
- păstrează neschimbate cele cinci grafice BAU2-E2026 validate anterior.

## 0.4.0 — 29 august 2026

- adaugă validare multi-origin fără folosirea datelor viitoare la selectarea
  parametrilor;
- afișează distinct performanța recentă și performanța multi-origin;
- expune explicit eșecul validării recente pentru sectorul industrial;
- adaugă valorile reperului ONU în cardurile demografice;
- adaugă controlul ajustării istorice și clarifică intervalul P10–P90
  condițional.

## 0.3.0 — 29 august 2026

- separă intervalul empiric P10–P90 de alternativa structurală BAU;
- adaugă linia BAU-E2026 ancorată la observații;
- face curba BAU2 originală opțională;
- identifică ajustarea istorică în legendă și ascunde reperul extern când lipsește;
- etichetează ultimul an observat direct pe grafic;
- afișează erorile MAPE din backtesting pentru fiecare indicator;
- compară emisiile anuale cu rata anuală de generare a poluării World3,
  eliminând comparația neomogenă dintre fluxul CO₂ și stocul persistent;
- întărește validarea statică a seriilor și intervalelor.

## 0.2.0 — 28 august 2026

- introduce observațiile globale recente și proiecția hibridă BAU2-E2026;
- adaugă delimitarea observație–proiecție, sensibilitatea BAU/BAU2 și
  backtestingul 2019–ultimul an disponibil.

## 0.1.1 — 28 august 2026

- corectează stocarea seriilor numerice pentru Vala 0.56.
