# EIA energy boundary audit — 2026-09-11

Reproduce with `python3 scripts/audit_energy_heat_rates.py`.

The manually transcribed US Table 8.1 covers 2014–2024. Its release is
2025-10-16, but this live-page extraction is available only from 2026-09-11
for retrospective availability checks. It is not an archived historical vintage.

Using EIA's rounded 3412 Btu/kWh conversion, net electric efficiency rises
from 43.152% to 44.003% for gas, but declines from 32.720% to 31.660% for coal.
Gas efficiency falls in 2018, 2022 and 2024. These fleet aggregates do not
identify technological learning, aging, dispatch or fuel-quality effects.
They do not support an assumption of monotonically improving fleet efficiency.
These are thermal conversion efficiencies, not extraction EROI.

Source and population:
https://www.eia.gov/electricity/annual/table.php?t=epa_08_01.html
Utility and independent power producer electricity-only plants; CHP and
commercial/industrial plants excluded.

Net-generation definition and conversion:
https://www.eia.gov/tools/faqs/faq.php?id=107&t=3
Net generation subtracts plant own-use. It is distinct from gross generation
and from retail sales. The new own-use function excludes transmission losses.
The heat-rate conversion preserves the source calorific basis and must not
be passed as NCV efficiency to the combustion module without verified conversion.

Rejected validation target:
https://www.eia.gov/electricity/annual/table.php?t=epa_09_01.html
Table 9.1 includes CHP and useful thermal output. Comparing its emissions total
with Table 8.1-derived electricity-only estimates would mix system boundaries.
Moreover, inventory emissions computed from fuel factors are not independent
measurements of those factors. No empirical emissions validation is claimed.

Next required dataset: matched plant-year electricity-only net generation,
fuel input and emissions, with fuel calorific basis and auxiliary use recorded.
Only then estimate errors for held-out plant-years. Preserve technology groups
and distinguish measurement from inventory estimates. No global parameter,
central World3 output or app release is changed by this diagnostic.
