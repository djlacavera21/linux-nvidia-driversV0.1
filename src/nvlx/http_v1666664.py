"""Absolute request-header deadline containment for nvlx 1.6.6.6.6.6.4."""
from __future__ import annotations

import socket
import threading

from .http_v1666662 import _validate_request_timeout
from .http_v1666663 import HealthServer as HealthServerV1666663


def _validate_request_header_deadline(value) -> float:
    """Return one finite positive absolute header deadline in seconds."""
    return _validate_request_timeout(value)


class HealthServer(HealthServerV1666663):
    """Bound total request-line/header parse time, not only per-read idle time."""

    def __init__(
        self,
        runtime,
        host: str = "0.0.0.0",
        port: int = 8080,
        *,
        request_timeout_seconds: float = 5.0,
        max_concurrent_requests: int = 32,
        request_header_deadline_seconds: float = 5.0,
    ):
        header_deadline = _validate_request_header_deadline(
            request_header_deadline_seconds
        )
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
        )
        self.request_header_deadline_seconds = header_deadline
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def _arm_request_header_deadline(self) -> None:
                lock = threading.Lock()
                state = {"armed": True}

                def expire() -> None:
                    with lock:
                        if not state["armed"]:
                            return
                        state["armed"] = False
                    try:
                        self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass

                timer = threading.Timer(header_deadline, expire)
                timer.daemon = True
                self._nvlx_header_deadline_lock = lock
                self._nvlx_header_deadline_state = state
                self._nvlx_header_deadline_timer = timer
                timer.start()

            def _cancel_request_header_deadline(self) -> None:
                lock = getattr(self, "_nvlx_header_deadline_lock", None)
                state = getattr(self, "_nvlx_header_deadline_state", None)
                timer = getattr(self, "_nvlx_header_deadline_timer", None)
                if lock is None or state is None:
                    return
                with lock:
                    state["armed"] = False
                if timer is not None:
                    timer.cancel()
                self._nvlx_header_deadline_lock = None
                self._nvlx_header_deadline_state = None
                self._nvlx_header_deadline_timer = None

            def handle_one_request(self) -> None:
                self._arm_request_header_deadline()
                try:
                    super().handle_one_request()
                finally:
                    self._cancel_request_header_deadline()

            def parse_request(self):
                try:
                    return super().parse_request()
                finally:
                    # Once the request line and headers have been parsed, the
                    # absolute ingress deadline no longer applies. Runtime and
                    # response work retain their historical behavior.
                    self._cancel_request_header_deadline()

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer", "_validate_request_header_deadline"]
