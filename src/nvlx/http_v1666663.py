"""Bounded live HTTP request admission for nvlx 1.6.6.6.6.6.3."""
from __future__ import annotations

import threading
from types import MethodType

from .http_v1666662 import HealthServer as HealthServerV1666662


def _validate_max_concurrent_requests(value) -> int:
    """Return one strict positive integer request-slot limit."""
    if type(value) is not int:
        raise TypeError("max concurrent requests must be a positive integer")
    if value <= 0:
        raise ValueError("max concurrent requests must be greater than zero")
    return value


class HealthServer(HealthServerV1666662):
    """Bound live-handler concurrency before request threads are created."""

    def __init__(
        self,
        runtime,
        host: str = "0.0.0.0",
        port: int = 8080,
        *,
        request_timeout_seconds: float = 5.0,
        max_concurrent_requests: int = 32,
    ):
        capacity = _validate_max_concurrent_requests(max_concurrent_requests)
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
        )
        slots = threading.BoundedSemaphore(capacity)
        self.max_concurrent_requests = capacity
        self._request_slots = slots

        original_process_request = self.httpd.process_request
        original_process_request_thread = self.httpd.process_request_thread

        def process_request(httpd, request, client_address) -> None:
            if not slots.acquire(blocking=False):
                # Admission happens before HTTP parsing, so do not invent a
                # method-blind HTTP response that could violate HEAD semantics.
                # Saturated clients are rejected at the transport boundary.
                httpd.shutdown_request(request)
                return
            try:
                original_process_request(request, client_address)
            except BaseException:
                slots.release()
                raise

        def process_request_thread(httpd, request, client_address) -> None:
            try:
                original_process_request_thread(request, client_address)
            finally:
                slots.release()

        self.httpd.process_request = MethodType(process_request, self.httpd)
        self.httpd.process_request_thread = MethodType(
            process_request_thread, self.httpd
        )


__all__ = ["HealthServer", "_validate_max_concurrent_requests"]
