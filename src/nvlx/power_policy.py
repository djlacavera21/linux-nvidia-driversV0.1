"""Fleet power and thermal policy planning."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class PowerPolicy:
    max_watts:int|None
    max_temp_c:int|None
    action:str
    valid:bool
    reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(*,max_watts:int|None=None,max_temp_c:int|None=None,action:str="quarantine")->PowerPolicy:
    reasons=[]
    if max_watts is not None and max_watts < 50: reasons.append("max_watts is implausibly low")
    if max_temp_c is not None and not 40 <= max_temp_c <= 95: reasons.append("max_temp_c must be between 40 and 95")
    if action not in {"alert","drain","quarantine"}: reasons.append("action must be alert, drain, or quarantine")
    return PowerPolicy(max_watts,max_temp_c,action,not reasons,tuple(reasons))
