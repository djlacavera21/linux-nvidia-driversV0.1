"""Deterministic policy-driven placement scoring."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from .policy import FleetPolicy,evaluate

@dataclass(frozen=True)
class PlacementDecision:
    target:str|None
    ranked:tuple[tuple[str,int],...]
    rejected:tuple[tuple[str,tuple[str,...]],...]
    def to_dict(self): return asdict(self)

def decide(candidates:list[dict[str,object]], policy:FleetPolicy)->PlacementDecision:
    ranked=[]; rejected=[]
    for c in candidates:
        name=str(c.get("name",""))
        ok,reasons=evaluate(c,policy)
        if not ok:
            rejected.append((name,reasons)); continue
        score=int(c.get("free_gpus",0))*100 + int(c.get("power_headroom_w",0) or 0)
        if c.get("rdma_ready"): score+=40
        if c.get("fabric_healthy"): score+=40
        temp=int(c.get("gpu_temp_c",0) or 0)
        if temp: score-=temp
        ranked.append((name,score))
    ranked.sort(key=lambda x:(-x[1],x[0]))
    return PlacementDecision(ranked[0][0] if ranked else None,tuple(ranked),tuple(sorted(rejected)))
