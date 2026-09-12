"""Reproducible natural-gas cohort; source-stratified accounting diagnostic."""
from collections import Counter
import math

FIELDS = ('YEAR','ORISPL','PNAME','SECTOR','PLPRMFL','CHPFLAG','USETHRMO',
          'RMBMFLAG','PLGSPR','PLNGENAN','UNHTI','UNCO2','UNCO2SRC','UNHTISRC')


def exclusion(row, expected_year=2023):
    if row['YEAR'] != expected_year:
        return 'other_year'
    if row['SECTOR'] not in ('Electric Utility', 'IPP Non-CHP'):
        return 'sector'
    if row['CHPFLAG'] not in (None, '') or row['USETHRMO'] not in (None, 0):
        return 'chp_or_unknown_adjustment'
    if row['RMBMFLAG'] not in (None, ''):
        return 'biomass_adjustment'
    if row['PLPRMFL'] != 'NG' or row['PLGSPR'] != 1:
        return 'not_exactly_gas_generation'
    for key in ('PLNGENAN','UNHTI','UNCO2'):
        v = row[key]
        if isinstance(v, bool) or not isinstance(v, (float,int)) or not math.isfinite(v) or v <= 0:
            return 'missing_or_nonpositive_quantities'
    if not row['UNCO2SRC'] or not row['UNHTISRC']:
        return 'missing_provenance'
    return None


def audit(rows, expected_year=2023):
    excluded = Counter()
    selected = []
    seen = set()
    for row in rows:
        for k in FIELDS:
            if k not in row:
                raise ValueError(f'Missing column {k}')
        key = (row['YEAR'], row['ORISPL'])
        if key in seen:
            raise ValueError('Duplicate plant-year')
        seen.add(key)
        reason = exclusion(row, expected_year)
        if reason:
            excluded[reason] += 1
        else:
            selected.append({k:row[k] for k in FIELDS})
    if not selected:
        raise ValueError('Empty eligible cohort')
    groups = {}
    for row in selected:
        key = row['UNCO2SRC'] + ' | ' + row['UNHTISRC']
        g = groups.setdefault(key, dict(plants=0, net_mwh=0., heat_mmbtu=0., co2_short_tons=0.))
        g['plants'] += 1
        g['net_mwh'] += row['PLNGENAN']
        g['heat_mmbtu'] += row['UNHTI']
        g['co2_short_tons'] += row['UNCO2']
    for g in groups.values():
        g['heat_rate_btu_per_net_kwh'] = 1000*g['heat_mmbtu']/g['net_mwh']
        g['co2_kg_per_net_mwh'] = 907.18474*g['co2_short_tons']/g['net_mwh']
        g['implied_co2_kg_per_mmbtu'] = 907.18474*g['co2_short_tons']/g['heat_mmbtu']
    return {'input_plants':len(seen), 'eligible_plants':len(selected),
            'excluded_first_reason':dict(sorted(excluded.items())),
            'groups_by_co2_and_heat_source':groups}, sorted(selected,key=lambda x:x['ORISPL'])
