"""Multi-GPU, NVLink, NVSwitch, and NUMA topology inspection."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess

@dataclass(frozen=True)
class TopologyReport:
    available:bool
    gpu_count:int
    matrix:tuple[tuple[str,...],...]
    gpu_names:tuple[str,...]
    nvlink_edges:int
    nvswitch_evidence:bool
    raw:str
    warnings:tuple[str,...]
    def to_dict(self): return asdict(self)

def _run(args:list[str])->str|None:
    exe=shutil.which("nvidia-smi")
    if not exe: return None
    try:
        result=subprocess.run([exe,*args],capture_output=True,text=True,timeout=10,check=False)
    except OSError: return None
    return result.stdout.strip() if result.returncode==0 else None

def topology_report()->TopologyReport:
    raw=_run(["topo","-m"])
    names_raw=_run(["--query-gpu=index,name,pci.bus_id","--format=csv,noheader"])
    names=tuple(line.strip() for line in (names_raw or "").splitlines() if line.strip())
    if raw is None: return TopologyReport(False,len(names),(),names,0,False,"",("nvidia-smi topo -m unavailable",))
    lines=[line.rstrip() for line in raw.splitlines() if line.strip()]
    matrix=[]; nvlink_edges=0; switch=False
    for line in lines:
        fields=tuple(line.split())
        if fields and fields[0].startswith("GPU"):
            matrix.append(fields)
            nvlink_edges+=sum(1 for token in fields[1:] if token.startswith("NV"))
        if "NVSwitch" in line or "NVS" in fields: switch=True
    warnings=[]
    if len(names)>1 and not matrix: warnings.append("multiple GPUs detected but topology matrix could not be parsed")
    # Symmetric matrix counts each NVLink adjacency twice.
    return TopologyReport(True,len(names),tuple(matrix),names,nvlink_edges//2,switch,raw,tuple(warnings))
