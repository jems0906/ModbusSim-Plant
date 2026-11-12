import unittest

from simulator.plant_model import PlantModel


class PlantModelTests(unittest.TestCase):
    def test_load_responds_with_lag(self):
        plant = PlantModel()
        plant.fuel_valve = 70.0
        plant.step()
        self.assertGreater(plant.gas_load, 360.0)
        self.assertLess(plant.gas_load, 420.0)
        self.assertAlmostEqual(plant.fuel_flow, 7.0)

    def test_balanced_flows_are_stable(self):
        plant = PlantModel()
        for _ in range(3600):
            plant.step()
        self.assertGreater(plant.drum_level, 48.0)
        self.assertLess(plant.drum_level, 52.0)

    def test_startup_and_shutdown_reduce_effective_fuel(self):
        plant = PlantModel()
        plant.mode = "shutdown"
        plant.step(45)
        self.assertLess(plant.gas_load, 200)
        self.assertEqual(plant.fuel_flow, 0)
        plant = PlantModel()
        plant.mode = "startup"
        plant.step(1)
        self.assertLess(plant.gas_load, 360)
        self.assertLess(plant.fuel_flow, plant.fuel_valve * 0.1)


if __name__ == "__main__":
    unittest.main()