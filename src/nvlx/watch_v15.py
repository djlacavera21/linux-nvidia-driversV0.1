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
    et=(event_type or "").upper()
    if expired or et=="ERROR": return WatchDecision("relist","",True,("watch cursor expired or errored",))
    if et not in {"ADDED","MODIFIED","DELETED","BOOKMARK"}: return WatchDecision("hold",resource_version or "",True,("unsupported watch event",))
    if et=="BOOKMARK": return WatchDecision("checkpoint",resource_version or "",False,())
    return WatchDecision("reconcile",resource_version or "",False,())
