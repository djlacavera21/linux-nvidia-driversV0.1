"""Cluster-wide NVIDIA GPU node qualification."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, shutil, subprocess

@dataclass(frozen=True)
class NodeQualification:
    name:str; ready:bool; schedulable:bool; gpu_present:bool; driver_state:str|None; operator_state:str|None; qualified:bool; reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def _kubectl(args:list[str])->dict:
    exe=shutil.which("kubectl")
    if not exe: raise RuntimeError("kubectl not found")
    r=subprocess.run([exe,*args,"-o","json"],capture_output=True,text=True,timeout=20,check=False)
    if r.returncode: raise RuntimeError(r.stderr.strip() or "kubectl failed")
    return json.loads(r.stdout)

def qualify_nodes()->tuple[NodeQualification,...]:
    data=_kubectl(["get","nodes"]); out=[]
    for item in data.get("items",[]):
        meta=item.get("metadata",{}); labels=meta.get("labels",{}); spec=item.get("spec",{}); status=item.get("status",{})
        name=meta.get("name","unknown"); ready=any(c.get("type")=="Ready" and c.get("status")=="True" for c in status.get("conditions",[]))
        schedulable=not spec.get("unschedulable",False); gpu=labels.get("nvidia.com/gpu.present")=="true" or int(status.get("capacity",{}).get("nvidia.com/gpu",0) or 0)>0
        driver=labels.get("nvidia.com/gpu-driver-upgrade-state"); operator=labels.get("nvidia.com/gpu.deploy.operator-validator")
        reasons=[]
        if not ready: reasons.append("node not Ready")
        if not schedulable: reasons.append("node unschedulable")
        if gpu and driver and driver not in {"upgrade-done","upgrade-required"}: reasons.append(f"driver state {driver}")
        if gpu and operator=="false": reasons.append("GPU Operator validator disabled")
        out.append(NodeQualification(name,ready,schedulable,gpu,driver,operator,not reasons,tuple(reasons)))
    return tuple(out)
