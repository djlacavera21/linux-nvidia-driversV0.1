"""HTTP2-Settings request containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.3."""
from __future__ import annotations

from .http_v166666666632 import (
    HealthServer as HealthServerV166666666632,
    _request_keep_alive_headers_are_safe,
)


def _request_http2_settings_are_safe(headers) -> bool:
    """Reject HTTP2-Settings fields and exact Connection nominations."""
    if not _request_keep_alive_headers_are_safe(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    settings_values = get_all("HTTP2-Settings", [])
    if type(settings_values) is not list or settings_values:
        return False

    connection_values = get_all("Connection", [])
    if type(connection_values) is not list:
        return False
    for value in connection_values:
        if type(value) is not str:
            return False
        for part in value.split(","):
            if part.strip(" \t").lower() == "http2-settings":
                return False
    return True


class HealthServer(HealthServerV166666666632):
    """Reject h2c HTTP2-Settings signaling before endpoint dispatch."""

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
                if _request_http2_settings_are_safe(self.headers):
                    return True

                # HTTP2-Settings is meaningful only to the cleartext HTTP/2
                # upgrade path. This health surface never upgrades protocols,
                # so refuse the field and its Connection nomination outright.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_http2_settings_are_safe"]
