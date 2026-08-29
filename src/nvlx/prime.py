"""Hybrid graphics and PRIME render-offload detection."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import shutil, subprocess
from .system import detect_nvidia_devices

@dataclass(frozen=True)
class PrimeReport:
    nvidia_gpu_count: int
    non_nvidia_display_gpu_count: int
    hybrid: bool
    xrandr_providers: tuple[str,...]
    nvidia_provider_present: bool
    render_offload_env: dict[str,str]
    notes: tuple[str,...]
    def to_dict(self): return asdict(self)

def _display_gpu_count(root: Path) -> int:
    count=0
    if not root.exists(): return 0
    for entry in root.iterdir():
        try:
            vendor=(entry/'vendor').read_text().strip().lower(); cls=(entry/'class').read_text().strip().lower()
        except OSError: continue
        if vendor!='0x10de' and cls.startswith('0x03'): count+=1
    return count

def _providers() -> tuple[str,...]:
    exe=shutil.which('xrandr')
    if not exe: return ()
    try: r=subprocess.run([exe,'--listproviders'],capture_output=True,text=True,timeout=5,check=False)
    except OSError: return ()
    return tuple(line.strip() for line in r.stdout.splitlines() if 'name:' in line)

def prime_report(sysfs_root: Path=Path('/sys/bus/pci/devices')) -> PrimeReport:
    nv=len(detect_nvidia_devices(sysfs_root)); integrated=_display_gpu_count(sysfs_root); providers=_providers(); hybrid=nv>0 and integrated>0
    return PrimeReport(nv,integrated,hybrid,providers,any('NVIDIA-G' in p or 'NVIDIA' in p for p in providers),{'__NV_PRIME_RENDER_OFFLOAD':'1','__GLX_VENDOR_LIBRARY_NAME':'nvidia'},('On muxless hybrid systems keep the integrated GPU as the display sink and use NVIDIA as the render-offload source.','For Vulkan/EGL __NV_PRIME_RENDER_OFFLOAD=1 is normally sufficient; GLX also uses __GLX_VENDOR_LIBRARY_NAME=nvidia.') if hybrid else ('No integrated+NVIDIA hybrid topology detected from PCI display functions.',))
