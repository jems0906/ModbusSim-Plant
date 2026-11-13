# Railway deployment

Railway runs this project as one container: Nginx serves the Plant HMI at `/` and AlarmaWatch at `/alarmwatch/`; the two FastAPI apps are loopback-only upstreams. The Modbus server listens on `127.0.0.1:502` inside the container. **Do not add a Railway TCP proxy or publish port 502.**

The public deployment is a read-only portfolio demo. Railway sets `RAILWAY_ENVIRONMENT`, the container sets `RAILWAY_READ_ONLY_DEMO=1`, and the frontend build disables setpoint, mode, trip-reset, and acknowledgment controls. Backend write endpoints independently return HTTP 403. Local development remains interactive.

## Deploy

From the repository root, with Railway CLI authenticated and linked to the intended account:

```powershell
railway init --name ModbusSim-Plant
railway up --detach
railway domain
```

The GitHub repository is already connected locally as `origin`; to use Railway GitHub autodeploys instead of local-source uploads, connect service source in the Railway dashboard to `jems0906/ModbusSim-Plant` on `main`.

After deploying, set or verify the Railway health check path `/healthz`. Wait for the deployment to become healthy, then open the Railway-provided domain and `/alarmwatch/`. `railway domain` provisions a public HTTP domain for the combined app. The API routes share that domain behind Nginx; the Modbus TCP listener does not.

## Validation and limitations

Verify `/healthz`, `/api/status`, `/api/security/status`, and the WebSocket-driven dashboards. Confirm POSTs to `/api/setpoints/...`, `/api/mode/...`, `/api/trip/reset`, and `/api/alarms/.../ack` return 403 in Railway. The public service contains only synthetic simulator data; its writable UI controls are intentionally disabled.

Railway filesystems are ephemeral by default, so simulation state and JSONL logs reset when the container is replaced or redeployed. The public app is a portfolio demonstration, not an operating control system. No live plant connectivity, public Modbus listener, packet capture, authentication of alarm findings, or safety/security certification is provided.