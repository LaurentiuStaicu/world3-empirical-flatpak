import unittest

from world3_empirical.world3_03 import SCENARIO_NAMES, _sanitized_model_text, _source_model_path


class World303AdapterTests(unittest.TestCase):
    def test_official_model_is_present_and_sanitization_is_numerically_neutral(self):
        source = _source_model_path()
        self.assertTrue(source.exists())
        cleaned = _sanitized_model_text(source)
        self.assertNotIn("help link :is:", cleaned)
        self.assertIn("initial nonrenewable resources scenario table", cleaned)
        self.assertIn("(1,1e+12),(2,2e+12)", cleaned)

    def test_only_verified_scenarios_are_exposed(self):
        self.assertEqual(SCENARIO_NAMES, {1: "world3_03_bau", 2: "world3_03_bau2"})


if __name__ == "__main__":
    unittest.main()

