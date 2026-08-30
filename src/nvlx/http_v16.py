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
    leader: bool
    leadership_fresh: bool
    inventory_fresh: bool
    nvidia_preflight_ready: bool
    checkpoint_ready: bool
    terminating: bool


@dataclass(frozen=True)
class MetricsSnapshot:
    """Frozen source values used to render one Prometheus response."""

    readiness: ReadinessSnapshot
    reconcile_total: int
    reconcile_failures: int
    checkpoint_writes: int
    checkpoint_idempotent_acks: int
    checkpoint_reconciled_commits: int
    checkpoint_rollbacks: int
    checkpoint_transaction_mismatches: int
    checkpoint_failures: int
    checkpoint_restore_attempts: int
    checkpoint_restore_successes: int
    checkpoint_sequence: int
    checkpoint_epoch: int


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


def _leadership_fresh_observation(
    runtime,
    stats,
    *,
    api_reachable: bool | None = None,
    leader: bool | None = None,
    terminating: bool | None = None,
) -> bool:
    """Observe Lease freshness from one captured gate state without mutating runtime state."""
    if api_reachable is None:
        api_reachable = bool(getattr(stats, "api_reachable", False))
    if leader is None:
        leader = bool(getattr(stats, "leader", False))
    if terminating is None:
        terminating = bool(getattr(stats, "terminating", False))

    if not api_reachable:
        return False
    if terminating or not leader:
        return False

    verified = getattr(runtime, "_leader_verified_monotonic", None)
    window = getattr(runtime, "leader_fresh_seconds", None)
    if verified is None or window is None:
        return leader

    try:
        verified = float(verified)
        window = float(window)
        age = time.monotonic() - verified
    except (TypeError, ValueError, OverflowError):
        return False
    return bool(verified > 0 and window > 0 and 0 <= age <= window)


def _readiness_snapshot(runtime, stats) -> ReadinessSnapshot:
    """Legacy compatibility path for runtimes without typed diagnosis."""
    ready_fn = getattr(runtime, "ready", None)
    if callable(ready_fn):
        controller_ready = _runtime_ready(runtime, stats)
        api_reachable = bool(getattr(stats, "api_reachable", False))
        leader = bool(getattr(stats, "leader", False))
        inventory_fresh = bool(getattr(stats, "inventory_fresh", False))
        terminating = bool(getattr(stats, "terminating", False))
    else:
        api_reachable = bool(getattr(stats, "api_reachable", False))
        leader = bool(getattr(stats, "leader", False))
        inventory_fresh = bool(getattr(stats, "inventory_fresh", False))
        terminating = bool(getattr(stats, "terminating", False))
        controller_ready = bool(
            api_reachable and leader and inventory_fresh and not terminating
        )

    nvidia_preflight_ready = bool(getattr(runtime, "nvidia_preflight_ok", True))
    leadership_fresh = _leadership_fresh_observation(
        runtime,
        stats,
        api_reachable=api_reachable,
        leader=leader,
        terminating=terminating,
    )
    checkpoint_ready = _checkpoint_ready(runtime)
    return ReadinessSnapshot(
        controller_ready=controller_ready,
        api_reachable=api_reachable,
        leader=leader,
        leadership_fresh=leadership_fresh,
        inventory_fresh=inventory_fresh,
        nvidia_preflight_ready=nvidia_preflight_ready,
        checkpoint_ready=checkpoint_ready,
        terminating=terminating,
    )


def _strict_bool_field(diagnosis, name: str) -> bool:
    value = getattr(diagnosis, name)
    if type(value) is not bool:
        raise TypeError(f"diagnosis field {name} must be bool")
    return value


def _strict_int_field(diagnosis, name: str) -> int:
    value = getattr(diagnosis, name)
    if type(value) is not int:
        raise TypeError(f"diagnosis field {name} must be int")
    return value


def _strict_nonnegative_int_field(diagnosis, name: str) -> int:
    value = _strict_int_field(diagnosis, name)
    if value < 0:
        raise ValueError(f"diagnosis field {name} must be nonnegative")
    return value


