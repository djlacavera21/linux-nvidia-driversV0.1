"""Read-only Kubernetes NVIDIA GPU Operator integration planning."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import shutil, subprocess
from .config import DriverConfig
from .system import read_os_release

GPU_OPERATOR_VERSION="v26.7.0"
K8S_MINORS=range(33,37)

@dataclass(frozen=True)
class GpuOperatorPlan:
    operator_version:str
    driver_version:str
    kubectl:str|None
    helm:str|None
    kubernetes_version:str|None
    supported_kubernetes:bool|None
    immutable_host:bool
    helm_command:tuple[str,...]
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def _k8s_version(kubectl:str|None)->str|None:
    if not kubectl: return None
    try:
        out=subprocess.run([kubectl,"version","--output=json"],capture_output=True,text=True,timeout=8,check=False).stdout
    except OSError: return None
    import json
    try: return json.loads(out).get("serverVersion",{}).get("gitVersion")
    except (ValueError,TypeError): return None

def _supported(version:str|None)->bool|None:
    if not version: return None
    import re
    m=re.search(r"v?1\.(\d+)",version)
    return int(m.group(1)) in K8S_MINORS if m else None

def gpu_operator_plan(config:DriverConfig, *, mig_strategy:str="none")->GpuOperatorPlan:
    kubectl=shutil.which("kubectl"); helm=shutil.which("helm"); version=_k8s_version(kubectl)
    distro=read_os_release().get("ID","").lower(); immutable=distro in {"rhcos","fedora-coreos","flatcar","bottlerocket","talos"}
    command=("helm","upgrade","--install","gpu-operator","nvidia/gpu-operator","--namespace","gpu-operator","--create-namespace",f"--version={GPU_OPERATOR_VERSION}",f"--set=driver.version={config.version}",f"--set=mig.strategy={mig_strategy}")
    notes=["GPU Operator 26.7 supports Kubernetes 1.33-1.36 on currently validated conventional platforms."]
    if immutable: notes.append("immutable hosts should prefer operator/container-managed GPU components instead of direct host package mutation")
    if distro=="rhcos": notes.append("RHCOS is NVIDIA-validated through Red Hat OpenShift; CRI-O is the validated runtime path")
    return GpuOperatorPlan(GPU_OPERATOR_VERSION,config.version,kubectl,helm,version,_supported(version),immutable,command,tuple(notes))
