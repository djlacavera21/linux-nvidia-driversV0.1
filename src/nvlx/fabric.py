"""GPU/NVLink/NVSwitch fabric qualification and topology-domain planning."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import subprocess

@dataclass(frozen=True)
class FabricReport:
    healthy:bool; gpu_count:int; nvlink_edges:int; nvswitch_detected:bool; fabric_manager_active:bool|None; reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def inspect()->FabricReport:
    p=subprocess.run(["nvidia-smi","topo","-m"],capture_output=True,text=True,timeout=10)
    if p.returncode: return FabricReport(False,0,0,False,None,("nvidia-smi topo unavailable",))
    lines=[x for x in p.stdout.splitlines() if x.strip()]; gpu=[x for x in lines if x.lstrip().startswith("GPU")]
    edges=sum(x.count("NV") for x in gpu)//2; switch=any("NVSwitch" in x or "NV#" in x for x in lines)
    s=subprocess.run(["systemctl","is-active","nvidia-fabricmanager"],capture_output=True,text=True,timeout=5)
    fm=s.returncode==0 if switch else None; reasons=[]
    if switch and not fm: reasons.append("NVSwitch detected but Fabric Manager is not active")
    return FabricReport(not reasons,len(gpu),edges,switch,fm,tuple(reasons))

def domain_labels(nodes:list[str], domain_size:int=8)->dict[str,str]:
    if domain_size<1: raise ValueError("domain_size must be positive")
    return {n:f"fabric-{i//domain_size:03d}" for i,n in enumerate(sorted(set(nodes)))}
