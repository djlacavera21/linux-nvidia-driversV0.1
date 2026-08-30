"""Canonical origin-form request-target containment for nvlx 1.6.6.6.6.6.6.5."""
from __future__ import annotations

from .http_v16666664 import HealthServer as HealthServerV16666664


def _request_target_is_safe(requestline, parsed_target) -> bool:
    """Accept only a canonical visible-ASCII origin-form target.

    The raw request target must survive BaseHTTPRequestHandler parsing unchanged.
    This deliberately rejects alternate request-target forms and parser
    normalization such as a raw leading ``//`` becoming ``/``.
    """
    if type(requestline) is not str or type(parsed_target) is not str:
        return False

    parts = requestline.split()
    if len(parts) != 3:
        return False
    target = parts[1]
    if target != parsed_target:
        return False
    if not target.startswith("/") or target.startswith("//"):
        return False
    if "#" in target or "\\" in target:
        return False

    for char in target:
        codepoint = ord(char)
        if codepoint < 0x21 or codepoint > 0x7E:
            return False
    return True


class HealthServer(HealthServerV16666664):
    """Reject ambiguous request-target forms before endpoint dispatch."""

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
                if _request_target_is_safe(self.requestline, self.path):
                    return True

                # The live surface has no proxy/tunnel role. Admit only a raw
                # origin-form target that the parser did not rewrite; terminate
                # every alternate or ambiguous form before endpoint evaluation.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_target_is_safe"]
