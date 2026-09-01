"""Grpc-Previous-Rpc-Attempts Connection-nomination containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.8.5.1.2.3.4.5.6."""
from __future__ import annotations

from .http_v16666666663311234567567851234455 import (
    HealthServer as HealthServerV16666666663311234567567851234455,
    _request_grpc_timeout_nomination_is_safe,
)


def _request_grpc_previous_rpc_attempts_nomination_is_safe(headers) -> bool:
    """Reject exact Connection nominations of Grpc-Previous-Rpc-Attempts."""
    if not _request_grpc_timeout_nomination_is_safe(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    connection_values = get_all("Connection", [])
    if type(connection_values) is not list:
        return False
    for value in connection_values:
        if type(value) is not str:
            return False
        for part in value.split(","):
            if part.strip(" \t").lower() == "grpc-previous-rpc-attempts":
                return False
    return True


class HealthServer(HealthServerV16666666663311234567567851234455):
    """Reject Connection attempts to demote Grpc-Previous-Rpc-Attempts to hop-by-hop."""

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
                if _request_grpc_previous_rpc_attempts_nomination_is_safe(self.headers):
                    return True

                # gRPC retry clients can place Grpc-Previous-Rpc-Attempts in
                # outgoing initial metadata to expose the number of preceding
                # attempts. Refuse an exact Connection nomination so that retry
                # provenance cannot be demoted to hop-by-hop before upstream
                # application or policy observes it. Values remain opaque here.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_grpc_previous_rpc_attempts_nomination_is_safe"]
