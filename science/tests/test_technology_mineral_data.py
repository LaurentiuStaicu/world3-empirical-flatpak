import unittest

import pandas as pd

from world3_empirical.sources.minerals import (
    build_2025_risk_table,
    parse_owid_history,
    parse_usgs_mcs,
    stitch_latest_production,
)


class TechnologyMineralDataTests(unittest.TestCase):
    def test_owid_parser_keeps_commodities_separate(self):
        raw = pd.DataFrame([
            {"Entity": "Copper", "Year": 2015, "Global mine production of different minerals": 10},
            {"Entity": "Nickel", "Year": 2015, "Global mine production of different minerals": 2},
            {"Entity": "Gold", "Year": 2015, "Global mine production of different minerals": 1},
        ])
        parsed = parse_owid_history(raw)
        self.assertEqual(set(parsed["commodity"]), {"copper", "nickel"})
        self.assertEqual(len(parsed), 2)

    def test_stitch_replaces_2024_and_normalizes_2015(self):
        commodities = ["cobalt", "copper", "graphite", "lithium", "nickel", "rare_earths"]
        history = pd.DataFrame([
            {"commodity": commodity, "year": year, "production_tonnes": value}
            for commodity in commodities
            for year, value in [(2015, 10.0), (2024, 20.0)]
        ])
        mcs = pd.DataFrame([
            {"commodity": commodity, "country": "World total", "statistic": "Production",
             "statistic_detail": "Mine production: rounded", "year": year,
             "value_tonnes": value, "lower_bound": False, "estimated": year == 2025,
             "notes": "Estimated." if year == 2025 else ""}
            for commodity in commodities
            for year, value in [(2024, 30.0), (2025, 40.0)]
        ])
        result = stitch_latest_production(history, mcs)
        copper = result.loc[result["commodity"].eq("copper")].set_index("year")
        self.assertEqual(float(copper.loc[2024, "production_tonnes"]), 30.0)
        self.assertEqual(float(copper.loc[2025, "production_tonnes"]), 40.0)
        self.assertEqual(float(copper.loc[2015, "production_index_2015_100"]), 100.0)

    def test_usgs_parser_converts_thousand_tonnes_and_flags_bounds(self):
        raw = pd.DataFrame([
            {"Commodity": "Copper", "Country": "World total", "Statistics": "Reserves",
             "Statistics_detail": "Reserves: rounded", "Unit": "thousand metric tons",
             "Year": "2025", "Value": ">1,000", "Notes": ""},
        ])
        parsed = parse_usgs_mcs(raw)
        self.assertEqual(float(parsed.iloc[0]["value_tonnes"]), 1_000_000.0)
        self.assertTrue(bool(parsed.iloc[0]["lower_bound"]))

    def test_risk_hhi_is_bounded_by_residual(self):
        commodities = ["cobalt", "copper", "graphite", "lithium", "nickel", "rare_earths"]
        production = pd.DataFrame([
            {"commodity": commodity, "year": year, "production_tonnes": value,
             "estimated": year == 2025}
            for commodity in commodities
            for year, value in [(2020, 80.0), (2025, 100.0)]
        ])
        mcs_rows = []
        for commodity in commodities:
            mcs_rows.extend([
                {"commodity": commodity, "country": "A", "statistic": "Production",
                 "statistic_detail": "Mine production", "year": 2025, "value_tonnes": 60.0,
                 "lower_bound": False, "estimated": True, "notes": ""},
                {"commodity": commodity, "country": "B", "statistic": "Production",
                 "statistic_detail": "Mine production", "year": 2025, "value_tonnes": 20.0,
                 "lower_bound": False, "estimated": True, "notes": ""},
                {"commodity": commodity, "country": "World total", "statistic": "Reserves",
                 "statistic_detail": "Reserves", "year": 2025, "value_tonnes": 1000.0,
                 "lower_bound": False, "estimated": False, "notes": ""},
            ])
        risk = build_2025_risk_table(production, pd.DataFrame(mcs_rows))
        copper = risk.set_index("commodity").loc["copper"]
        self.assertAlmostEqual(float(copper["production_hhi_lower_bound"]), 0.40)
        self.assertAlmostEqual(float(copper["production_hhi_upper_bound"]), 0.44)


if __name__ == "__main__":
    unittest.main()
