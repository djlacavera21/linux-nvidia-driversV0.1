"""Power-curtailment planning without implicit GPU power-limit mutation."""
from __future__ import annotations
from dataclasses import asdict,dataclass

@dataclass(frozen=True)
class CurtailmentPlan:
    current_watts:int
    target_watts:int
    reduction_percent:float
    action:str
    safe:bool
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(current_watts:int,target_watts:int,*,checkpointable:bool=False)->CurtailmentPlan:
    if current_watts<=0 or target_watts<=0: raise ValueError("power values must be positive")
    if target_watts>=current_watts:
        return CurtailmentPlan(current_watts,target_watts,0.0,"hold",True,("no curtailment required",))
    reduction=round((current_watts-target_watts)*100/current_watts,2)
    if reduction<=25: action="scheduler-throttle"
    elif checkpointable: action="checkpoint-and-evacuate"
    else: action="stop-admission-and-drain"
    return CurtailmentPlan(current_watts,target_watts,reduction,action,checkpointable or reduction<=25,("plan only; no nvidia-smi power-limit changes are issued",))
