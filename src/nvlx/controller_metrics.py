"""Prometheus text metrics for nvlx controller health and runtime gates."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class MetricSpec:
    """Static Prometheus metadata for one exported metric."""

    metric_type: str
    help: str

    def __post_init__(self):
        if self.metric_type not in {"counter", "gauge"}:
            raise ValueError("Prometheus metric type must be counter or gauge")
        if not isinstance(self.help, str) or not self.help.strip():
            raise ValueError("Prometheus metric HELP text must be nonempty")
        if "\n" in self.help or "\r" in self.help:
            raise ValueError("Prometheus metric HELP text must be single-line")


_METRIC_SPECS = MappingProxyType(
    {
        "nvlx_controller_leader": MetricSpec(
            "gauge", "Whether this controller currently holds effective leadership."
        ),
        "nvlx_controller_ready": MetricSpec(
            "gauge", "Whether the controller's complete readiness contract currently passes."
        ),
        "nvlx_controller_api_reachable": MetricSpec(
            "gauge", "Whether the Kubernetes API is currently reachable."
        ),
        "nvlx_controller_leadership_fresh": MetricSpec(
            "gauge", "Whether the current Lease leadership proof is still fresh."
        ),
        "nvlx_controller_inventory_fresh": MetricSpec(
            "gauge", "Whether controller inventory continuity is currently fresh."
        ),
        "nvlx_controller_terminating": MetricSpec(
            "gauge", "Whether the controller is intentionally terminating."
        ),
        "nvlx_nvidia_preflight_ready": MetricSpec(
            "gauge", "Whether NVIDIA inventory and preflight validation currently pass."
        ),
        "nvlx_controller_reconcile_total": MetricSpec(
            "counter", "Total controller reconcile attempts observed by this process."
        ),
        "nvlx_controller_reconcile_failures_total": MetricSpec(
            "counter", "Total controller reconcile failures observed by this process."
        ),
        "nvlx_controller_pending_approvals": MetricSpec(
            "gauge", "Current number of pending controller approvals."
        ),
        "nvlx_controller_rollback_required": MetricSpec(
            "gauge", "Current number of controller rollback requirements."
        ),
        "nvlx_controller_circuit_open": MetricSpec(
            "gauge", "Whether the controller circuit breaker is currently open."
        ),
        "nvlx_controller_rollout_slots": MetricSpec(
            "gauge", "Current number of rollout slots available to the controller."
        ),
        "nvlx_controller_completed_executions": MetricSpec(
            "gauge", "Current count of completed controller executions retained in runtime state."
        ),
        "nvlx_controller_preflight_stale_total": MetricSpec(
            "counter", "Total stale controller preflight observations."
        ),
        "nvlx_controller_canary_wave": MetricSpec(
            "gauge", "Current controller canary rollout wave."
        ),
        "nvlx_nvidia_checkpoint_writes_total": MetricSpec(
            "counter", "Total successful NVIDIA continuity checkpoint writes."
        ),
        "nvlx_nvidia_checkpoint_idempotent_acks_total": MetricSpec(
            "counter", "Total proven idempotent NVIDIA checkpoint acknowledgements."
        ),
        "nvlx_nvidia_checkpoint_reconciled_commits_total": MetricSpec(
            "counter",
            "Total successful NVIDIA checkpoint commits recovered after transport-ambiguous outcomes.",
        ),
        "nvlx_nvidia_checkpoint_rollbacks_total": MetricSpec(
            "counter", "Total NVIDIA checkpoint sequence rollback detections."
        ),
        "nvlx_nvidia_checkpoint_transaction_mismatches_total": MetricSpec(
            "counter", "Total NVIDIA checkpoint transaction state mismatches."
        ),
        "nvlx_nvidia_checkpoint_failures_total": MetricSpec(
            "counter", "Total NVIDIA continuity checkpoint persistence failures."
        ),
        "nvlx_nvidia_checkpoint_restore_attempts_total": MetricSpec(
            "counter", "Total NVIDIA continuity checkpoint restore attempts."
        ),
        "nvlx_nvidia_checkpoint_restore_successes_total": MetricSpec(
            "counter", "Total successful NVIDIA continuity checkpoint restores."
        ),
        "nvlx_nvidia_checkpoint_sequence": MetricSpec(
            "gauge", "Current accepted NVIDIA continuity checkpoint sequence."
        ),
        "nvlx_nvidia_checkpoint_epoch": MetricSpec(
            "gauge", "Current accepted NVIDIA continuity checkpoint Lease transition epoch."
        ),
        "nvlx_nvidia_checkpoint_ready": MetricSpec(
            "gauge", "Whether the NVIDIA continuity checkpoint readiness gate currently passes."
        ),
    }
)

# Backward-compatible private views derived from the single schema source.
_COUNTER_METRICS = frozenset(
    name for name, spec in _METRIC_SPECS.items() if spec.metric_type == "counter"
)
_METRIC_HELP = MappingProxyType(
    {name: spec.help for name, spec in _METRIC_SPECS.items()}
)


def _nonnegative(value: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _metric_type(name: str) -> str:
    return _METRIC_SPECS[name].metric_type


def _validate_metric_values(vals: dict[str, int]) -> None:
    expected = tuple(_METRIC_SPECS)
    actual = tuple(vals)
    if actual == expected:
        return

    missing = [name for name in expected if name not in vals]
    extra = [name for name in actual if name not in _METRIC_SPECS]
    details = []
    if missing:
        details.append("missing=" + ",".join(missing))
    if extra:
        details.append("extra=" + ",".join(extra))
    if not missing and not extra:
        details.append("order mismatch")
    raise RuntimeError(
        "Prometheus metric schema/sample mismatch: " + "; ".join(details)
    )


def _render_metric_values(vals: dict[str, int]) -> str:
    _validate_metric_values(vals)
    return "".join(
        f"# HELP {name} {spec.help}\n"
        f"# TYPE {name} {spec.metric_type}\n"
        f"{name} {vals[name]}\n"
        for name, spec in _METRIC_SPECS.items()
    )


def render(
    *,
    leader: bool,
    reconcile_total: int,
    reconcile_failures: int,
    pending_approvals: int,
    rollback_required: int,
    circuit_open: bool = False,
    rollout_slots: int = 0,
    completed_executions: int = 0,
    preflight_stale: int = 0,
    canary_wave: int = 0,
    controller_ready: bool = False,
    api_reachable: bool = False,
    leadership_fresh: bool = False,
    inventory_fresh: bool = False,
    nvidia_preflight_ready: bool = False,
    terminating: bool = False,
    checkpoint_writes: int = 0,
    checkpoint_idempotent_acks: int = 0,
    checkpoint_reconciled_commits: int = 0,
    checkpoint_rollbacks: int = 0,
    checkpoint_transaction_mismatches: int = 0,
    checkpoint_failures: int = 0,
    checkpoint_restore_attempts: int = 0,
    checkpoint_restore_successes: int = 0,
    checkpoint_sequence: int = 0,
    checkpoint_epoch: int = 0,
    checkpoint_ready: bool = True,
) -> str:
    vals = {
        "nvlx_controller_leader": 1 if leader else 0,
        "nvlx_controller_ready": 1 if controller_ready else 0,
        "nvlx_controller_api_reachable": 1 if api_reachable else 0,
        "nvlx_controller_leadership_fresh": 1 if leadership_fresh else 0,
        "nvlx_controller_inventory_fresh": 1 if inventory_fresh else 0,
        "nvlx_controller_terminating": 1 if terminating else 0,
        "nvlx_nvidia_preflight_ready": 1 if nvidia_preflight_ready else 0,
        "nvlx_controller_reconcile_total": _nonnegative(reconcile_total),
        "nvlx_controller_reconcile_failures_total": _nonnegative(reconcile_failures),
        "nvlx_controller_pending_approvals": _nonnegative(pending_approvals),
        "nvlx_controller_rollback_required": _nonnegative(rollback_required),
        "nvlx_controller_circuit_open": 1 if circuit_open else 0,
        "nvlx_controller_rollout_slots": _nonnegative(rollout_slots),
        "nvlx_controller_completed_executions": _nonnegative(completed_executions),
        "nvlx_controller_preflight_stale_total": _nonnegative(preflight_stale),
        "nvlx_controller_canary_wave": _nonnegative(canary_wave),
        "nvlx_nvidia_checkpoint_writes_total": _nonnegative(checkpoint_writes),
        "nvlx_nvidia_checkpoint_idempotent_acks_total": _nonnegative(checkpoint_idempotent_acks),
        "nvlx_nvidia_checkpoint_reconciled_commits_total": _nonnegative(checkpoint_reconciled_commits),
        "nvlx_nvidia_checkpoint_rollbacks_total": _nonnegative(checkpoint_rollbacks),
        "nvlx_nvidia_checkpoint_transaction_mismatches_total": _nonnegative(checkpoint_transaction_mismatches),
        "nvlx_nvidia_checkpoint_failures_total": _nonnegative(checkpoint_failures),
        "nvlx_nvidia_checkpoint_restore_attempts_total": _nonnegative(checkpoint_restore_attempts),
        "nvlx_nvidia_checkpoint_restore_successes_total": _nonnegative(checkpoint_restore_successes),
        "nvlx_nvidia_checkpoint_sequence": _nonnegative(checkpoint_sequence),
        "nvlx_nvidia_checkpoint_epoch": _nonnegative(checkpoint_epoch),
        "nvlx_nvidia_checkpoint_ready": 1 if checkpoint_ready else 0,
    }
    return _render_metric_values(vals)
