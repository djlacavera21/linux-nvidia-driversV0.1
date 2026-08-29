"""NVSDM and NVSwitch monitoring readiness for Blackwell-class systems."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess
from .system import nvidia_smi_driver_version

@dataclass(frozen=True)
class NvsdmReport:
    driver_version:str|None
    required_package:str|None
    package_installed:bool|None
    cli:str|None
    dcgmi:str|None
    nvswitch_discovered:bool|None
    aligned:bool|None
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def _package_present(name:str)->bool|None:
    if shutil.which("dpkg-query"):
        return subprocess.run(["dpkg-query","-W","-f=${Status}",name],capture_output=True,text=True,check=False).returncode==0
    if shutil.which("rpm"):
        return subprocess.run(["rpm","-q",name],capture_output=True,text=True,check=False).returncode==0
    return None

def nvsdm_report()->NvsdmReport:
    driver=nvidia_smi_driver_version(); branch=driver.split(".",1)[0] if driver and "," not in driver else None
    package=f"libnvsdm-{branch}" if branch else None; present=_package_present(package) if package else None
    dcgmi=shutil.which("dcgmi"); discovered=None
    if dcgmi:
        try:
            out=subprocess.run([dcgmi,"discovery","--list"],capture_output=True,text=True,timeout=8,check=False).stdout.lower()
            discovered="switch" in out or "nvswitch" in out
        except OSError: discovered=None
    notes=["NVSDM is NVIDIA's Blackwell NVSwitch monitoring library; nvsdm_cli remains experimental."]
    if package and present is False: notes.append(f"install the driver-major-aligned {package} package before relying on NVSDM telemetry")
    return NvsdmReport(driver,package,present,shutil.which("nvsdm_cli"),dcgmi,discovered,present if package else None,tuple(notes))
