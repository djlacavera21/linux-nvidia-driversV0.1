"""Strict request-header field-value containment for nvlx 1.6.6.6.6.6.6.6.2."""
from __future__ import annotations

from .http_v166666661 import HealthServer as HealthServerV166666661


def _header_field_value_is_safe(line) -> bool:
    """Allow only SP, HTAB and visible ASCII in one physical field value."""
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

    value = field_line[colon + 1 :]
    return all(byte in (0x09, 0x20) or 0x21 <= byte <= 0x7E for byte in value)


class _HeaderFieldValueTrackingReader:
    """Track forbidden raw field-value octets without altering stream bytes."""

    def __init__(self, stream):
        self._stream = stream
        self.saw_invalid_field_value = False

    def readline(self, size: int = -1):
        line = self._stream.readline(size)
        if line in (b"", b"\r\n", b"\n"):
            return line

        # Obsolete continuation lines remain owned by the inherited obs-fold
        # layer. Field-name defects remain owned by the inherited name layer.
        if line.startswith((b" ", b"\t")):
            return line

        if not _header_field_value_is_safe(line):
            self.saw_invalid_field_value = True
        return line

    def __getattr__(self, name):
        return getattr(self._stream, name)


class HealthServer(HealthServerV166666661):
    """Reject unsafe request-header field values before endpoint dispatch."""

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
                tracker = _HeaderFieldValueTrackingReader(original_rfile)
                self.rfile = tracker
                try:
                    parsed = super().parse_request()
                finally:
                    self.rfile = original_rfile

                if not parsed:
                    return False
                if not tracker.saw_invalid_field_value:
                    return True

                # This minimal live surface does not need opaque control or
                # non-ASCII field-value octets. Reject them before resource or
                # runtime evaluation to avoid parser/intermediary disagreement.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_HeaderFieldValueTrackingReader",
    "_header_field_value_is_safe",
]
