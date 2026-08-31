"""Connection lifecycle conflict containment for nvlx 1.6.6.6.6.6.6.6.6.6.1."""
from __future__ import annotations

from .http_v1666666666 import (
    HealthServer as HealthServerV1666666666,
    _connection_token_list_is_safe,
)


def _connection_lifecycle_is_safe(headers) -> bool:
    """Reject contradictory close and keep-alive Connection directives."""
    if not _connection_token_list_is_safe(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    saw_close = False
    saw_keep_alive = False
    for value in get_all("Connection", []):
        if type(value) is not str:
            return False
        for part in value.split(","):
            token = part.strip(" \t").lower()
            if token == "close":
                saw_close = True
            elif token == "keep-alive":
                saw_keep_alive = True
            if saw_close and saw_keep_alive:
                return False
    return True


class HealthServer(HealthServerV1666666666):
    """Reject contradictory Connection lifecycle directives before dispatch."""

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
                if _connection_lifecycle_is_safe(self.headers):
                    return True

                # close and keep-alive express contradictory connection-lifecycle
                # intent. Refuse the combination so intermediaries and this origin
                # cannot choose different persistence semantics for one request.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_connection_lifecycle_is_safe"]
