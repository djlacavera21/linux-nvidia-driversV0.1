"""Canonical Connection token-list containment for nvlx 1.6.6.6.6.6.6.6.6.6."""
from __future__ import annotations

from .http_v1666666665 import HealthServer as HealthServerV1666666665


_TOKEN_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


def _connection_token_list_is_safe(headers) -> bool:
    """Accept only syntactically canonical HTTP token lists in Connection fields."""
    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    for value in get_all("Connection", []):
        if type(value) is not str or not value.isascii():
            return False
        parts = value.split(",")
        if not parts:
            return False
        for part in parts:
            token = part.strip(" \t")
            if not token:
                return False
            if any(char not in _TOKEN_CHARS for char in token):
                return False
    return True


class HealthServer(HealthServerV1666666665):
    """Reject malformed Connection token lists before endpoint dispatch."""

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
                if _connection_token_list_is_safe(self.headers):
                    return True

                # Connection is defined as a comma-separated list of HTTP tokens.
                # Refuse malformed list syntax so proxies and the origin cannot
                # disagree about empty, quoted, parameterized, or invalid options.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_connection_token_list_is_safe"]
