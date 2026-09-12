import unittest
from world3_empirical.egrid_audit import FIELDS,audit

class EgridTests(unittest.TestCase):
    def row(self, **changes):
        r=dict.fromkeys(FIELDS)
        r.update(YEAR=2023,ORISPL=1,PNAME='Synthetic',SECTOR='IPP Non-CHP',PLPRMFL='NG',
                 PLGSPR=1,PLNGENAN=100,UNHTI=1000,UNCO2=50,UNCO2SRC='EIA',UNHTISRC='EIA')
        r.update(changes);return r
    def test_conversion_and_weights(self):
        report,_=audit([self.row(),self.row(ORISPL=2,PLNGENAN=200)])
        g=report['groups_by_co2_and_heat_source']['EIA | EIA']
        self.assertAlmostEqual(g['heat_rate_btu_per_net_kwh'],2000000/300)
        self.assertAlmostEqual(g['co2_kg_per_net_mwh'],90718.474/300)
    def test_chp_and_mixed_fuel_excluded(self):
        report,cohort=audit([self.row(),self.row(ORISPL=2,CHPFLAG='Yes'),self.row(ORISPL=3,PLGSPR=.99)])
        self.assertEqual(len(cohort),1)
        self.assertEqual(sum(report['excluded_first_reason'].values()),2)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):audit([self.row(),self.row()])
    def test_missing_schema_rejected(self):
        r=self.row();del r['UNCO2SRC']
        with self.assertRaises(ValueError):audit([r])
    def test_missing_quantities_not_zero_filled(self):
        report,_=audit([self.row(),self.row(ORISPL=2,UNHTI=None)])
        self.assertEqual(report['excluded_first_reason']['missing_or_nonpositive_quantities'],1)
    def test_sources_kept_separate(self):
        report,_=audit([self.row(),self.row(ORISPL=2,UNCO2SRC='EPA/CAPD',UNHTISRC='EPA/CAPD')])
        self.assertEqual(len(report['groups_by_co2_and_heat_source']),2)
