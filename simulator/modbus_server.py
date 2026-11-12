import json
from pathlib import Path

from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext
from pymodbus.constants import ExcCodes
from pymodbus.server import ModbusTcpServer

MAP_PATH = Path(__file__).with_name("register_map.json")
REGISTER_MAP = json.loads(MAP_PATH.read_text(encoding="utf-8"))
BASES = {"holding": 40000, "input": 30000, "coil": 10000}
DEFAULT_MODBUS_PORT = 502


class PlantBlock:
    def __init__(self, engine, table):
        self.engine = engine
        self.points = {point["address"] - BASES[table]: point for point in REGISTER_MAP["points"] if point["table"] == table}

    def reset(self):
        pass

    def getValues(self, address, count=1):
        if any(index not in self.points for index in range(address, address + count)):
            return ExcCodes.ILLEGAL_ADDRESS
        snapshot = self.engine.snapshot()
        return [int(round(snapshot[self.points[index]["name"]] * self.points[index]["scale"])) for index in range(address, address + count)]

    def setValues(self, address, values):
        points = [self.points.get(index) for index in range(address, address + len(values))]
        if any(point is None or point["access"] != "write" for point in points):
            return ExcCodes.ILLEGAL_ADDRESS
        updates = []
        for point, value in zip(points, values):
            name = point.get("target", point["name"])
            scaled = value / point["scale"]
            if name == "level_setpoint" and not 30 <= scaled <= 70 or name == "load_setpoint" and not 0 <= scaled <= 600:
                return ExcCodes.ILLEGAL_VALUE
            updates.append((name, scaled))
        for name, value in updates:
            if name == "reset_trip":
                self.engine.reset_trip = bool(value)
            else:
                self.engine.set_setpoint(name, value)
        return None


def make_server(engine, host="127.0.0.1", port=DEFAULT_MODBUS_PORT, audit_log=None):
    device = ModbusDeviceContext(hr=PlantBlock(engine, "holding"), ir=PlantBlock(engine, "input"), co=PlantBlock(engine, "coil"), di=PlantBlock(engine, "coil"))
    return ModbusTcpServer(ModbusServerContext(devices=device, single=True), address=(host, port),
                           trace_pdu=audit_log.trace_pdu if audit_log else None,
                           trace_packet=audit_log.trace_packet if audit_log else None,
                           trace_connect=audit_log.trace_connect if audit_log else None)