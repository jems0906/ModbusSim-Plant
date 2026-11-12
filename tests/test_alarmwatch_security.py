import unittest

from alarmwatch.security import ModbusSecurityObserver


class ModbusSecurityObserverTests(unittest.TestCase):
    def test_findings_metrics_source_health_and_overlap_deduplication(self):
        observer = ModbusSecurityObserver()
        events = [
            {"timestamp": "2026-11-12T00:00:00+00:00", "category": "modbus", "event": "request",
             "function_code": 6, "is_write": True, "write_policy": "rejected_by_register_map",
             "address": 40001, "device_id": 1, "transaction_id": 1},
            {"timestamp": "2026-11-12T00:00:01+00:00", "category": "modbus", "event": "request",
             "function_code": 43, "function": "unknown", "is_write": False,
             "address": 40001, "device_id": 1, "transaction_id": 2},
            {"timestamp": "2026-11-12T00:00:02+00:00", "category": "modbus", "event": "request",
             "function_code": 6, "is_write": True, "write_policy": "allowed_by_register_map",
             "address": 40005, "device_id": 1, "transaction_id": 3},
            {"timestamp": "2026-11-12T00:00:03+00:00", "category": "modbus", "event": "response",
             "function_code": 6, "is_exception": True, "exception_code": 2,
             "device_id": 1, "transaction_id": 4},
        ]
        newest_first = list(reversed(events))
        findings = observer.ingest(newest_first)
        self.assertEqual([finding["rule_id"] for finding in findings], ["SEC-001", "SEC-002"])
        self.assertEqual(observer.ingest(newest_first), [])
        status = observer.status()
        self.assertEqual(status["rejected_write_count"], 1)
        self.assertEqual(status["unsupported_function_count"], 1)
        self.assertEqual(status["protocol_exception_count"], 1)
        self.assertEqual(status["observation_count"], 2)
        self.assertTrue(all(not finding["payload_logged"] and finding["peer_identity"] is None for finding in findings))
        observer.update_source(True)
        self.assertTrue(observer.status()["available"])
        observer.update_source(False, "audit endpoint timed out")
        self.assertFalse(observer.status()["available"])
        self.assertEqual(observer.status()["last_error"], "audit endpoint timed out")

    def test_recent_limit_is_validated(self):
        observer = ModbusSecurityObserver()
        with self.assertRaises(ValueError):
            observer.recent(0)


if __name__ == "__main__":
    unittest.main()