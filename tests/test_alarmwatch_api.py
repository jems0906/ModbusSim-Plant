import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from alarmwatch.engine import AlarmEngine
from alarmwatch.security import ModbusSecurityObserver
import alarmwatch.main as main
from alarmwatch.main import app


class AlarmApiTests(unittest.TestCase):
    def test_alarm_acknowledgment_and_no_control_write_endpoint(self):
        async def idle_poller():
            await asyncio.Event().wait()

        with tempfile.TemporaryDirectory() as directory:
            with patch("alarmwatch.main.EVENT_PATH", Path(directory) / "events.jsonl"), \
                 patch("alarmwatch.main.engine", AlarmEngine(event_sink=main.append_event)), \
                 patch("alarmwatch.main.security_observer", ModbusSecurityObserver()), \
                 patch("alarmwatch.main.polling_loop", idle_poller), \
                 patch("alarmwatch.main.security_polling_loop", idle_poller), \
                 TestClient(app) as client:
                main.engine.evaluate({"low_low_alarm": True}, 0)
                response = client.get("/api/alarms")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()[0]["id"], "ALM-002")
                ack = client.post("/api/alarms/ALM-002/ack", json={"actor": "operator-1"})
                self.assertEqual(ack.status_code, 200)
                self.assertEqual(ack.json()["actor"], "operator-1")
                self.assertEqual(client.post("/api/setpoints/load_setpoint", json={"value": 400}).status_code, 404)
                event = client.get("/api/events").json()[0]
                self.assertEqual(event["event"], "acknowledged")
                main.security_observer.ingest([{"timestamp": "2026-11-12T00:00:00+00:00", "category": "modbus",
                                                "event": "request", "function_code": 6, "is_write": True,
                                                "write_policy": "rejected_by_register_map", "address": 40001,
                                                "device_id": 1, "transaction_id": 7}])
                self.assertEqual(client.get("/api/security/status").json()["rejected_write_count"], 1)
                findings = client.get("/api/security/events").json()
                self.assertEqual(findings[0]["rule_id"], "SEC-001")
                self.assertEqual(client.get("/api/security/events?limit=0").status_code, 422)

    def test_railway_read_only_demo_blocks_acknowledgment(self):
        async def idle_poller():
            await asyncio.Event().wait()

        with patch("alarmwatch.main.RAILWAY_READ_ONLY_DEMO", True), \
             patch("alarmwatch.main.polling_loop", idle_poller), \
             patch("alarmwatch.main.security_polling_loop", idle_poller), \
             TestClient(app) as client:
            response = client.post("/api/alarms/ALM-002/ack", json={"actor": "reviewer"})
            self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()