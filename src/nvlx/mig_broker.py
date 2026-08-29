"""MIG and DynamicMIG capacity brokerage plans."""
from __future__ import annotations
from dataclasses import asdict, dataclass

CONFLICTS={"PassthroughSupport","NVMLDeviceHealthCheck","MPSSupport"}

@dataclass(frozen=True)
class MIGBrokerPlan:
    mode:str
    profile:str|None
    replicas:int
    dynamic_mig:bool
    feature_gates:tuple[str,...]
    valid:bool
    reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(*,profile:str|None,replicas:int=1,dynamic:bool=False,enabled_feature_gates=())->MIGBrokerPlan:
    if replicas < 1: raise ValueError("replicas must be >= 1")
    gates=set(enabled_feature_gates)
    reasons=[]
    if dynamic:
        gates.add("DynamicMIG")
        bad=sorted(CONFLICTS & gates)
        if bad: reasons.append("DynamicMIG conflicts with: "+", ".join(bad))
        if not profile: reasons.append("DynamicMIG requires an explicit MIG profile")
    mode="dynamic" if dynamic else "preconfigured"
    return MIGBrokerPlan(mode,profile,replicas,dynamic,tuple(sorted(gates)),not reasons,tuple(reasons))
