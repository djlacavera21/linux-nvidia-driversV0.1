"""Prometheus text metrics for nvlx controller health and runtime gates."""
from __future__ import annotations

def render(*, leader: bool, reconcile_total: int, reconcile_failures: int, pending_approvals: int, rollback_required: int, circuit_open: bool=False, rollout_slots: int=0, completed_executions: int=0, preflight_stale: int=0, canary_wave: int=0) -> str:
    vals={
        "nvlx_controller_leader":1 if leader else 0,
        "nvlx_controller_reconcile_total":max(0,reconcile_total),
        "nvlx_controller_reconcile_failures_total":max(0,reconcile_failures),
        "nvlx_controller_pending_approvals":max(0,pending_approvals),
        "nvlx_controller_rollback_required":max(0,rollback_required),
        "nvlx_controller_circuit_open":1 if circuit_open else 0,
        "nvlx_controller_rollout_slots":max(0,rollout_slots),
        "nvlx_controller_completed_executions":max(0,completed_executions),
        "nvlx_controller_preflight_stale_total":max(0,preflight_stale),
        "nvlx_controller_canary_wave":max(0,canary_wave),
    }
    return "".join(f"# TYPE {k} gauge\n{k} {v}\n" for k,v in vals.items())
