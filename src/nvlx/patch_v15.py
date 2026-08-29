"""Conflict-safe Kubernetes patch plans and response classification."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class PatchPlan:
    subresource: str
    patch_type: str
    field_manager: str
    resource_version: str
    force: bool
    valid: bool
    reasons: tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(resource_version: str, *, subresource: str="status", field_manager: str="nvlx-controller") -> PatchPlan:
    rv=(resource_version or "").strip()
    if not rv: return PatchPlan(subresource,"application/merge-patch+json",field_manager,"",False,False,("resourceVersion required for optimistic concurrency",))
    if subresource not in {"status","metadata"}: return PatchPlan(subresource,"application/merge-patch+json",field_manager,rv,False,False,("only status or metadata patches are controller-owned",))
    return PatchPlan(subresource,"application/merge-patch+json",field_manager,rv,False,True,())

def classify_status(status_code: int) -> tuple[str,bool]:
    if status_code in {200,201}: return "success",False
    if status_code==404: return "gone",False
    if status_code==409: return "relist-retry",True
    if status_code==429 or 500 <= status_code <= 599: return "retry",True
    if 400 <= status_code <= 499: return "hold",False
    return "hold",False
