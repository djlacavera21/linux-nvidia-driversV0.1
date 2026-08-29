"""Minimal Prometheus text metrics for nvlx controller health."""
from __future__ import annotations

def render(*, leader: bool, reconcile_total: int, reconcile_failures: int, pending_approvals: int, rollback_required: int) -> str:
    vals={
        "nvlx_controller_leader":1 if leader else 0,
        "nvlx_controller_reconcile_total":max(0,reconcile_total),
        "nvlx_controller_reconcile_failures_total":max(0,reconcile_failures),
        "nvlx_controller_pending_approvals":max(0,pending_approvals),
        "nvlx_controller_rollback_required":max(0,rollback_required),
    }
    return "".join(f"# TYPE {k} gauge\n{k} {v}\n" for k,v in vals.items())
