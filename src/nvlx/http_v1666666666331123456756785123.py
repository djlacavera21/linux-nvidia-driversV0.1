"""X-Datadog-Sampling-Priority Connection-nomination containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.8.5.1.2.3."""
from __future__ import annotations

from .http_v1666666666331123456756785122 import (
    HealthServer as HealthServerV1666666666331123456756785122,
    _request_x_datadog_parent_id_nomination_is_safe,
)


def _request_x_datadog_sampling_priority_nomination_is_safe(headers) -> bool:
    """Reject exact Connection nominations of X-Datadog-Sampling-Priority metadata."""
    if not _request_x_datadog_parent_id_nomination_is_safe(headers):
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
            if part.strip(" \t").lower() == "x-datadog-sampling-priority":
                return False
    return True


class HealthServer(HealthServerV1666666666331123456756785122):
    """Reject Connection attempts to demote X-Datadog-Sampling-Priority to hop-by-hop."""

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
                if _request_x_datadog_sampling_priority_nomination_is_safe(self.headers):
                    return True

                # X-Datadog-Sampling-Priority carries the Datadog trace sampling
                # decision. Refuse an exact Connection nomination so an intermediary
                # cannot reinterpret or strip it as hop-by-hop before tracing policy
                # is applied.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_x_datadog_sampling_priority_nomination_is_safe"]
