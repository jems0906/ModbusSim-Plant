import unittest

from control.engine import ControlEngine
from control.logger import DecisionLogger
from simulator.plant_model import PlantModel


class InterlockTests(unittest.TestCase):
    def test_trip_on_first_scan_for_many_crossings_and_latches(self):
        for seed in range(100):
            plant = PlantModel(seed)
            controller = ControlEngine(plant, DecisionLogger(None))
            plant.drum_level = 20.1
            controller.run()
            self.assertTrue(plant.pump_running)
            plant.drum_level = 20.0 - seed / 1000
            controller.run()
            self.assertFalse(plant.pump_running)
            self.assertTrue(plant.bypass_open)
            self.assertTrue(controller.low_low_alarm)
            plant.drum_level = 30
            controller.run()
            self.assertTrue(controller.low_low_alarm)
            controller.reset_trip = True
            controller.run()
            self.assertFalse(controller.low_low_alarm)
            self.assertTrue(plant.pump_running)

    def test_reset_denied_until_recovered(self):
        plant = PlantModel()
        controller = ControlEngine(plant, DecisionLogger(None))
        plant.drum_level = 20
        controller.run()
        plant.drum_level = 25
        controller.reset_trip = True
        controller.run()
        self.assertTrue(controller.low_low_alarm)