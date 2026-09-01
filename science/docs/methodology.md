# Metodologia World3 Empirical 2026

## 1. Identitatea modelului

Modelul păstrează stocurile, fluxurile, întârzierile și funcțiile neliniare ale
World3. Proiectul conține două referințe separate: implementarea tehnică din
1974 prin `pyworld3` și fișierul oficial Vensim World3-03 folosit în actualizarea
din 2004. Scenariile 1 și 2 din fișierul oficial sunt expuse drept
`world3_03_bau` și `world3_03_bau2`.

Scenariul vechi `bau2_structural_proxy` rămâne numai ca test de compatibilitate
cu motorul din 1974. Pentru analiza BAU2 se folosește acum scenariul 2 din
modelul oficial World3-03, în care tabelul de scenarii setează resursele
inițiale la 2×10^12 unități față de 1×10^12 în scenariul 1.

## 2. Reguli pentru date

Fiecare observație trebuie să aibă o sursă, o versiune, o unitate și o regulă
de transformare. Datele lipsă nu sunt completate implicit. Interpolarea se
aplică numai după declararea metodei și păstrarea valorilor originale.

Variabilele sunt clasificate drept empirice, latente sau folosite numai în
scenarii. O variabilă latentă poate fi estimată prin model, dar nu poate fi
prezentată drept măsurată.

## 3. Strategia de calibrare

Calibrarea structurală folosește seriile lungi disponibile. Pentru perioada
recentă, intervalul 2010–2018 este folosit pentru ajustare, iar 2019–2024 sau
2025 pentru testare în afara eșantionului. Separarea poate fi modificată numai
înaintea estimării și trebuie consemnată.

Parametrii sunt limitați la intervale justificate fizic sau empiric. Modelul nu
permite ajustarea liberă a tuturor constantelor, deoarece aceasta ar produce
echifinalitate și identificare slabă.

Funcția obiectivă folosește reziduuri logaritmice pentru serii strict pozitive,
astfel încât populația să nu domine numeric indicatorii mai mici. Evaluarea
raportează RMSE, MAPE, eroarea de direcție și diferențele dintre anii punctelor
de inflexiune.

## 4. Incertitudinea

Un singur set optim de parametri nu reprezintă prognoza modelului. Simulările
Monte Carlo propagă intervalele parametrilor către distribuțiile rezultatelor.
Scenariile 2025–2035 vor raporta mediane și intervale, plus probabilitatea ca
mai multe sectoare să intre simultan în stagnare sau declin.

## 5. Extensii planificate

Extensiile sunt adăugate succesiv și testate prin comparație cu modelul fără
extensie. Ordinea propusă este energia netă și EROI, climă-apă-agricultură,
resurse diferențiate, apoi infrastructura energetică și materială a AI.

Datoria, conflictele și dezorganizarea instituțională rămân factori de scenariu
până când relațiile lor pot fi identificate empiric. Complexitatea nouă trebuie
să îmbunătățească testarea în afara eșantionului, nu doar potrivirea istorică.
