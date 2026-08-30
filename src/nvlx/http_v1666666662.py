"""Protocol-upgrade containment for nvlx 1.6.6.6.6.6.6.6.6.2."""
from __future__ import annotations

from .http_v1666666661 import HealthServer as HealthServerV1666666661


def _request_upgrade_headers_are_safe(headers) -> bool:
    """Reject Upgrade fields and Connection tokens that request an upgrade."""
    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    # This minimal health surface never switches protocols. Presence alone is
    # enough to reject an Upgrade field, including empty or duplicate fields.
    if get_all("Upgrade", []):
        return False

    for value in get_all("Connection", []):
        if type(value) is not str:
            return False
        tokens = (token.strip(" \t").lower() for token in value.split(","))
        if any(token == "upgrade" for token in tokens):
            return False
    return True


class HealthServer(HealthServerV1666666661):
    """Reject protocol-upgrade negotiation before endpoint dispatch."""

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
                if _request_upgrade_headers_are_safe(self.headers):
                    return True

                # The live health server has no WebSocket, h2c, or extension
                # negotiation role. Reject both sides of HTTP/1.x upgrade
                # signaling before resource or runtime evaluation.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_upgrade_headers_are_safe"]
