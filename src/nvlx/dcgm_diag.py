"""DCGM diagnostic burn-in planning and guarded execution."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess

@dataclass(frozen=True)
class DiagnosticPlan:
    level:int; timeout_sec:int; command:tuple[str,...]
    def to_dict(self): return asdict(self)

def plan(level:int=3, timeout_sec:int=900)->DiagnosticPlan:
    if level not in {1,2,3,4}: raise ValueError("DCGM diagnostic level must be 1-4")
    exe=shutil.which("dcgmi") or "dcgmi"
    return DiagnosticPlan(level,timeout_sec,(exe,"diag","-r",str(level)))

def run(level:int=3, timeout_sec:int=900, *, confirmed:bool=False)->dict[str,object]:
    if not confirmed: raise RuntimeError("DCGM burn-in requires --yes")
    p=plan(level,timeout_sec)
    r=subprocess.run(list(p.command),capture_output=True,text=True,timeout=timeout_sec,check=False)
    return {"plan":p.to_dict(),"returncode":r.returncode,"passed":r.returncode==0,"stdout":r.stdout[-12000:],"stderr":r.stderr[-4000:]}
