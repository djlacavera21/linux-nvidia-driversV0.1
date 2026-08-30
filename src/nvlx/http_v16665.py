"""Terminal rejected-method transport for nvlx 1.6.6.6.5."""
from __future__ import annotations

from .http_v16663 import _ALLOWED_METHODS, _METHOD_REJECTION_BODY
from .http_v16664 import _LIVE_PATHS, HealthServer as HealthServerV16664


class HealthServer(HealthServerV16664):
    """Close connections after unsupported methods so unread bodies cannot desync."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def _send_method_not_allowed_and_close(self) -> None:
                payload = _METHOD_REJECTION_BODY.encode("utf-8")
                self.close_connection = True
                self.send_response(405)
                self.send_header("Allow", _ALLOWED_METHODS)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

            def _send_unknown_method_not_found_and_close(self) -> None:
                self.close_connection = True
                self.send_response(404)
                self.send_header("Connection", "close")
                self.end_headers()

            def send_error(self, code, message=None, explain=None):
                if code == 501 and self.command not in ("GET", "HEAD"):
                    if self.path in _LIVE_PATHS:
                        self._send_method_not_allowed_and_close()
                    else:
                        self._send_unknown_method_not_found_and_close()
                    return
                super().send_error(code, message, explain)

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
