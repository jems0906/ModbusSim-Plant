# Portfolio demo runbook

This walkthrough demonstrates register-backed simulation, control response, alarm delay, operator acknowledgment, return-to-normal, and a read-only monitoring boundary. It uses a temporary load setpoint change, restores the value that was present at start, and waits for the modeled process to settle. It is designed for local software simulation only.

## Start the three services

From the workspace root, start each command in its own terminal:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
python -m uvicorn alarmwatch.main:app --host 127.0.0.1 --port 8001
node frontend/node_modules/vite/bin/vite.js frontend --host 127.0.0.1 --port 5173 --strictPort
node alarmwatch/frontend/node_modules/vite/bin/vite.js alarmwatch/frontend --host 127.0.0.1 --port 5174 --strictPort
```

Open the [ModbusSim Plant HMI](http://127.0.0.1:5173/) and [AlarmaWatch console](http://127.0.0.1:5174/). Verify the plant is near its load setpoint and AlarmaWatch reports a connected source before triggering a demo.

## Automated walkthrough

In a separate terminal at the workspace root:

```powershell
python scripts/demo_walkthrough.py
```

The script checks AlarmaWatch connectivity and its published API routes, confirms the load is settled and no load-deviation alarm is already active, then:

1. Selects a temporary load setpoint at the opposite end of the range through the **ModbusSim** API.
2. Waits for AlarmaWatch's configured deviation on-delay and acknowledges `ALM-005` as `portfolio-demo`.
3. Restores the original setpoint and waits for the process to respond and the alarm to return to normal.
4. Prints a JSON pass summary; raise, acknowledgment, and clear events remain visible in AlarmaWatch history.

The process response can take several minutes. The script times out rather than claiming success if the source, alarm, or clear event does not arrive. On an error after changing a setpoint, it attempts to restore the original value. Run only against the local simulator, never against a real control network.

For a manual walkthrough, set the gas turbine load setpoint from the Plant HMI, observe the corresponding `ALM-005` in AlarmaWatch, enter an operator label and acknowledge it, then return the load setpoint to its original value. Wait for the process to recover and verify the `returned_to_normal` event. Do not acknowledge by changing the alarm's process value in AlarmaWatch; it has no process-control endpoint.

## Three-minute presentation

Run the automated walkthrough before the presentation; process response and alarm clearing can take several minutes. Leave both dashboards open at their normal operating state, with the completed alarm events in history.

| Time | Show and say |
| --- | --- |
| 0:00-0:30 | Set the boundary: “This is a laptop simulation, not a plant replica or safety system. ModbusSim models the process; AlarmaWatch reads the map and manages alarm events.” |
| 0:30-1:00 | Show the Plant HMI and register-map document. Point out FC03 holding offset 0: raw 3600 represents 360.0 MW. |
| 1:00-1:40 | Describe the completed load-setpoint demo: the operator changed the setpoint through ModbusSim, the modeled load responded over time, and AlarmaWatch raised `ALM-005`. Show its acknowledgment and return-to-normal events. |
| 1:40-2:20 | Switch AlarmaWatch to Modbus activity, select Writes & exceptions, and show the FC06 request at 40005 with its map-policy result. Explain that request payloads and peer IP addresses are not logged. |
| 2:20-3:00 | Close with the evidence: 25 passing tests, clean installs and builds for both frontends, the 60-minute level-control test, and the 100-scenario finite trip test. State that the audit is not packet capture or intrusion detection. |

If asked to run the alarm scenario live, start `python scripts/demo_walkthrough.py` and allow several minutes for the process to return to its clear band. Do not promise a three-minute end-to-end simulation.

## Evidence to show

- ModbusSim FC03 holding offset 0 reads raw `3600` at its default 360.0 MW load.
- The Plant HMI setpoint change affects the modeled load over time.
- AlarmaWatch shows `ALM-005` transition from on-delay to active, then acknowledged, then returned to normal.
- The event history records the rule, value, UTC timestamp, and acknowledgment actor.
- The Modbus activity filters show connection lifecycle, function codes, mapped addresses, writes accepted or rejected by the register map, and exception responses.
- AlarmaWatch status shows `read_only: true`, source health, and read latency. The audit omits payload values and peer IP addresses; it is not a packet monitor or intrusion detector.
- Run `python -m unittest discover -s tests -v` and build both frontends with `npm run build` in their respective directories. See [Plant test report](test_report.md) and [AlarmaWatch scope](alarmwatch.md).

All displays and alarm settings are training examples, not La Paloma/NAES plant settings. These projects do not qualify as a safety system or production ICS security control.