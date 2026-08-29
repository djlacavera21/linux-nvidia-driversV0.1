"""Confidential GPU workload readiness validation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, subprocess

@dataclass(frozen=True)
class ConfidentialReport:
    enabled_nodes:int; kata_runtime:bool; isolated:bool; valid:bool; reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def inspect()->ConfidentialReport:
    p=subprocess.run(["kubectl","get","nodes","-o","json"],capture_output=True,text=True,timeout=15)
    if p.returncode: return ConfidentialReport(0,False,False,False,("node inventory unavailable",))
    nodes=json.loads(p.stdout).get("items",[]); enabled=0; bad=[]
    for n in nodes:
        labels=n.get("metadata",{}).get("labels",{}); mode=labels.get("nvidia.com/gpu.workload.config")
        if mode=="vm-passthrough": enabled+=1
        if mode=="vm-passthrough" and labels.get("nvlx.io/traditional-gpu-workloads")=="true": bad.append(n["metadata"]["name"])
    q=subprocess.run(["kubectl","get","runtimeclass","-o","name"],capture_output=True,text=True,timeout=10)
    kata=q.returncode==0 and "kata" in q.stdout.lower(); reasons=[]
    if enabled and not kata: reasons.append("confidential GPU nodes require a Kata runtime class")
    if bad: reasons.append("confidential and traditional GPU workload modes overlap: "+", ".join(bad))
    return ConfidentialReport(enabled,kata,not bad,not reasons,tuple(reasons))
