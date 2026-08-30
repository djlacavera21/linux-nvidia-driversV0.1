"""Strict request-line byte budget for nvlx 1.6.6.6.6.6.6."""
from __future__ import annotations

from .http_v1666665 import HealthServer as HealthServerV1666665

_BASEHTTP_MAX_REQUEST_LINE_BYTES = 65536


class _RequestLineTooLong(Exception):
    """Raised internally when the configured request-line budget is exceeded."""

    def __init__(self, *, is_head: bool):
        super().__init__("request line exceeds byte budget")
        self.is_head = is_head


class _RequestLineBudgetReader:
    """Apply one byte budget to the first request-line readline only."""

    def __init__(self, stream, limit: int):
        self._stream = stream
        self._limit = limit
        self._checked = False

    def readline(self, size: int = -1):
        if self._checked:
            return self._stream.readline(size)

        self._checked = True
        budgeted_size = self._limit + 1
        if size is not None and size >= 0:
            budgeted_size = min(size, budgeted_size)

        line = self._stream.readline(budgeted_size)
        if len(line) > self._limit:
            raise _RequestLineTooLong(is_head=line.startswith(b"HEAD "))
        return line

    def __getattr__(self, name):
        return getattr(self._stream, name)


def _validate_request_line_bytes(value) -> int:
    """Return one strict positive request-line limit within BaseHTTP's hard cap."""
    if type(value) is not int:
        raise TypeError("max request line bytes must be a positive integer")
    if value <= 0:
        raise ValueError("max request line bytes must be greater than zero")
    if value > _BASEHTTP_MAX_REQUEST_LINE_BYTES:
        raise ValueError("max request line bytes must not exceed 65536")
    return value


class HealthServer(HealthServerV1666665):
    """Bound request-line bytes before BaseHTTP parsing or endpoint evaluation."""

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
    ):
        line_budget = _validate_request_line_bytes(max_request_line_bytes)
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            request_header_deadline_seconds=request_header_deadline_seconds,
            max_request_header_bytes=max_request_header_bytes,
        )
        self.max_request_line_bytes = line_budget
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def handle_one_request(self) -> None:
                original_rfile = self.rfile
                self.rfile = _RequestLineBudgetReader(original_rfile, line_budget)
                try:
                    try:
                        return super().handle_one_request()
                    except _RequestLineTooLong as exc:
                        # BaseHTTP historically emits 414 before parse_request()
                        # when its own 64 KiB line bound is crossed. Preserve that
                        # parser status while enforcing the tighter nvlx budget.
                        self.requestline = ""
                        self.command = "HEAD" if exc.is_head else None
                        self.close_connection = True
                        self.send_error(414)
                        return
                finally:
                    self.rfile = original_rfile

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_RequestLineBudgetReader",
    "_RequestLineTooLong",
    "_validate_request_line_bytes",
]
