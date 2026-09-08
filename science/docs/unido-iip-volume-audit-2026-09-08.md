# Audit UNIDO IIP — producția manufacturieră reală

## Decizie

Seria UNIDO IIP este adăugată ca diagnostic independent de producție brută
reală, dar nu înlocuiește ținta industrială și nu modifică BAU Hibrid 2026
v0.10.0. Cu ferestre de validare compatibile cu disponibilitatea IIP, ținta
World Bank și ținta IIP aleg aceiași candidați. Câștigul prospectiv datorat
schimbării proxy-ului este astfel 0%, sub pragul predeclarat de 5%.

## Date și reconstrucție

Snapshotul din 8 septembrie 2026 folosește datasetul UNIDO „IIP, ISIC Revision
4”, identificator dinamic 166 la extragere, inserat în portal la 28 august
2026. Sunt păstrate numai:

- variabila 52, „Original index”;
- activitatea C, „Total manufacturing”;
- observațiile anuale 2005–2025;
- ponderile MVA în dolari curenți din anul de bază 2020.

UNIDO descrie IIP drept măsură a producției industriale reale, fără efectul
prețurilor, și precizează că seriile subanuale reprezintă în general producție
brută. Metoda 2026 folosește agregare Laspeyres cu ponderi bazate pe contribuția
MVA în 2020. Reproducerea aplică aceeași idee publică: media indicilor naționali
ponderată fix cu MVA 2020.

API-ul public nu furnizează grupul `WORLD` pentru IIP, iar imputările folosite
de UNIDO în agregatele sale nu sunt publicate la nivel de țară. Pentru a nu
confunda schimbarea compoziției cu creșterea, auditul folosește un panou
echilibrat: 101 economii care au toate cele 21 de observații. Ele reprezintă
94,4903% din suma ponderilor MVA 2020 disponibile pentru 211 economii. Rezultatul
este o reconstrucție transparentă din date publice, nu seria mondială oficială
UNIDO.

Indicele mondial rezultat este împărțit la populația mondială folosită deja de
model și normalizat la 2015 = 100. Fișierele brute, hash-urile SHA-256, formula,
codul variabilei, activitatea și acoperirea sunt versionate în repository.

## Protocol prospectiv

Se schimbă numai seria observată pentru `industry_per_capita`. Ecuațiile
World3, cei 128 de candidați, celelalte patru ținte și limitele parametrilor
rămân fixe. Criteriile de promovare sunt:

1. acoperire a ponderii MVA 2020 de cel puțin 90%;
2. reducerea log-RMSE pe IIP după originea 2018 cu cel puțin 5%;
3. deteriorare agregată a țintelor neindustriale de cel mult 5%;
4. nicio țintă neindustrială deteriorată cu mai mult de 10%.

Originea standard 2009 nu poate fi folosită: seria începe în 2005 și nu oferă
minimum trei observații înaintea originii 2005 a primei ferestre interne.
Auditul nu inventează ani anteriori. Sunt folosite originile 2014 și 2018,
respectiv ferestrele interne care încep din 2010. Originea 2018 este separată
temporal, dar a mai fost folosită în auditurile proiectului și nu este numită
holdout confirmator complet neatins.

## Rezultate

- corelația variațiilor logaritmice anuale IIP–World Bank în 2005–2025: 0,9849;
- corelația variațiilor IIP–UNIDO MVA: 0,9881;
- diferența absolută medie IIP–World Bank între indicii normalizați: 2,6530%;
- diferența în 2025: −3,9723%;
- candidat selectat la originea 2014: 99 cu ambele proxy-uri;
- candidat selectat la originea 2018: 100 cu ambele proxy-uri;
- îmbunătățire prospectivă pe IIP: 0%;
- deteriorare agregată și sectorială neindustrială: 0%;
- candidat central după refitul complet: 114 în ambele cazuri.

Reancorarea aceleiași structuri la nivelul IIP ar coborî valoarea proiectată a
industriei/locuitor în 2030 și 2035 cu 3,9723%. Aceasta este exact diferența de
nivel dintre proxy-uri în 2025, nu o nouă dinamică. Populația, hrana, poluarea
și bunăstarea rămân numeric identice.

## Interpretare

IIP este conceptual mai apropiat de producția brută reală din World3 decât MVA
sau valoarea adăugată World Bank. Totuși, acest avantaj conceptual nu schimbă
selecția structurii în testele disponibile. Producția manufacturieră exclude
minerit, utilități, construcții și alte componente ale sectorului industrial
World3; acoperirea începe târziu, iar agregatul public nu poate reproduce
imputările UNIDO.

Prin urmare, seria este utilă pentru triangulare și pentru un viitor model de
observație care separă volum, valoare adăugată și compoziția industrială. Nu
există însă dovadă prospectivă pentru a modifica acum curbele din aplicație.

## Surse

- [UNIDO IIP, ISIC Revision 4](https://stat.unido.org/portal/dataset/getDataset/IIP)
- [Methodological Note: Index of Industrial Production, 2026 edition](https://stat.unido.org/portal/storage/file/publications/qiip/iip_method_note_edition2026.pdf)
- [UNIDO Statistics API](https://stat.unido.org/portal/user-guide/api-guide)
