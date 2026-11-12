# Test report

Run: `python -m unittest discover -s tests -v`. Verified 2026-11-12 with Python 3.13 and pymodbus 3.11.4: **25 tests passed**. Both frontend clean installs and production builds passed. A browser check submitted a 400 MW setpoint and observed a rising displayed gas load; the setpoint was returned to 360 MW. Mobile layout was checked for horizontal overflow.

| Requirement | Evidence |
| --- | --- |
| FC03 at 40001 | Real TCP client reads PDU offset 0 and receives raw 3600, representing 360.0 MW. |
| Default TCP port | Unit test confirms the server defaults to port 502; a local TCP smoke test bound port 502 and read raw 3600 at FC03 offset 0. Port 5020 remains an environment-configurable fallback. |
| Invalid address | Real TCP holding and input reads return exception 02. |
| Read-only write | FC06 against the read-only holding point at offset 0 and FC05 against a read-only coil return exception 02. The Modbus standard has no input-register write function; FC06 addresses the separate holding table. |
| Level control | Ten seeded 60-minute simulations, one-second scans: level stays within 49-51%. This is a steady-state test, not a guarantee under all disturbances. |
| Low-low trip | 100 independent seeded scenarios cross from 20.1% to at or below 20%. All 100 trip pump, open bypass and latch on the first scan; recovery without reset remains latched, and reset at 25% is denied. Maximum detection delay for this scan-based test is one simulated second. |
| Operator setpoint | API integration test sends an HMI setpoint via FC06, checks WebSocket value and simulates a measurable load increase; browser interaction was also checked. |
| Fuel flow | The model derives simplified fuel flow from effective valve demand; tests check steady, startup, and shutdown behavior, and the turbine HMI displays the mapped point. |
| Logging | A scan record contains UTC timestamp, complete input/output snapshots and all three program decisions. |
| Log retention | Rotation test confirms control-decision JSONL logs stay within the configured active file plus three backups. |
| Modbus audit | Real TCP tests record connections, FC03/FC06/FC16 requests, mapped addresses, register-map write acceptance/rejection, and exception responses without recording payload values or peer addresses. The AlarmaWatch activity view exposes all, write/exception, and connection filters. |
| Security observations | Real TCP tests verify rejected-write SEC-001 and reserved-function SEC-002 observations; synthetic cases verify exception counters, overlapping-window deduplication, and audit-source unavailable state. This is local simulator telemetry, not intrusion detection. |
| Map consistency | Test compares documented address, name, table, scale, access and version with the JSON map and checks each implemented point. |
| Additional coverage | FC01, FC04, FC05, FC06 and FC16 are exercised on TCP; FC16 tests two values, atomic illegal-address and illegal-value rejection. On/off timers and mode responses are checked. |

The 100 successful trip scenarios are finite simulation tests, not proof that the interlock can never fail. No hardware-in-the-loop, real-time scheduling, network fault, cybersecurity certification, or safety validation was performed.