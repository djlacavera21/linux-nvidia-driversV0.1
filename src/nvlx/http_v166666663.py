"""Request Expect-header containment for nvlx 1.6.6.6.6.6.6.6.3."""
from __future__ import annotations

from .http_v166666662 import HealthServer as HealthServerV166666662


def _request_expectation_is_safe(headers) -> bool:
    """Accept only requests with no Expect header fields at all."""
    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False
    return not get_all("Expect", [])


class HealthServer(HealthServerV166666662):
    """Reject request expectations on the deliberately bodyless live surface."""

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
                if _request_expectation_is_safe(self.headers):
                    return True

                # The live endpoints accept no request body and have no reason to
                # negotiate 100-continue or any extension expectation. Reject the
                # expectation itself after all earlier syntax/framing gates pass.
                self.close_connection = True
                self.send_error(417)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_expectation_is_safe"]
