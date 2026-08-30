"""Aggregate request-header byte budget for nvlx 1.6.6.6.6.6.5."""
from __future__ import annotations

import http.client

from .http_v1666663 import _validate_max_concurrent_requests
from .http_v1666664 import HealthServer as HealthServerV1666664


class _HeaderBudgetReader:
    """Expose readline while enforcing one aggregate byte budget."""

    def __init__(self, stream, limit: int):
        self._stream = stream
        self._remaining = limit

    @property
    def remaining(self) -> int:
        return self._remaining

    def readline(self, size: int = -1):
        if self._remaining <= 0:
            raise http.client.HTTPException("request headers exceed byte budget")

        budgeted_size = self._remaining + 1
        if size is not None and size >= 0:
            budgeted_size = min(size, budgeted_size)

        line = self._stream.readline(budgeted_size)
        if len(line) > self._remaining:
            raise http.client.HTTPException("request headers exceed byte budget")
        self._remaining -= len(line)
        return line


def _validate_request_header_bytes(value) -> int:
    """Return one strict positive integer aggregate header-byte limit."""
    return _validate_max_concurrent_requests(value)


class HealthServer(HealthServerV1666664):
    """Bound aggregate request-header bytes before endpoint evaluation."""

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
    ):
        header_budget = _validate_request_header_bytes(max_request_header_bytes)
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            request_header_deadline_seconds=request_header_deadline_seconds,
        )
        self.max_request_header_bytes = header_budget
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def parse_request(self):
                original_rfile = self.rfile
                self.rfile = _HeaderBudgetReader(original_rfile, header_budget)
                try:
                    return super().parse_request()
                finally:
                    self.rfile = original_rfile

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_HeaderBudgetReader",
    "_validate_request_header_bytes",
]
