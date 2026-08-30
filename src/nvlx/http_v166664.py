"""Cross-version non-reflective HTTP logging for nvlx 1.6.6.6.6.4."""
from __future__ import annotations

import sys

from .http_v166663 import HealthServer as HealthServerV166663

_LOG_PREFIX = "nvlx http"


class HealthServer(HealthServerV166663):
    """Keep live HTTP stderr logs bounded and free of request-controlled text."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            @staticmethod
            def _safe_status(code) -> str:
                try:
                    value = int(code)
                except (TypeError, ValueError, OverflowError):
                    return "-"
                if 100 <= value <= 599:
                    return str(value)
                return "-"

            @staticmethod
            def _write_safe_log(line: str) -> None:
                sys.stderr.write(line + "\n")

            def log_request(self, code="-", size="-") -> None:
                self._write_safe_log(
                    f"{_LOG_PREFIX} status={self._safe_status(code)}"
                )

            def log_error(self, format, *args) -> None:
                self._write_safe_log(f"{_LOG_PREFIX} error")

            def log_message(self, format, *args) -> None:
                self._write_safe_log(f"{_LOG_PREFIX} event")

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
