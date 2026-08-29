"""GPU Operator ClusterPolicy validation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, shutil, subprocess

@dataclass(frozen=True)
class ClusterPolicyReport:
    exists:bool; state:str|None; driver_enabled:bool|None; dcgm_exporter_enabled:bool|None; mig_strategy:str|None; cdi_enabled:bool|None; valid:bool; reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def validate_clusterpolicy()->ClusterPolicyReport:
    exe=shutil.which("kubectl")
    if not exe: raise RuntimeError("kubectl not found")
    r=subprocess.run([exe,"get","clusterpolicy","cluster-policy","-o","json"],capture_output=True,text=True,timeout=15,check=False)
    if r.returncode: return ClusterPolicyReport(False,None,None,None,None,None,False,("cluster-policy not found",))
    d=json.loads(r.stdout); spec=d.get("spec",{}); status=d.get("status",{})
    state=status.get("state") or status.get("status"); driver=spec.get("driver",{}).get("enabled",True); dcgm=spec.get("dcgmExporter",{}).get("enabled",True); mig=spec.get("mig",{}).get("strategy","none"); cdi=spec.get("cdi",{}).get("enabled")
    reasons=[]
    if state and str(state).lower() not in {"ready","success"}: reasons.append(f"ClusterPolicy state {state}")
    if not dcgm: reasons.append("DCGM Exporter disabled")
    if mig not in {"none","single","mixed"}: reasons.append(f"unknown MIG strategy {mig}")
    return ClusterPolicyReport(True,state,driver,dcgm,mig,cdi,not reasons,tuple(reasons))
