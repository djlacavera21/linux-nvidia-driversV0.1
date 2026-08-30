"""Prometheus text metrics for nvlx controller health and runtime gates."""
from __future__ import annotations


def _nonnegative(value: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


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
    checkpoint_writes: int = 0,
    checkpoint_idempotent_acks: int = 0,
    checkpoint_rollbacks: int = 0,
    checkpoint_transaction_mismatches: int = 0,
    checkpoint_failures: int = 0,
    checkpoint_restore_attempts: int = 0,
    checkpoint_restore_successes: int = 0,
    checkpoint_sequence: int = 0,
    checkpoint_epoch: int = 0,
) -> str:
    vals = {
        "nvlx_controller_leader": 1 if leader else 0,
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
    }
    return "".join(f"# TYPE {k} gauge\n{k} {v}\n" for k, v in vals.items())
