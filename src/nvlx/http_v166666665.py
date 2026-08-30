"""Canonical request-line separator containment for nvlx 1.6.6.6.6.6.6.6.5."""
from __future__ import annotations

from .http_v166666664 import HealthServer as HealthServerV166666664


def _request_line_spacing_is_safe(requestline, command, target, request_version) -> bool:
    """Require exactly one ASCII SP between the three parsed request-line tokens."""
    values = (requestline, command, target, request_version)
    if any(type(value) is not str for value in values):
        return False
    if not command or not target or not request_version:
        return False

    # BaseHTTPRequestHandler tokenizes with generic whitespace. Reconstruct the
    # only request-line spelling this origin server admits so HTAB, repeated SP,
    # leading/trailing whitespace, and parser-normalized separators fail closed.
    return requestline == f"{command} {target} {request_version}"


class HealthServer(HealthServerV166666664):
    """Reject non-canonical request-line separators before endpoint dispatch."""

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
                if _request_line_spacing_is_safe(
                    self.requestline,
                    self.command,
                    self.path,
                    self.request_version,
                ):
                    return True

                # All inherited framing, version, Host, target, header and Expect
                # gates have already passed. Refuse generic-whitespace spellings
                # that BaseHTTPRequestHandler would otherwise normalize.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_line_spacing_is_safe"]
