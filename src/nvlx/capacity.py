"""Cluster GPU capacity, allocation and fragmentation reporting."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, subprocess

@dataclass(frozen=True)
class CapacityReport:
    nodes:int; allocatable:int; requested:int; free:int; stranded_nodes:int; utilization:float
    def to_dict(self): return asdict(self)

def inspect()->CapacityReport:
    p=subprocess.run(["kubectl","get","nodes","-o","json"],capture_output=True,text=True,timeout=15)
    if p.returncode: return CapacityReport(0,0,0,0,0,0.0)
    items=json.loads(p.stdout).get("items",[]); alloc={}
    for n in items:
        name=n["metadata"]["name"]; raw=n.get("status",{}).get("allocatable",{}).get("nvidia.com/gpu","0")
        try: alloc[name]=int(raw)
        except ValueError: alloc[name]=0
    q=subprocess.run(["kubectl","get","pods","-A","-o","json"],capture_output=True,text=True,timeout=20)
    used={n:0 for n in alloc}
    if q.returncode==0:
        for pod in json.loads(q.stdout).get("items",[]):
            node=pod.get("spec",{}).get("nodeName");
            if node not in used: continue
            for c in pod.get("spec",{}).get("containers",[]):
                try: used[node]+=int(c.get("resources",{}).get("requests",{}).get("nvidia.com/gpu",0))
                except (TypeError,ValueError): pass
    total=sum(alloc.values()); req=sum(used.values()); free=max(0,total-req); stranded=sum(1 for n,a in alloc.items() if a-used.get(n,0)>0)
    return CapacityReport(sum(1 for x in alloc.values() if x),total,req,free,stranded,(req/total if total else 0.0))
