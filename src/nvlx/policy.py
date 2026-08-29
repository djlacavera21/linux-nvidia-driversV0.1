"""Policy-as-code for fleet placement and disruption governance."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json

@dataclass(frozen=True)
class FleetPolicy:
    min_free_gpus:int=1
    require_rdma:bool=False
    require_fabric:bool=False
    max_gpu_temp_c:int=82
    min_power_headroom_w:int=50
    allow_alpha_dra:bool=False
    allow_cross_cluster_failover:bool=True
    require_checkpoint_before_evacuation:bool=True
    def to_dict(self): return asdict(self)

def load(path:str)->FleetPolicy:
    data=json.loads(open(path,encoding="utf-8").read())
    allowed=set(FleetPolicy.__dataclass_fields__)
    unknown=sorted(set(data)-allowed)
    if unknown: raise ValueError(f"unknown policy keys: {', '.join(unknown)}")
    return FleetPolicy(**data)

def evaluate(candidate:dict[str,object], policy:FleetPolicy)->tuple[bool,tuple[str,...]]:
    reasons=[]
    if int(candidate.get("free_gpus",0)) < policy.min_free_gpus: reasons.append("insufficient free GPUs")
    if policy.require_rdma and not candidate.get("rdma_ready",False): reasons.append("RDMA required")
    if policy.require_fabric and not candidate.get("fabric_healthy",False): reasons.append("healthy GPU fabric required")
    temp=int(candidate.get("gpu_temp_c",0) or 0)
    if temp and temp > policy.max_gpu_temp_c: reasons.append("temperature above policy")
    if int(candidate.get("power_headroom_w",0) or 0) < policy.min_power_headroom_w: reasons.append("insufficient power headroom")
    return not reasons,tuple(reasons)
