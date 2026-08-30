"""Bodyless live GET/HEAD request contract for nvlx 1.6.6.6.6."""
from __future__ import annotations

from .http_v16664 import _LIVE_PATHS
from .http_v16665 import HealthServer as HealthServerV16665

_REQUEST_REJECTION_BODY = "request rejected\n"


class HealthServer(HealthServerV16665):
    """Reject body-framed live GET/HEAD requests before runtime evaluation."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def _live_request_body_is_valid(self) -> bool:
                if self.path not in _LIVE_PATHS:
                    return True

                transfer_encoding = self.headers.get_all("Transfer-Encoding") or []
                if transfer_encoding:
                    return False

                content_lengths = self.headers.get_all("Content-Length") or []
                if not content_lengths:
                    return True
                if len(content_lengths) != 1:
                    return False

                raw_length = content_lengths[0].strip()
                if not raw_length or not raw_length.isascii() or not raw_length.isdigit():
                    return False

                try:
                    return int(raw_length, 10) == 0
                except (TypeError, ValueError, OverflowError):
                    return False

            def _send_bad_live_request_and_close(self) -> None:
                payload = _REQUEST_REJECTION_BODY.encode("utf-8")
                self.close_connection = True
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

            def _guard_live_request_body(self) -> bool:
                if self._live_request_body_is_valid():
                    return True
                self._send_bad_live_request_and_close()
                return False

            def do_GET(self):
                if self._guard_live_request_body():
                    super().do_GET()

            def do_HEAD(self):
                if self._guard_live_request_body():
                    super().do_HEAD()

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
