"""Explicit live HTTP method contract for nvlx 1.6.6.6.3."""
from __future__ import annotations

from .http_v16662 import HealthServer as HealthServerV16662

_ALLOWED_METHODS = "GET, HEAD"
_METHOD_REJECTION_BODY = "request rejected\n"


class HealthServer(HealthServerV16662):
    """Advertise the live GET/HEAD method contract and contain unsupported methods."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def _send_method_not_allowed(self) -> None:
                payload = _METHOD_REJECTION_BODY.encode("utf-8")
                self.send_response(405)
                self.send_header("Allow", _ALLOWED_METHODS)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

            def send_error(self, code, message=None, explain=None):
                if code == 501 and self.command not in ("GET", "HEAD"):
                    self._send_method_not_allowed()
                    return
                super().send_error(code, message, explain)

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
