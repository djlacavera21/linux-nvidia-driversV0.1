"""NVIDIA inventory snapshot continuity fencing for nvlx 1.6.3.2."""
from __future__ import annotations

from dataclasses import dataclass

from .nvidia_inventory_v163 import NvidiaSnapshot
from .nvidia_inventory_v1631 import NvidiaInventoryError


@dataclass(frozen=True)
class SnapshotIdentity:
    api_versions: tuple[tuple[str, str], ...]
    available_resources: tuple[tuple[str, tuple[str, ...]], ...]
    gpuclusters: tuple[tuple[str, str, str], ...]
    clusterpolicies: tuple[tuple[str, str, str], ...]
    drivers: tuple[tuple[str, str, str], ...]
    computedomains: tuple[tuple[str, str, str], ...]
    computedomaincliques: tuple[tuple[str, str, str], ...]
    gpu_nodes: tuple[tuple[str, str, str], ...]


def _object_identity(obj: object, label: str, *, default_api: str = "") -> tuple[str, str, str]:
    if not isinstance(obj, dict):
        raise NvidiaInventoryError(f"{label} continuity object must be an object")
    meta = obj.get("metadata")
    if not isinstance(meta, dict):
        raise NvidiaInventoryError(f"{label} continuity metadata must be an object")
    name = meta.get("name")
    uid = meta.get("uid")
    api = obj.get("apiVersion", default_api)
    if not isinstance(name, str) or not name.strip():
        raise NvidiaInventoryError(f"{label} continuity name is missing")
    if not isinstance(uid, str) or not uid.strip():
        raise NvidiaInventoryError(f"{label} continuity requires metadata.uid")
    if not isinstance(api, str) or not api.strip():
        raise NvidiaInventoryError(f"{label} continuity requires apiVersion")
    return name.strip(), uid.strip(), api.strip()


def snapshot_identity(snapshot: NvidiaSnapshot) -> SnapshotIdentity:
    if not isinstance(snapshot, NvidiaSnapshot):
        raise NvidiaInventoryError("NVIDIA continuity requires a normalized snapshot")

    def identities(objects: tuple[dict, ...], label: str) -> tuple[tuple[str, str, str], ...]:
        values = [_object_identity(obj, label) for obj in objects]
        if len(values) != len(set(values)):
            raise NvidiaInventoryError(f"{label} continuity contains duplicate identities")
        return tuple(sorted(values))

    node_values = [_object_identity(obj, "GPU Node", default_api="v1") for obj in snapshot.gpu_nodes]
    if len(node_values) != len(set(node_values)):
        raise NvidiaInventoryError("GPU Node continuity contains duplicate identities")

    api_versions = tuple(sorted(snapshot.api_versions))
    if len(api_versions) != len(set(api_versions)):
        raise NvidiaInventoryError("NVIDIA continuity contains duplicate API versions")

    normalized_resources: list[tuple[str, tuple[str, ...]]] = []
    seen_groups: set[str] = set()
    for group, resources in snapshot.available_resources:
        if not isinstance(group, str) or not group or group in seen_groups:
            raise NvidiaInventoryError("NVIDIA continuity contains invalid resource group identity")
        if not isinstance(resources, tuple) or any(not isinstance(value, str) or not value for value in resources):
            raise NvidiaInventoryError(f"{group} continuity resources are invalid")
        seen_groups.add(group)
        normalized_resources.append((group, tuple(sorted(set(resources)))))

    return SnapshotIdentity(
        api_versions=api_versions,
        available_resources=tuple(sorted(normalized_resources)),
        gpuclusters=identities(snapshot.gpuclusters, "GPUCluster"),
        clusterpolicies=identities(snapshot.clusterpolicies, "ClusterPolicy"),
        drivers=identities(snapshot.drivers, "NVIDIADriver"),
        computedomains=identities(snapshot.computedomains, "ComputeDomain"),
        computedomaincliques=identities(snapshot.computedomaincliques, "ComputeDomainClique"),
        gpu_nodes=tuple(sorted(node_values)),
    )


def changed_sections(old: SnapshotIdentity, new: SnapshotIdentity) -> tuple[str, ...]:
    names = (
        "api_versions", "available_resources", "gpuclusters", "clusterpolicies", "drivers",
        "computedomains", "computedomaincliques", "gpu_nodes",
    )
    return tuple(name for name in names if getattr(old, name) != getattr(new, name))
