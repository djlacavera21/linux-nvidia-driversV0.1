"""GPU Direct Storage / cuFile readiness and checkpoint-target qualification."""
from __future__ import annotations
from dataclasses import asdict,dataclass
import shutil,subprocess

@dataclass(frozen=True)
class GdsReport:
    cufile_binary:bool
    nvidia_fs_loaded:bool
    mount_count:int
    checkpoint_ready:bool
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def inspect()->GdsReport:
    binary=bool(shutil.which("cufile_sample_001") or shutil.which("gdscheck"))
    modules=subprocess.run(["sh","-c","grep -q '^nvidia_fs ' /proc/modules"],capture_output=True).returncode==0
    mounts=[]
    try:
        mounts=[x for x in open('/proc/mounts',encoding='utf-8').read().splitlines() if any(fs in x for fs in ('nfs','lustre','weka','beegfs','xfs','ext4'))]
    except OSError: pass
    notes=[]
    if not binary: notes.append("cuFile/GDS validation utility not found")
    if not modules: notes.append("nvidia_fs module not loaded; modern DMA-BUF paths may differ by platform")
    ready=bool(mounts) and binary
    return GdsReport(binary,modules,len(mounts),ready,tuple(notes))
