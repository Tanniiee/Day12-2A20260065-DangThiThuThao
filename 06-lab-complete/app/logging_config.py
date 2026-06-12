"""
Structured JSON logging — production best practice.

Log dạng JSON để cloud platform (Railway/Render/Cloud Run) parse được,
thay vì print() như bản develop.
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Gắn thêm context (request_id, user_id, latency...) nếu có
        for key in ("user_id", "request_id", "path", "status_code", "latency_ms", "cost_usd"):
            if hasattr(record, key):
                log[key] = getattr(record, key)
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Giảm noise từ uvicorn access log (đã có middleware log riêng)
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger("agent")
