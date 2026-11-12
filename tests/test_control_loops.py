import json
import tempfile
import unittest
from pathlib import Path

from control.engine import ControlEngine
from control.logger import DecisionLogger
from simulator.plant_model import PlantModel


class ControlTests(unittest.TestCase):
    def test_drum_band_for_sixty_minutes(self):
        for seed in range(10):
            plant = PlantModel(seed)
            controller = ControlEngine(plant, DecisionLogger(None))
            for _ in range(3600):
                controller.run()
                plant.step()
                self.assertTrue(49 <= plant.drum_level <= 51)

    def test_setpoint_changes_response(self):
        plant = PlantModel()
        controller = ControlEngine(plant, DecisionLogger(None))
        controller.set_setpoint("load_setpoint", 420)
        for _ in range(300):
            controller.run()
            plant.step()
        self.assertGreater(plant.gas_load, 400)

    def test_every_scan_logs_inputs_outputs_and_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.jsonl"
            controller = ControlEngine(PlantModel(), DecisionLogger(path))
            controller.run()
            entry = json.loads(path.read_text(encoding="utf-8"))
            controller.logger.close()
            self.assertIn("timestamp", entry)
            self.assertIn("drum_level", entry["inputs"])
            self.assertIn("feedwater_valve", entry["outputs"])
            self.assertEqual(len(entry["decisions"]), 3)

    def test_decision_log_rotates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.jsonl"
            logger = DecisionLogger(path, max_bytes=200, backup_count=1)
            for index in range(6):
                logger.write({"scan": index, "detail": "x" * 100})
            logger.close()
            self.assertTrue(path.exists())
            self.assertTrue(Path(f"{path}.1").exists())
            self.assertLessEqual(len(list(Path(directory).glob("control.jsonl*"))), 2)

    def test_on_and_off_delay_timers(self):
        plant = PlantModel()
        controller = ControlEngine(plant, DecisionLogger(None))
        controller.programs = [{"name": "timer_test", "instructions": [
            {"op": "read", "source": "pump_running", "as": "active"},
            {"op": "timer_on", "condition": "active", "delay": 2, "as": "on"},
            {"op": "timer_off", "condition": "active", "delay": 2, "as": "off"},
        ]}]
        controller.run()
        self.assertFalse(controller.timers["timer_test:on"][0])
        self.assertTrue(controller.timers["timer_test:off"][0])
        controller.run()
        self.assertTrue(controller.timers["timer_test:on"][0])
        plant.pump_running = False
        controller.run()
        self.assertFalse(controller.timers["timer_test:on"][0])
        self.assertTrue(controller.timers["timer_test:off"][0])
        controller.run()
        self.assertFalse(controller.timers["timer_test:off"][0])