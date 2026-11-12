import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from alarmwatch.collector import ReadOnlyModbusCollector
from alarmwatch.engine import AlarmEngine
from control.engine import ControlEngine
from control.logger import DecisionLogger
from simulator.modbus_server import make_server
from simulator.plant_model import PlantModel


class AlarmEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = AlarmEngine()

    def test_on_delay_and_deadband(self):
        normal = {"drum_level": 40}
        low = {"drum_level": 29}
        self.engine.evaluate(normal, 0)
        self.assertEqual(self.engine.evaluate(low, 1), [])
        self.assertEqual(self.engine.states["ALM-001"]["phase"], "pending")
        self.assertEqual(self.engine.evaluate(low, 3.9), [])
        raised = self.engine.evaluate(low, 4)
        self.assertEqual([event["alarm_id"] for event in raised], ["ALM-001"])
        self.assertEqual(self.engine.states["ALM-001"]["phase"], "active")
        self.engine.evaluate({"drum_level": 31}, 5)
        self.assertEqual(self.engine.states["ALM-001"]["phase"], "active")
        cleared = self.engine.evaluate({"drum_level": 32}, 6)
        self.assertEqual([event["event"] for event in cleared], ["returned_to_normal"])

    def test_acknowledgment_and_event_history(self):
        events = []
        self.engine.event_sink = events.append
        self.engine.evaluate({"low_low_alarm": True}, 0)
        self.assertEqual(self.engine.states["ALM-002"]["phase"], "active")
        event = self.engine.acknowledge("ALM-002", "operator-1")
        self.assertEqual(event["event"], "acknowledged")
        self.assertEqual(event["actor"], "operator-1")
        with self.assertRaises(ValueError):
            self.engine.acknowledge("ALM-002", "operator-1")
        self.engine.evaluate({"low_low_alarm": False}, 1)
        self.assertEqual(self.engine.states["ALM-002"]["phase"], "normal")
        self.assertEqual([event["event"] for event in events], ["raised", "acknowledged", "returned_to_normal"])

    def test_load_deviation_rule(self):
        self.engine.evaluate({"gas_load": 300, "load_setpoint": 360}, 0)
        self.assertEqual(self.engine.states["ALM-005"]["phase"], "pending")
        self.engine.evaluate({"gas_load": 300, "load_setpoint": 360}, 10)
        self.assertEqual(self.engine.states["ALM-005"]["phase"], "active")
        self.engine.evaluate({"gas_load": 331, "load_setpoint": 360}, 11)
        self.assertEqual(self.engine.states["ALM-005"]["phase"], "normal")


class ReadOnlyCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_all_mapped_points_without_issuing_writes(self):
        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.reads = 0
                self.read_holding_registers = AsyncMock(side_effect=self.register_response)
                self.read_input_registers = AsyncMock(side_effect=self.register_response)
                self.read_coils = AsyncMock(side_effect=self.coil_response)
                self.close = lambda: None

            async def connect(self):
                return True

            async def register_response(self, *args, **kwargs):
                self.reads += 1
                return SimpleNamespace(isError=lambda: False, registers=[5000])

            async def coil_response(self, *args, **kwargs):
                self.reads += 1
                return SimpleNamespace(isError=lambda: False, bits=[True])

        fake = FakeClient()
        collector = ReadOnlyModbusCollector(client_factory=lambda *args, **kwargs: fake)
        values = await collector.poll_once()
        self.assertIn("load_setpoint", values)
        self.assertIn("level_setpoint", values)
        self.assertEqual(fake.reads, len(collector.points))
        self.assertGreater(len(values), 0)
        self.assertEqual(collector.health()["read_point_count"], len(collector.points))
        self.assertFalse(any("write" in method for method in vars(fake)))

    async def test_reads_real_simulator_over_modbus_tcp(self):
        engine = ControlEngine(PlantModel(), DecisionLogger(None))
        server = make_server(engine, port=0)
        await server.serve_forever(background=True)
        try:
            port = server.transport.sockets[0].getsockname()[1]
            collector = ReadOnlyModbusCollector(port=port)
            values = await collector.poll_once()
            self.assertEqual(values["gas_load"], 360)
            self.assertEqual(values["drum_level"], 50)
            self.assertTrue(values["pump_running"])
            self.assertIn("load_setpoint", values)
            self.assertTrue(collector.health()["connected"])
        finally:
            await server.shutdown()


if __name__ == "__main__":
    unittest.main()