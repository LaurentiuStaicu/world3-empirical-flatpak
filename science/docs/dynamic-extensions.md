# Extensii dinamice propuse pentru modelul empiric

Extensiile nu se adaugă toate simultan. Fiecare modul trebuie să îmbunătățească
predicția în afara eșantionului sau să reprezinte o limită fizică observabilă.
În caz contrar, rămâne scenariu de stres și nu intră în calibrarea centrală.

## 1. Energie netă și EROI — prioritatea 1

Stadiu la 31 august 2026: motorul separat este implementat, iar o cuplare
conservatoare înapoi în World3 a fost testată. Cuplarea folosește maximul dintre
povara originală World3 și povara EROI, nu suma lor, pentru a evita dubla
numărare. Seria globală EROI fosil Aramendia 1971–2020 a fost ingerată cu
frontierele primară, finală și utilă păstrate separat. Legătura propusă între
resursele World3 și EROI a pierdut însă în fața persistenței în testele
prospective de cinci ani la toate cele trei frontiere. Modulul rămâne, prin
urmare, sensibilitate structurală și nu intră în proiecția centrală v0.10.0.
Detaliile sunt în `docs/energy-coupling-audit-2026-08-30.md`.

Stocuri: resurse fosile pe clase de calitate, capital de extracție, capital
regenerabil, rețea și stocare.

Fluxuri: extracție, declinul zăcămintelor, construcție, depreciere, reciclare și
consumul energetic intern al sectorului energetic.

Relația centrală:

`energie netă = energie brută × (1 − 1 / EROI la frontiera aleasă)`

Pentru amestecul de surse se folosește media armonică ponderată energetic:

`1 / EROI sistemic = Σ(pondere sursă / EROI sursă)`

Această formulă adună energia reinvestită în fiecare filieră. Nu se folosește
media aritmetică a EROI, care ar supraestima energia netă a unui mix eterogen.

Feedback: scăderea calității resursei reduce EROI, mărește capitalul necesar
energiei și lasă mai puțin capital pentru industrie, servicii și agricultură.

Date: seria globală Energy Institute 1965–2025, mixul pe surse și seria globală
EROI fosil 1971–2020 au fost ingerate. Mai sunt necesare o punte observabilă
între reinvestirea energetică și capital, serii pe tehnologii cu aceeași
frontieră, IEA/EIA, curbe publice de cost, capacități IRENA și costuri de sistem.

## 2. Climă, apă, sol și hrană — prioritatea 2

Stadiu la 31 august 2026: NASA GISTEMP v4 1880–2025 a fost ingerat, iar o
legătură incrementală între temperatura medie globală și producția alimentară
FAOSTAT a fost testată fără informație din viitor. Ea a redus log-RMSE cu 2,27%
în originile de dezvoltare, dar a mărit eroarea cu 56,09% în holdoutul
independent 2019–2024. Legătura este respinsă pentru proiecția centrală. Testul
arată că este necesar un indice regional ponderat cu culturile, cu apă și
umiditatea solului, nu un multiplicator bazat numai pe temperatura globală.
Detaliile sunt în `docs/climate-food-audit-2026-08-31.md`.

Al doilea test climatic folosește un panou FAOSTAT–ERA5 pentru 174 de țări,
cu stres anual de căldură și uscăciune ponderat prin producția de cereale.
Ramura prospectivă îmbunătățește holdoutul 2019–2024 cu 36,23%, dar
înrăutățește originile de dezvoltare cu 30,95% și ansamblul originilor cu
27,53%. Nici varianta condiționată pe clima ulterior observată nu ajută.
Extensia rămâne în afara v0.10.0. Auditul complet este în
`docs/regional-agricultural-stress-audit-2026-08-31.md`; pasul următor trebuie
să folosească sezoane de vegetație, umiditatea solului și ponderi separate pe
culturi, nu o nouă reglare a mediilor anuale naționale.

Stocuri: CO2 atmosferic, anomalie termică, umiditatea solului, suprafață
agricolă productivă și capacitate de irigații.

Fluxuri: emisii și absorbție, degradare și refacere a solului, extinderea și
pierderea terenului, retrageri și realimentare cu apă.

Feedback: emisii → încălzire și extreme → pierderi de randament și apă →
investiții agricole mai mari → presiune asupra capitalului industrial și a
energiei.

Date: GISTEMP și FAOSTAT sunt disponibile. Mai sunt necesare Global Carbon
Project, ERA5/Copernicus, AQUASTAT, ISIMIP și indicatori observați ai
umidității solului, păstrați regional înaintea agregării.

## 3. Minerale și substituție tehnologică — prioritatea 3

Stocuri: resurse și rezerve pe mineral, stocuri în uz, material recuperabil și
capacitate de rafinare.

Fluxuri: extracție, rafinare, intrare în utilizare, scoatere din uz și
reciclare. Cuprul, litiul, nichelul și elementele rare trebuie păstrate separat;
un agregat unic ar ascunde blocajele.

Feedback: cererea de electrificare și AI → investiții miniere și energie →
declinul concentrației minereului și apă suplimentară → costuri și întârzieri →
încetinirea instalării noii infrastructuri.

Date necesare: USGS, IEA Critical Minerals, BGS și registre de proiecte cu
stadii distincte.

## 4. Infrastructura AI — prioritatea 4

Stocuri: capacitate IT instalată, proiecte în coada de conectare, generare
dedicată, rețea, răcire și capacitate de producție a cipurilor.

Lanțul de stări:

`anunțat → cerere de conectare → contractat → autorizat → construcție → conectat → utilizat`

Fiecărei tranziții îi revine o probabilitate de abandon și o distribuție a
întârzierii. PUE și WUE variază cu încărcarea, clima, răcirea și punerea în
funcțiune.

Feedback: eficiență mai mare → cost mai mic al calculului → volum mai mare de
inferență/antrenare → efect de recul asupra electricității, apei și cipurilor.

Date necesare: IEA, Lawrence Berkeley National Laboratory, rapoarte ale
operatorilor de rețea, registre de proiecte, raportări PUE/WUE și curbe de
utilizare observată.

## 5. Instituții, datorie și geopolitică — numai scenarii de stres

Acești factori pot modifica întârzierile investițiilor, deprecierea capitalului,
comerțul și mortalitatea, dar relațiile globale sunt slab identificate. Până la
un protocol empiric separat, modulul va aplica șocuri transparențe și reversibile,
nu parametri calibrați împreună cu sectoarele fizice.

## Ordinea de acceptare în model

1. Definirea stocului, fluxurilor și unităților.
2. Înregistrarea seriilor observate și a versiunilor.
3. Estimarea parametrilor pe fereastra de calibrare.
4. Testarea pe ani nefolosiți la estimare.
5. Compararea cu modelul fără extensie.
6. Acceptarea numai dacă eroarea scade și incertitudinea rămâne identificabilă.
