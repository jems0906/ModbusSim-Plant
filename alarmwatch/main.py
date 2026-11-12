import asyncio
import json
import os
import re
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from alarmwatch.collector import ReadOnlyModbusCollector
from alarmwatch.engine import AlarmEngine
from alarmwatch.security import ModbusSecurityObserver
from simulator.modbus_server import DEFAULT_MODBUS_PORT

EVENT_PATH = Path(os.getenv("ALARMAWATCH_EVENT_LOG", "logs/alarmwatch-events.jsonl"))
SCAN_SECONDS = max(0.5, float(os.getenv("ALARMAWATCH_SCAN_SECONDS", "1")))
AUDIT_API_URL = os.getenv("ALARMAWATCH_AUDIT_API_URL", "http://127.0.0.1:8000").rstrip("/")
AUDIT_SCAN_SECONDS = max(1.0, float(os.getenv("ALARMAWATCH_AUDIT_SCAN_SECONDS", "2")))


def append_event(event):
    EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_PATH.open("a", encoding="utf-8") as output:
        output.write(json.dumps(event, allow_nan=False) + "\n")


collector = ReadOnlyModbusCollector(
    host=os.getenv("ALARMAWATCH_MODBUS_HOST", "127.0.0.1"),
    port=int(os.getenv("ALARMAWATCH_MODBUS_PORT", str(DEFAULT_MODBUS_PORT))),
    device_id=int(os.getenv("ALARMAWATCH_MODBUS_DEVICE_ID", "1")),
)
engine = AlarmEngine(event_sink=append_event)
security_observer = ModbusSecurityObserver()
latest_values = {}
last_poll_error = None
started = asyncio.Event()


async def polling_loop():
    global latest_values, last_poll_error
    started.set()
    while True:
        try:
            values = await collector.poll_once()
            latest_values = values
            last_poll_error = None
            engine.evaluate({**values, "modbus_connected": True}, asyncio.get_running_loop().time())
        except Exception as error:
            last_poll_error = str(error)
            engine.evaluate({"modbus_connected": False}, asyncio.get_running_loop().time())
        await asyncio.sleep(SCAN_SECONDS)


async def security_polling_loop():
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            try:
                response = await client.get(f"{AUDIT_API_URL}/api/audit", params={"limit": 500, "kind": "all"})
                response.raise_for_status()
                security_observer.ingest(response.json().get("events", []))
                security_observer.update_source(True)
            except Exception as error:
                security_observer.update_source(False, error)
            await asyncio.sleep(AUDIT_SCAN_SECONDS)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(polling_loop())
    security_task = asyncio.create_task(security_polling_loop())
    yield
    task.cancel()
    security_task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    with suppress(asyncio.CancelledError):
        await security_task


app = FastAPI(title="AlarmaWatch", description="Read-only alarm management and ICS connection health monitor", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"], allow_methods=["GET", "POST"], allow_headers=["*"])


class AcknowledgeRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=64)


def snapshot():
    return {"values": latest_values, "health": collector.health(), "alarms": engine.active_alarms(),
            "rule_version": engine.version, "read_only": True, "last_poll_error": last_poll_error}


@app.get("/api/status")
async def status():
    return snapshot()


@app.get("/api/alarms")
async def alarms():
    return engine.active_alarms()


@app.get("/api/events")
async def events(limit: int = 100):
    if not 1 <= limit <= 500:
        raise HTTPException(422, "limit must be between 1 and 500")
    if not EVENT_PATH.exists():
        return []
    lines = EVENT_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(line) for line in reversed(lines)]


@app.get("/api/security/status")
async def security_status():
    return security_observer.status()


@app.get("/api/security/events")
async def security_events(limit: int = 100):
    try:
        return security_observer.recent(limit)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/api/alarms/{alarm_id}/ack")
async def acknowledge(alarm_id: str, body: AcknowledgeRequest):
    actor = body.actor.strip()
    if not actor or not re.fullmatch(r"[A-Za-z0-9_.@ -]+", actor):
        raise HTTPException(422, "actor must use letters, numbers, spaces, dot, underscore, @ or hyphen")
    try:
        return engine.acknowledge(alarm_id, actor)
    except KeyError as error:
        raise HTTPException(404, "Unknown alarm") from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(snapshot())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass