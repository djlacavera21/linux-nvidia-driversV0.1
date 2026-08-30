"""HEAD parity adapter for nvlx 1.6.6.6.1."""
from __future__ import annotations

from .http_v16 import (
    _render_metrics_snapshot,
    _runtime_metrics_snapshot,
    _runtime_readiness_snapshot,
)
from .http_v1666 import HealthServer as HealthServerV1666


class HealthServer(HealthServerV1666):
    """Mirror live GET representation metadata for HEAD without sending bodies."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(runtime, host, port)
        base_handler = self.httpd.RequestHandlerClass
        server = self

        class Handler(base_handler):
            def _send_head_text(
                self,
                status: int,
                body: str,
                *,
                content_type: str = "text/plain; charset=utf-8",
            ) -> None:
                payload = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()

            def do_HEAD(self):
                runtime = server.runtime
                if self.path == "/livez":
                    self._send_head_text(200, "ok\n")
                    return
                if self.path == "/readyz":
                    snapshot = _runtime_readiness_snapshot(runtime)
                    self._send_head_text(
                        200 if snapshot.controller_ready else 503,
                        "ready\n" if snapshot.controller_ready else "not ready\n",
                    )
                    return
                if self.path == "/metrics":
                    try:
                        snapshot = _runtime_metrics_snapshot(runtime)
                        body = _render_metrics_snapshot(snapshot)
                    except Exception:
                        self._send_head_text(500, "metrics unavailable\n")
                        return
                    self._send_head_text(
                        200,
                        body,
                        content_type="text/plain; version=0.0.4; charset=utf-8",
                    )
                    return
                self.send_response(404)
                self.end_headers()

        self.httpd.RequestHandlerClass = Handler


__all__ = ["HealthServer"]