def _typed_serving_gates_pass(snapshot: ReadinessSnapshot) -> bool:
    return bool(
        snapshot.api_reachable
        and snapshot.leader
        and snapshot.leadership_fresh
        and snapshot.inventory_fresh
        and snapshot.nvidia_preflight_ready
        and snapshot.checkpoint_ready
        and not snapshot.terminating
    )


def _validate_typed_readiness_domain(snapshot: ReadinessSnapshot) -> None:
    if snapshot.leadership_fresh and (
        not snapshot.api_reachable or not snapshot.leader or snapshot.terminating
    ):
        raise ValueError(
            "fresh leadership requires API reachability, effective leadership and non-termination"
        )
    if snapshot.controller_ready and not _typed_serving_gates_pass(snapshot):
        raise ValueError(
            "controller readiness cannot contradict exported serving gates"
        )


def _coerce_readiness_diagnosis(diagnosis) -> ReadinessSnapshot:
    """Validate a runtime-owned diagnosis and normalize it to the HTTP presentation shape."""
    snapshot = ReadinessSnapshot(
        controller_ready=_strict_bool_field(diagnosis, "controller_ready"),
        api_reachable=_strict_bool_field(diagnosis, "api_reachable"),
        leader=_strict_bool_field(diagnosis, "leader"),
        leadership_fresh=_strict_bool_field(diagnosis, "leadership_fresh"),
        inventory_fresh=_strict_bool_field(diagnosis, "inventory_fresh"),
        nvidia_preflight_ready=_strict_bool_field(
            diagnosis, "nvidia_preflight_ready"
        ),
        checkpoint_ready=_strict_bool_field(diagnosis, "checkpoint_ready"),
        terminating=_strict_bool_field(diagnosis, "terminating"),
    )
    _validate_typed_readiness_domain(snapshot)
    return snapshot


def _runtime_readiness_snapshot(runtime) -> ReadinessSnapshot:
    """Prefer runtime-owned diagnosis; retain the historical fallback for compatibility."""
    diagnosis_fn = getattr(runtime, "readiness_diagnosis", None)
    if callable(diagnosis_fn):
        try:
            return _coerce_readiness_diagnosis(diagnosis_fn())
        except Exception:
            return ReadinessSnapshot(
                controller_ready=False,
                api_reachable=False,
                leader=False,
                leadership_fresh=False,
                inventory_fresh=False,
                nvidia_preflight_ready=False,
                checkpoint_ready=False,
                terminating=False,
            )
    return _readiness_snapshot(runtime, runtime.stats)


def _metrics_snapshot(runtime, stats) -> MetricsSnapshot:
    """Legacy compatibility path for runtimes without typed metrics diagnosis."""
    readiness = _readiness_snapshot(runtime, stats)
    return MetricsSnapshot(
        readiness=readiness,
        reconcile_total=stats.reconcile_total,
        reconcile_failures=stats.reconcile_failures,
        checkpoint_writes=getattr(runtime, "nvidia_checkpoint_writes", 0),
        checkpoint_idempotent_acks=getattr(runtime, "nvidia_checkpoint_idempotent_acks", 0),
        checkpoint_reconciled_commits=getattr(
            runtime, "nvidia_checkpoint_reconciled_commits", 0
        ),
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
    )


def _validate_typed_metrics_domain(snapshot: MetricsSnapshot) -> None:
    if snapshot.reconcile_failures > snapshot.reconcile_total:
        raise ValueError("reconcile failures cannot exceed reconcile attempts")
    if snapshot.checkpoint_restore_successes > snapshot.checkpoint_restore_attempts:
        raise ValueError("checkpoint restore successes cannot exceed restore attempts")
    if snapshot.checkpoint_reconciled_commits > (
        snapshot.checkpoint_writes + snapshot.checkpoint_idempotent_acks
    ):
        raise ValueError("reconciled commits cannot exceed accepted checkpoint commits")


