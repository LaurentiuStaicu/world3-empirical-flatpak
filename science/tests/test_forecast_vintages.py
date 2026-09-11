import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from world3_empirical.forecast_vintages import load_forecasts, available_forecasts, calibration_observations

SOURCE = Path(__file__).resolve().parents[1] / "data/forecasts/eia-steo-2026-09-11.json"


class ForecastVintageTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(SOURCE.read_text())

    def check_bad(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                load_forecasts(path)

    def test_verified_values_and_units(self):
        rows = load_forecasts(SOURCE)
        self.assertEqual(len(rows), 4)
        self.assertEqual([(r['value'], r['unit']) for r in rows], [(4135, 'TWh'), (4211, 'TWh'), (4821, 'Mt CO2'), (4816, 'Mt CO2')])

    def test_release_date_does_not_backdate_live_capture(self):
        rows = load_forecasts(SOURCE)
        self.assertEqual(available_forecasts(rows, date(2026, 9, 9)), [])
        self.assertEqual(len(available_forecasts(rows, date(2026, 9, 11))), 4)
        self.assertEqual(available_forecasts(rows, date(2018, 12, 31)), [])

    def test_forecasts_cannot_be_calibration_observations(self):
        with self.assertRaises(ValueError):
            calibration_observations(load_forecasts(SOURCE))

    def test_duplicate_and_mislabel_rejected(self):
        bad = copy.deepcopy(self.payload)
        bad['records'].append(bad['records'][0])
        self.check_bad(bad)
        self.payload['records'][0]['evidence_type'] = 'observed'
        self.check_bad(self.payload)

    def test_backdating_and_nonfinite_values_rejected(self):
        for field, value in [('available_from', '2026-09-09'), ('value', float('nan')), ('value', -1)]:
            with self.subTest(field=field, value=value):
                bad = copy.deepcopy(self.payload)
                bad['records'][0][field] = value
                self.check_bad(bad)

    def test_future_revision_is_excluded(self):
        rows = load_forecasts(SOURCE)
        future = dict(rows[0], captured_on='2026-10-01', available_from='2026-10-01', value=9999)
        self.assertEqual(available_forecasts(rows + [future], date(2026, 9, 11)), rows)


if __name__ == '__main__':
    unittest.main()
