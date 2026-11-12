# Register map

Version **1.0.1**. This document and `simulator/register_map.json` are the contract; change both, increment the version, record the change here, and run the map test before changing an address. Only listed points exist. A read spanning an unlisted point returns exception 02. All registers are unsigned 16-bit integers; engineering value = raw value / scale. Boolean values are 0 or 1. `write` means readable and writable. No signed values or multi-register values are defined.

Human references are one-based; Modbus PDU offsets are zero-based: 40001 = holding offset 0, 30001 = input offset 0, 10001 = coil offset 0. **10001 is used here as the requested project label for coils**, although conventional Modbus notation normally uses 0xxxx for coils and 1xxxx for discrete inputs. Use function 01/05 for these points, not the label to choose the function. Unit ID 1; default TCP port 502. Set `MODBUS_PORT=5020` and `ALARMAWATCH_MODBUS_PORT=5020` to use an unprivileged alternate port if the platform reserves 502 or it is already occupied.

| Address | Name | Table | Scale | Access | Unit | Meaning |
| --- | --- | --- | --- | --- | --- | --- |
| 40001 | `gas_load` | holding | 10 | read | MW | Gas turbine load |
| 40002 | `exhaust_temp` | holding | 10 | read | deg C | Exhaust temperature |
| 40003 | `fuel_valve` | holding | 10 | read | % | Fuel valve position, proxy for fuel flow |
| 40004 | `rpm` | holding | 1 | read | rpm | Rotor speed, simplified |
| 40005 | `load_setpoint` | holding | 10 | write | MW | Load setpoint, 0-600 MW |
| 40006 | `level_setpoint_batch` | holding | 10 | write | % | Alias of 40055, for atomic FC16 setpoint writes |
| 40007 | `fuel_flow` | holding | 10 | read | kg/s | Simplified gas turbine fuel flow derived from valve demand |
| 40051 | `drum_level` | holding | 10 | read | % | Drum level |
| 40052 | `steam_pressure` | holding | 10 | read | bar | Steam pressure |
| 40053 | `steam_temp` | holding | 10 | read | deg C | Steam temperature |
| 40054 | `feedwater_flow` | holding | 10 | read | % | Normalized feedwater flow |
| 40055 | `level_setpoint` | holding | 10 | write | % | Level setpoint, 30-70% |
| 40056 | `feedwater_valve` | holding | 10 | read | % | Feedwater valve position |
| 40057 | `steam_flow` | holding | 10 | read | % | Normalized steam flow |
| 40101 | `steam_inlet_pressure` | holding | 10 | read | bar | Steam turbine inlet pressure |
| 40102 | `steam_load` | holding | 10 | read | MW | Steam turbine load |
| 40103 | `extraction_pressure` | holding | 10 | read | bar | Extraction pressure |
| 40151 | `generator_mw` | holding | 10 | read | MW | Generator active power |
| 40152 | `mvar` | holding | 10 | read | MVAR | Generator reactive power, fixed at zero |
| 40153 | `frequency` | holding | 100 | read | Hz | Generator frequency, fixed at 60 Hz |
| 40154 | `breaker_closed` | holding | 1 | read | bool | Generator breaker status |
| 10001 | `pump_running` | coil | 1 | read | bool | Feedwater pump running |
| 10002 | `bypass_open` | coil | 1 | read | bool | Feedwater bypass open |
| 10003 | `low_low_alarm` | coil | 1 | read | bool | Low-low trip latched |
| 10010 | `reset_trip` | coil | 1 | write | bool | Write true to request reset; reads false |
| 30001 | `exhaust_sensor` | input | 10 | read | deg C | Exhaust transmitter |
| 30002 | `level_sensor` | input | 10 | read | % | Level transmitter |
| 30003 | `pressure_sensor` | input | 10 | read | bar | Steam pressure transmitter |

Functions: 01 read coils, 03 read holding registers, 04 read input registers, 05 write single coil, 06 write single holding register, 16 write multiple holding registers. The standard defines no write function for input registers: FC06 at the same numeric offset addresses the **holding** table, not the input table. Such a write returns exception 02 when the holding point is read-only. Invalid setpoint values return exception 03. Multiple writes validate the whole request before applying any value. Only mapped writable points may be written.

Change history: 1.0.0 initial published map; 1.0.1 adds simplified gas turbine fuel flow at 40007 without moving existing points.