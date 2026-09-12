"""Reproduce diagnostic efficiencies; not a model validation or calibration."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'science/src'), str(ROOT / 'science/vendor')]
from world3_empirical.energy_emissions import efficiency_from_heat_rate

source = json.loads((ROOT / 'science/data/energy_audit/eia-heat-rate-2024.json').read_text())
records = source['records']
if source['unit'] != 'Btu/net kWh' or [r['year'] for r in records] != list(range(2014, 2025)):
    raise ValueError('Unexpected units or year coverage')
result = {'status': 'diagnostic_only_not_independent_emissions_validation', 'fuels': {}}
for fuel in ('natural_gas', 'coal'):
    efficiencies = [efficiency_from_heat_rate(btu_per_net_kwh=r[fuel]) for r in records]
    result['fuels'][fuel] = {
        'efficiency_percent_2014': 100 * efficiencies[0],
        'efficiency_percent_2024': 100 * efficiencies[-1],
        'change_percentage_points': 100 * (efficiencies[-1] - efficiencies[0]),
        'years_efficiency_decreased': [records[i]['year'] for i in range(1, len(records)) if efficiencies[i] < efficiencies[i-1]]}
print(json.dumps(result, indent=2))
