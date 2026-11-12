"""Deterministic alarm lifecycle engine for the AlarmaWatch simulation."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path


RULES_PATH = Path(__file__).with_name("rules.json")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class AlarmEngine:
    def __init__(self, rules_path=RULES_PATH, event_sink=None):
        document = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        self.version = document["version"]
        self.rules = document["rules"]
        self.event_sink = event_sink
        self.states = {
            rule["id"]: {"phase": "normal", "active_since": None, "clear_since": None, "acknowledged": False, "last_value": None}
            for rule in self.rules
        }
        self.events = []

    def _condition(self, rule, values, active=True):
        tag = rule["tag"]
        operation = rule["condition"] if active else rule.get("clear_condition")
        if not active and operation is None and rule["condition"] in ("is_true", "is_false"):
            operation = "is_false" if rule["condition"] == "is_true" else "is_true"
        if operation is None:
            return False
        if operation == "is_false":
            return values.get(tag) is False or values.get(tag) == 0
        if operation == "is_true":
            return values.get(tag) is True or values.get(tag) == 1
        value = values.get(tag)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False
        reference_key = "reference" if active else "clear_reference"
        threshold_key = "limit" if active else "clear_limit"
        if operation.startswith("deviation_"):
            reference = values.get(rule.get(reference_key, rule.get("reference")))
            if not isinstance(reference, (int, float)) or not math.isfinite(reference):
                return False
            value = abs(value - reference)
            operation = operation.removeprefix("deviation_")
        threshold = rule.get(threshold_key)
        if threshold is None:
            return False
        return {"lt": lambda: value < threshold, "lte": lambda: value <= threshold,
                "gt": lambda: value > threshold, "gte": lambda: value >= threshold,
                "eq": lambda: value == threshold}.get(operation, lambda: False)()

    def _emit(self, rule, event_type, state, value, timestamp, actor=None):
        event = {"timestamp": timestamp, "alarm_id": rule["id"], "event": event_type,
                 "priority": rule["priority"], "tag": rule["tag"], "label": rule["label"],
                 "area": rule["area"], "value": value, "unit": rule["unit"], "actor": actor}
        self.events.append(event)
        if self.event_sink:
            self.event_sink(event)
        return event

    def evaluate(self, values, now):
        """Apply one timestamped sample. `now` is monotonic seconds for dwell timing."""
        emitted = []
        timestamp = utc_now()
        for rule in self.rules:
            state = self.states[rule["id"]]
            value = values.get(rule["tag"])
            state["last_value"] = value
            if state["phase"] in ("normal", "pending"):
                if self._condition(rule, values):
                    if state["phase"] == "normal":
                        state["phase"] = "pending"
                        state["active_since"] = now
                    if now - state["active_since"] >= rule["delay_seconds"]:
                        state["phase"] = "active"
                        state["active_since"] = timestamp
                        state["acknowledged"] = False
                        emitted.append(self._emit(rule, "raised", state, value, timestamp))
                else:
                    state["phase"] = "normal"
                    state["active_since"] = None
            elif state["phase"] == "active":
                if self._condition(rule, values, active=False):
                    if state["clear_since"] is None:
                        state["clear_since"] = now
                    if now - state["clear_since"] >= rule.get("clear_delay_seconds", 0):
                        state["phase"] = "normal"
                        state["clear_since"] = None
                        emitted.append(self._emit(rule, "returned_to_normal", state, value, timestamp))
                else:
                    state["clear_since"] = None
        return emitted

    def acknowledge(self, alarm_id, actor):
        rule = next((item for item in self.rules if item["id"] == alarm_id), None)
        if rule is None:
            raise KeyError(alarm_id)
        state = self.states[alarm_id]
        if state["phase"] != "active":
            raise ValueError("Only active alarms can be acknowledged")
        if state["acknowledged"]:
            raise ValueError("Alarm is already acknowledged")
        state["acknowledged"] = True
        return self._emit(rule, "acknowledged", state, state["last_value"], utc_now(), actor)

    def active_alarms(self):
        by_id = {rule["id"]: rule for rule in self.rules}
        result = []
        for alarm_id, state in self.states.items():
            if state["phase"] in ("active", "pending"):
                rule = by_id[alarm_id]
                result.append({**rule, **state})
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(result, key=lambda item: (order.get(item["priority"], 4), item["id"]))
