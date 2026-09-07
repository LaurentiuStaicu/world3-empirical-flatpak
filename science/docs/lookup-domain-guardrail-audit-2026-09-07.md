# Auditul pragului pentru domeniile lookup World3 — 7 septembrie 2026

## Decizie

Penalizarea sau eliminarea candidaților care extrapolează frecvent tabelele
lookup World3 nu intră în selecția centrală BAU Hibrid 2026 v0.10.0. Cea mai
bună regulă aleasă numai pe originile de dezvoltare a redus eroarea agregată cu
3,42% în dezvoltare și cu 4,12% în testul independent 2018–ultimul an. Ambele
câștiguri sunt sub pragul predeclarat de 5%, iar unele sectoare s-au degradat
material.

Rezultatul nu spune că extrapolările sunt inofensive. Arată că numărul lor, luat
singur, nu este un substitut validat pentru eroarea predictivă și nu trebuie
folosit automat pentru a alege o traiectorie mai favorabilă.

## Problema măsurată

PySD păstrează valoarea de capăt atunci când intrarea unei funcții lookup iese
din domeniul tabulat. Auditul precedent a înregistrat pentru fiecare candidat:

- funcția lookup și direcția depășirii;
- anul și numărul evenimentelor;
- valorile de intrare și limitele tabelului;
- distanța absolută și normalizată până la limita depășită.

Comutatoarele cu nume `scenario_table` sunt excluse din acest test. Ele
codifică date și selecții de scenariu, nu răspunsuri cauzale ale sistemului.
Pentru fiecare origine sunt folosite numai evenimentele din 1970 până în anul
originii; auditul nu poate vedea extrapolări din viitor.

## Reguli evaluate

Au fost evaluate patru măsuri:

1. numărul total de evenimente cauzale;
2. numărul evenimentelor aflate la cel puțin 5% din lățimea domeniului în afara
   tabelului;
3. expunerea cumulată `count × log(1 + distanță normalizată)`;
4. numărul funcțiilor lookup distincte afectate.

Pentru fiecare măsură au fost predefinite patru praguri de retenție: cei mai
puțin expuși 25%, 50%, 75% și 90% dintre cei 128 de candidați. Candidații care
ating o limită a mapării observaționale rămân excluși înaintea filtrului.

Originile 2005, 2010 și 2015 formează dezvoltarea. Regula cu eroarea agregată
cea mai mică în aceste origini este înghețată, apoi evaluată separat la originea
2018. În 2005 nu există încă un segment anterior complet pentru selecție, astfel
încât candidatul de bază 0 este păstrat de ambele proceduri.

## Rezultat

Cea mai bună regulă de dezvoltare păstrează quartila cu cele mai puține
evenimente (`events_q25`). Ea selectează candidatul 0 în originile de
dezvoltare și candidatul 100 la originea independentă 2018, față de candidatul
73 al procedurii existente.

| Criteriu | Rezultat | Prag de acceptare |
|---|---:|---:|
| reducerea log-RMSE în dezvoltare | 3,42% | minimum 5% |
| reducerea log-RMSE în testul independent | 4,12% | minimum 5% |
| cea mai mare deteriorare sectorială independentă | 120,88% | maximum 10% |

În testul independent, eroarea populației crește cu 120,88%, iar eroarea
hranei pe locuitor cu 14,68%. O mică îmbunătățire agregată este obținută în
principal prin sectorul de poluare și nu compensează pierderea de robustețe
între sectoare.

## Consecință pentru model

BAU Hibrid 2026 v0.10.0 rămâne neschimbat. Diagnosticul lookup rămâne obligatoriu
pentru transparență, dar nu devine penalizare în funcția obiectivă și nu
filtrează ansamblul P10–P90.

Un pas ulterior justificat ar trebui să clasifice funcțiile după mecanism și să
testeze limite fizice specifice, nu să reducă toate extrapolările la un singur
număr. Extinderea controlată a unui tabel ar necesita o sursă empirică pentru
forma lui în afara domeniului original; prelungirea arbitrară a curbei ar
ascunde tocmai incertitudinea pe care auditul o evidențiază.

Codul este în `scripts/evaluate_lookup_domain_guardrail.py`, iar rezultatele
reproductibile sunt în `outputs/lookup_domain_guardrail/`.
