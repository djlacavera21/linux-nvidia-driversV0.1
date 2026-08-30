"""Canonical parser-error status-line containment for nvlx 1.6.6.6.6.3."""
from __future__ import annotations

from .http_v16666 import _REQUEST_REJECTION_BODY
from .http_v166662 import HealthServer as HealthServerV166662

_PARSER_REASON = "Request Rejected"


class HealthServer(HealthServerV166662):
    """Keep parser status codes while removing framework-defined reason phrases."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def _send_parser_error_and_close(self, code: int) -> None:
                payload = _REQUEST_REJECTION_BODY.encode("utf-8")
                self.close_connection = True

                # Parser failures can begin before a trustworthy request version exists.
                # Pin the response to the server's HTTP/1.0 baseline and use one stable
                # reason phrase so Python-version-specific BaseHTTP phrases never leak.
                self.request_version = "HTTP/1.0"
                self.send_response(code, _PARSER_REASON)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
