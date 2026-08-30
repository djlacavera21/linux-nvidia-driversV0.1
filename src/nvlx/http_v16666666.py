"""Obsolete folded request-header containment for nvlx 1.6.6.6.6.6.6.6."""
from __future__ import annotations

from .http_v16666665 import HealthServer as HealthServerV16666665


class _ObsFoldTrackingReader:
    """Track obsolete header continuation lines without altering stream bytes."""

    def __init__(self, stream):
        self._stream = stream
        self.saw_obs_fold = False

    def readline(self, size: int = -1):
        line = self._stream.readline(size)
        if line.startswith((b" ", b"\t")):
            self.saw_obs_fold = True
        return line

    def __getattr__(self, name):
        return getattr(self._stream, name)


class HealthServer(HealthServerV16666665):
    """Reject obsolete folded request headers before endpoint dispatch."""

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
                original_rfile = self.rfile
                tracker = _ObsFoldTrackingReader(original_rfile)
                self.rfile = tracker
                try:
                    parsed = super().parse_request()
                finally:
                    self.rfile = original_rfile

                if not parsed:
                    return False
                if not tracker.saw_obs_fold:
                    return True

                # Continuation-line folding is obsolete and can produce different
                # header interpretations across intermediaries. Terminate the
                # request through the existing non-reflective parser-error surface.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_ObsFoldTrackingReader"]
