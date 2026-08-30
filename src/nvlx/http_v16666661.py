"""Request-header field-count budget for nvlx 1.6.6.6.6.6.6.1."""
from __future__ import annotations

import http.client

from .http_v1666666 import HealthServer as HealthServerV1666666

_BASEHTTP_MAX_HEADER_FIELDS = 100


class _HeaderFieldCountReader:
    """Count physical header-field starts while preserving continuation lines."""

    def __init__(self, stream, limit: int):
        self._stream = stream
        self._limit = limit
        self._fields = 0

    @property
    def fields(self) -> int:
        return self._fields

    def readline(self, size: int = -1):
        line = self._stream.readline(size)
        if line in (b"", b"\r\n", b"\n"):
            return line

        # Obsolete folded continuation lines remain byte-accounted by the
        # inherited aggregate header budget but do not start another field.
        if not line.startswith((b" ", b"\t")):
            self._fields += 1
            if self._fields > self._limit:
                raise http.client.HTTPException(
                    "request headers exceed field-count budget"
                )
        return line

    def __getattr__(self, name):
        return getattr(self._stream, name)


def _validate_request_header_fields(value) -> int:
    """Return one strict positive header-field cap within BaseHTTP's ceiling."""
    if type(value) is not int:
        raise TypeError("max request header fields must be a positive integer")
    if value <= 0:
        raise ValueError("max request header fields must be greater than zero")
    if value > _BASEHTTP_MAX_HEADER_FIELDS:
        raise ValueError("max request header fields must not exceed 100")
    return value


class HealthServer(HealthServerV1666666):
    """Bound request-header field cardinality before endpoint evaluation."""

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
        field_budget = _validate_request_header_fields(max_request_header_fields)
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            request_header_deadline_seconds=request_header_deadline_seconds,
            max_request_header_bytes=max_request_header_bytes,
            max_request_line_bytes=max_request_line_bytes,
        )
        self.max_request_header_fields = field_budget
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def parse_request(self):
                original_rfile = self.rfile
                self.rfile = _HeaderFieldCountReader(original_rfile, field_budget)
                try:
                    return super().parse_request()
                finally:
                    self.rfile = original_rfile

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_HeaderFieldCountReader",
    "_validate_request_header_fields",
]
