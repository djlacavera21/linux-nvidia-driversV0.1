"""v1 production compatibility and migration preflight."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re

@dataclass(frozen=True)
class CompatibilityReport:
    compatible: bool
    kubernetes_version: str
    dra_stable: bool
    allocation_mode: str
    computedomains_crd_ready: bool
    migration_supported: bool
    errors: tuple[str,...]
    warnings: tuple[str,...]
    def to_dict(self): return asdict(self)

def _minor(version: str) -> int:
    m=re.search(r"v?1\.(\d+)",version or "")
    return int(m.group(1)) if m else 0

def check(*, kubernetes_version: str, has_gpucluster: bool, has_clusterpolicy: bool, computedomains_crd_ready: bool, migrating_clusterpolicy_to_gpucluster: bool=False) -> CompatibilityReport:
    errors=[]; warnings=[]; minor=_minor(kubernetes_version)
    dra_stable=minor >= 34
    if minor and minor < 34: errors.append("Kubernetes <1.34 does not meet the v1 stable DRA baseline")
    if not minor: warnings.append("Kubernetes version could not be parsed")
    if has_gpucluster and has_clusterpolicy: errors.append("GPUCluster and ClusterPolicy cannot coexist")
    mode="dra" if has_gpucluster else "device-plugin" if has_clusterpolicy else "unmanaged"
    migration_supported=not migrating_clusterpolicy_to_gpucluster
    if migrating_clusterpolicy_to_gpucluster: errors.append("in-place ClusterPolicy to GPUCluster migration is not supported by GPU Operator")
    if has_gpucluster and not computedomains_crd_ready: errors.append("ComputeDomain CRDs must be verified/applied before GPUCluster upgrade")
    return CompatibilityReport(not errors,kubernetes_version,dra_stable,mode,computedomains_crd_ready,migration_supported,tuple(errors),tuple(warnings))
