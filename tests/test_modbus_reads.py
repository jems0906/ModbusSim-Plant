import asyncio
import inspect
import unittest

from pymodbus.client import AsyncModbusTcpClient

from control.engine import ControlEngine
from control.logger import DecisionLogger
from simulator.modbus_server import DEFAULT_MODBUS_PORT, make_server
from simulator.plant_model import PlantModel


class ModbusTests(unittest.IsolatedAsyncioTestCase):
    def test_default_port_matches_project_specification(self):
        self.assertEqual(DEFAULT_MODBUS_PORT, 502)
        self.assertEqual(inspect.signature(make_server).parameters["port"].default, 502)

    async def asyncSetUp(self):
        self.plant = PlantModel()
        self.engine = ControlEngine(self.plant, DecisionLogger(None))
        self.server = make_server(self.engine, port=0)
        await self.server.serve_forever(background=True)
        port = self.server.transport.sockets[0].getsockname()[1]
        self.client = AsyncModbusTcpClient("127.0.0.1", port=port)
        self.assertTrue(await self.client.connect())

    async def asyncTearDown(self):
        self.client.close()
        await self.server.shutdown()

    async def test_real_function_codes(self):
        holding = await self.client.read_holding_registers(0, count=1)
        self.assertEqual(holding.registers[0], 3600)
        analog = await self.client.read_input_registers(0, count=1)
        self.assertEqual(analog.registers[0], 4800)
        coils = await self.client.read_coils(0, count=1)
        self.assertTrue(coils.bits[0])
        self.assertFalse((await self.client.write_register(4, 4000)).isError())
        self.assertEqual(self.engine.load_setpoint, 400)
        self.assertFalse((await self.client.write_registers(4, [4100, 510])).isError())
        self.assertEqual(self.engine.load_setpoint, 410)
        self.assertEqual(self.engine.level_setpoint, 51)
        invalid = await self.client.write_registers(4, [4200, 900])
        self.assertEqual(invalid.exception_code, 3)
        self.assertEqual(self.engine.load_setpoint, 410)
        self.assertEqual(self.engine.level_setpoint, 51)
        rejected = await self.client.write_registers(4, [4200, 520, 0])
        self.assertEqual(rejected.exception_code, 2)
        self.assertEqual(self.engine.load_setpoint, 410)
        self.assertEqual(self.engine.level_setpoint, 51)
        self.assertFalse((await self.client.write_coil(9, True)).isError())
        self.assertTrue(self.engine.reset_trip)

    async def test_exceptions(self):
        self.assertEqual((await self.client.read_holding_registers(500, count=1)).exception_code, 2)
        self.assertEqual((await self.client.read_input_registers(500, count=1)).exception_code, 2)
        self.assertEqual((await self.client.write_register(0, 10)).exception_code, 2)
        self.assertEqual((await self.client.write_coil(0, False)).exception_code, 2)
        self.assertEqual((await self.client.write_register(4, 6500)).exception_code, 3)