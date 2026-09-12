# Plant-level gas accounting audit, 12 September 2026

Source: EPA eGRID2023 revision 2 (12 June 2025), obtained 12 September 2026:
https://www.epa.gov/system/files/documents/2025-06/egrid2023_data_rev2.xlsx
Metadata and SHA-256: science/data/energy_audit/egrid-source.json.
The original 21 MB workbook is externally hosted, not committed. The full
selected cohort is retained as deterministic gzip JSON; source fields unchanged.

Reproduce: install the project's scientific environment plus openpyxl, download
the URL above, then run `python3 scripts/audit_egrid.py INPUT.xlsx OUTPUT_DIR`.
The extractor refuses any file whose SHA-256 differs from the reviewed revision.

## Selection

All 12,612 PLNT23 rows were considered. Keep year 2023, Electric Utility or
IPP Non-CHP sector, no CHP adjustment flag or positive useful thermal output,
no biomass adjustment flag, primary fuel NG, reported gas generation share
exactly 1, positive finite net generation, unadjusted combustion heat input
and unadjusted CO2, and nonempty source provenance. Blank adjustment flags
are accepted as in this workbook, with sector and useful-heat checks as well.
This is a selected reporting cohort, not a verified census of pure-gas fuel use:
100% gas generation does not rule out startup fuel use. No cutoff was selected
based on the resulting emissions factor. Exclusion counts use first failing rule.

735 plants pass. Net generation, fuel input and CO2 come from the same
plant-year within EPA's integrated dataset. Aggregation is by sum of quantities,
not mean of plant ratios. CO2 short tons convert using 907.18474 kg/short ton.
Heat input remains MMBtu on source conventions; no NCV conversion is assumed.

## Results and limits

567 EPA/CAPD-source plants: 1,106.653 TWh, 7550.39 Btu/net kWh,
406.04 kg CO2/net MWh, implied 53.777 kg CO2/MMBtu.
167 EIA-source plants: 16.435 TWh, 8819.63 Btu/net kWh,
467.75 kg CO2/net MWh, implied 53.035 kg CO2/MMBtu.
One mixed-source plant is retained as its own group.

Source grouping is not a measurement-method classification: EPA/CAPD provenance
does not establish that every CO2 value is independently measured by a monitor.
EIA-derived emissions may reuse fuel factors. The implied factor is therefore
an accounting diagnostic, not an independently validated coefficient. Fleet
composition, dispatch and reporting methods can confound between-group differences.

This resolves plant-year alignment for a reproducible cohort. It does not
validate forecasts, estimate a global efficiency, or recalibrate World3.
A genuine predictive test needs earlier-year training data, later-year matching
plants, technology/dispatch controls and unit-level emissions-method checks.
Central curves and the Flatpak version remain unchanged.

EPA source integration methodology:
https://www.epa.gov/egrid/frequent-questions-about-egrid
