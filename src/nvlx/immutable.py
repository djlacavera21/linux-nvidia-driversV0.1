"""Immutable/container-host NVIDIA deployment strategy detection."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from .system import read_os_release

@dataclass(frozen=True)
class ImmutablePlan:
    distribution_id:str
    immutable:bool
    nvidia_validated:bool
    strategy:str
    commands:tuple[str,...]
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def immutable_plan(os_release:dict[str,str]|None=None)->ImmutablePlan:
    data=os_release or read_os_release(); distro=data.get("ID","unknown").lower()
    if distro=="rhcos":
        return ImmutablePlan(distro,True,True,"OpenShift GPU Operator",(),("Use Red Hat OpenShift + NVIDIA GPU Operator; do not mutate the ostree host with nvlx direct install.",))
    if distro in {"fedora-coreos","flatcar","bottlerocket","talos","cos"}:
        return ImmutablePlan(distro,True,False,"container/operator-managed driver",(),("No NVIDIA validation claim is made for this host by nvlx; prefer a platform-supported GPU operator/extension path and keep the base image immutable.",))
    return ImmutablePlan(distro,False,False,"conventional host",(),("Use distro/native nvlx planning; immutable-host restrictions do not apply.",))
