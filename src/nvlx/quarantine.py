"""Explicit Kubernetes quarantine/unquarantine controls for GPU nodes."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess

@dataclass(frozen=True)
class QuarantinePlan:
    node:str; reason:str; label_command:tuple[str,...]; taint_command:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(node:str, reason:str)->QuarantinePlan:
    safe=reason.strip().replace(" ","-")[:63] or "gpu-fault"
    return QuarantinePlan(node,safe,("kubectl","label","node",node,"nvlx.io/quarantined=true","--overwrite"),("kubectl","taint","node",node,f"nvlx.io/gpu-fault={safe}:NoSchedule","--overwrite"))

def apply(node:str, reason:str, *, confirmed:bool)->QuarantinePlan:
    if not confirmed: raise RuntimeError("quarantine requires --yes")
    if not shutil.which("kubectl"): raise RuntimeError("kubectl not found")
    p=plan(node,reason)
    subprocess.run(list(p.label_command),check=True); subprocess.run(list(p.taint_command),check=True)
    return p

def clear(node:str, *, confirmed:bool)->None:
    if not confirmed: raise RuntimeError("unquarantine requires --yes")
    exe=shutil.which("kubectl") or "kubectl"
    subprocess.run([exe,"label","node",node,"nvlx.io/quarantined-"],check=False)
    subprocess.run([exe,"taint","node",node,"nvlx.io/gpu-fault-"],check=False)
