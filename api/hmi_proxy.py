from pymodbus.client import AsyncModbusTcpClient

from simulator.modbus_server import BASES, DEFAULT_MODBUS_PORT, REGISTER_MAP


class HmiProxy:
    def __init__(self, host="127.0.0.1", port=DEFAULT_MODBUS_PORT):
        self.host = host
        self.port = port

    async def read_points(self):
        client = AsyncModbusTcpClient(self.host, port=self.port)
        if not await client.connect():
            raise ConnectionError("Modbus server is unavailable")
        values = {}
        try:
            for point in REGISTER_MAP["points"]:
                address = point["address"] - BASES[point["table"]] - 1
                if point["table"] == "holding":
                    response = await client.read_holding_registers(address, count=1)
                elif point["table"] == "input":
                    response = await client.read_input_registers(address, count=1)
                else:
                    response = await client.read_coils(address, count=1)
                if response.isError():
                    raise ConnectionError(f"Modbus read failed for {point['name']}: {response}")
                raw = response.bits[0] if point["table"] == "coil" else response.registers[0]
                values[point["name"]] = raw / point["scale"]
            return values
        finally:
            client.close()

    async def write_point(self, name, value):
        point = next((point for point in REGISTER_MAP["points"] if point["name"] == name and point["access"] == "write"), None)
        if point is None:
            raise ValueError("Point is not writable")
        client = AsyncModbusTcpClient(self.host, port=self.port)
        if not await client.connect():
            raise ConnectionError("Modbus server is unavailable")
        try:
            address = point["address"] - BASES[point["table"]] - 1
            if point["table"] == "coil":
                response = await client.write_coil(address, bool(value))
            else:
                response = await client.write_register(address, round(value * point["scale"]))
            if response.isError():
                raise ValueError(f"Modbus rejected write: {response}")
        finally:
            client.close()