"""Duplicate Connection-option containment for nvlx 1.6.6.6.6.6.6.6.6.6.3."""
from __future__ import annotations

from .http_v16666666662 import (
    HealthServer as HealthServerV16666666662,
    _connection_critical_nomination_is_safe,
)


def _connection_options_are_unique(headers) -> bool:
    """Reject duplicate Connection options across all canonical fields."""
    if not _connection_critical_nomination_is_safe(headers):
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    seen: set[str] = set()
    for value in get_all("Connection", []):
        if type(value) is not str:
            return False
        for part in value.split(","):
            token = part.strip(" \t").lower()
            if token in seen:
                return False
            seen.add(token)
    return True


class HealthServer(HealthServerV16666666662):
    """Reject duplicate Connection options before endpoint dispatch."""

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
                if _connection_options_are_unique(self.headers):
                    return True

                # Duplicate options can be collapsed, reordered, or interpreted
                # inconsistently by intermediaries. Require one occurrence of
                # each canonical Connection option across the whole field set.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_connection_options_are_unique"]
