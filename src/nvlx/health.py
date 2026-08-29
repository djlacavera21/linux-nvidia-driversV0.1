"""NVIDIA driver boot/runtime health validation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess
from .config import load_driver_config
from .mig import mig_fabric_report
from .secureboot import verify_installed_modules
from .session import session_report
from .system import detect_nvidia_devices, loaded_modules, nvidia_smi_driver_version
from .topology import topology_report

@dataclass(frozen=True)
class HealthReport:
    healthy:bool
    driver_version:str|None
    expected_version:str
    gpu_count:int
    nvidia_module_loaded:bool
    nvidia_smi_ok:bool
    signatures_ok:bool|None
    session_warnings:int
    topology_available:bool
    mig_fabric_warnings:int
    errors:tuple[str,...]
    def to_dict(self): return asdict(self)

def _smi_ok()->bool:
    exe=shutil.which("nvidia-smi")
    if not exe: return False
    try: return subprocess.run([exe,"-L"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False).returncode==0
    except OSError: return False

def health_report(*, require_expected_version:bool=True)->HealthReport:
    config=load_driver_config(); version=nvidia_smi_driver_version(); gpu_count=len(detect_nvidia_devices()); modules=loaded_modules(); smi_ok=_smi_ok()
    signatures=verify_installed_modules(); signatures_ok=None if not signatures else all(item.signed for item in signatures)
    session=session_report(); topology=topology_report(); fabric=mig_fabric_report(); errors=[]
    if gpu_count and "nvidia" not in modules: errors.append("NVIDIA PCI device detected but nvidia module is not loaded")
    if gpu_count and not smi_ok: errors.append("nvidia-smi cannot enumerate GPUs")
    if require_expected_version and version and version!=config.version: errors.append(f"driver version {version} does not match configured {config.version}")
    if require_expected_version and gpu_count and version is None: errors.append("driver version could not be determined")
    if signatures_ok is False: errors.append("one or more installed NVIDIA modules are unsigned")
    if fabric.fabric_manager_aligned is False: errors.append("Fabric Manager version does not match the NVIDIA driver")
    return HealthReport(not errors,version,config.version,gpu_count,"nvidia" in modules,smi_ok,signatures_ok,len(session.warnings),topology.available,len(fabric.warnings),tuple(errors))
