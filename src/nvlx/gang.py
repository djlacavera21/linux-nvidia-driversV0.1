"""Topology-aware gang scheduling plans."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class GangPlan:
    replicas:int
    gpus_per_replica:int
    compute_domain:str|None
    min_available:int
    requires_all_or_nothing:bool
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(replicas:int,gpus_per_replica:int,*,compute_domain:str|None=None,min_available:int|None=None)->GangPlan:
    if replicas < 1 or gpus_per_replica < 1: raise ValueError("replicas and gpus_per_replica must be >= 1")
    minimum=replicas if min_available is None else min_available
    if minimum < 1 or minimum > replicas: raise ValueError("min_available must be within replica count")
    notes=("DRA resources do not support Kubernetes preemption; reserve capacity before admission.","Use a gang scheduler/JobSet integration for atomic pod admission; nvlx does not install one implicitly.")
    return GangPlan(replicas,gpus_per_replica,compute_domain,minimum,minimum==replicas,notes)
