"""Conflict-safe Kubernetes patch plans; no blind overwrite semantics."""
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
    if not resource_version: return PatchPlan(subresource,"application/merge-patch+json",field_manager,"",False,False,("resourceVersion required for optimistic concurrency",))
    if subresource not in {"status","metadata"}: return PatchPlan(subresource,"application/merge-patch+json",field_manager,resource_version,False,False,("only status or metadata patches are controller-owned",))
    return PatchPlan(subresource,"application/merge-patch+json",field_manager,resource_version,False,True,())
