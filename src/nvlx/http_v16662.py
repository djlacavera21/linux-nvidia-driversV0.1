"""Unified GET/HEAD live-request dispatcher for nvlx 1.6.6.6.2."""
from __future__ import annotations

from dataclasses import dataclass

from .http_v16 import (
    _render_metrics_snapshot,
    _runtime_metrics_snapshot,
    _runtime_readiness_snapshot,
)
from .http_v1666 import HealthServer as HealthServerV1666


@dataclass(frozen=True)
class _LiveResponse:
    status: int
    body: str
    content_type: str = "text/plain; charset=utf-8"


def _resolve_live_response(runtime, path: str) -> _LiveResponse | None:
    """Resolve one live representation for both GET and HEAD."""
    if path == "/livez":
        return _LiveResponse(200, "ok\n")
    if path == "/readyz":
        snapshot = _runtime_readiness_snapshot(runtime)
        return _LiveResponse(
            200 if snapshot.controller_ready else 503,
            "ready\n" if snapshot.controller_ready else "not ready\n",
        )
    if path == "/metrics":
        try:
            snapshot = _runtime_metrics_snapshot(runtime)
            body = _render_metrics_snapshot(snapshot)
        except Exception:
            return _LiveResponse(500, "metrics unavailable\n")
        return _LiveResponse(
            200,
            body,
            "text/plain; version=0.0.4; charset=utf-8",
        )
    return None


class HealthServer(HealthServerV1666):
    """Serve GET and HEAD through one live-request resolution path."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass
        server = self

        class Handler(base_handler):
            def _send_live_response(
                self,
                response: _LiveResponse,
                *,
                write_body: bool,
            ) -> None:
                payload = response.body.encode("utf-8")
                self.send_response(response.status)
                self.send_header("Content-Type", response.content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if write_body:
                    self.wfile.write(payload)

            def _handle_live_request(self, *, write_body: bool) -> None:
                response = _resolve_live_response(server.runtime, self.path)
                if response is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                self._send_live_response(response, write_body=write_body)

            def do_GET(self):
                self._handle_live_request(write_body=True)

            def do_HEAD(self):
                self._handle_live_request(write_body=False)

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
