# World3 Empirical 2026

Cadru reproductibil pentru replicarea World3, calibrare empirică, testare în
afara eșantionului și extensii modulare de dinamică a sistemelor.

## Stadiul actual

Versiunea de producție 0.10.0 oferă:

- un motor World3 complet, bazat pe implementarea `pyworld3` a modelului tehnic
  din 1974;
- scenariile oficiale World3-03 BAU și BAU2 din fișierul Vensim distribuit de
  Vensim, plus motorul tehnic din 1974 pentru comparație;
- rezultate standardizate pentru populație, producție industrială, hrană,
  resurse, poluare, servicii și speranță de viață;
- un registru validat al seriilor empirice;
- calibrare cu limite explicite ale parametrilor;
- testare temporală separată de calibrare;
- simulări Monte Carlo și intervale de incertitudine;
- teste automate și un audit empiric datat.

Ramura de audit adaugă un modul dinamic separat pentru energia netă și EROI. El
reprezintă stocul de resurse fosile pe clase de calitate, declinul EROI fosil,
învățarea regenerabilelor, povara de integrare și mixul energetic. Relația
centrală este `energie netă = energie brută × (1 − 1/EROI sistemic)`. Modulul
este intenționat exclus din proiecția centrală: seria globală EROI fosil
1971–2020 a fost ingerată, dar legătura resurse World3–EROI nu a depășit
persistența în backtestul de cinci ani la niciuna dintre frontierele primară,
finală sau utilă.

Un al doilea audit testează temperatura globală NASA GISTEMP ca semnal
incremental pentru producția alimentară FAOSTAT. Legătura nu folosește
temperaturi observate după originea fiecărei prognoze. Ea eșuează în holdoutul
2019–2024 și rămâne exclusă din proiecția centrală; următoarea etapă necesită
stres hidric, umiditatea solului și extreme termice regionale.

Un al treilea audit folosește un panou FAOSTAT–ERA5 pentru 174 de țări și
ponderează stresul anual de căldură și uscăciune cu producția de cereale.
Extensia prospectivă reduce eroarea în holdoutul 2019–2024, dar o mărește cu
30,95% pe originile de dezvoltare; chiar și varianta condiționată pe clima
realizată este mai slabă. Indicatorul este respins, iar v0.10.0 rămâne
neschimbată. Următorul test necesită sezoane de vegetație și umiditatea solului.

În stratul BAU2-E2026 pentru aplicație, intervalul Monte Carlo P10–P90 este
exportat separat de alternativa structurală BAU. Emisiile anuale de CO₂ sunt
comparate cu rata de generare a poluării World3, flux-la-flux; stocul persistent
latent rămâne exclus din observațiile directe.

Validarea include originile 2005, 2010, 2015 și 2018. La fiecare origine,
hiperparametrii sunt selectați numai pe o fereastră anterioară, astfel încât
anii aflați după origine nu influențează alegerea modelului. Testul recent
2019–ultimul an este raportat chiar și atunci când modelul este mai slab decât
ancorarea simplă.

`bau2_structural_proxy` este păstrat numai pentru compatibilitate și diagnostic.
Analiza principală trebuie să folosească `world3_03_bau2`, scenariul 2 al
fișierului oficial. Acesta este un scenariu de referință, nu o predicție
empirică recalibrată.

## Rulare rapidă

Din directorul proiectului:

```bash
PYTHONPATH=src:vendor python3 -m world3_empirical simulate \
  --scenario world3_standard \
  --output outputs/world3_standard.csv

PYTHONPATH=src:vendor python3 -m world3_empirical simulate \
  --scenario bau2_structural_proxy \
  --output outputs/bau2_structural_proxy.csv
```

Pentru graficele comparative:

```bash
PYTHONPATH=src:vendor python3 scripts/run_baselines.py
```

Pentru extensia dinamică energie netă/EROI:

