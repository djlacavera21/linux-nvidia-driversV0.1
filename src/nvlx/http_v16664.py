"""Resource-aware live HTTP method contract for nvlx 1.6.6.6.4."""
from __future__ import annotations

from .http_v16663 import HealthServer as HealthServerV16663

_LIVE_PATHS = frozenset(("/livez", "/readyz", "/metrics"))


class HealthServer(HealthServerV16663):
    """Advertise GET/HEAD only for resources that actually exist."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def send_error(self, code, message=None, explain=None):
                if code == 501 and self.command not in ("GET", "HEAD"):
                    if self.path in _LIVE_PATHS:
                        self._send_method_not_allowed()
                    else:
                        self.send_response(404)
                        self.end_headers()
                    return
                super().send_error(code, message, explain)

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
