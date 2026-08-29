"""Live Kubernetes operator reconciliation planner for nvlx 1.5."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .watch_v15 import decide as watch_decide
from .patch_v15 import plan as patch_plan
from .workqueue_v15 import retry as retry_plan
from .reconcile_v14 import reconcile

@dataclass(frozen=True)
class OperatorPlan:
    action: str
    reconcile: dict|None
    patch: dict|None
    queue: dict|None
    def to_dict(self): return asdict(self)

def plan(name: str, *, event_type: str, resource_version: str, generation: int, allowed: bool, runtime_action: str, reasons=(), current_wave: int=0, promoted: bool=False, attempt: int=0, expired: bool=False) -> OperatorPlan:
    w=watch_decide(event_type,resource_version,expired=expired)
    if w.action=="relist": return OperatorPlan("relist",None,None,retry_plan(attempt).to_dict())
    if w.action=="checkpoint": return OperatorPlan("checkpoint",None,None,None)
    if w.action=="hold": return OperatorPlan("hold",None,None,retry_plan(attempt).to_dict())
    r=reconcile(name,generation=generation,allowed=allowed,runtime_action=runtime_action,runtime_reasons=reasons,current_wave=current_wave,promoted=promoted)
    p=patch_plan(resource_version,subresource="status")
    if not p.valid: return OperatorPlan("hold",r.to_dict(),p.to_dict(),retry_plan(attempt).to_dict())
    return OperatorPlan("patch-status",r.to_dict(),p.to_dict(),retry_plan(attempt).to_dict() if r.requeue else None)
