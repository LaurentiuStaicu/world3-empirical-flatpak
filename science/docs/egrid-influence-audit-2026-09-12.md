# Concentration of eGRID persistence errors

This follow-up attributes the already observed temporal errors to individual
plants. It is post-hoc diagnosis using target-year outcomes, not a new
validation experiment or a rule for excluding inconvenient observations.
Reproduce with `python3 scripts/audit_egrid_influence.py`. The input cohorts,
original EPA workbook URLs and SHA-256 hashes remain those of the temporal audit.

| Transition | Top two plants' share of heat error | Top two plants' share of CO2 error |
|---|---:|---:|
| 2021–2022 | 93.16% | 93.07% |
| 2022–2023 | 82.45% | 81.54% |

For heat input, T J Labbe (ORIS 56108) and Hargis-Hebert (56283) dominate the
first transition. Their prior net generation is only 22 and 30 MWh,
respectively, followed by 95,973 and 84,246 MWh. Applying the prior ratio of
heat input to that tiny generation denominator produces extreme estimates.
AES Huntington Beach (335) and AES Alamitos (315) dominate the second
transition. Huntington Beach's net generation rises from 106,269 to 3,212,590
MWh. Its source-derived prior heat ratio is about 268,014 Btu/net kWh.

These numbers are ratios of reported fields, not verified design efficiencies.
The arithmetic explains why the unregularized persistence rule is unstable.
It does not establish why the underlying ratios are extreme. Low utilization,
station use, outages, configuration changes, differences between unit and
plant accounting boundaries, or reporting anomalies need separate checks.
An ORIS match alone does not prove constant plant composition. Do not infer
an outage or a data error from this diagnostic alone.

The earlier finding that the cohort mean beats raw plant persistence remains
numerically correct. Its interpretation must be narrow: a few influential
plant-years dominate the loss. This is not general evidence against plant-level
models, nor validation of a constant global thermal-efficiency prior.

No plants are removed, no errors are recomputed after outcome-based trimming,
and no central-model parameters change. Before testing partial pooling or
technology groups, check the influential plants against the official unit and
generator sheets and reconcile the numerator and denominator. Any thresholds
or shrinkage chosen after inspecting these years require new evaluation data;
2021–2023 can no longer serve as untouched confirmation for that choice.

The JSON report includes total WMAPE, concentration at the top 1/2/5/10 plants,
and the top ten contributors with generation, intensity and provenance in
both years. A zero-error panel has undefined concentration, represented as null.
