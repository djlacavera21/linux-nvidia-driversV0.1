"""Canonical zero-length live request framing for nvlx 1.6.6.6.6.1."""
from __future__ import annotations

from .http_v16664 import _LIVE_PATHS
from .http_v16666 import HealthServer as HealthServerV16666


class HealthServer(HealthServerV16666):
    """Accept only the canonical explicit Content-Length value ``0`` on live GET/HEAD."""

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
                return len(content_lengths) == 1 and content_lengths[0] == "0"

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
