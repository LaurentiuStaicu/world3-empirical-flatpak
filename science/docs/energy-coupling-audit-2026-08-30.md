# Auditul cuplării energie netă/EROI — 30 august 2026

## Decizie

Cuplarea EROI nu intră încă în linia centrală BAU Hibrid 2026. Ea rămâne o
sensibilitate structurală până când poate fi calibrată și testată cu date
energetice suficient de omogene. Versiunea Flatpak 0.10.0 rămâne versiunea de
producție.

## Mecanism testat

World3-03 alocă deja o parte din capitalul industrial obținerii resurselor.
Pentru a evita dubla numărare, extensia nu adună povara EROI la această
alocare. Modelul folosește valoarea mai mare dintre:

1. alocarea originală World3 pentru obținerea resurselor;
2. povara suplimentară derivată din creșterea ponderii energiei reinvestite.

Ponderea reinvestită este calculată prin identitatea armonică:

`reinvestire = pondere_fosil / EROI_fosil + pondere_regenerabil / EROI_regenerabil`

În 2025, extensia este exact egală cu povara World3 de 5%. Toate stările și
fluxurile rămân numeric identice cu BAU Hibrid până la această limită.

Mixul inițial nu mai este o ipoteză rotundă de 80%. Ediția 2026 a Statistical
Review of World Energy indică pentru 2025 o ofertă globală de energie primară
de 600,313 EJ, dintre care 517,700 EJ fosil, adică 86,2384%. Seria 1965–2025,
hashul fișierului de intrare și proveniența sunt păstrate în
`data/processed/energy_institute_global_2026*`.

## Date EROI și frontiera contabilă

Seria globală Aramendia și colaboratorii acoperă anii 1971–2020 și separă
explicit EROI la energia primară, finală și utilă, cu și fără energia indirectă.
Aceste frontiere nu sunt interschimbabile și nu sunt amestecate în calibrare.
Fișierul original `global_erois.csv` este verificat prin MD5
`c3f330ee874e10aca547d73d76cd3cd2`; proveniența și selecția sunt păstrate în
`data/processed/aramendia_global_fossil_eroi_2024.provenance.json`.

Pentru scenariul de sensibilitate, valoarea fosilă inițială este EROI final cu
energie indirectă inclusă: 8,46945 în 2020. Ea este menținută constantă până în
2025, deoarece persistența a avut cea mai mică eroare în testul prospectiv la
această frontieră. Valoarea nu este prezentată ca observație pentru 2025.

## Testul prospectiv al legăturii resurse–EROI

Relația propusă între fracția de resurse World3 și EROI fosil a fost estimată
la originile 1995, 2000, 2005, 2010 și 2015 și testată pe următorii cinci ani.
Ea trebuia să depășească persistența la toate frontierele pentru a fi acceptată.

| Frontieră | Persistență RMSE | Legătura World3 RMSE | Decizie |
|---|---:|---:|---|
| energie primară | 1,5278 | 1,6397 | respinsă |
| energie finală | 0,2261 | 0,2634 | respinsă |
| energie utilă | 0,0702 | 0,1980 | respinsă |

Legătura pierde în fața reperului simplu la toate cele trei frontiere. Prin
urmare, nu există suport empiric suficient pentru a transforma scăderea
resurselor World3 într-o traiectorie centrală EROI.

## Rezultatele sensibilității structurale

| Scenariu | EROI 2030 | Povară capital 2030 | Industrie/loc. 2030 față de v0.10 | Industrie/loc. 2050 față de v0.10 |
|---|---:|---:|---:|---:|
| tranziție accelerată | 8,60 | 5,07% | −0,07% | −0,01% |
| cuplare conservatoare | 8,43 | 5,30% | −0,31% | −1,10% |
| blocare fosilă | 8,10 | 5,79% | −0,81% | −6,47% |

Ordinea este coerentă în intervalul relevant 2025–2050: blocarea fosilă produce
cea mai mare povară și cea mai mică producție industrială. Efectul asupra
populației rămâne mic până în 2050 din cauza inerției demografice.

După 2080, ordinea poate deveni ne-monotonă. O restricție energetică severă
reduce mai devreme producția și utilizarea resurselor, conservând o parte din
stoc și diminuând ulterior unele mecanisme de colaps. Acesta este un rezultat
posibil al feedbackurilor și nu trebuie eliminat cosmetic, dar face improprie
interpretarea modulului ca simplu multiplicator descrescător.

## De ce nu intră în proiecția centrală

- seria EROI observată se oprește în 2020, iar pentru 2021–2025 persistența este
  doar reperul predictiv cel mai prudent, nu o observație;
- EROI al surselor nu este echivalent cu EROI la nivelul întregului sistem;
- relația resurse World3–EROI a eșuat testul prospectiv față de persistență;
- traducerea reinvestirii energetice în capital World3 nu este identificată
  empiric;
- BAU2 conține deja o povară generică a accesului la resurse;
- rezultatele după 2025 depind material de ipotezele despre tranziție,
  integrarea regenerabilelor și declinul calității resurselor.

## Următorul prag de acceptare

Datele de energie primară 1965–2025 și EROI fosil 1971–2020 sunt acum
înregistrate. Pentru acceptare este necesară o relație mai bună decât
persistența în ferestre temporale nefolosite la estimare și o punte măsurabilă
între energia reinvestită și capitalul industrial. Până atunci, coeficientul de
cuplare rămâne exclus din ansamblul central.

Codul auditabil se află în `src/world3_empirical/energy_coupling.py`, iar
rezultatele, inclusiv backtestul, în `outputs/energy_coupling/`. Toate cele 49
de teste automate au trecut după această corecție de frontieră.
