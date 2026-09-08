# Audit UNIDO pentru proxy-ul industrial — 7 septembrie 2026

## Decizie

Agregatul mondial UNIDO pentru valoarea adăugată manufacturieră pe locuitor
este acceptat în registrul observațiilor ca reper independent. Nu înlocuiește
ținta World Bank și nu modifică BAU Hibrid 2026 v0.10.0: în testele temporale,
cele două proxy-uri aleg exact aceiași candidați, iar pragul predeclarat pentru
promovarea unei recalibrări nu este atins.

## Sursa și reproducerea

Datele provin din baza UNIDO National Accounts, prin API-ul portalului de
statistică. Conectorul:

1. citește metadatele datasetului și identificatorul său curent, fără a fixa
   numeric un ID care se poate schimba;
2. solicită agregatul oficial `WORLD`, evitând dubla numărare care ar putea
   apărea prin însumarea manuală a țărilor și agregatelor;
3. extrage `MvaCod`, etichetat „MVA (Manufacturing Value Added), constant 2020
   USD”, și `Pop` din același răspuns;
4. calculează MVA pe locuitor și indicele 2015 = 100;
5. păstrează răspunsurile brute, proveniența și amprentele SHA-256.

Snapshotul conține 36 observații anuale, 1990–2025. Portalul marchează 2025
drept estimare UNIDO. Câmpul intern `base_year` din metadate indică 2015, în
timp ce eticheta variabilei indică dolari constanți 2020; inconsecvența este
păstrată explicit în fișierul de proveniență și valorile nu sunt rebazate în
monedă. Pentru comparația de traiectorie, ambele proxy-uri sunt transformate în
indici 2015 = 100, ceea ce elimină diferența de scară monetară.

Materialele portalului sunt declarate CC BY 4.0 dacă nu se precizează altfel.
Fișierele de proveniență păstrează instituția, URL-urile și atribuirea.

## Întrebarea testată

Seria curentă World Bank pentru industrie include și construcțiile. UNIDO MVA
exclude construcțiile și este conceptual mai apropiată de manufactură, dar
rămâne valoare adăugată monetară, nu producția fizică brută reprezentată de
sectorul industrial World3.

Auditul întreabă dacă înlocuirea exclusivă a țintei observate pentru industrie
cu UNIDO MVA conduce la o selecție prospectivă mai bună. Structura World3,
ecuațiile, celelalte ținte, limitele parametrilor și setul înghețat de 128 de
candidați nu sunt schimbate.

Originile 2009 și 2014 sunt folosite pentru dezvoltare. Originea 2018 este o
comparație temporală ulterioară, dar a mai fost folosită de alte audituri ale
proiectului și nu este prezentată drept holdout confirmator complet neatins.

Regula de promovare, declarată înaintea interpretării, cere simultan:

- cel puțin 5% reducere a erorii pe ținta UNIDO;
- cel mult 5% deteriorare agregată pe țintele neindustriale;
- cel mult 10% deteriorare pentru oricare țintă neindustrială.

## Rezultate

În perioada comună 1992–2025, corelația variațiilor logaritmice anuale ale
celor două proxy-uri este 0,954. Diferența absolută medie dintre indicii
2015 = 100 este 2,06 puncte, iar diferența în 2025 este −0,27 puncte pentru
UNIDO față de World Bank.

Ambele ținte aleg aceiași candidați la fiecare origine:

| Origine | Candidat selectat | Perioadă evaluată | MAPE UNIDO |
|---:|---:|---:|---:|
| 2009 | 101 | 2010–2025 | 7,02% |
| 2014 | 99 | 2015–2025 | 1,39% |
| 2018 | 73 | 2019–2025 | 1,66% |

În consecință, selecția pe UNIDO aduce 0% îmbunătățire față de selecția
curentă atunci când este evaluată pe UNIDO și 0% deteriorare pentru țintele
neindustriale. Criteriul de minimum 5% nu trece.

Refitul de producție păstrează candidatul central 114. Dacă nivelul industriei
ar fi reancorat numai la UNIDO, indicele industrie/locuitor ar fi cu 0,265% mai
mic în 2030 și 2035; populația, hrana, poluarea-proxy și bunăstarea nu s-ar
schimba. Aceasta este o diferență de mapare observațională, nu una structurală.

## Credibilitate și limite

UNIDO este instituția specializată a ONU pentru dezvoltare industrială, iar
folosirea agregatului său mondial reduce ambiguitatea operațională a agregării.
Auditul este reproductibil și nu folosește informații ulterioare originii
pentru selectarea candidatului.

Totuși, rezultatul nu validează mecanismul industrial World3. Atât MVA, cât și
indicatorul World Bank sunt măsuri monetare de valoare adăugată, sensibile la
prețuri relative, cursuri, revizuiri statistice și schimbarea compoziției
producției. Niciuna nu măsoară direct tonajul, energia sau serviciile materiale
livrate. Seria 2025 este estimată, iar originea 2018 este reutilizată.

Următorul test cu valoare informațională mai mare ar trebui să combine MVA cu
indicele UNIDO al producției industriale și cu serii fizice pentru o selecție
de materiale-cheie, păstrând separat valoarea economică de throughputul fizic.

## Fișiere rezultate

- `science/data/processed/unido_national_accounts_world_2026-09-07.csv`
- `science/data/processed/unido_national_accounts_world_2026-09-07.provenance.json`
- `science/outputs/unido_industry_proxy/observed_proxy_comparison.csv`
- `science/outputs/unido_industry_proxy/cross_proxy_backtest.csv`
- `science/outputs/unido_industry_proxy/nonindustry_backtest.csv`
- `science/outputs/unido_industry_proxy/production_projection_comparison.csv`
- `science/outputs/unido_industry_proxy/manifest.json`
