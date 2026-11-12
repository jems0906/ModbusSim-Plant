"""Passive, simulator-local observations derived from Modbus audit records."""

from collections import deque
from datetime import datetime, timezone

SUPPORTED_FUNCTIONS = {1, 3, 4, 5, 6, 16}


class ModbusSecurityObserver:
    def __init__(self, capacity=500, dedupe_capacity=10000):
        self.events = deque(maxlen=capacity)
        self._seen = set()
        self._seen_order = deque()
        self._dedupe_capacity = dedupe_capacity
        self.audit_connected = False
        self.last_success_epoch = None
        self.last_error = None
        self.observation_count = 0
        self.rejected_write_count = 0
        self.unsupported_function_count = 0
        self.protocol_exception_count = 0

    def update_source(self, connected, error=None):
        self.audit_connected = bool(connected)
        self.last_error = None if connected else str(error or "Audit source unavailable")
        if connected:
            self.last_success_epoch = datetime.now(timezone.utc).timestamp()

    def _remember(self, event):
        key = (event.get("timestamp"), event.get("category"), event.get("event"),
               event.get("device_id"), event.get("transaction_id"), event.get("function_code"),
               event.get("address"), event.get("exception_code"))
        if key in self._seen:
            return False
        if len(self._seen_order) >= self._dedupe_capacity:
            self._seen.discard(self._seen_order.popleft())
        self._seen.add(key)
        self._seen_order.append(key)
        return True

    def ingest(self, audit_events):
        added = []
        for event in reversed(audit_events):
            if not self._remember(event) or event.get("category") != "modbus":
                continue
            if event.get("event") == "response" and event.get("is_exception"):
                self.protocol_exception_count += 1
                continue
            if event.get("event") != "request":
                continue
            function_code = event.get("function_code")
            if event.get("unsupported_function") or function_code not in SUPPORTED_FUNCTIONS:
                finding = self._finding("SEC-002", "HIGH", "unsupported_function",
                                        "Unsupported Modbus function code observed", event)
                self.unsupported_function_count += 1
            elif event.get("is_write") and event.get("write_policy") == "rejected_by_register_map":
                finding = self._finding("SEC-001", "MEDIUM", "rejected_write",
                                        "Write request rejected by register map", event)
                self.rejected_write_count += 1
            else:
                continue
            self.events.append(finding)
            self.observation_count += 1
            added.append(finding)
        return added

    @staticmethod
    def _finding(rule_id, severity, kind, summary, source_event):
        return {"timestamp": source_event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "rule_id": rule_id, "severity": severity, "kind": kind, "summary": summary,
                "function_code": source_event.get("function_code"),
                "address": source_event.get("address"), "device_id": source_event.get("device_id"),
                "transaction_id": source_event.get("transaction_id"),
                "payload_logged": False, "peer_identity": None}

    def recent(self, limit=100):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        return list(reversed(list(self.events)[-limit:]))

    def status(self):
        return {"available": self.audit_connected, "audit_connected": self.audit_connected,
                "last_success_epoch": self.last_success_epoch, "last_error": self.last_error,
                "observation_count": self.observation_count,
                "rejected_write_count": self.rejected_write_count,
                "unsupported_function_count": self.unsupported_function_count,
                "protocol_exception_count": self.protocol_exception_count,
                "payload_values_logged": False, "peer_addresses_logged": False}