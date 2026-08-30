"""Canonical CRLF request-line/header containment for nvlx 1.6.6.6.6.6.6.6.6.1."""
from __future__ import annotations

from .http_v166666666 import HealthServer as HealthServerV166666666


def _line_uses_canonical_crlf(line) -> bool:
    """Require one physical HTTP line to terminate with CRLF."""
    return type(line) is bytes and line.endswith(b"\r\n")


class _CanonicalCRLFTrackingReader:
    """Track non-CRLF header-section reads without changing stream bytes."""

    def __init__(self, stream):
        self._stream = stream
        self.saw_noncanonical_line_ending = False

    def readline(self, size: int = -1):
        line = self._stream.readline(size)
        if not _line_uses_canonical_crlf(line):
            self.saw_noncanonical_line_ending = True
        return line

    def __getattr__(self, name):
        return getattr(self._stream, name)


class HealthServer(HealthServerV166666666):
    """Reject non-CRLF request/header lines before endpoint dispatch."""

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
                raw_requestline = self.raw_requestline
                original_rfile = self.rfile
                tracker = _CanonicalCRLFTrackingReader(original_rfile)
                self.rfile = tracker
                try:
                    parsed = super().parse_request()
                finally:
                    self.rfile = original_rfile

                if not parsed:
                    return False
                if (
                    _line_uses_canonical_crlf(raw_requestline)
                    and not tracker.saw_noncanonical_line_ending
                ):
                    return True

                # BaseHTTPRequestHandler and email-style header parsing can accept
                # LF-only or EOF-terminated lines. Keep the live surface byte-
                # canonical: one CRLF request line, CRLF header fields, and a CRLF
                # blank line terminating the header section.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_CanonicalCRLFTrackingReader",
    "_line_uses_canonical_crlf",
]
