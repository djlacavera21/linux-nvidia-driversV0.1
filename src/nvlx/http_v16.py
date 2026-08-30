"""HTTP liveness, readiness and metrics endpoints for nvlx 1.6."""
from __future__ import annotations
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from .controller_metrics import render as render_metrics


@dataclass(frozen=True)
class ReadinessSnapshot:
    controller_ready: bool
    api_reachable: bool
    leadership_fresh: bool
    inventory_fresh: bool
    nvidia_preflight_ready: bool
    checkpoint_ready: bool
    terminating: bool


def _runtime_ready(runtime, stats) -> bool:
    """Use the runtime's readiness contract when available and fail closed on errors."""
    ready_fn = getattr(runtime, "ready", None)
    try:
        if callable(ready_fn):
            return bool(ready_fn())
        return bool(
            getattr(stats, "api_reachable", False)
            and getattr(stats, "leader", False)
            and getattr(stats, "inventory_fresh", False)
            and not getattr(stats, "terminating", False)
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


def _leadership_fresh_observation(runtime, stats) -> bool:
    """Observe Lease freshness without invoking the runtime's mutating fail-closed hook."""
    if not getattr(stats, "api_reachable", False):
        return False
    if getattr(stats, "terminating", False) or not getattr(stats, "leader", False):
        return False

    verified = getattr(runtime, "_leader_verified_monotonic", None)
    window = getattr(runtime, "leader_fresh_seconds", None)
    if verified is None or window is None:
        # Compatibility for runtimes that predate timestamped Lease freshness.
        return bool(getattr(stats, "leader", False))

    try:
        verified = float(verified)
        window = float(window)
        age = time.monotonic() - verified
    except (TypeError, ValueError, OverflowError):
        return False
    return bool(verified > 0 and window > 0 and 0 <= age <= window)


def _readiness_snapshot(runtime, stats) -> ReadinessSnapshot:
    """Evaluate full readiness once and capture the independently observable gates."""
    api_reachable = bool(getattr(stats, "api_reachable", False))
    inventory_fresh = bool(getattr(stats, "inventory_fresh", False))
    terminating = bool(getattr(stats, "terminating", False))
    nvidia_preflight_ready = bool(getattr(runtime, "nvidia_preflight_ok", True))
    leadership_fresh = _leadership_fresh_observation(runtime, stats)
    checkpoint_ready = _checkpoint_ready(runtime)
    controller_ready = _runtime_ready(runtime, stats)
    return ReadinessSnapshot(
        controller_ready=controller_ready,
        api_reachable=api_reachable,
        leadership_fresh=leadership_fresh,
        inventory_fresh=inventory_fresh,
        nvidia_preflight_ready=nvidia_preflight_ready,
        checkpoint_ready=checkpoint_ready,
        terminating=terminating,
    )


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
                    snapshot = _readiness_snapshot(runtime, s)
                    self.send_response(200 if snapshot.controller_ready else 503)
                    self.end_headers()
                    self.wfile.write(
                        ("ready\n" if snapshot.controller_ready else "not ready\n").encode()
                    )
                    return
                if self.path == "/metrics":
                    snapshot = _readiness_snapshot(runtime, s)
                    body = render_metrics(
                        leader=s.leader,
                        reconcile_total=s.reconcile_total,
                        reconcile_failures=s.reconcile_failures,
                        pending_approvals=0,
                        rollback_required=0,
                        controller_ready=snapshot.controller_ready,
                        api_reachable=snapshot.api_reachable,
                        leadership_fresh=snapshot.leadership_fresh,
                        inventory_fresh=snapshot.inventory_fresh,
                        nvidia_preflight_ready=snapshot.nvidia_preflight_ready,
                        terminating=snapshot.terminating,
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
                        checkpoint_ready=snapshot.checkpoint_ready,
                    )
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "text/plain; version=0.0.4; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))
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
