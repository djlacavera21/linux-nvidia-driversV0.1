"""NVIDIA Network Operator / RDMA readiness checks."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, subprocess

@dataclass(frozen=True)
class NetworkReport:
    operator_present:bool; nic_nodes:int; rdma_nodes:int; healthy:bool; reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def inspect()->NetworkReport:
    p=subprocess.run(["kubectl","get","nodes","-o","json"],capture_output=True,text=True,timeout=15)
    if p.returncode: return NetworkReport(False,0,0,False,("kubectl node inventory unavailable",))
    data=json.loads(p.stdout); nic=rdma=0
    for n in data.get("items",[]):
        labels=n.get("metadata",{}).get("labels",{})
        if any("mellanox" in k.lower() or "nvidia.com/network" in k.lower() for k in labels): nic+=1
        if any("rdma" in k.lower() for k in labels): rdma+=1
    q=subprocess.run(["kubectl","get","nicclusterpolicies.mellanox.com","-A","-o","name"],capture_output=True,text=True,timeout=10)
    present=q.returncode==0 and bool(q.stdout.strip()); reasons=[]
    if nic and not present: reasons.append("NVIDIA/Mellanox NIC nodes detected without Network Operator policy")
    return NetworkReport(present,nic,rdma,not reasons,tuple(reasons))
