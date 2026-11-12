import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.hmi_proxy import HmiProxy
from control.engine import ControlEngine
from simulator.audit_log import ModbusAuditLog
from simulator.modbus_server import DEFAULT_MODBUS_PORT, make_server
from simulator.plant_model import PlantModel

plant = PlantModel()
engine = ControlEngine(plant)
MODBUS_HOST = os.getenv("MODBUS_HOST", "127.0.0.1")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", str(DEFAULT_MODBUS_PORT)))
proxy = HmiProxy(MODBUS_HOST, MODBUS_PORT)
audit_log = ModbusAuditLog(os.getenv("MODBUS_AUDIT_LOG", "logs/modbus-audit.jsonl"))


async def scan_loop():
    while True:
        engine.run(1.0)
        plant.step(1.0)
        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app):
    server = make_server(engine, MODBUS_HOST, MODBUS_PORT, audit_log)
    await server.serve_forever(background=True)
    task = asyncio.create_task(scan_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    await server.shutdown()
    engine.logger.close()
    audit_log.close()


app = FastAPI(title="ModbusSim Plant", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])


class Setpoint(BaseModel):
    value: float


@app.get("/api/status")
async def status():
    try:
        values = await proxy.read_points()
        return {**values, "mode": plant.mode, "simulated_seconds": plant.time,
                "audit": audit_log.health()}
    except ConnectionError as error:
        raise HTTPException(503, str(error)) from error


@app.get("/api/audit")
async def audit(limit: int = 100, kind: str = "all"):
    try:
        return {"events": audit_log.tail(limit, kind), "health": audit_log.health()}
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/api/setpoints/{name}")
async def setpoint(name: str, body: Setpoint):
    if name not in ("level_setpoint", "load_setpoint"):
        raise HTTPException(404, "Unknown setpoint")
    try:
        limits = {"level_setpoint": (30, 70), "load_setpoint": (0, 600)}
        if not limits[name][0] <= body.value <= limits[name][1]:
            raise ValueError(f"Setpoint must be between {limits[name][0]} and {limits[name][1]}")
        await proxy.write_point(name, body.value)
    except (ValueError, OverflowError) as error:
        raise HTTPException(422, str(error)) from error
    except ConnectionError as error:
        raise HTTPException(503, str(error)) from error
    return {"accepted": True}


@app.post("/api/trip/reset")
async def reset_trip():
    await proxy.write_point("reset_trip", True)
    return {"accepted": True}


@app.post("/api/mode/{mode}")
async def set_mode(mode: str):
    if mode not in ("startup", "steady", "shutdown"):
        raise HTTPException(422, "Unknown mode")
    plant.mode = mode
    plant.mode_elapsed = 0.0
    return {"mode": mode}


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(await status())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass