"""Bodyless request-framing containment for nvlx 1.6.6.6.6.6.6.2."""
from __future__ import annotations

from .http_v16666661 import HealthServer as HealthServerV16666661


def _request_body_framing_is_safe(headers) -> bool:
    """Return True only for the bodyless framing accepted by live endpoints."""
    transfer_encodings = headers.get_all("Transfer-Encoding", [])
    if transfer_encodings:
        return False

    content_lengths = headers.get_all("Content-Length", [])
    if not content_lengths:
        return True
    if len(content_lengths) != 1:
        return False

    value = content_lengths[0]
    if not isinstance(value, str):
        return False
    if "\r" in value or "\n" in value:
        return False
    return value.strip(" \t") == "0"


class HealthServer(HealthServerV16666661):
    """Reject request-body framing before endpoint or runtime evaluation."""

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
                if _request_body_framing_is_safe(self.headers):
                    return True

                # The live surface is intentionally bodyless. Reject ambiguous
                # framing before dispatch and terminate the connection so bytes
                # following the header block cannot be reinterpreted as another
                # pipelined request.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_body_framing_is_safe"]
