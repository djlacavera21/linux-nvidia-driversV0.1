"""HTTP/1.1 Host singleton containment for nvlx 1.6.6.6.6.6.6.4."""
from __future__ import annotations

from .http_v16666663 import HealthServer as HealthServerV16666663


def _request_host_is_safe(request_version, headers) -> bool:
    """Require one non-empty Host field for HTTP/1.1; keep HTTP/1.0 compatible."""
    if request_version == "HTTP/1.0":
        return True
    if request_version != "HTTP/1.1":
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False

    hosts = get_all("Host", [])
    if len(hosts) != 1:
        return False

    value = hosts[0]
    if type(value) is not str:
        return False
    if "\r" in value or "\n" in value:
        return False
    value = value.strip(" \t")
    if not value or "," in value:
        return False
    return True


class HealthServer(HealthServerV16666663):
    """Reject ambiguous HTTP/1.1 Host framing before endpoint dispatch."""

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
                if _request_host_is_safe(self.request_version, self.headers):
                    return True

                # HTTP/1.1 authority selection must not depend on absent,
                # duplicate, folded, empty, or list-like Host fields. Reuse the
                # canonical terminal parser-error surface and close the socket.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_request_host_is_safe"]
