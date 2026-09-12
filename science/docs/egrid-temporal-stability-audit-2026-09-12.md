# eGRID gas-cohort temporal stability audit, 12 September 2026

This audit tests whether one-year plant-level persistence is a defensible prior
for gas-generation heat rate and direct CO2 intensity. It does not modify the
application or BAU Hibrid 2026.

## Sources and timing

- eGRID2021, released 30 January 2023:
  https://www.epa.gov/system/files/documents/2023-01/eGRID2021_data.xlsx
- eGRID2022, released 30 January 2024:
  https://www.epa.gov/system/files/documents/2024-01/egrid2022_data.xlsx
- eGRID2023 revision 2, released 12 June 2025:
  https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx

The source workbooks are not committed. Their URLs, release dates, byte sizes
and SHA-256 hashes are retained in `science/data/energy_audit/egrid*-source.json`.
Deterministic gzip JSON cohorts retain the selected source rows.

Because every edition was published after its data year, this is a
release-lagged hindcast of temporal stability. It is not a real-time forecast
backtest. The target-year cohort membership and generation are known during
evaluation, so the experiment tests intensity conditional on actual activity;
it does not forecast total generation, fuel demand or emissions.

## Cohort and metrics

Each annual cohort independently applies the predeclared eGRID2023 selection:
Electric Utility or IPP Non-CHP, no CHP/useful-heat or biomass adjustment,
primary fuel NG, gas generation share exactly one, positive finite net
generation, heat input and CO2, and nonempty provenance. Consecutive cohorts
are then joined by ORIS plant code. Entrants and exits are counted but excluded
from matched-panel errors.

Two deliberately simple predictors are compared:

1. plant persistence applies each plant's prior-year intensity to its actual
   target-year net generation;
2. cohort-mean persistence applies the matched panel's prior-year aggregate
   intensity to every target-year plant.

The audit reports aggregate bias and quantity-weighted absolute percentage
error (WMAPE). Weighting is implicit in the physical target quantity. No
outlier cutoff, winsorization or result-dependent exclusion is used.

## Results

| Transition | Matched plants | Target generation covered | Heat-rate change | CO2-intensity change |
|---|---:|---:|---:|---:|
| 2021 to 2022 | 635 | 94.71% | +0.54% | +0.50% |
| 2022 to 2023 | 649 | 95.33% | -0.67% | -0.85% |

| Transition and signal | Plant persistence WMAPE | Cohort mean WMAPE | Plant rule versus mean |
|---|---:|---:|---:|
| 2021 to 2022 heat rate | 32.33% | 11.04% | 192.89% worse |
| 2021 to 2022 CO2 intensity | 32.39% | 11.06% | 192.78% worse |
| 2022 to 2023 heat rate | 14.70% | 11.04% | 33.11% worse |
| 2022 to 2023 CO2 intensity | 14.91% | 11.12% | 34.00% worse |

The matched cohort's aggregate intensities are stable to within one percent in
both transitions, but raw plant-specific persistence is unstable and biased
upward. The simpler cohort-mean rule wins in all four comparisons. This result
does not prove that a constant global intensity is structurally correct. It
shows that an unregularized plant-level prior is not justified by these two
transitions.

Follow-up attribution in `egrid-influence-audit-2026-09-12.md` finds that two
plants account for 93.16% and 82.45% of heat-input error in the respective
transitions. The result therefore diagnoses unregularized ratio persistence,
not plant-level modeling in general. These years are now exploratory evidence
for any subsequent threshold or shrinkage choice.

EPA renamed the dominant provenance label from `EPA/CAMD` to `EPA/CAPD` in
2023. The audit preserves exact labels and also normalizes these two names to an
EPA source family, preventing an organizational rename from being interpreted
as an independent measurement-method change.

## Decision for BAU Hibrid 2026

No central curve or parameter changes. A later coupled energy module should:

- model generation activity separately from heat and emissions intensity;
- start from aggregate, technology-stratified priors rather than raw
  plant-specific persistence;
- use partial pooling or another predeclared shrinkage rule before adding plant
  heterogeneity;
- include entry, exit and dispatch uncertainty instead of conditioning silently
  on target-year generation;
- require multi-year, genuinely as-of validation before promotion.

The evidence is US-only, gas-only and observational. eGRID integrates EPA and
EIA sources; provenance fields are not measurement-method classifications.
Plant outages, dispatch, maintenance, fuel mix details and reporting changes
can drive errors. Two annual transitions are too few for a calibrated global
prior or a World3 feedback.

Reproduce the annual cohorts with `scripts/audit_egrid.py`, then run
`python3 scripts/audit_egrid_temporal.py`. Machine-readable results are in
`science/data/energy_audit/egrid-temporal-audit.json`.
