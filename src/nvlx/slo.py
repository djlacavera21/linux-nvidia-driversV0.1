"""Fleet SLO gates for rollout and failover decisions."""
from __future__ import annotations
from dataclasses import asdict,dataclass

@dataclass(frozen=True)
class SloGate:
    passed:bool
    reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def evaluate(*,healthy_fraction:float,p95_startup_seconds:float,quarantined:int,xid_events:int,max_p95_startup_seconds:float=120.0,min_healthy_fraction:float=0.99,max_xid_events:int=0)->SloGate:
    reasons=[]
    if healthy_fraction < min_healthy_fraction: reasons.append("healthy GPU-node fraction below SLO")
    if p95_startup_seconds > max_p95_startup_seconds: reasons.append("GPU workload startup p95 above SLO")
    if quarantined: reasons.append("quarantined GPU nodes present")
    if xid_events > max_xid_events: reasons.append("Xid error budget exhausted")
    return SloGate(not reasons,tuple(reasons))
