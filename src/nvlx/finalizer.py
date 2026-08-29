"""Finalizer lifecycle planning for GPUFleet deletion."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .fleet_crd import FINALIZER

@dataclass(frozen=True)
class FinalizerDecision:
    action: str
    remove_finalizer: bool
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def decide(*, deleting: bool, rollback_pending: bool, quarantined_nodes: int, active_execution: bool) -> FinalizerDecision:
    if not deleting: return FinalizerDecision("retain",False,("resource not deleting",))
    reasons=[]
    if rollback_pending: reasons.append("rollback pending")
    if quarantined_nodes: reasons.append("quarantined nodes remain")
    if active_execution: reasons.append("execution active")
    if reasons: return FinalizerDecision("hold",False,tuple(reasons))
    return FinalizerDecision("finalize",True,(f"safe to remove {FINALIZER}",))
