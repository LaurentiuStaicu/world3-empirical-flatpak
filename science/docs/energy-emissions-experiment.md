# Experimental energy and emissions accounting

This module is an accounting foundation, not an empirically calibrated forecast.
It is not imported by the central World3 simulation and changes no app curves.

## Boundaries and units

`combustion_generation` represents one combustion technology over a supplied
number of hours. GW × capacity factor × hours / 1000 gives gross electricity
in TWh. Multiplying by 3.6 and dividing by net-calorific efficiency gives fuel
input in PJ. Fuel PJ × emission factor kg CO2/TJ / 1e6 gives Mt CO2.
Capacity is operational capacity, not announced projects. The caller must
supply a consistent interval and factor including its oxidation convention.
No empirical default factors are prescribed. Test values are synthetic.

Method reference: IPCC 2006 National Greenhouse Gas Inventories, Volume 2,
stationary combustion worksheets:
https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_x_An1_Worksheets.pdf

This excludes upstream methane, lifecycle construction emissions, carbon
capture and auxiliary electricity. Gross generation must not be equated with
retail electricity sales. Renewable generation needs separate accounting, not
a fictitious thermal efficiency. Existing net-energy index scenarios cannot
be passed as physical PJ without an independently justified scale and boundary.

`advance_atmospheric_co2` integrates specified interval-average sources minus
removals in Gt CO2/year against atmospheric mass in Gt CO2. Natural sources
and removals must not cover the same process twice. The function does not
estimate ocean/land sinks or treat CO2 as a single exponential-decay reservoir.
Atmospheric mass is not ppm, temperature or World3 persistent pollution.
Negative resulting mass raises an error rather than hiding it with clipping.

## Verification and next data requirements

Six tests cover hand-calculated conversion, efficiency sensitivity, idle
capacity, invalid inputs, conservation and interval subdivision, and excessive
removal. These verify accounting, not real-world predictive accuracy.

Before coupling: acquire observed generation/fuel/emissions on matching system
boundaries; estimate technology efficiencies; specify and validate a carbon
cycle and mass-to-concentration conversion; then validate climate response.
A subsequent damage module must audit overlap with existing World3 pollution
impacts. Do not add a generic warming multiplier to the central run.
