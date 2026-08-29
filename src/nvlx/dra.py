"""NVIDIA GPU DRA/CDI cluster qualification."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, subprocess

@dataclass(frozen=True)
class DraReport:
    mode:str; valid:bool; gpucluster:bool; clusterpolicy:bool; compute_domains:int; alpha_features:tuple[str,...]; reasons:tuple[str,...]
    def to_dict(self): return asdict(self)

def _get(resource:str)->dict:
    p=subprocess.run(["kubectl","get",resource,"-o","json"],capture_output=True,text=True,timeout=15)
    if p.returncode: return {"items":[]}
    try: return json.loads(p.stdout)
    except json.JSONDecodeError: return {"items":[]}

def validate()->DraReport:
    gc=_get("gpuclusters.nvidia.com").get("items",[]); cp=_get("clusterpolicies.nvidia.com").get("items",[])
    cd=_get("computedomains.resource.nvidia.com").get("items",[])
    reasons=[]; mode="dra" if gc else "device-plugin" if cp else "unmanaged"
    if gc and cp: reasons.append("GPUCluster and ClusterPolicy must not coexist")
    alpha=[]
    if gc:
        gates=gc[0].get("spec",{}).get("draDriver",{}).get("featureGates",{}) or {}
        alpha=[k for k,v in gates.items() if v and k in {"ConsumableShares","DeviceMetadata","DynamicMIG","MPSSupport","NVMLDeviceHealthCheck","PassthroughSupport","TimeSlicingSettings"}]
        if alpha: reasons.append("alpha DRA feature gates enabled: "+", ".join(sorted(alpha)))
    return DraReport(mode,not (gc and cp),bool(gc),bool(cp),len(cd),tuple(sorted(alpha)),tuple(reasons))
