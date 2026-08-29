"""Governed multi-cluster failover execution planning."""
from __future__ import annotations
from dataclasses import asdict,dataclass

@dataclass(frozen=True)
class FailoverPlan:
    source_cluster:str
    target_cluster:str
    namespace:str
    checkpoint_required:bool
    steps:tuple[str,...]
    safe:bool
    def to_dict(self): return asdict(self)

def plan(source_cluster:str,target_cluster:str,namespace:str,*,checkpoint_ready:bool,capacity_ready:bool,security_ready:bool)->FailoverPlan:
    safe=capacity_ready and security_ready and checkpoint_ready
    steps=(
        f"freeze admissions in {source_cluster}:{namespace}",
        "verify application checkpoint manifest and storage reachability",
        f"restore workload manifests and claims into {target_cluster}:{namespace}",
        "wait for GPU placement, readiness, and SLO gates",
        "switch traffic only after target health is green",
    )
    return FailoverPlan(source_cluster,target_cluster,namespace,True,steps,safe)
