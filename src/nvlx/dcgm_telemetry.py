"""Per-GPU ECC and Xid telemetry from NVIDIA tools and DCGM Exporter."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import re, shutil, subprocess, urllib.request

@dataclass(frozen=True)
class GpuReliability:
    index:str
    uuid:str
    pci_bus_id:str
    corrected_volatile:int|None
    uncorrected_volatile:int|None
    xid_last:int|None
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class DcgmExporterState:
    executable:str|None
    metrics_url:str
    reachable:bool
    xid_series:int
    ecc_series:int
    def to_dict(self): return asdict(self)

def _int(value:str)->int|None:
    value=value.strip()
    if value in {"N/A","[N/A]",""}: return None
    try: return int(float(value))
    except ValueError: return None

def _bus(value:str)->str:
    value=value.strip().lower()
    if re.match(r"^[0-9a-f]{8}:",value): value=value[4:]
    return value

def _kernel_xids()->dict[str,int]:
    journal=shutil.which("journalctl")
    if not journal: return {}
    try: text=subprocess.run([journal,"-k","-b","--no-pager"],capture_output=True,text=True,timeout=8,check=False).stdout
    except OSError: return {}
    out:dict[str,int]={}
    for line in text.splitlines():
        m=re.search(r"Xid \(PCI:([0-9A-Fa-f:.]+)\):\s*(\d+)",line)
        if m: out[_bus(m.group(1))]=int(m.group(2))
    return out

def reliability_rows()->tuple[GpuReliability,...]:
    smi=shutil.which("nvidia-smi")
    if not smi: return ()
    fields="index,uuid,pci.bus_id,ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total"
    try: r=subprocess.run([smi,f"--query-gpu={fields}","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=8,check=False)
    except OSError: return ()
    xids=_kernel_xids(); rows=[]
    for line in r.stdout.splitlines():
        parts=[p.strip() for p in line.split(",")]
        if len(parts)>=5:
            bus=_bus(parts[2]); rows.append(GpuReliability(parts[0],parts[1],bus,_int(parts[3]),_int(parts[4]),xids.get(bus)))
    return tuple(rows)

def exporter_state(url:str="http://127.0.0.1:9400/metrics")->DcgmExporterState:
    text=""; reachable=False
    try:
        with urllib.request.urlopen(url,timeout=2) as r: text=r.read().decode("utf-8","replace"); reachable=True
    except Exception: pass
    xid=sum(1 for line in text.splitlines() if line.startswith(("DCGM_FI_DEV_XID_ERRORS","DCGM_EXP_XID_ERRORS_TOTAL","DCGM_EXP_XID_ERRORS_COUNT")))
    ecc=sum(1 for line in text.splitlines() if line.startswith(("DCGM_FI_DEV_ECC_","DCGM_FI_DEV_RETIRED_")))
    return DcgmExporterState(shutil.which("dcgm-exporter"),url,reachable,xid,ecc)
