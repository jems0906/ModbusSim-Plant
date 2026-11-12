"""Read-only Modbus polling. No write operation is exposed by this class."""

import time

from pymodbus.client import AsyncModbusTcpClient

from simulator.modbus_server import BASES, DEFAULT_MODBUS_PORT, REGISTER_MAP


class ReadOnlyModbusCollector:
    def __init__(self, host="127.0.0.1", port=DEFAULT_MODBUS_PORT, device_id=1, client_factory=AsyncModbusTcpClient):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.client_factory = client_factory
        self.points = list(REGISTER_MAP["points"])
        self.last_success = None
        self.last_latency_ms = None
        self.last_point_count = 0
        self.consecutive_failures = 0
        self.last_error = None

    async def poll_once(self):
        client = self.client_factory(self.host, port=self.port)
        started = time.monotonic()
        try:
            if not await client.connect():
                raise ConnectionError("Modbus TCP connection failed")
            values = {}
            for point in self.points:
                address = point["address"] - BASES[point["table"]] - 1
                if point["table"] == "holding":
                    response = await client.read_holding_registers(address, count=1, device_id=self.device_id)
                elif point["table"] == "input":
                    response = await client.read_input_registers(address, count=1, device_id=self.device_id)
                else:
                    response = await client.read_coils(address, count=1, device_id=self.device_id)
                if response.isError():
                    raise ConnectionError(f"Read failed for {point['name']}")
                raw = response.bits[0] if point["table"] == "coil" else response.registers[0]
                values[point["name"]] = raw if point["table"] == "coil" else raw / point["scale"]
            self.last_success = time.time()
            self.last_latency_ms = round((time.monotonic() - started) * 1000, 1)
            self.last_point_count = len(values)
            self.consecutive_failures = 0
            self.last_error = None
            return values
        except Exception as error:
            self.consecutive_failures += 1
            self.last_error = str(error)
            raise
        finally:
            client.close()

    def health(self):
        return {"connected": self.consecutive_failures == 0 and self.last_success is not None,
                "last_success_epoch": self.last_success, "last_latency_ms": self.last_latency_ms,
                "read_point_count": self.last_point_count, "consecutive_failures": self.consecutive_failures,
                "last_error": self.last_error, "mode": "read-only Modbus polling"}