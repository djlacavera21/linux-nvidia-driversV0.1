"""Terminal framework-error containment for nvlx 1.6.6.6.6.2."""
from __future__ import annotations

from .http_v16666 import _REQUEST_REJECTION_BODY
from .http_v166661 import HealthServer as HealthServerV166661

_PARSER_ERROR_CODES = frozenset({400, 414, 431, 505})


class HealthServer(HealthServerV166661):
    """Make parser-generated HTTP errors fixed-body, non-reflective and terminal."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def _send_parser_error_and_close(self, code: int) -> None:
                payload = _REQUEST_REJECTION_BODY.encode("utf-8")
                self.close_connection = True

                # Python 3.11/3.12 can leave parser failures at HTTP/0.9,
                # which suppresses the status line and headers in send_response().
                # Normalize response framing only; the rejected request is terminal.
                self.request_version = "HTTP/1.0"
                self.send_response(code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

            def send_error(self, code, message=None, explain=None):
                if code in _PARSER_ERROR_CODES:
                    self._send_parser_error_and_close(code)
                    return
                super().send_error(code, message, explain)

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
