import socket
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app, engine, plant
from api.hmi_proxy import HmiProxy


class ApiTests(unittest.TestCase):
    def test_operator_setpoint_through_websocket_and_modbus(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        with patch("api.main.MODBUS_PORT", port), patch("api.main.proxy", HmiProxy(port=port)), TestClient(app) as client:
            self.assertEqual(client.get("/api/status").status_code, 200)
            self.assertEqual(client.get("/api/audit?limit=10&kind=all").status_code, 200)
            self.assertEqual(client.get("/api/audit?limit=10&kind=unknown").status_code, 422)
            self.assertEqual(client.post("/api/setpoints/load_setpoint", json={"value": 420}).status_code, 200)
            self.assertEqual(engine.load_setpoint, 420)
            with client.websocket_connect("/ws") as websocket:
                self.assertEqual(websocket.receive_json()["load_setpoint"], 420)
            before = plant.gas_load
            for _ in range(120):
                engine.run()
                plant.step()
            self.assertGreater(plant.gas_load, before + 30)
            self.assertEqual(client.post("/api/setpoints/load_setpoint", json={"value": 1000}).status_code, 422)