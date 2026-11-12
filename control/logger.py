import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler


class DecisionLogger:
    def __init__(self, path="logs/control.jsonl", max_bytes=5 * 1024 * 1024, backup_count=3):
        self.path = Path(path) if path else None
        self.logger = logging.getLogger(f"control-decisions.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handler = None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.handler = RotatingFileHandler(self.path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
            self.handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(self.handler)

    def write(self, entry):
        if self.path is None:
            return
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **entry}
        self.logger.info("%s", json.dumps(entry, allow_nan=False))

    def close(self):
        if self.handler is not None:
            self.logger.removeHandler(self.handler)
            self.handler.close()
            self.handler = None