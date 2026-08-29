"""Checkpoint and workload evacuation planning."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class EvacuationPlan:
    node:str
    checkpoint_mode:str
    commands:tuple[tuple[str,...],...]
    destructive:bool
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(node:str,*,checkpoint_mode:str="application",namespace:str|None=None)->EvacuationPlan:
    if checkpoint_mode not in {"application","criu","none"}: raise ValueError("checkpoint_mode must be application, criu, or none")
    ns=("-n",namespace) if namespace else ()
    commands=(("kubectl","cordon",node),("kubectl","get","pods",*ns,"--field-selector",f"spec.nodeName={node}","-o","wide"),("kubectl","drain",node,"--ignore-daemonsets","--delete-emptydir-data","--timeout=10m"))
    notes=("GPU application state is not assumed checkpointable; application-level checkpointing is the default.","CRIU mode is advisory and requires workload/runtime support; nvlx never claims transparent CUDA checkpoint support.")
    return EvacuationPlan(node,checkpoint_mode,commands,True,notes)