```bash
PYTHONPATH=src:scripts .venv/bin/python scripts/run_net_energy_scenarios.py
PYTHONPATH=src:scripts .venv/bin/python scripts/evaluate_eroi_resource_link.py
PYTHONPATH=src:scripts .venv/bin/python scripts/analyze_energy_coupling.py
```

Pentru auditul climatic alimentar:

```bash
PYTHONPATH=src:scripts .venv/bin/python scripts/ingest_gistemp.py
PYTHONPATH=src:scripts .venv/bin/python scripts/evaluate_climate_food_link.py
PYTHONPATH=src:scripts .venv/bin/python scripts/ingest_regional_agricultural_climate.py
PYTHONPATH=src:scripts .venv/bin/python scripts/evaluate_regional_agricultural_stress.py
```

Rezultatele din `outputs/net_energy/` sunt scenarii structurale, nu intervale
de probabilitate. Ele nu modifică încă traiectoria centrală BAU2-E2026.

Pentru rularea scenariilor oficiale World3-03 BAU și BAU2:

```bash
python3 -m pip install -e '.[world3-03]'
PYTHONPATH=src:vendor python3 scripts/run_world3_03.py
PYTHONPATH=src:vendor python3 scripts/analyze_world3_03.py
```

Compatibilitatea numerică a modelului oficial este fixată la NumPy 1.26.x și
PySD 3.14.3; NumPy 2 schimbă tipul returnat de unele lookup-uri PySD.

Pentru actualizarea snapshotului World Bank și comparația empirică necalibrată:

```bash
PYTHONPATH=src:vendor python3 scripts/ingest_world_bank.py
PYTHONPATH=src:vendor python3 scripts/compare_empirical.py
```

Fișierul `data/raw/world_bank/2026-08-28/manifest.json` păstrează adresa,
intervalul și amprenta SHA-256 a fiecărui răspuns. Comparația necalibrată este
un test de diagnostic, nu o validare a modelului.

Interpretarea numerică și excluderile de calitate sunt documentate în
`docs/empirical-audit-2026-08-28.md`.

Structura propusă pentru energia netă/EROI, climă–apă–hrană, minerale și
infrastructura AI este descrisă în `docs/dynamic-extensions.md`. Factorii
instituționali și geopolitici rămân scenarii de stres până la identificarea
unor relații empirice robuste.

Pentru teste:

```bash
PYTHONPATH=src:scripts .venv/bin/python -m unittest discover -s tests -v
```

## Principii metodologice

Modelul separă strict:

1. scenariile istorice reproduse;
2. parametrii recalibrați pe observații;
3. variabilele latente fără corespondent empiric direct;
4. extensiile folosite numai în scenarii de stres.

O curbă apropiată vizual de date nu reprezintă validare. Calibrarea și testarea
folosesc perioade temporale distincte, indicatori numerici și intervale de
incertitudine. Proiecțiile pentru 2025–2035 sunt condiționale, nu predicții
deterministe.

Arhiva FAOSTAT brută, prea mare pentru repository, este o intrare externă
înghețată prin URL, dimensiune și SHA-256 în `data/remote_inputs.json`.
`../scripts/reproduce_scientific_results.py` o descarcă automat și refuză
reproducerea dacă octeții nu corespund snapshotului declarat. Datele procesate
și toate seriile incluse în aplicație rămân versionate în repository.

## Structură

```text
configs/          scenarii și metadatele lor
data/             registrul seriilor empirice
docs/             metodologie și planul extensiilor
scripts/          rulări reproductibile
src/              codul proiectului
tests/            teste automate
vendor/pyworld3/  motorul tehnic World3 și licența CeCILL
vendor/world3_03/ modelul oficial Vensim World3-03
```

## Licențe

Codul original al acestui proiect este oferit sub licența MIT. Motorul
`pyworld3`, inclus în `vendor/`, aparține lui Charles Vanwynsberghe și este
distribuit sub licența CeCILL 2.1. Consultați `THIRD_PARTY_NOTICES.md` și
`vendor/LICENSE-pyworld3.txt`.
