"""Kubernetes watch cursor and relist semantics for GPUFleet resources."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class WatchDecision:
    action: str
    resource_version: str
    requeue: bool
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def decide(event_type: str, resource_version: str | None, *, expired: bool=False) -> WatchDecision:
    et=(event_type or "").strip().upper()
    rv=(resource_version or "").strip()
    if expired or et=="ERROR":
        return WatchDecision("relist","",True,("watch cursor expired or errored",))
    if et not in {"ADDED","MODIFIED","DELETED","BOOKMARK"}:
        return WatchDecision("hold",rv,True,("unsupported watch event",))
    if not rv:
        return WatchDecision("relist","",True,("resourceVersion required to advance watch cursor",))
    if et=="BOOKMARK":
        return WatchDecision("checkpoint",rv,False,())
    return WatchDecision("reconcile",rv,False,())
