"""Best-effort HTTP log-sink containment for nvlx 1.6.6.6.6.5."""
from __future__ import annotations

import sys

from .http_v166664 import HealthServer as HealthServerV166664


class HealthServer(HealthServerV166664):
    """Prevent stderr/log-sink failures from changing live HTTP behavior."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            @staticmethod
            def _write_safe_log(line: str) -> None:
                try:
                    sys.stderr.write(line + "\n")
                except Exception:
                    # Logging is diagnostic only. A closed, replaced, or failing stderr
                    # sink must never change endpoint status, framing, or containment.
                    return

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