def _coerce_metrics_diagnosis(diagnosis) -> MetricsSnapshot:
    """Strictly validate runtime-owned metrics diagnosis without live-state fallback."""
    snapshot = MetricsSnapshot(
        readiness=_coerce_readiness_diagnosis(diagnosis.readiness),
        reconcile_total=_strict_nonnegative_int_field(diagnosis, "reconcile_total"),
        reconcile_failures=_strict_nonnegative_int_field(
            diagnosis, "reconcile_failures"
        ),
        checkpoint_writes=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_writes"
        ),
        checkpoint_idempotent_acks=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_idempotent_acks"
        ),
        checkpoint_reconciled_commits=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_reconciled_commits"
        ),
        checkpoint_rollbacks=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_rollbacks"
        ),
        checkpoint_transaction_mismatches=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_transaction_mismatches"
        ),
        checkpoint_failures=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_failures"
        ),
        checkpoint_restore_attempts=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_restore_attempts"
        ),
        checkpoint_restore_successes=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_restore_successes"
        ),
        checkpoint_sequence=_strict_nonnegative_int_field(
            diagnosis, "checkpoint_sequence"
        ),
        checkpoint_epoch=_strict_nonnegative_int_field(diagnosis, "checkpoint_epoch"),
    )
    _validate_typed_metrics_domain(snapshot)
    return snapshot


def _runtime_metrics_snapshot(runtime) -> MetricsSnapshot:
    """Prefer the runtime-owned frozen metrics diagnosis for live runtimes."""
    diagnosis_fn = getattr(runtime, "metrics_diagnosis", None)
    if callable(diagnosis_fn):
        return _coerce_metrics_diagnosis(diagnosis_fn())
    return _metrics_snapshot(runtime, runtime.stats)


def _render_metrics_snapshot(snapshot: MetricsSnapshot) -> str:
    """Render Prometheus output using only a frozen capture, never live runtime state."""
    readiness = snapshot.readiness
    return render_metrics(
        leader=readiness.leader,
        reconcile_total=snapshot.reconcile_total,
        reconcile_failures=snapshot.reconcile_failures,
        pending_approvals=0,
        rollback_required=0,
        controller_ready=readiness.controller_ready,
        api_reachable=readiness.api_reachable,
        leadership_fresh=readiness.leadership_fresh,
        inventory_fresh=readiness.inventory_fresh,
        nvidia_preflight_ready=readiness.nvidia_preflight_ready,
        terminating=readiness.terminating,
        checkpoint_writes=snapshot.checkpoint_writes,
        checkpoint_idempotent_acks=snapshot.checkpoint_idempotent_acks,
        checkpoint_reconciled_commits=snapshot.checkpoint_reconciled_commits,
        checkpoint_rollbacks=snapshot.checkpoint_rollbacks,
        checkpoint_transaction_mismatches=snapshot.checkpoint_transaction_mismatches,
        checkpoint_failures=snapshot.checkpoint_failures,
        checkpoint_restore_attempts=snapshot.checkpoint_restore_attempts,
        checkpoint_restore_successes=snapshot.checkpoint_restore_successes,
        checkpoint_sequence=snapshot.checkpoint_sequence,
        checkpoint_epoch=snapshot.checkpoint_epoch,
        checkpoint_ready=readiness.checkpoint_ready,
    )


class HealthServer:
    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        self.runtime = runtime
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def version_string(self) -> str:
                """Expose a stable product token without BaseHTTP or Python version details."""
                return "nvlx"

            def send_error(self, code, message=None, explain=None):
                """Contain framework-generated errors without reflecting parser or method details."""
                body = "request rejected\n"
                payload = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)

            def _send_text(
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
                self.wfile.write(payload)

            def do_GET(self):
                runtime = outer.runtime
                if self.path == "/livez":
                    self._send_text(200, "ok\n")
                    return
                if self.path == "/readyz":
                    snapshot = _runtime_readiness_snapshot(runtime)
                    self._send_text(
                        200 if snapshot.controller_ready else 503,
                        "ready\n" if snapshot.controller_ready else "not ready\n",
                    )
                    return
                if self.path == "/metrics":
                    try:
                        snapshot = _runtime_metrics_snapshot(runtime)
                        body = _render_metrics_snapshot(snapshot)
                    except Exception:
                        self._send_text(500, "metrics unavailable\n")
                        return
                    self._send_text(
                        200,
                        body,
                        content_type="text/plain; version=0.0.4; charset=utf-8",
                    )
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
