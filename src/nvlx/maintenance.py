"""Guarded Kubernetes node maintenance and drain orchestration."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess

@dataclass(frozen=True)
class MaintenancePlan:
    node:str; cordon:tuple[str,...]; drain:tuple[str,...]; uncordon:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(node:str, *, timeout:str="10m")->MaintenancePlan:
    return MaintenancePlan(node,("kubectl","cordon",node),("kubectl","drain",node,"--ignore-daemonsets","--delete-emptydir-data",f"--timeout={timeout}"),("kubectl","uncordon",node))

def apply(node:str, *, confirmed:bool, timeout:str="10m")->MaintenancePlan:
    if not confirmed: raise RuntimeError("maintenance requires --yes")
    if not shutil.which("kubectl"): raise RuntimeError("kubectl not found")
    p=plan(node,timeout=timeout)
    subprocess.run(list(p.cordon),check=True); subprocess.run(list(p.drain),check=True)
    return p

def release(node:str, *, confirmed:bool)->None:
    if not confirmed: raise RuntimeError("uncordon requires --yes")
    subprocess.run([shutil.which("kubectl") or "kubectl","uncordon",node],check=True)
