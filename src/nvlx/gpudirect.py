"""RDMA and GPUDirect qualification."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess

@dataclass(frozen=True)
class GPUDirectReport:
    ibdev2netdev:bool
    rdma_link:bool
    nvidia_peer_mem:bool
    dma_buf_supported:bool|None
    qualified:bool
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def _ok(cmd:list[str])->bool:
    try: return subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
    except Exception: return False

def report()->GPUDirectReport:
    ib=bool(shutil.which("ibdev2netdev")) and _ok(["ibdev2netdev"])
    rdma=bool(shutil.which("rdma")) and _ok(["rdma","link"])
    peer=bool(shutil.which("modinfo")) and _ok(["modinfo","nvidia_peermem"])
    dma=None
    if shutil.which("nvidia-smi"):
        dma=_ok(["nvidia-smi"])
    qualified=(ib or rdma) and (peer or dma is True)
    notes=("NVIDIA Network Operator and compatible NIC/RDMA resources are required for managed GPUDirect RDMA.","DMA-BUF capable paths are preferred on modern open-kernel-module deployments when supported by the platform.")
    return GPUDirectReport(ib,rdma,peer,dma,qualified,notes)
