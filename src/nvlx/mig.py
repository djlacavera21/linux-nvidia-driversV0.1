"""MIG, Fabric Manager, and DCGM compatibility inspection."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import re, shutil, subprocess
from .system import nvidia_smi_driver_version

@dataclass(frozen=True)
class MigFabricReport:
    driver_version:str|None
    mig_capable:bool|None
    mig_enabled:bool|None
    mig_instances:tuple[str,...]
    fabric_manager_version:str|None
    fabric_manager_running:bool|None
    fabric_manager_aligned:bool|None
    dcgm_version:str|None
    dcgm_compatible:bool|None
    warnings:tuple[str,...]
    def to_dict(self): return asdict(self)

def _run(command:list[str])->tuple[int,str]:
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=10,check=False)
        return result.returncode,(result.stdout+"\n"+result.stderr).strip()
    except OSError: return 127,""

def _mig_state()->tuple[bool|None,bool|None,tuple[str,...]]:
    smi=shutil.which("nvidia-smi")
    if not smi: return None,None,()
    rc,out=_run([smi,"-q","-d","MIG"])
    if rc!=0: return None,None,()
    capable="MIG Mode" in out
    enabled=bool(re.search(r"Current\s*:\s*Enabled",out,re.I)) if capable else False
    rc2,listing=_run([smi,"-L"])
    instances=tuple(line.strip() for line in listing.splitlines() if "MIG" in line) if rc2==0 else ()
    return capable,enabled,instances

def _fabric_version()->str|None:
    exe=shutil.which("nv-fabricmanager")
    if not exe: return None
    rc,out=_run([exe,"-v"])
    if rc!=0: return None
    match=re.search(r"(\d+\.\d+(?:\.\d+)?)",out); return match.group(1) if match else None

def _service_running()->bool|None:
    systemctl=shutil.which("systemctl")
    if not systemctl: return None
    rc,_=_run([systemctl,"is-active","--quiet","nvidia-fabricmanager.service"]); return rc==0

def _dcgm_version()->str|None:
    for command in (["dcgmi","--version"],["nv-hostengine","--version"]):
        if not shutil.which(command[0]): continue
        rc,out=_run(command)
        if rc==0:
            match=re.search(r"(\d+\.\d+(?:\.\d+)?)",out)
            if match: return match.group(1)
    return None

def _major_minor(version:str|None)->tuple[int,int]|None:
    if not version: return None
    try:
        parts=version.split("."); return int(parts[0]),int(parts[1]) if len(parts)>1 else 0
    except ValueError: return None

def mig_fabric_report()->MigFabricReport:
    driver=nvidia_smi_driver_version(); capable,enabled,instances=_mig_state(); fabric=_fabric_version(); service=_service_running(); dcgm=_dcgm_version()
    aligned=None if not driver or not fabric else fabric==driver
    dcgm_tuple=_major_minor(dcgm); dcgm_ok=None if dcgm_tuple is None else dcgm_tuple>=(4,3)
    warnings=[]
    if fabric and aligned is False: warnings.append(f"Fabric Manager {fabric} does not match NVIDIA driver {driver}")
    if service is False and fabric: warnings.append("Fabric Manager is installed but the service is not active")
    if dcgm and dcgm_ok is False: warnings.append("R610 requires DCGM 4.3.x or newer")
    if enabled and not instances: warnings.append("MIG mode is enabled but no MIG instances were listed")
    return MigFabricReport(driver,capable,enabled,instances,fabric,service,aligned,dcgm,dcgm_ok,tuple(warnings))
