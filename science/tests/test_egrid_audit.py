import unittest
from world3_empirical.egrid_audit import FIELDS,audit
from world3_empirical.egrid_temporal import temporal_stability_audit

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
    def test_audit_accepts_explicit_historical_year(self):
        report,cohort=audit([self.row(YEAR=2022)],2022)
        self.assertEqual(report['eligible_plants'],1)
        self.assertEqual(cohort[0]['YEAR'],2022)

class EgridTemporalTests(unittest.TestCase):
    def row(self,year,plant,generation,heat,co2,source='EIA'):
        return dict(YEAR=year,ORISPL=plant,PNAME='Synthetic',SECTOR='IPP Non-CHP',
                    PLPRMFL='NG',CHPFLAG=None,USETHRMO=None,RMBMFLAG=None,
                    PLGSPR=1,PLNGENAN=generation,UNHTI=heat,UNCO2=co2,
                    UNCO2SRC=source,UNHTISRC=source)
    def test_matched_panel_and_entry_exit_counts(self):
        train=[self.row(2022,1,100,1000,50),self.row(2022,2,100,800,40)]
        target=[self.row(2023,1,200,2000,100),self.row(2023,3,100,900,45)]
        report=temporal_stability_audit(train,target,2022,2023)
        self.assertEqual(report['matched_plants'],1)
        self.assertEqual(report['exiting_plants'],1)
        self.assertEqual(report['entering_plants'],1)
        self.assertAlmostEqual(report['matched_share_of_target_generation_pct'],200/3)
    def test_persistence_is_scored_conditionally_on_target_generation(self):
        train=[self.row(2022,1,100,1000,50),self.row(2022,2,200,1600,80)]
        target=[self.row(2023,1,300,2700,135),self.row(2023,2,100,900,45)]
        report=temporal_stability_audit(train,target,2022,2023)
        heat=report['signals']['heat_rate_btu_per_net_kwh']
        self.assertAlmostEqual(heat['training_aggregate_intensity'],2600000/300)
        self.assertAlmostEqual(heat['target_aggregate_intensity'],3600000/400)
        self.assertGreaterEqual(heat['plant_specific_persistence']['quantity_weighted_absolute_percentage_error_pct'],0)
    def test_epa_organizational_rename_is_normalized_not_erased(self):
        train=[self.row(2022,1,100,1000,50,'EPA/CAMD')]
        target=[self.row(2023,1,100,1000,50,'EPA/CAPD')]
        report=temporal_stability_audit(train,target,2022,2023)
        self.assertIn('EPA/CAMD | EPA/CAMD -> EPA/CAPD | EPA/CAPD',report['raw_source_transitions'])
        self.assertEqual(report['normalized_source_family_transitions']['EPA | EPA -> EPA | EPA'],1)
    def test_nonconsecutive_years_are_rejected(self):
        with self.assertRaises(ValueError):
            temporal_stability_audit([self.row(2021,1,1,1,1)],[self.row(2023,1,1,1,1)],2021,2023)
    def test_invalid_physical_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            temporal_stability_audit([self.row(2022,1,0,1,1)],[self.row(2023,1,1,1,1)],2022,2023)
