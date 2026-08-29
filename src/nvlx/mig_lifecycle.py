"""Guarded local MIG profile lifecycle operations."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import os, shutil, subprocess
from .build import BuildError

@dataclass(frozen=True)
class MigProfilePlan:
    target:str
    mig_capable:bool|None
    active_compute_processes:int
    commands:tuple[tuple[str,...],...]
    disruptive:bool
    def to_dict(self): return asdict(self)

def _smi()->str|None: return shutil.which("nvidia-smi")
def _process_count(smi:str)->int:
    r=subprocess.run([smi,"--query-compute-apps=pid","--format=csv,noheader"],capture_output=True,text=True,timeout=6,check=False)
    return len([x for x in r.stdout.splitlines() if x.strip()])

def plan_mig_profile(target:str)->MigProfilePlan:
    smi=_smi()
    if not smi: return MigProfilePlan(target,None,0,(),True)
    probe=subprocess.run([smi,"mig","-lgip"],capture_output=True,text=True,timeout=8,check=False)
    capable=probe.returncode==0
    if target.lower() in {"off","disabled","none"}:
        commands=((smi,"mig","-dci"),(smi,"mig","-dgi"),(smi,"-mig","0"))
    else:
        commands=((smi,"-mig","1"),(smi,"mig","-dci"),(smi,"mig","-dgi"),(smi,"mig","-cgi",target,"-C"))
    return MigProfilePlan(target,capable,_process_count(smi),commands,True)

def apply_mig_profile(target:str,*,confirmed:bool,maintenance:bool)->MigProfilePlan:
    if not confirmed or not maintenance: raise BuildError("MIG reconfiguration requires --yes and --maintenance")
    if os.geteuid()!=0: raise BuildError("MIG reconfiguration must run as root")
    plan=plan_mig_profile(target)
    if plan.mig_capable is not True: raise BuildError("MIG capability was not confirmed")
    if plan.active_compute_processes: raise BuildError("active GPU compute processes detected; drain workloads before MIG reconfiguration")
    for command in plan.commands: subprocess.run(list(command),check=True)
    return plan
