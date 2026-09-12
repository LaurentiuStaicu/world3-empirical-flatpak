import unittest
from world3_empirical.egrid_influence import error_influence


def row(year, plant, generation, heat):
    return dict(YEAR=year, ORISPL=plant, PNAME=str(plant), PLNGENAN=generation,
                UNHTI=heat, UNCO2=heat/20, UNHTISRC='EIA', UNCO2SRC='EIA')


class InfluenceTests(unittest.TestCase):
    def test_small_denominator_dominates_without_exclusion(self):
        train=[row(2021,1,1,100), row(2021,2,100,1000)]
        target=[row(2022,1,100,1000), row(2022,2,100,1100)]
        report=error_influence(train,target,2021,2022)
        heat=report['signals']['heat_rate_btu_per_net_kwh']
        self.assertEqual(heat['matched_plants'],2)
        self.assertAlmostEqual(heat['wmape_pct'],100*9100/2100)
        self.assertAlmostEqual(heat['top_error_shares_pct']['1'],100*9000/9100)
        self.assertEqual(heat['top_plants'][0]['generation_ratio'],100)
        self.assertFalse(report['exclusions_applied'])

    def test_zero_error_share_is_undefined(self):
        report=error_influence([row(2021,1,1,10)],[row(2022,1,2,20)],2021,2022)
        heat=report['signals']['heat_rate_btu_per_net_kwh']
        self.assertEqual(heat['wmape_pct'],0)
        self.assertFalse(heat['error_share_defined'])
        self.assertIsNone(heat['top_error_shares_pct']['1'])

    def test_duplicates_and_nonconsecutive_years_rejected(self):
        a=row(2021,1,1,10)
        with self.assertRaises(ValueError):
            error_influence([a,a],[row(2022,1,2,20)],2021,2022)
        with self.assertRaises(ValueError):
            error_influence([a],[row(2023,1,2,20)],2021,2023)

    def test_input_order_does_not_change_rank_or_metrics(self):
        train=[row(2021,2,10,100),row(2021,1,10,100)]
        target=[row(2022,2,10,110),row(2022,1,10,110)]
        self.assertEqual(error_influence(train,target,2021,2022),
                         error_influence(train[::-1],target[::-1],2021,2022))
