"""Ingress-idle request timeout containment for nvlx 1.6.6.6.6.6.2."""
from __future__ import annotations

import errno
import math
from types import MethodType

from .http_v1666661 import HealthServer as HealthServerV1666661


_TIMEOUT_ERRNOS = frozenset(
    value
    for value in (getattr(errno, "ETIMEDOUT", None),)
    if value is not None
)


def _validate_request_timeout(value) -> float:
    """Return one finite positive request-read timeout in seconds."""
    if type(value) is bool:
        raise TypeError("request timeout must be a finite positive number")
    try:
        seconds = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError("request timeout must be a finite positive number") from exc
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("request timeout must be finite and greater than zero")
    return seconds


def _is_request_timeout_error(exc: BaseException) -> bool:
    """Recognize only connection-local request read expiration."""
    return bool(
        isinstance(exc, TimeoutError)
        or (
            isinstance(exc, OSError)
            and getattr(exc, "errno", None) in _TIMEOUT_ERRNOS
        )
    )


class HealthServer(HealthServerV1666661):
    """Bound idle/partial request reads without changing completed responses."""

    def __init__(
        self,
        runtime,
        host: str = "0.0.0.0",
        port: int = 8080,
        *,
        request_timeout_seconds: float = 5.0,
    ):
        timeout = _validate_request_timeout(request_timeout_seconds)
        super().__init__(runtime, host, port)
        self.request_timeout_seconds = timeout

        original_get_request = self.httpd.get_request
        original_handle_error = self.httpd.handle_error
        base_handler = self.httpd.RequestHandlerClass

        def get_request(httpd):
            request, client_address = original_get_request()
            request.settimeout(timeout)
            return request, client_address

        def handle_error(httpd, request, client_address) -> None:
            import sys

            exc = sys.exc_info()[1]
            if exc is not None and _is_request_timeout_error(exc):
                return
            original_handle_error(request, client_address)

        class Handler(base_handler):
            def handle(self) -> None:
                try:
                    super().handle()
                except OSError as exc:
                    if not _is_request_timeout_error(exc):
                        raise
                    self.close_connection = True

        self.httpd.get_request = MethodType(get_request, self.httpd)
        self.httpd.handle_error = MethodType(handle_error, self.httpd)
        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_is_request_timeout_error",
    "_validate_request_timeout",
]
