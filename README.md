# ModbusSim Plant

A local combined-cycle **training simulator**, with a pymodbus TCP server, JSON control programs, a FastAPI/WebSocket gateway, and a React operator display. It is not a real plant model, safety instrumented system, or production control system. The simplified model is not a representation of La Paloma's actual equipment or operating limits.

The companion [AlarmaWatch project](docs/alarmwatch.md) polls mapped values using Modbus read functions only, provides alarm acknowledgment and source-health monitoring, and surfaces the simulator-only security observations defined in [its scope](docs/alarmwatch_security_spec.md).

For a complete alarm trigger, acknowledgment, and return-to-normal walkthrough, see the [portfolio demo runbook](docs/portfolio_demo.md).

See the [portfolio evidence page](docs/portfolio_evidence.md) for screenshots, clean-install results, and test evidence.

## Run

Requires Python 3.10+ and Node.js 20+. From the workspace root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The backend starts its Modbus server at `127.0.0.1:502`, unit ID 1. If port 502 is reserved or occupied, set `MODBUS_PORT=5020` before starting the backend and `ALARMAWATCH_MODBUS_PORT=5020` for AlarmaWatch. Never bind this training server to a plant network. It has no authentication, encryption, or production hardening. The API also defaults to loopback; CORS permits only the local Vite origin. The optional frontend Docker image uses `host.docker.internal` for its API proxy; connecting it requires a backend interface reachable from the container and appropriate firewall restrictions, so the default loopback-only backend may not be reachable from Docker.

## Verify

```powershell
python -m unittest discover -s tests -v
cd frontend
npm run build
```

See [register map](docs/register_map.md), [control narrative](docs/control_narrative.md), [programming guide](docs/logic_programming_guide.md), and [test report](docs/test_report.md). The simulator uses one-second scans at approximately real time; tests advance simulated time without waiting. Control-decision JSONL logs rotate at 5 MiB with three backups; Modbus audit logs use the same retention. For a real Modbus client read holding offset 0, count 1 (FC03): raw 3600 initially means 360.0 MW.