"""Critical Connection-option nomination containment for nvlx 1.6.6.6.6.6.6.6.6.6.2."""
from __future__ import annotations

from .http_v16666666661 import (
    HealthServer as HealthServerV16666666661,
    _connection_lifecycle_is_safe,
)


_CRITICAL_CONNECTION_OPTIONS = frozenset(
    {
        "connection",
        "host",
        "content-length",
        "transfer-encoding",
        "trailer",
        "expect",
    }
)


def _connection_critical_nomination_is_safe(headers) -> bool:
    """Reject Connection options that nominate critical routing/framing fields."""
    if not _connection_lifecycle_is_safe(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    for value in get_all("Connection", []):
        if type(value) is not str:
            return False
        for part in value.split(","):
            token = part.strip(" \t").lower()
            if token in _CRITICAL_CONNECTION_OPTIONS:
                return False
    return True


class HealthServer(HealthServerV16666666661):
    """Reject critical header nomination through Connection before dispatch."""

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
                if _connection_critical_nomination_is_safe(self.headers):
                    return True

                # Connection options can cause intermediaries to strip nominated
                # fields before forwarding. Critical routing/framing fields must
                # therefore never be reclassified as hop-by-hop on this surface.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_CRITICAL_CONNECTION_OPTIONS",
    "_connection_critical_nomination_is_safe",
]
