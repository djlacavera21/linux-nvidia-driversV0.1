"""DRA-native placement plan generation."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class PlacementPlan:
    device_class:str
    count:int
    selectors:tuple[str,...]
    compute_domain:str|None
    manifest:str
    def to_dict(self): return asdict(self)

def plan(*, count:int=1, product:str|None=None, min_memory_gib:int|None=None, compute_domain:str|None=None)->PlacementPlan:
    if count < 1: raise ValueError("count must be >= 1")
    selectors=[]
    if product: selectors.append(f"device.attributes['gpu.nvidia.com'].product == '{product}'")
    if min_memory_gib is not None:
        if min_memory_gib < 1: raise ValueError("min_memory_gib must be >= 1")
        selectors.append(f"device.attributes['gpu.nvidia.com'].memoryGiB >= {min_memory_gib}")
    name="nvlx-gpu-claim"
    lines=["apiVersion: resource.k8s.io/v1", "kind: ResourceClaim", "metadata:", f"  name: {name}", "spec:", "  devices:", "    requests:", "    - name: gpu", "      exactly:", "        deviceClassName: gpu.nvidia.com", f"        count: {count}"]
    if selectors:
        lines += ["        selectors:"] + [f"        - cel:\n            expression: \"{s}\"" for s in selectors]
    if compute_domain: lines += ["---", "# ComputeDomain affinity requested by nvlx", f"# computeDomain: {compute_domain}"]
    return PlacementPlan("gpu.nvidia.com",count,tuple(selectors),compute_domain,"\n".join(lines)+"\n")
