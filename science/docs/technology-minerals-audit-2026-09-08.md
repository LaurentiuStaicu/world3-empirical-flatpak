# Auditul mineralelor tehnologice — 8 septembrie 2026

## Decizie

Datele intră în registrul observat de risc, dar nu modifică proiecția centrală
BAU Hibrid 2026 v0.10.0. Producția minieră este un flux observat, în timp ce
„resursele neregenerabile rămase” din World3 reprezintă un stoc global latent.
Calibrarea unuia direct pe celălalt ar confunda unitățile și mecanismul.

Auditul păstrează separat cuprul, nichelul, litiul, cobaltul, pământurile rare
și grafitul natural. Tonajele nu sunt însumate între materiale.

## Surse și versiuni

- istoric până în 2023: seria OWID care armonizează USGS Mineral Commodity
  Summaries, USGS Historical Statistics și BGS World Mineral Statistics;
- 2024–2025: USGS Mineral Commodity Summaries 2026 Data Release,
  DOI `10.5066/P1WKQ63T`;
- raportul aferent: USGS Mineral Commodity Summaries 2026,
  DOI `10.3133/mcs2026`.

Fișierul USGS original este cp1252 cu finaluri CRLF. Copia din repository este
normalizată la LF și comprimată determinist cu gzip; proveniența păstrează
SHA-256-ul arhivei și al conținutului decomprimat, precum și MD5 și SHA-256
pentru octeții oficiali. Decomprimarea și restabilirea CRLF reproduc
amprentele oficiale declarate.

USGS marchează toate valorile mondiale de producție pentru 2025 drept
estimări. Seria 2024 din sursa istorică este înlocuită cu ediția MCS 2026,
deoarece aceasta conține revizuiri. De exemplu, valorile revizuite diferă
pentru litiu, cobalt și pământuri rare.

## Indicatorii calculați

Pentru fiecare material sunt publicate:

- producția minieră anuală și indicele 2015=100;
- creșterea medie anuală 2020–2025;
- ponderea celui mai mare producător nominalizat;
- un interval HHI pentru concentrarea producției;
- rezervele raportate și raportul rezerve/producție, unde versiunea sursei este
  coerentă.

Limita inferioară HHI însumează pătratele ponderilor țărilor nominalizate și
presupune că restul producției este complet fragmentat. Limita superioară
tratează întregul rest ca un singur producător. Astfel, categoria agregată
„alte țări” nu este confundată cu o țară reală.

Raportul rezerve/producție nu reprezintă „ani până la epuizare”. Rezervele sunt
economice și se schimbă cu prețurile, tehnologia, explorarea și raportarea.

## Rezultate pentru 2025

| Material | Creștere anuală 2020–2025 | Cel mai mare producător | Pondere | Interval HHI |
|---|---:|---|---:|---:|
| Cobalt | 16,90% | Congo (Kinshasa) | 74,19% | 0,5720–0,5722 |
| Cupru | 2,23% | Chile | 23,04% | 0,1037–0,1206 |
| Grafit natural | 13,26% | China | 77,78% | 0,6114–0,6121 |
| Litiu | 28,58% | Australia | 31,72% | 0,2024–0,2024 |
| Nichel | 9,21% | Indonezia | 66,67% | 0,4559–0,4620 |
| Pământuri rare | 10,20% | China | 69,23% | 0,5054–0,5055 |

Concentrarea este o limită potențială distinctă de epuizarea geologică. Ea poate
produce întârzieri, volatilitate și substituții tehnologice chiar când
rezervele globale raportate sunt mari.

## Conflict de versiune păstrat vizibil

Data release-ul ScienceBase publică pentru pământurile rare rezerve mondiale
de peste 85 milioane tone. Capitolul curent MCS 2026 v1.3 publică peste
75 milioane tone. Raportul rezerve/producție pentru pământuri rare este exclus,
nu recalculat prin amestecarea tăcută a celor două versiuni.

## Comparația cu modelul

Între 2000 și 2025, media geometrică egal ponderată a indicilor celor șase
materiale are o corelație de 0,6343 între variațiile logaritmice anuale și
industria mondială observată. Corelația cu fluxul de utilizare a resurselor
dedus din BAU Hibrid este −0,2779.

Media geometrică este numai o sensibilitate: ponderarea egală este arbitrară,
iar indicele nu este un tonaj fizic total. Rezultatele pe materiale sunt și mai
eterogene: în 2015–2025 producția de cupru a crescut cu aproximativ 19%, în timp
ce litiul a crescut cu peste 800%. Un singur coeficient global de „resurse” nu
poate descrie aceste tranziții.

## De ce nu intră în curba centrală

- fluxul minier nu observă stocul neregenerabil World3;
- materialele nu pot fi adunate în tone fără ponderi fizice sau economice;
- rezervele raportate nu sunt un stoc geologic fix;
- lipsesc serii coerente pentru concentrația minereului, recuperare, cost,
  reciclare, rafinare, inventare și pipeline-ul proiectelor;
- valorile 2025 sunt estimări.

## Următorul model justificat

Modulul dinamic trebuie să păstreze câte un stoc pe material și să includă:

1. capacitate minieră și proiecte în construcție;
2. rezerve economice cu versiune și intervale;
3. stocuri de materiale aflate în utilizare;
4. fluxuri secundare și capacitate de reciclare;
5. capacitate de rafinare și concentrare geografică;
6. întârzieri de autorizare, construire și substituție.

Abia după ce acești indicatori pot fi validați temporal față de un model mai
simplu se poate testa cuplarea în BAU Hibrid.
