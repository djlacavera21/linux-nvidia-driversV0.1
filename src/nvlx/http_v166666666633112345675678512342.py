"""Referer Connection-nomination containment for nvlx 1.6.6.6.6.6.6.6.6.6.3.3.1.2.3.4.5.6.7.5.6.7.8.5.1.2.3.4.2."""
from __future__ import annotations

from .http_v166666666633112345675678512341 import (
    HealthServer as HealthServerV166666666633112345675678512341,
    _request_x_envoy_local_overloaded_nomination_is_safe,
)


def _request_referer_nomination_is_safe(headers) -> bool:
    """Reject exact Connection nominations of Referer request metadata."""
    if not _request_x_envoy_local_overloaded_nomination_is_safe(headers):
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
            if part.strip(" \t").lower() == "referer":
                return False
    return True


class HealthServer(HealthServerV166666666633112345675678512341):
    """Reject Connection attempts to demote Referer to hop-by-hop."""

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
                if _request_referer_nomination_is_safe(self.headers):
                    return True

                # Envoy sanitizes Referer during request decoding. Refuse an exact
                # Connection nomination so an intermediary cannot reinterpret or
                # strip that request metadata as hop-by-hop before the configured
                # request-header policy is applied. Referer values stay opaque here.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_referer_nomination_is_safe"]
