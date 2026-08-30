"""Client-abort response-write containment for nvlx 1.6.6.6.6.6."""
from __future__ import annotations

import errno

from .http_v166665 import HealthServer as HealthServerV166665


_CLIENT_ABORT_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "EPIPE", None),
        getattr(errno, "ECONNRESET", None),
        getattr(errno, "ECONNABORTED", None),
        getattr(errno, "ENOTCONN", None),
        getattr(errno, "ESHUTDOWN", None),
    )
    if value is not None
)


def _is_client_abort_error(exc: BaseException) -> bool:
    """Return True only for connection-local abort/write failures."""
    return bool(
        isinstance(exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError))
        or (
            isinstance(exc, OSError)
            and getattr(exc, "errno", None) in _CLIENT_ABORT_ERRNOS
        )
    )


class HealthServer(HealthServerV166665):
    """Keep probe disconnects from escalating into server-level request errors."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def handle(self) -> None:
                try:
                    super().handle()
                except OSError as exc:
                    if not _is_client_abort_error(exc):
                        raise
                    self.close_connection = True

            def finish(self) -> None:
                try:
                    super().finish()
                except OSError as exc:
                    if not _is_client_abort_error(exc):
                        raise
                    self.close_connection = True

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
