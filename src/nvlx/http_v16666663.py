"""Strict request-version admission for nvlx 1.6.6.6.6.6.6.3."""
from __future__ import annotations

from email.message import Message

from .http_v16666662 import HealthServer as HealthServerV16666662

_SUPPORTED_REQUEST_VERSIONS = frozenset({"HTTP/1.0", "HTTP/1.1"})


def _request_version_is_supported(value) -> bool:
    """Accept only the two HTTP request versions supported by the live surface."""
    return type(value) is str and value in _SUPPORTED_REQUEST_VERSIONS


class HealthServer(HealthServerV16666662):
    """Reject legacy or non-canonical HTTP versions before endpoint dispatch."""

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
                # BaseHTTPRequestHandler's HTTP/0.9 compatibility path can return
                # successfully without creating self.headers. Seed an empty message
                # so the inherited body-framing gate can inspect that path safely.
                # HTTP/1.x parsing replaces this object with the parsed header set.
                self.headers = Message()
                parsed = super().parse_request()
                if not parsed:
                    return False
                if _request_version_is_supported(self.request_version):
                    return True

                # Keep unsupported-version handling inside the existing canonical
                # parser-error contract. That path normalizes response framing to
                # HTTP/1.0, emits a fixed non-reflective 505, and closes the socket.
                self.close_connection = True
                self.send_error(505)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_SUPPORTED_REQUEST_VERSIONS",
    "_request_version_is_supported",
]
