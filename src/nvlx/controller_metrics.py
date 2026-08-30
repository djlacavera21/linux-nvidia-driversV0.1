"""Prometheus text metrics for nvlx controller health and runtime gates."""
from __future__ import annotations


_COUNTER_METRICS = {
    "nvlx_controller_reconcile_total",
    "nvlx_controller_reconcile_failures_total",
    "nvlx_controller_preflight_stale_total",
    "nvlx_nvidia_checkpoint_writes_total",
    "nvlx_nvidia_checkpoint_idempotent_acks_total",
    "nvlx_nvidia_checkpoint_reconciled_commits_total",
    "nvlx_nvidia_checkpoint_rollbacks_total",
    "nvlx_nvidia_checkpoint_transaction_mismatches_total",
    "nvlx_nvidia_checkpoint_failures_total",
    "nvlx_nvidia_checkpoint_restore_attempts_total",
    "nvlx_nvidia_checkpoint_restore_successes_total",
}

_METRIC_HELP = {
    "nvlx_controller_leader": "Whether this controller currently holds effective leadership.",
    "nvlx_controller_ready": "Whether the controller's complete readiness contract currently passes.",
    "nvlx_controller_api_reachable": "Whether the Kubernetes API is currently reachable.",
    "nvlx_controller_leadership_fresh": "Whether the current Lease leadership proof is still fresh.",
    "nvlx_controller_inventory_fresh": "Whether controller inventory continuity is currently fresh.",
    "nvlx_controller_terminating": "Whether the controller is intentionally terminating.",
    "nvlx_nvidia_preflight_ready": "Whether NVIDIA inventory and preflight validation currently pass.",
    "nvlx_controller_reconcile_total": "Total controller reconcile attempts observed by this process.",
    "nvlx_controller_reconcile_failures_total": "Total controller reconcile failures observed by this process.",
    "nvlx_controller_pending_approvals": "Current number of pending controller approvals.",
    "nvlx_controller_rollback_required": "Current number of controller rollback requirements.",
    "nvlx_controller_circuit_open": "Whether the controller circuit breaker is currently open.",
    "nvlx_controller_rollout_slots": "Current number of rollout slots available to the controller.",
    "nvlx_controller_completed_executions": "Current count of completed controller executions retained in runtime state.",
    "nvlx_controller_preflight_stale_total": "Total stale controller preflight observations.",
    "nvlx_controller_canary_wave": "Current controller canary rollout wave.",
    "nvlx_nvidia_checkpoint_writes_total": "Total successful NVIDIA continuity checkpoint writes.",
    "nvlx_nvidia_checkpoint_idempotent_acks_total": "Total proven idempotent NVIDIA checkpoint acknowledgements.",
    "nvlx_nvidia_checkpoint_reconciled_commits_total": "Total successful NVIDIA checkpoint commits recovered after transport-ambiguous outcomes.",
    "nvlx_nvidia_checkpoint_rollbacks_total": "Total NVIDIA checkpoint sequence rollback detections.",
    "nvlx_nvidia_checkpoint_transaction_mismatches_total": "Total NVIDIA checkpoint transaction state mismatches.",
    "nvlx_nvidia_checkpoint_failures_total": "Total NVIDIA continuity checkpoint persistence failures.",
    "nvlx_nvidia_checkpoint_restore_attempts_total": "Total NVIDIA continuity checkpoint restore attempts.",
    "nvlx_nvidia_checkpoint_restore_successes_total": "Total successful NVIDIA continuity checkpoint restores.",
    "nvlx_nvidia_checkpoint_sequence": "Current accepted NVIDIA continuity checkpoint sequence.",
    "nvlx_nvidia_checkpoint_epoch": "Current accepted NVIDIA continuity checkpoint Lease transition epoch.",
    "nvlx_nvidia_checkpoint_ready": "Whether the NVIDIA continuity checkpoint readiness gate currently passes.",
}


def _nonnegative(value: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _metric_type(name: str) -> str:
    return "counter" if name in _COUNTER_METRICS else "gauge"


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
    return "".join(
        f"# HELP {name} {_METRIC_HELP[name]}\n"
        f"# TYPE {name} {_metric_type(name)}\n"
        f"{name} {value}\n"
        for name, value in vals.items()
    )
