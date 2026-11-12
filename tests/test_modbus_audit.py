import asyncio
import unittest

from pymodbus.client import AsyncModbusTcpClient

from control.engine import ControlEngine
from control.logger import DecisionLogger
from simulator.audit_log import ModbusAuditLog
from simulator.modbus_server import make_server
from simulator.plant_model import PlantModel


class ModbusAuditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.audit = ModbusAuditLog(path=None)
        self.server = make_server(ControlEngine(PlantModel(), DecisionLogger(None)), port=0, audit_log=self.audit)
        await self.server.serve_forever(background=True)
        self.port = self.server.transport.sockets[0].getsockname()[1]
        self.client = AsyncModbusTcpClient("127.0.0.1", port=self.port)
        self.assertTrue(await self.client.connect())

    async def asyncTearDown(self):
        self.client.close()
        await self.server.shutdown()

    async def test_logs_connections_reads_writes_and_rejections_without_payload(self):
        self.assertFalse((await self.client.read_holding_registers(0, count=1)).isError())
        self.assertFalse((await self.client.write_register(4, 4000)).isError())
        self.assertFalse((await self.client.write_registers(4, [4100, 500])).isError())
        self.assertEqual((await self.client.write_register(0, 10)).exception_code, 2)

        events = self.audit.tail(100)
        self.assertTrue(any(event["category"] == "connection" and event["event"] == "opened" for event in events))
        requests = [event for event in events if event["event"] == "request"]
        self.assertTrue(any(event["function_code"] == 3 and event["address"] == 40001 for event in requests))
        writes = [event for event in requests if event["is_write"]]
        self.assertEqual([event["write_policy"] for event in reversed(writes)],
                 ["allowed_by_register_map", "allowed_by_register_map", "rejected_by_register_map"])
        self.assertTrue(any(event["function_code"] == 16 for event in writes))
        self.assertTrue(any(event["event"] == "response" and event["is_exception"] for event in events))
        self.assertTrue(all("registers" not in event and "bits" not in event for event in events))
        self.assertTrue(all(event["peer_identity"] is None for event in events if event["category"] == "connection"))
        filtered = self.audit.tail(20, "writes")
        self.assertTrue(filtered)
        self.assertTrue(all(event.get("is_write") or event.get("is_exception") for event in filtered))
        self.assertTrue(all(event["category"] != "connection" for event in self.audit.tail(20, "writes")))

    async def test_raw_unsupported_function_frame_is_audited_without_payload(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        frame = b"\x00\x2a\x00\x00\x00\x02\x01\x41"
        try:
            writer.write(frame)
            await writer.drain()
            response = await asyncio.wait_for(reader.read(64), timeout=2)
            self.assertTrue(response)
        finally:
            writer.close()
            await writer.wait_closed()
        event = next(item for item in self.audit.tail(100) if item.get("transaction_id") == 42)
        self.assertEqual(event["function_code"], 65)
        self.assertEqual(event["transaction_id"], 42)
        self.assertTrue(event["unsupported_function"])
        self.assertFalse(event["payload_logged"])
        self.assertNotIn("packet", event)


if __name__ == "__main__":
    unittest.main()