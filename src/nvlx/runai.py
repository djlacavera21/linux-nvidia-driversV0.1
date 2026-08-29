"""NVIDIA Run:ai presence and DRA integration inspection."""
from __future__ import annotations
from dataclasses import asdict,dataclass
import json,shutil,subprocess

@dataclass(frozen=True)
class RunAiReport:
    kubectl:bool
    installed:bool
    scheduler_present:bool
    dra_claims_present:bool
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def _json(args:list[str])->dict:
    p=subprocess.run(args,capture_output=True,text=True)
    if p.returncode: return {}
    try:return json.loads(p.stdout)
    except json.JSONDecodeError:return {}

def inspect()->RunAiReport:
    if not shutil.which("kubectl"):
        return RunAiReport(False,False,False,False,("kubectl not found",))
    pods=_json(["kubectl","get","pods","-A","-o","json"]).get("items",[])
    names=[str(p.get("metadata",{}).get("name","")) for p in pods]
    installed=any("runai" in n.lower() for n in names)
    scheduler=any("scheduler" in n.lower() and "runai" in n.lower() for n in names)
    claims=_json(["kubectl","get","resourceclaims","-A","-o","json"]).get("items",[])
    dra=bool(claims)
    notes=[]
    if installed and not dra: notes.append("Run:ai detected but no ResourceClaims observed")
    return RunAiReport(True,installed,scheduler,dra,tuple(notes))
