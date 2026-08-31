"""WebSocket handshake metadata containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.3.1."""
from __future__ import annotations

from .http_v166666666633 import (
    HealthServer as HealthServerV166666666633,
    _request_http2_settings_are_safe,
)


def _request_websocket_metadata_is_safe(headers) -> bool:
    """Reject Sec-WebSocket-* request metadata on this non-upgrade surface."""
    if not _request_http2_settings_are_safe(headers):
        return False

    items = getattr(headers, "items", None)
    if not callable(items):
        return False

    try:
        fields = list(items())
    except Exception:
        return False

    for name, value in fields:
        if type(name) is not str or type(value) is not str:
            return False
        if name.lower().startswith("sec-websocket-"):
            return False
    return True


class HealthServer(HealthServerV166666666633):
    """Reject WebSocket handshake metadata before endpoint dispatch."""

    def __init__(
        self,
        runtime,
        host: str = "0.0.0.0",
        port: int = 8080,
        *,
        request_timeout_seconds: float = 5.0,
        max_concurrent_requests: int = 32,
        request_header_deadline_seconds: float = 5.0,
        max_request_header_bytes: int = 32768,
        max_request_line_bytes: int = 8192,
        max_request_header_fields: int = 32,
    ):
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            request_header_deadline_seconds=request_header_deadline_seconds,
            max_request_header_bytes=max_request_header_bytes,
            max_request_line_bytes=max_request_line_bytes,
            max_request_header_fields=max_request_header_fields,
        )
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def parse_request(self):
                parsed = super().parse_request()
                if not parsed:
                    return False
                if _request_websocket_metadata_is_safe(self.headers):
                    return True

                # This health surface never switches to WebSocket. Reject its
                # handshake metadata rather than leaving proxy/backend layers to
                # disagree about whether upgrade-related state is meaningful.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_websocket_metadata_is_safe"]
