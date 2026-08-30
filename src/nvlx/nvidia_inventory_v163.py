"""Live read-only NVIDIA Kubernetes inventory and preflight for nvlx 1.6.3."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .k8s_api_v16 import ApiError, KubeClient


@dataclass(frozen=True)
class NvidiaSnapshot:
    gpuclusters: tuple[dict, ...]
    clusterpolicies: tuple[dict, ...]
    drivers: tuple[dict, ...]
    computedomains: tuple[dict, ...]
    computedomaincliques: tuple[dict, ...]
    gpu_nodes: tuple[dict, ...]
    api_versions: tuple[tuple[str, str], ...]
    available_resources: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class NvidiaPreflight:
    ready: bool
    mode: str
    reasons: tuple[str, ...]
    snapshot: NvidiaSnapshot


class NvidiaInventoryError(RuntimeError):
    """Fail-closed inventory/discovery error."""


def _metadata_name(obj: object) -> str:
    if not isinstance(obj, dict):
        return ""
    meta = obj.get("metadata")
    if not isinstance(meta, dict):
        return ""
    name = meta.get("name")
    return name if isinstance(name, str) else ""


def _state(obj: object) -> str:
    if not isinstance(obj, dict):
        return ""
    status = obj.get("status")
    if not isinstance(status, dict):
        return ""
    value = status.get("state", status.get("status", ""))
    return value.strip().lower() if isinstance(value, str) else ""


def _items(body: object, label: str) -> tuple[dict, ...]:
    if not isinstance(body, dict):
        raise NvidiaInventoryError(f"{label} list body must be an object")
    items = body.get("items")
    if not isinstance(items, list):
        raise NvidiaInventoryError(f"{label} list items must be a list")
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict) or not _metadata_name(item):
            raise NvidiaInventoryError(f"{label} contains malformed object identity")
        out.append(item)
    return tuple(out)


class NvidiaInventory:
    """Discover served NVIDIA APIs and build a read-only normalized snapshot."""

    def __init__(self, client: KubeClient):
        self.client = client

    def _discover_group(self, group: str, *, optional: bool) -> tuple[str, tuple[str, ...]] | None:
        try:
            response = self.client.request_json("GET", f"/apis/{group}")
        except ApiError as exc:
            if optional and exc.status == 404:
                return None
            raise NvidiaInventoryError(f"cannot discover {group}: {exc}") from None
        body = response.body
        if not isinstance(body, dict):
            raise NvidiaInventoryError(f"{group} discovery body must be an object")
        preferred = body.get("preferredVersion")
        group_version = preferred.get("groupVersion") if isinstance(preferred, dict) else None
        if not isinstance(group_version, str) or not group_version.startswith(group + "/"):
            versions = body.get("versions")
            group_version = None
            if isinstance(versions, list):
                for entry in versions:
                    if isinstance(entry, dict):
                        candidate = entry.get("groupVersion")
                        if isinstance(candidate, str) and candidate.startswith(group + "/"):
                            group_version = candidate
                            break
        if not group_version:
            raise NvidiaInventoryError(f"{group} discovery has no served version")
        version = group_version.split("/", 1)[1]
        try:
            resources_response = self.client.request_json("GET", f"/apis/{group}/{version}")
        except ApiError as exc:
            raise NvidiaInventoryError(f"cannot discover {group}/{version} resources: {exc}") from None
        resources_body = resources_response.body
        if not isinstance(resources_body, dict):
            raise NvidiaInventoryError(f"{group}/{version} resource discovery must be an object")
        resources = resources_body.get("resources")
        if not isinstance(resources, list):
            raise NvidiaInventoryError(f"{group}/{version} resources must be a list")
        names: list[str] = []
        for entry in resources:
            if not isinstance(entry, dict):
                raise NvidiaInventoryError(f"{group}/{version} contains malformed resource discovery")
            name = entry.get("name")
            if isinstance(name, str) and name and "/" not in name:
                names.append(name)
        return version, tuple(sorted(set(names)))

    def _list_discovered(
        self,
        group: str,
        version: str,
        resources: tuple[str, ...],
        plural: str,
        *,
        optional_resource: bool = True,
    ) -> tuple[dict, ...]:
        if plural not in resources:
            if optional_resource:
                return ()
            raise NvidiaInventoryError(f"required resource {plural}.{group} is not served")
        try:
            response = self.client.request_json("GET", f"/apis/{group}/{version}/{plural}")
        except ApiError as exc:
            raise NvidiaInventoryError(f"cannot list {plural}.{group}: {exc}") from None
        return _items(response.body, f"{plural}.{group}")

    def snapshot(self) -> NvidiaSnapshot:
        nvidia = self._discover_group("nvidia.com", optional=True)
        resource_nvidia = self._discover_group("resource.nvidia.com", optional=True)
        api_versions: list[tuple[str, str]] = []
        available: list[tuple[str, tuple[str, ...]]] = []

        gpuclusters: tuple[dict, ...] = ()
        clusterpolicies: tuple[dict, ...] = ()
        drivers: tuple[dict, ...] = ()
        if nvidia is not None:
            version, resources = nvidia
            api_versions.append(("nvidia.com", version))
            available.append(("nvidia.com", resources))
            gpuclusters = self._list_discovered("nvidia.com", version, resources, "gpuclusters")
            clusterpolicies = self._list_discovered("nvidia.com", version, resources, "clusterpolicies")
            drivers = self._list_discovered("nvidia.com", version, resources, "nvidiadrivers")

        computedomains: tuple[dict, ...] = ()
        cliques: tuple[dict, ...] = ()
        if resource_nvidia is not None:
            version, resources = resource_nvidia
            api_versions.append(("resource.nvidia.com", version))
            available.append(("resource.nvidia.com", resources))
            computedomains = self._list_discovered("resource.nvidia.com", version, resources, "computedomains")
            cliques = self._list_discovered("resource.nvidia.com", version, resources, "computedomaincliques")

        try:
            nodes_response = self.client.request_json("GET", "/api/v1/nodes")
        except ApiError as exc:
            raise NvidiaInventoryError(f"cannot list Kubernetes nodes: {exc}") from None
        nodes = _items(nodes_response.body, "nodes")
        gpu_nodes: list[dict] = []
        for node in nodes:
            labels = node.get("metadata", {}).get("labels", {})
            if isinstance(labels, dict) and labels.get("nvidia.com/gpu.present") == "true":
                gpu_nodes.append(node)

        return NvidiaSnapshot(
            gpuclusters=gpuclusters,
            clusterpolicies=clusterpolicies,
            drivers=drivers,
            computedomains=computedomains,
            computedomaincliques=cliques,
            gpu_nodes=tuple(gpu_nodes),
            api_versions=tuple(api_versions),
            available_resources=tuple(available),
        )

    @staticmethod
    def evaluate(snapshot: NvidiaSnapshot) -> NvidiaPreflight:
        reasons: list[str] = []
        gpuclusters = snapshot.gpuclusters
        policies = snapshot.clusterpolicies
        drivers = snapshot.drivers

        if len(gpuclusters) > 1:
            reasons.append("more than one GPUCluster exists")
        if len(policies) > 1:
            reasons.append("more than one ClusterPolicy exists")
        if gpuclusters and policies:
            reasons.append("GPUCluster and ClusterPolicy cannot coexist")

        mode = "unmanaged"
        if gpuclusters:
            mode = "dra"
            if len(gpuclusters) == 1 and _metadata_name(gpuclusters[0]) != "gpu-cluster":
                reasons.append("GPUCluster singleton must be named gpu-cluster")
        elif policies:
            mode = "device-plugin"
        elif snapshot.gpu_nodes:
            reasons.append("GPU nodes are present without GPUCluster or ClusterPolicy")
        else:
            mode = "no-gpu"

        for kind, objects in (("GPUCluster", gpuclusters), ("ClusterPolicy", policies)):
            for obj in objects:
                state = _state(obj)
                if state and state != "ready":
                    reasons.append(f"{kind} {_metadata_name(obj)} reports {state}")

        defaults = [obj for obj in drivers if bool((obj.get("spec") or {}).get("default"))]
        if len(defaults) > 1:
            reasons.append("more than one default NVIDIADriver exists")
        for driver in drivers:
            state = _state(driver)
            if state and state != "ready":
                reasons.append(f"NVIDIADriver {_metadata_name(driver)} reports {state}")

        if mode == "dra":
            resources = dict(snapshot.available_resources).get("resource.nvidia.com", ())
            if "computedomains" not in resources:
                # ComputeDomain can be disabled, so absence is recorded only when
                # GPUCluster explicitly enables it. The managed 26.7 default is
                # enabled, but a user may opt out.
                spec = gpuclusters[0].get("spec") if len(gpuclusters) == 1 else {}
                dra = spec.get("draDriver") if isinstance(spec, dict) else {}
                compute = dra.get("computeDomains") if isinstance(dra, dict) else {}
                enabled = compute.get("enabled") if isinstance(compute, dict) else None
                if enabled is True:
                    reasons.append("GPUCluster enables ComputeDomains but resource.nvidia.com/computedomains is not served")

        return NvidiaPreflight(
            ready=not reasons,
            mode=mode,
            reasons=tuple(reasons),
            snapshot=snapshot,
        )

    def check(self) -> NvidiaPreflight:
        return self.evaluate(self.snapshot())
