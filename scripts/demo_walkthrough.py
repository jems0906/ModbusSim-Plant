"""Run a safe, repeatable local ModbusSim Plant + AlarmaWatch demo."""

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PLANT_API = "http://127.0.0.1:8000"
ALARM_API = "http://127.0.0.1:8001"
ACTOR = "portfolio-demo"


def request_json(base, path, method="GET", body=None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(base + path, data=payload, method=method,
                      headers={"Content-Type": "application/json"} if payload else {})
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach {base}: {error.reason}") from error


def wait_for(description, predicate, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(1)
    raise TimeoutError(f"Timed out after {timeout}s waiting for {description}")


def active_load_alarm():
    return next((alarm for alarm in request_json(ALARM_API, "/api/alarms")
                 if alarm["id"] == "ALM-005" and alarm["phase"] == "active"), None)


def load_alarm_cleared():
    active = any(alarm["id"] == "ALM-005" for alarm in request_json(ALARM_API, "/api/alarms"))
    if active:
        return False
    events = request_json(ALARM_API, "/api/events?limit=500")
    return any(event["alarm_id"] == "ALM-005" and event["event"] == "returned_to_normal"
               for event in events)


def run_demo():
    initial = request_json(ALARM_API, "/api/status")
    plant = request_json(PLANT_API, "/api/status")
    if not initial["read_only"] or not initial["health"]["connected"]:
        raise RuntimeError("AlarmaWatch must be connected to the ModbusSim source in read-only mode")
    if "load_setpoint" not in initial["values"]:
        raise RuntimeError("AlarmaWatch is missing the load setpoint read-back")

    routes = request_json(ALARM_API, "/openapi.json")["paths"]
    if any("setpoint" in path or "control" in path for path in routes):
        raise RuntimeError("AlarmaWatch exposes a control route; refusing to run the demo")

    original_setpoint = float(plant["load_setpoint"])
    baseline = float(initial["values"]["gas_load"])
    if any(alarm["id"] == "ALM-005" for alarm in initial["alarms"]):
        raise RuntimeError("Wait for the existing load-deviation alarm to clear before starting")
    if abs(baseline - original_setpoint) > 30:
        raise RuntimeError("Wait for plant load to settle near its current setpoint before starting")

    changed = False
    try:
        challenge_setpoint = 0 if baseline > 300 else 600
        request_json(PLANT_API, "/api/setpoints/load_setpoint", "POST", {"value": challenge_setpoint})
        changed = True
        print(f"1/4 Setpoint changed through ModbusSim operator API: {original_setpoint:g} -> {challenge_setpoint:g} MW")

        alarm = wait_for("ALM-005 to become active", active_load_alarm, timeout=90)
        print(f"2/4 AlarmaWatch raised {alarm['id']} at {alarm['last_value']} MW; acknowledging as {ACTOR}")
        acknowledgment = request_json(ALARM_API, f"/api/alarms/{alarm['id']}/ack", "POST", {"actor": ACTOR})
        if acknowledgment["event"] != "acknowledged":
            raise RuntimeError("AlarmaWatch did not record the acknowledgment")

        request_json(PLANT_API, "/api/setpoints/load_setpoint", "POST", {"value": original_setpoint})
        print(f"3/4 Original setpoint restored to {original_setpoint:g} MW; waiting for process response and alarm clear")
        wait_for("ALM-005 return-to-normal event", load_alarm_cleared, timeout=300)
        changed = False
        print("4/4 Alarm returned to normal; acknowledgment and clear events are in AlarmaWatch history")
        return {"result": "PASS", "alarm": "ALM-005", "acknowledgment": acknowledgment["event"],
                "return_to_normal": True, "original_setpoint_mw": original_setpoint,
                "alarmwatch_read_only": initial["read_only"]}
    finally:
        if changed:
            request_json(PLANT_API, "/api/setpoints/load_setpoint", "POST", {"value": original_setpoint})


if __name__ == "__main__":
    try:
        print(json.dumps(run_demo(), indent=2))
    except (RuntimeError, TimeoutError, KeyError, ValueError) as error:
        print(f"DEMO FAILED: {error}", file=sys.stderr)
        raise SystemExit(1) from error