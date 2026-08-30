"""Strict request-header field-name containment for nvlx 1.6.6.6.6.6.6.6.1."""
from __future__ import annotations

from .http_v16666666 import HealthServer as HealthServerV16666666

_FIELD_NAME_TOKEN_BYTES = frozenset(
    b"!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


def _header_field_name_is_safe(line) -> bool:
    """Require one non-empty RFC token-style field name before the first colon."""
    if type(line) is not bytes or not line:
        return False

    if line.endswith(b"\r\n"):
        field_line = line[:-2]
    elif line.endswith(b"\n"):
        field_line = line[:-1]
    else:
        field_line = line

    colon = field_line.find(b":")
    if colon <= 0:
        return False

    name = field_line[:colon]
    return all(byte in _FIELD_NAME_TOKEN_BYTES for byte in name)


class _HeaderFieldNameTrackingReader:
    """Track malformed physical header-field names without altering stream bytes."""

    def __init__(self, stream):
        self._stream = stream
        self.saw_invalid_field_name = False

    def readline(self, size: int = -1):
        line = self._stream.readline(size)
        if line in (b"", b"\r\n", b"\n"):
            return line

        # Obsolete continuation lines are handled by the inherited obs-fold gate.
        # This layer validates only physical header-field starts.
        if line.startswith((b" ", b"\t")):
            return line

        if not _header_field_name_is_safe(line):
            self.saw_invalid_field_name = True
        return line

    def __getattr__(self, name):
        return getattr(self._stream, name)


class HealthServer(HealthServerV16666666):
    """Reject malformed request-header field names before endpoint dispatch."""

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
                tracker = _HeaderFieldNameTrackingReader(original_rfile)
                self.rfile = tracker
                try:
                    parsed = super().parse_request()
                finally:
                    self.rfile = original_rfile

                if not parsed:
                    return False
                if not tracker.saw_invalid_field_name:
                    return True

                # Some parser paths silently ignore whitespace-before-colon or
                # other malformed names, while others accept non-token names.
                # Terminate every such raw spelling through the canonical fixed
                # parser-error surface before resource or runtime evaluation.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_FIELD_NAME_TOKEN_BYTES",
    "_HeaderFieldNameTrackingReader",
    "_header_field_name_is_safe",
]
