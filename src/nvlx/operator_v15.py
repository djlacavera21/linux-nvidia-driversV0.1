"""Live Kubernetes operator reconciliation planner for nvlx 1.5.x."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .watch_v15 import decide as watch_decide
from .patch_v15 import plan as patch_plan
from .workqueue_v15 import retry as retry_plan
from .reconcile_v14 import reconcile
from .generation_v153 import evaluate as generation_evaluate
from .status_write_v153 import changed as status_changed
from .event_dedupe_v154 import fingerprint as event_fingerprint, duplicate as event_duplicate

@dataclass(frozen=True)
class OperatorPlan:
    action: str
    reconcile: dict|None
    patch: dict|None
    queue: dict|None
    status_fingerprint: str|None = None
    event_fingerprint: str|None = None
    def to_dict(self): return asdict(self)

def _queue(attempt: int, jitter_key: str|None=None):
    q=retry_plan(attempt,jitter_key=jitter_key)
    return q.to_dict()

def plan(name: str, *, event_type: str, resource_version: str, generation: int, allowed: bool, runtime_action: str, reasons=(), current_wave: int=0, promoted: bool=False, attempt: int=0, expired: bool=False, latest_generation: int|None=None, previous_status_fingerprint: str|None=None, previous_event_fingerprint: str|None=None, mutation_fence_ok: bool=True) -> OperatorPlan:
    efp=event_fingerprint(event_type=event_type,resource_version=resource_version,generation=generation)
    if event_duplicate(efp,previous_event_fingerprint):
        return OperatorPlan("event-noop",None,None,None,None,efp)
    w=watch_decide(event_type,resource_version,expired=expired)
    if w.action=="relist":
        q=_queue(attempt,efp)
        return OperatorPlan("dead-letter" if q["dead_letter"] else "relist",None,None,q,None,efp)
    if w.action=="checkpoint": return OperatorPlan("checkpoint",None,None,None,None,efp)
    if w.action=="hold":
        q=_queue(attempt,efp)
        return OperatorPlan("dead-letter" if q["dead_letter"] else "hold",None,None,q,None,efp)
    if (event_type or "").strip().upper()=="DELETED":
        return OperatorPlan("observe-delete",None,None,None,None,efp)
    if latest_generation is not None:
        gd=generation_evaluate(generation,latest_generation)
        if gd.stale:
            return OperatorPlan("discard-stale",None,None,None,None,efp)
    if not mutation_fence_ok:
        return OperatorPlan("fenced",None,None,None,None,efp)
    r=reconcile(name,generation=generation,allowed=allowed,runtime_action=runtime_action,runtime_reasons=reasons,current_wave=current_wave,promoted=promoted)
    rd=r.to_dict()
    did_change,status_fp=status_changed(rd,previous_status_fingerprint)
    if not did_change:
        return OperatorPlan("status-noop",rd,None,None,status_fp,efp)
    p=patch_plan(resource_version,subresource="status")
    if not p.valid:
        q=_queue(attempt,efp)
        return OperatorPlan("dead-letter" if q["dead_letter"] else "hold",rd,p.to_dict(),q,status_fp,efp)
    q=_queue(attempt,efp) if r.requeue else None
    if q and q["dead_letter"]:
        return OperatorPlan("dead-letter",rd,p.to_dict(),q,status_fp,efp)
    return OperatorPlan("patch-status",rd,p.to_dict(),q,status_fp,efp)
