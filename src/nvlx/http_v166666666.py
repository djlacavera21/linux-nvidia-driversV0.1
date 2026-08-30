"""Malformed percent-escape containment for nvlx 1.6.6.6.6.6.6.6.6."""
from __future__ import annotations

from .http_v166666665 import HealthServer as HealthServerV166666665

_HEX_DIGITS = frozenset("0123456789ABCDEFabcdef")


def _request_target_percent_escapes_are_safe(target) -> bool:
    """Require every percent escape in the encoded request target to be %HH."""
    if type(target) is not str:
        return False

    index = 0
    while True:
        index = target.find("%", index)
        if index < 0:
            return True
        if index + 2 >= len(target):
            return False
        if target[index + 1] not in _HEX_DIGITS or target[index + 2] not in _HEX_DIGITS:
            return False
        index += 3


class HealthServer(HealthServerV166666665):
    """Reject malformed percent escapes before endpoint dispatch."""

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
                if _request_target_percent_escapes_are_safe(self.path):
                    return True

                # All inherited framing and request-line/target gates have passed.
                # Keep percent encoding opaque, but refuse incomplete or non-hex
                # escapes that different URI parsers could interpret differently.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_HEX_DIGITS", "_request_target_percent_escapes_are_safe"]
