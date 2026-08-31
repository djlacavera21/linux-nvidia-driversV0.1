"""Keep-Alive request-field containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.2."""
from __future__ import annotations

from .http_v166666666631 import (
    HealthServer as HealthServerV166666666631,
    _connection_field_cardinality_is_safe,
)


def _request_keep_alive_headers_are_safe(headers) -> bool:
    """Reject the legacy Keep-Alive request field on this minimal surface."""
    if not _connection_field_cardinality_is_safe(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    values = get_all("Keep-Alive", [])
    return type(values) is list and not values


class HealthServer(HealthServerV166666666631):
    """Reject Keep-Alive request fields before endpoint dispatch."""

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
                if _request_keep_alive_headers_are_safe(self.headers):
                    return True

                # The legacy Keep-Alive field carries connection-specific
                # parameters that this minimal health surface neither needs nor
                # interprets. Refuse it instead of relying on proxy behavior.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_keep_alive_headers_are_safe"]
