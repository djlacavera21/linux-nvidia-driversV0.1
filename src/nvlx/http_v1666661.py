"""Server-level client-abort traceback containment for nvlx 1.6.6.6.6.6.1."""
from __future__ import annotations

import sys
from types import MethodType

from .http_v166666 import (
    HealthServer as HealthServerV166666,
    _is_client_abort_error,
)


class HealthServer(HealthServerV166666):
    """Suppress only expected disconnects that escape before handler containment."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        original_handle_error = self.httpd.handle_error

        def handle_error(httpd, request, client_address) -> None:
            exc = sys.exc_info()[1]
            if exc is not None and _is_client_abort_error(exc):
                return
            original_handle_error(request, client_address)

        self.httpd.handle_error = MethodType(handle_error, self.httpd)


__all__ = ["HealthServer"]
