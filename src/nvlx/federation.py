"""Multi-cluster federation and disaster-recovery planning."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class ClusterTarget:
    name:str
    region:str
    gpu_capacity:int
    healthy:bool=True
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class FederationPlan:
    primary:str
    failover_order:tuple[str,...]
    required_gpus:int
    valid:bool
    reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(clusters:list[ClusterTarget],*,primary:str,required_gpus:int)->FederationPlan:
    if required_gpus < 1: raise ValueError("required_gpus must be >= 1")
    by_name={c.name:c for c in clusters}
    reasons=[]
    if primary not in by_name: reasons.append("primary cluster not present")
    candidates=[c for c in clusters if c.name!=primary and c.healthy and c.gpu_capacity>=required_gpus]
    candidates.sort(key=lambda c:(-c.gpu_capacity,c.region,c.name))
    if not candidates: reasons.append("no healthy failover cluster has sufficient GPU capacity")
    return FederationPlan(primary,tuple(c.name for c in candidates),required_gpus,not reasons,tuple(reasons))
