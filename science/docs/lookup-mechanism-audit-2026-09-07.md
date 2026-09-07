# Auditul mecanismelor lookup World3 — 7 septembrie 2026

## Decizie

Niciun filtru specific unui mecanism lookup nu intră în selecția centrală BAU
Hibrid 2026 v0.10.0. Politica aleasă exclusiv pe originile de dezvoltare reduce
log-RMSE cu 2,09%, sub pragul predeclarat de 5%. La originea temporală 2018,
aceeași politică mărește eroarea agregată cu 11,64%, iar deteriorarea maximă a
unui sector ajunge la 276,41%.

Acest rezultat întărește concluzia auditului generic: extrapolările lookup sunt
un diagnostic structural important, dar nu sunt încă un criteriu validat de
selecție a candidaților.

## Taxonomia înghețată

Înaintea evaluării politicilor, toate cele 33 de tabele cauzale care ies din
domeniul tabulat au fost atribuite o singură dată uneia dintre cele șase
familii. Tabelele `scenario_table` rămân excluse deoarece codifică date și
comutatoare de scenariu, nu răspunsuri cauzale ale sistemului.

| Mecanism | Lookup-uri | Rol general |
|---|---:|---|
| capacitate și muncă | 4 | utilizarea capacității și intensitatea muncii/capitalului |
| agricultură, teren și hrană | 6 | alocări agricole, randament și viața terenului |
| poluare și ecologie | 3 | asimilare, degradarea fertilității și efecte asupra vieții |
| sănătate și mortalitate | 8 | servicii medicale, speranță de viață și mortalitate pe vârste |
| fertilitate și răspuns social | 6 | fecunditate, normă familială și controlul fertilității |
| afluență și cerere materială | 6 | servicii, resurse, teren urban și efectul industriei |

Maparea completă și variabila care conduce fiecare tabel sunt exportate în
`lookup_mechanism_mapping.csv`. Testul automat cere egalitate exactă între
taxonomie și lookup-urile cauzale observate; o ecuație nouă sau omisă oprește
auditul.

## Situația rulării centrale

Pentru candidatul central 114, după 1970, diagnosticul găsește:

| Mecanism | Evenimente | Evenimente materiale | Primul–ultimul an | După 2025 |
|---|---:|---:|---:|---:|
| capacitate și muncă | 596 | 326 | 1970–2100 | 374 |
| fertilitate și răspuns social | 159 | 157 | 2020,5–2099,5 | 149 |
| poluare și ecologie | 84 | 73 | 1970–2099,5 | 75 |
| sănătate și mortalitate | 66 | 57 | 2065–2100 | 66 |
| agricultură, teren și hrană | 34 | 23 | 2051–2067,5 | 34 |
| afluență și cerere materială | 16 | 11 | 2092–2099,5 | 16 |

„Material” înseamnă o intrare aflată cu cel puțin 5% din lățimea domeniului în
afara tabelului. Numărul mare din familia capacității este dominat de funcțiile
de muncă și nu demonstrează singur că traiectoria este eronată.

## Politici și separare temporală

Pentru fiecare familie sunt testate trei măsuri:

1. numărul de evenimente;
2. numărul de evenimente materiale;
3. expunerea `count × log(1 + distanță normalizată)`.

Fiecare măsură păstrează alternativ cei mai puțin expuși 25% sau 50% dintre
cei 128 de candidați: 36 de politici predeclarate, dintre care 35 sunt fezabile
la toate originile. La fiecare origine sunt vizibile numai extrapolările până
în acel an.

Originile 2005, 2010 și 2015 aleg politica. Originea 2018 este folosită numai
după înghețarea alegerii. Totuși, ea a fost deja folosită în alte audituri ale
proiectului; de aceea este denumită comparație temporală reutilizată, nu
holdout confirmator complet neatins.

În cazul egalității scorului de dezvoltare, departajarea este lexicală după
numele politicii. Scorul din 2018 nu este folosit niciodată pentru departajare.

## Rezultat

Cea mai bună politică după dezvoltare este
`fertility_social_response__distance_exposure_q25`. Ea selectează candidații
0, 73 și 73 la originile 2005, 2010 și 2015, apoi candidatul 125 în comparația
2018.

| Criteriu | Rezultat | Prag de acceptare |
|---|---:|---:|
| reducerea log-RMSE în dezvoltare | 2,09% | minimum 5% |
| reducerea log-RMSE la originea 2018 | −11,64% | minimum 5% |
| cea mai mare deteriorare sectorială | 276,41% | maximum 10% |

Politica eșuează toate cele trei condiții. BAU Hibrid 2026 v0.10.0, candidatul
central și ansamblul P10–P90 rămân neschimbate.

## Interpretare și pas următor

Agregarea pe familii este mai informativă decât un singur număr global, dar
tot comprimă mecanisme cu forme și unități diferite. Următorul test justificat
nu este extinderea arbitrară a tabelelor. Este selectarea unuia sau a două
lookup-uri dominante și construirea unor extensii cauzale cu surse empirice,
unități și limite fizice explicite, urmată de o nouă validare temporală.

Codul este în `scripts/evaluate_lookup_mechanisms.py`, iar rezultatele
reproductibile sunt în `outputs/lookup_mechanisms/`.
