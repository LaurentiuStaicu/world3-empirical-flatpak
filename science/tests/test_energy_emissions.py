import unittest
from world3_empirical.energy_emissions import combustion_generation, advance_atmospheric_co2

class EnergyEmissionsTests(unittest.TestCase):
    def generation(self, **overrides):
        args = dict(capacity_gw=1., capacity_factor=.5, hours=8760.,
                    efficiency_ncv=.5, co2_kg_per_tj_ncv=50000.)
        args.update(overrides)
        return combustion_generation(**args)

    def test_hand_calculated_units(self):
        r = self.generation()
        self.assertAlmostEqual(r.electricity_twh, 4.38)
        self.assertAlmostEqual(r.fuel_input_pj_ncv, 31.536)
        self.assertAlmostEqual(r.direct_co2_mt, 1.5768)

    def test_efficiency_changes_fuel_not_electricity(self):
        a, b = self.generation(), self.generation(efficiency_ncv=.25)
        self.assertEqual(a.electricity_twh, b.electricity_twh)
        self.assertEqual(b.direct_co2_mt, 2*a.direct_co2_mt)

    def test_idle_capacity_has_no_combustion(self):
        self.assertEqual(self.generation(capacity_factor=0).direct_co2_mt, 0)

    def test_invalid_inputs(self):
        for args in ({'efficiency_ncv':0}, {'capacity_factor':1.1},
                     {'capacity_gw':float('nan')}, {'hours':-1},
                     {'co2_kg_per_tj_ncv':True}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.generation(**args)

    def test_mass_balance_and_interval_consistency(self):
        args = dict(anthropogenic_gtco2_per_year=10,
                    natural_net_source_gtco2_per_year=2,
                    removal_gtco2_per_year=8)
        full = advance_atmospheric_co2(stock_gtco2=100, years=1, **args)
        half = advance_atmospheric_co2(stock_gtco2=100, years=.5, **args)
        self.assertEqual(full, 104)
        self.assertEqual(full, advance_atmospheric_co2(stock_gtco2=half, years=.5, **args))

    def test_excess_removal_fails_instead_of_clipping(self):
        with self.assertRaises(ValueError):
            advance_atmospheric_co2(stock_gtco2=1, years=1,
                anthropogenic_gtco2_per_year=0, natural_net_source_gtco2_per_year=0,
                removal_gtco2_per_year=2)


class NetElectricityTests(unittest.TestCase):
    def test_own_use_is_not_grid_loss(self):
        from world3_empirical.energy_emissions import net_electricity_twh
        self.assertEqual(net_electricity_twh(gross_twh=100, auxiliary_fraction=.05), 95)
        with self.assertRaises(ValueError):
            net_electricity_twh(gross_twh=100, auxiliary_fraction=1.1)

    def test_eia_heat_rate_conversion(self):
        from world3_empirical.energy_emissions import efficiency_from_heat_rate
        self.assertAlmostEqual(efficiency_from_heat_rate(btu_per_net_kwh=7754), .44003095176683004)
        for invalid in (0, 3000, float('nan')):
            with self.assertRaises(ValueError):
                efficiency_from_heat_rate(btu_per_net_kwh=invalid)
