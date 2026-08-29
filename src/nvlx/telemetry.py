"""JSON and Prometheus health telemetry for nvlx."""
from __future__ import annotations
from dataclasses import asdict
import json, time
from .dcgm_telemetry import exporter_state, reliability_rows
from .health import health_report
from .mig import mig_fabric_report
from .nvsdm import nvsdm_report
from .topology import topology_report

def json_health()->dict[str,object]:
    health=health_report(); topo=topology_report(); mig=mig_fabric_report(); exporter=exporter_state(); nvsdm=nvsdm_report()
    return {"schema":2,"timestamp":int(time.time()),"health":asdict(health),"topology":asdict(topo),"mig_fabric":asdict(mig),"gpu_reliability":[asdict(x) for x in reliability_rows()],"dcgm_exporter":asdict(exporter),"nvsdm":asdict(nvsdm)}

def json_text()->str: return json.dumps(json_health(),indent=2,sort_keys=True)+"\n"

def _gauge(name:str,value:float,help_text:str,labels:str="")->str:
    label_block=f"{{{labels}}}" if labels else ""
    return f"# HELP {name} {help_text}\n# TYPE {name} gauge\n{name}{label_block} {value}\n"

def prometheus_text()->str:
    h=health_report(); t=topology_report(); m=mig_fabric_report(); exp=exporter_state(); nv=nvsdm_report(); rows=reliability_rows(); chunks=[]
    chunks.append(_gauge("nvlx_health_ok",1 if h.healthy else 0,"Overall NVIDIA driver health"))
    chunks.append(_gauge("nvlx_gpu_count",h.gpu_count,"Detected NVIDIA GPU count"))
    chunks.append(_gauge("nvlx_nvidia_module_loaded",1 if h.nvidia_module_loaded else 0,"Whether the core NVIDIA kernel module is loaded"))
    chunks.append(_gauge("nvlx_nvidia_smi_ok",1 if h.nvidia_smi_ok else 0,"Whether nvidia-smi can enumerate GPUs"))
    chunks.append(_gauge("nvlx_topology_available",1 if t.available else 0,"Whether nvidia-smi topology data is available"))
    chunks.append(_gauge("nvlx_nvlink_edges",t.nvlink_edges,"Parsed NVLink adjacency count"))
    chunks.append(_gauge("nvlx_nvswitch_evidence",1 if t.nvswitch_evidence else 0,"Whether NVSwitch evidence was detected"))
    chunks.append(_gauge("nvlx_mig_instances",len(m.mig_instances),"Detected MIG instance count"))
    chunks.append(_gauge("nvlx_dcgm_exporter_reachable",1 if exp.reachable else 0,"Whether DCGM Exporter metrics endpoint is reachable"))
    chunks.append(_gauge("nvlx_dcgm_exporter_xid_series",exp.xid_series,"Detected Xid metric series at DCGM Exporter"))
    chunks.append(_gauge("nvlx_dcgm_exporter_ecc_series",exp.ecc_series,"Detected ECC metric series at DCGM Exporter"))
    if nv.aligned is not None: chunks.append(_gauge("nvlx_nvsdm_aligned",1 if nv.aligned else 0,"Whether NVSDM package is aligned with driver major"))
    for r in rows:
        labels=f'gpu="{r.index}",uuid="{r.uuid}"'
        if r.corrected_volatile is not None: chunks.append(_gauge("nvlx_gpu_ecc_corrected_volatile",r.corrected_volatile,"Volatile corrected ECC errors",labels))
        if r.uncorrected_volatile is not None: chunks.append(_gauge("nvlx_gpu_ecc_uncorrected_volatile",r.uncorrected_volatile,"Volatile uncorrected ECC errors",labels))
        if r.xid_last is not None: chunks.append(_gauge("nvlx_gpu_last_xid",r.xid_last,"Last Xid observed this boot for GPU",labels))
    if m.fabric_manager_running is not None: chunks.append(_gauge("nvlx_fabric_manager_running",1 if m.fabric_manager_running else 0,"Whether NVIDIA Fabric Manager service is active"))
    if m.fabric_manager_aligned is not None: chunks.append(_gauge("nvlx_fabric_manager_aligned",1 if m.fabric_manager_aligned else 0,"Whether Fabric Manager version matches driver"))
    if m.dcgm_compatible is not None: chunks.append(_gauge("nvlx_dcgm_compatible",1 if m.dcgm_compatible else 0,"Whether DCGM meets driver compatibility"))
    return "".join(chunks)
