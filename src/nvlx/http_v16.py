"""HTTP liveness, readiness and metrics endpoints for nvlx 1.6."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from .controller_metrics import render as render_metrics


def _runtime_ready(runtime, stats) -> bool:
    """Use the runtime's readiness contract when available and fail closed on errors."""
    ready_fn = getattr(runtime, "ready", None)
    try:
        if callable(ready_fn):
            return bool(ready_fn())
        return bool(
            stats.api_reachable
            and stats.leader
            and stats.inventory_fresh
            and not stats.terminating
        )
    except Exception:
        return False


def _checkpoint_ready(runtime) -> bool:
    """Expose the narrower checkpoint gate independently from full readiness."""
    checkpoint_ready_fn = getattr(runtime, "_checkpoint_ready", None)
    try:
        return bool(checkpoint_ready_fn()) if callable(checkpoint_ready_fn) else True
    except Exception:
        return False


class HealthServer:
    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        self.runtime = runtime
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                runtime = outer.runtime
                s = runtime.stats
                if self.path == "/livez":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"ok\n")
                    return
                if self.path == "/readyz":
                    ready = _runtime_ready(runtime, s)
                    self.send_response(200 if ready else 503)
                    self.end_headers()
                    self.wfile.write(("ready\n" if ready else "not ready\n").encode())
                    return
                if self.path == "/metrics":
                    # Evaluate full readiness first so any inherited fail-closed
                    # invalidation (for example expired Lease freshness) is also
                    # reflected by the individual status gauges in this scrape.
                    controller_ready = _runtime_ready(runtime, s)
                    checkpoint_ready = _checkpoint_ready(runtime)
                    body = render_metrics(
                        leader=s.leader,
                        reconcile_total=s.reconcile_total,
                        reconcile_failures=s.reconcile_failures,
                        pending_approvals=0,
                        rollback_required=0,
                        controller_ready=controller_ready,
                        checkpoint_writes=getattr(runtime, "nvidia_checkpoint_writes", 0),
                        checkpoint_idempotent_acks=getattr(runtime, "nvidia_checkpoint_idempotent_acks", 0),
                        checkpoint_rollbacks=getattr(runtime, "nvidia_checkpoint_rollbacks", 0),
                        checkpoint_transaction_mismatches=getattr(
                            runtime, "nvidia_checkpoint_transaction_mismatches", 0
                        ),
                        checkpoint_failures=getattr(runtime, "nvidia_checkpoint_failures", 0),
                        checkpoint_restore_attempts=getattr(
                            runtime, "nvidia_checkpoint_restore_attempts", 0
                        ),
                        checkpoint_restore_successes=getattr(
                            runtime, "nvidia_checkpoint_restore_successes", 0
                        ),
                        checkpoint_sequence=getattr(runtime, "nvidia_checkpoint_sequence", 0),
                        checkpoint_epoch=getattr(runtime, "nvidia_checkpoint_epoch", 0),
                        checkpoint_ready=checkpoint_ready,
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    self.wfile.write(body.encode())
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
