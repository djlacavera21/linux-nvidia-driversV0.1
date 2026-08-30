"""Prometheus text metrics for nvlx controller health and runtime gates."""
from __future__ import annotations


_COUNTER_METRICS = {
    "nvlx_controller_reconcile_total",
    "nvlx_controller_reconcile_failures_total",
    "nvlx_controller_preflight_stale_total",
    "nvlx_nvidia_checkpoint_writes_total",
    "nvlx_nvidia_checkpoint_idempotent_acks_total",
    "nvlx_nvidia_checkpoint_rollbacks_total",
    "nvlx_nvidia_checkpoint_transaction_mismatches_total",
    "nvlx_nvidia_checkpoint_failures_total",
    "nvlx_nvidia_checkpoint_restore_attempts_total",
    "nvlx_nvidia_checkpoint_restore_successes_total",
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
        f"# TYPE {name} {_metric_type(name)}\n{name} {value}\n"
        for name, value in vals.items()
    )
