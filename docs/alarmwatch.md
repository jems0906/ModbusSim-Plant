# AlarmaWatch

AlarmaWatch is a companion training project. It polls mapped ModbusSim Plant points using read function codes only (including read-back of writable setpoints needed for deviation alarms), evaluates configurable alarms, offers operator acknowledgment, and records alarm events in JSON Lines. The collector never invokes a Modbus write function. Default API port: 8001; default source: `127.0.0.1:502`, unit ID 1.

## Run

Start ModbusSim Plant as described in the root [README](../README.md). In a second terminal at the workspace root:

```powershell
python -m uvicorn alarmwatch.main:app --host 127.0.0.1 --port 8001
```

In a third terminal:

```powershell
cd alarmwatch/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

Open http://127.0.0.1:5174. Source host, port, unit ID, scan interval, and event-log path can be set with `ALARMAWATCH_MODBUS_HOST`, `ALARMAWATCH_MODBUS_PORT`, `ALARMAWATCH_MODBUS_DEVICE_ID`, `ALARMAWATCH_SCAN_SECONDS`, and `ALARMAWATCH_EVENT_LOG`.

## Alarm behavior

Rules live in `alarmwatch/rules.json`, version 1.0.0. A condition must persist for its configured on-delay before becoming active. Clearing uses a separate threshold where configured, providing hysteresis. Acknowledgment records the supplied operator label; it does not clear an alarm. The process condition must clear independently. Every raise, acknowledgment, and return-to-normal is appended to `logs/alarmwatch-events.jsonl` by default. This is a local append-only-for-normal-operation log, not tamper-proof audit storage.

The console shows active and pending alarms, alarm priority, values, operator acknowledgment, event history, Modbus poll latency/failures, and data-source availability. Its Modbus activity view reads the simulator's local audit endpoint and filters connection lifecycle, function codes, mapped addresses, register-map write policy, and exception responses. The separate security-observation view implements [SEC-001/SEC-002/MET-001](alarmwatch_security_spec.md); it does not block requests or infer a client identity. The server keeps 10,000 events in memory and rotates JSONL audit files at 5 MiB with three backups. `SYS-001` reports a Modbus source outage after a three-second delay.

AlarmaWatch checks the Plant HTTP audit API at `ALARMAWATCH_AUDIT_API_URL` (default `http://127.0.0.1:8000`) every `ALARMAWATCH_AUDIT_SCAN_SECONDS` (default 2 seconds). Audit-source unavailability is shown separately from “no findings.”

## Scope and security boundary

The collector only invokes Modbus read function codes; no Modbus write method is present. The API only accepts alarm acknowledgments and exposes no setpoint, coil, or process-control write route. Health indicators cover polling connectivity and read failures. The simulator audit hook logs requests and responses, but does not block them. It does not record payload values, peer IP addresses, or an authenticated client identity. This project does **not** capture network packets, detect unauthorized Modbus clients, authenticate users, encrypt traffic, or certify alarm performance. It is not a security appliance, alarm rationalization, safety instrumented system, or production-ready control-room tool. Keep both services loopback-bound; do not connect them to a live plant network.

## Verify

From the project root, run `python -m unittest discover -s tests -v`. From `alarmwatch/frontend`, run `npm run build`. Tests exercise alarm delays, deadbands, acknowledgment history, a real read-only TCP poll, and the absence of a control-write API.