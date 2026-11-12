"""Bounded in-memory and JSONL audit trail for local Modbus simulation traffic."""

import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from simulator.modbus_server import BASES, REGISTER_MAP

FUNCTIONS = {1: "read_coils", 3: "read_holding_registers", 4: "read_input_registers",
             5: "write_single_coil", 6: "write_single_register", 16: "write_multiple_registers"}
WRITE_FUNCTIONS = {5, 6, 16}


class ModbusAuditLog:
    def __init__(self, path="logs/modbus-audit.jsonl", capacity=10000):
        self.path = Path(path) if path else None
        self.events = deque(maxlen=capacity)
        self.lock = threading.Lock()
        self.write_errors = 0
        self.logger = logging.getLogger(f"modbus-audit.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.handler = RotatingFileHandler(self.path, maxBytes=5 * 1024 * 1024,
                                               backupCount=3, encoding="utf-8")
            self.handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(self.handler)
        self.points = {table: {point["address"] - BASES[table]: point
                               for point in REGISTER_MAP["points"] if point["table"] == table}
                       for table in BASES}

    def _append(self, event):
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.lock:
            self.events.append(event)
            if self.handler is not None:
                try:
                    self.logger.info("%s", json.dumps(event, allow_nan=False))
                except OSError:
                    self.write_errors += 1

    def trace_connect(self, connected):
        self._append({"category": "connection", "event": "opened" if connected else "closed",
                      "peer_identity": None})

    def trace_packet(self, is_send, packet):
        if not is_send and len(packet) >= 8:
            function_code = packet[7]
            if function_code not in FUNCTIONS:
                self._append({"category": "modbus", "event": "request", "function_code": function_code,
                              "function": "unknown", "device_id": packet[6],
                              "transaction_id": int.from_bytes(packet[:2], "big"), "is_write": False,
                              "unsupported_function": True, "payload_logged": False})
        return packet

    def trace_pdu(self, is_response, pdu):
        function_code = pdu.function_code
        base_function = function_code & 0x7F
        is_write = not is_response and base_function in WRITE_FUNCTIONS
        event = {"category": "modbus", "event": "response" if is_response else "request",
                 "function_code": base_function, "function": FUNCTIONS.get(base_function, "unknown"),
                 "device_id": pdu.dev_id, "transaction_id": pdu.transaction_id,
                 "is_write": is_write, "exception_code": getattr(pdu, "exception_code", 0) or None}
        if not is_response:
            table = "coil" if base_function in (1, 5) else "input" if base_function == 4 else "holding"
            count = max(1, getattr(pdu, "count", 0))
            event["count"] = count
            event["address"] = BASES[table] + pdu.address + 1
            if is_write:
                allowed = all((point := self.points[table].get(index)) is not None and point["access"] == "write"
                              for index in range(pdu.address + 1, pdu.address + count + 1))
                event["write_policy"] = "allowed_by_register_map" if allowed else "rejected_by_register_map"
                event["value_count"] = len(getattr(pdu, "registers", [])) + len(getattr(pdu, "bits", []))
        else:
            event["is_exception"] = pdu.isError()
        self._append(event)
        return pdu

    def tail(self, limit=100, kind="all"):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if kind not in ("all", "writes", "connections"):
            raise ValueError("kind must be all, writes, or connections")
        with self.lock:
            events = list(self.events)
            if kind == "writes":
                events = [event for event in events if event.get("is_write") or event.get("is_exception")]
            elif kind == "connections":
                events = [event for event in events if event["category"] == "connection"]
            return list(reversed(events[-limit:]))

    def health(self):
        with self.lock:
            return {"buffered_events": len(self.events), "write_errors": self.write_errors,
                    "payload_values_logged": False, "peer_addresses_logged": False,
                    "disk_retention": "5 MiB per file, 3 rotated backups" if self.path else "memory only"}

    def close(self):
        if self.handler is not None:
            self.logger.removeHandler(self.handler)
            self.handler.close()
            self.handler = None