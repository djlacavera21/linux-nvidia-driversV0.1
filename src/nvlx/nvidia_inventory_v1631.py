"""Inventory identity and discovery-contract hardening for nvlx 1.6.3.1."""
from __future__ import annotations

from .nvidia_inventory_v163 import (
    NvidiaInventory as NvidiaInventoryV163,
    NvidiaInventoryError,
    NvidiaPreflight,
    NvidiaSnapshot,
)


class NvidiaInventory(NvidiaInventoryV163):
    """Require coherent discovery metadata and object API identities."""

    def _discover_group(self, group: str, *, optional: bool):
        result = super()._discover_group(group, optional=optional)
        if result is None:
            return None
        resource_versions, resources = result
        for plural, version in resource_versions.items():
            response = self.client.request_json("GET", f"/apis/{group}/{version}")
            body = response.body
            if not isinstance(body, dict):
                raise NvidiaInventoryError(f"{group}/{version} resource discovery must be an object")
            gv = body.get("groupVersion")
            if gv is not None and gv != f"{group}/{version}":
                raise NvidiaInventoryError(f"{group}/{version} discovery groupVersion mismatch")
            discovered = body.get("resources")
            if not isinstance(discovered, list):
                raise NvidiaInventoryError(f"{group}/{version} resources must be a list")
            match = next((entry for entry in discovered if isinstance(entry, dict) and entry.get("name") == plural), None)
            if match is None:
                raise NvidiaInventoryError(f"{plural}.{group} disappeared during discovery")
            namespaced = match.get("namespaced")
            if namespaced is True:
                raise NvidiaInventoryError(f"{plural}.{group} must be cluster scoped")
        return resource_versions, resources

    def _list_discovered(self, group: str, resource_versions: dict[str, str], plural: str):
        items = super()._list_discovered(group, resource_versions, plural)
        version = resource_versions.get(plural)
        if version is None:
            return items
        expected_api = f"{group}/{version}"
        for item in items:
            api_version = item.get("apiVersion")
            if api_version is not None and api_version != expected_api:
                raise NvidiaInventoryError(f"{plural}.{group} object apiVersion mismatch")
            kind = item.get("kind")
            if kind is not None and (not isinstance(kind, str) or not kind.strip()):
                raise NvidiaInventoryError(f"{plural}.{group} object kind is invalid")
            meta = item.get("metadata")
            if not isinstance(meta, dict):
                raise NvidiaInventoryError(f"{plural}.{group} object metadata must be an object")
            namespace = meta.get("namespace")
            if namespace not in (None, ""):
                raise NvidiaInventoryError(f"{plural}.{group} object must be cluster scoped")
            uid = meta.get("uid")
            if uid is not None and (not isinstance(uid, str) or not uid.strip()):
                raise NvidiaInventoryError(f"{plural}.{group} object uid is invalid")
            rv = meta.get("resourceVersion")
            if rv is not None and (not isinstance(rv, str) or not rv.strip()):
                raise NvidiaInventoryError(f"{plural}.{group} object resourceVersion is invalid")
        return items

    def snapshot(self) -> NvidiaSnapshot:
        snapshot = super().snapshot()
        for node in snapshot.gpu_nodes:
            api_version = node.get("apiVersion")
            if api_version is not None and api_version != "v1":
                raise NvidiaInventoryError("node apiVersion mismatch")
            kind = node.get("kind")
            if kind is not None and kind != "Node":
                raise NvidiaInventoryError("GPU node kind mismatch")
            meta = node.get("metadata")
            if not isinstance(meta, dict):
                raise NvidiaInventoryError("GPU node metadata must be an object")
            if meta.get("namespace") not in (None, ""):
                raise NvidiaInventoryError("GPU node must be cluster scoped")
        return snapshot


__all__ = ["NvidiaInventory", "NvidiaInventoryError", "NvidiaPreflight", "NvidiaSnapshot"]
