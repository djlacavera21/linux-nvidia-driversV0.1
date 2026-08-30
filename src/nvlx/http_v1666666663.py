"""Request Trailer declaration containment for nvlx 1.6.6.6.6.6.6.6.6.3."""
from __future__ import annotations

from .http_v1666666662 import HealthServer as HealthServerV1666666662


def _request_trailer_declaration_is_safe(headers) -> bool:
    """Accept only requests with no Trailer declaration fields."""
    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    # The live surface admits no transfer-encoded request body and therefore has
    # no valid request-trailer phase. Presence alone is ambiguous across proxies,
    # including an empty or duplicated Trailer declaration.
    return not get_all("Trailer", [])


class HealthServer(HealthServerV1666666662):
    """Reject request Trailer declarations before endpoint dispatch."""

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
                if _request_trailer_declaration_is_safe(self.headers):
                    return True

                # Transfer-Encoding is already forbidden on this bodyless live
                # surface. Refuse Trailer declarations so intermediaries cannot
                # disagree about a trailer phase that this server never accepts.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_trailer_declaration_is_safe"]
