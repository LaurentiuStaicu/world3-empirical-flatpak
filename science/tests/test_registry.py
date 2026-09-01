import unittest

from world3_empirical.registry import load_registry


class RegistryTests(unittest.TestCase):
    def test_registry_is_valid_and_marks_latent_constructs(self):
        registry = load_registry()
        self.assertFalse(registry.empty)
        pollution = registry.loc[registry["series_id"] == "world3_persistent_pollution"].iloc[0]
        self.assertEqual(pollution["observation_type"], "latent")
        self.assertEqual(pollution["status"], "not_observed")


if __name__ == "__main__":
    unittest.main()

