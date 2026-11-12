import re
import unittest
from pathlib import Path

from simulator.modbus_server import REGISTER_MAP, PlantBlock
from simulator.plant_model import PlantModel
from control.engine import ControlEngine
from control.logger import DecisionLogger


class RegisterMapTests(unittest.TestCase):
    def test_document_and_implemented_points_match(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "register_map.md").read_text(encoding="utf-8")
        self.assertIn(f'Version **{REGISTER_MAP["version"]}**', text)
        documented = {(int(address), name, table, int(scale), access) for address, name, table, scale, access in re.findall(r"\| (\d{5}) \| `([^`]+)` \| (holding|coil|input) \| (\d+) \| (read|write) \|", text)}
        points = REGISTER_MAP["points"]
        expected = {(point["address"], point["name"], point["table"], point["scale"], point["access"]) for point in points}
        self.assertEqual(documented, expected)
        self.assertEqual(len(expected), len(points))
        engine = ControlEngine(PlantModel(), DecisionLogger(None))
        snapshot = engine.snapshot()
        for point in points:
            self.assertIn(point["name"], snapshot)
            self.assertIn(point["address"] - {"holding": 40000, "input": 30000, "coil": 10000}[point["table"]], PlantBlock(engine, point["table"]).points)