"""Proxy-Connection containment for nvlx 1.6.6.6.6.6.6.6.6.5."""
from __future__ import annotations

from .http_v1666666664 import HealthServer as HealthServerV1666666664


def _request_proxy_connection_is_safe(headers) -> bool:
    """Reject Proxy-Connection fields and matching Connection tokens."""
    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    # Proxy-Connection is non-standard and interpreted inconsistently by legacy
    # proxies. This direct health surface has no semantics for it, so presence
    # alone is ambiguous, including empty or duplicate fields.
    if get_all("Proxy-Connection", []):
        return False

    for value in get_all("Connection", []):
        if type(value) is not str:
            return False
        tokens = (token.strip(" \t").lower() for token in value.split(","))
        if any(token == "proxy-connection" for token in tokens):
            return False
    return True


class HealthServer(HealthServerV1666666664):
    """Reject Proxy-Connection signaling before endpoint dispatch."""

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
                if _request_proxy_connection_is_safe(self.headers):
                    return True

                # Refuse legacy proxy-specific connection signaling before
                # resource or runtime evaluation so intermediaries and origin
                # cannot disagree about persistence or hop-by-hop semantics.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_proxy_connection_is_safe"]
