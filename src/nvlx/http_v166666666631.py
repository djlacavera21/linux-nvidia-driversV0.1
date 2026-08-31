"""Singleton Connection-field containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.1."""
from __future__ import annotations

from .http_v16666666663 import (
    HealthServer as HealthServerV16666666663,
    _connection_options_are_unique,
)


def _connection_field_cardinality_is_safe(headers) -> bool:
    """Require at most one canonical Connection header field."""
    if not _connection_options_are_unique(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    values = get_all("Connection", [])
    return type(values) is list and len(values) <= 1


class HealthServer(HealthServerV16666666663):
    """Reject repeated Connection header fields before endpoint dispatch."""

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
                if _connection_field_cardinality_is_safe(self.headers):
                    return True

                # RFC list fields can often be combined, but intermediaries differ
                # in whether and when they merge repeated Connection fields. Keep
                # this health surface unambiguous by admitting zero or one field.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_connection_field_cardinality_is_safe"]
