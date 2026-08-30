"""Lease-backed NVIDIA continuity checkpoint for nvlx 1.6.3.3."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from urllib import parse

from .k8s_api_v16 import ApiError
from .nvidia_continuity_v1632 import SnapshotIdentity
from .nvidia_inventory_v1631 import NvidiaInventoryError

ANNOTATION = "nvlx.io/nvidia-continuity-v1"


def _identity_from(value: object) -> SnapshotIdentity | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint identity must be an object")
    fields = (
        "api_versions", "available_resources", "gpuclusters", "clusterpolicies", "drivers",
        "computedomains", "computedomaincliques", "gpu_nodes",
    )
    if set(value) != set(fields):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint identity fields are invalid")
    try:
        api_versions = tuple(tuple(x) for x in value["api_versions"])
        available_resources = tuple((x[0], tuple(x[1])) for x in value["available_resources"])
        collections = {
            name: tuple(tuple(x) for x in value[name])
            for name in ("gpuclusters", "clusterpolicies", "drivers", "computedomains", "computedomaincliques", "gpu_nodes")
        }
    except (TypeError, ValueError, IndexError):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint identity is malformed") from None
    identity = SnapshotIdentity(
        api_versions=api_versions,
        available_resources=available_resources,
        gpuclusters=collections["gpuclusters"],
        clusterpolicies=collections["clusterpolicies"],
        drivers=collections["drivers"],
        computedomains=collections["computedomains"],
        computedomaincliques=collections["computedomaincliques"],
        gpu_nodes=collections["gpu_nodes"],
    )
    for group, version in identity.api_versions:
        if not isinstance(group, str) or not group or not isinstance(version, str) or not version:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint API identity is invalid")
    for group, resources in identity.available_resources:
        if not isinstance(group, str) or not group or any(not isinstance(x, str) or not x for x in resources):
            raise NvidiaInventoryError("NVIDIA continuity checkpoint resource identity is invalid")
    for collection in (identity.gpuclusters, identity.clusterpolicies, identity.drivers, identity.computedomains, identity.computedomaincliques, identity.gpu_nodes):
        for item in collection:
            if len(item) != 3 or any(not isinstance(x, str) or not x for x in item):
                raise NvidiaInventoryError("NVIDIA continuity checkpoint object identity is invalid")
    return identity


def _payload(baseline: SnapshotIdentity | None, candidate: SnapshotIdentity | None) -> dict:
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity candidate cannot exist without a baseline")
    return {
        "baseline": asdict(baseline) if baseline is not None else None,
        "candidate": asdict(candidate) if candidate is not None else None,
    }


def encode_checkpoint(baseline: SnapshotIdentity | None, candidate: SnapshotIdentity | None) -> str:
    payload = _payload(baseline, candidate)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return json.dumps({"version": 1, "sha256": digest, "payload": payload}, sort_keys=True, separators=(",", ":"))


def decode_checkpoint(raw: object) -> tuple[SnapshotIdentity | None, SnapshotIdentity | None]:
    if not isinstance(raw, str) or not raw:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint annotation is invalid")
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint is not valid JSON") from None
    if not isinstance(envelope, dict) or envelope.get("version") != 1:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint version is unsupported")
    payload = envelope.get("payload")
    digest = envelope.get("sha256")
    if not isinstance(payload, dict) or not isinstance(digest, str):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint envelope is malformed")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if digest != expected:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint integrity mismatch")
    if set(payload) != {"baseline", "candidate"}:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint payload is malformed")
    baseline = _identity_from(payload.get("baseline"))
    candidate = _identity_from(payload.get("candidate"))
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint candidate lacks baseline")
    return baseline, candidate


class LeaseCheckpointStore:
    """Persist continuity state in the existing controller Lease annotation."""

    def __init__(self, client, identity: str, *, namespace: str = "nvlx-system", lease_name: str = "nvlx-controller"):
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("identity required")
        self.client = client
        self.identity = identity.strip()
        self.namespace = namespace
        self.lease_name = lease_name

    @property
    def path(self) -> str:
        return f"/apis/coordination.k8s.io/v1/namespaces/{parse.quote(self.namespace,safe='')}/leases/{parse.quote(self.lease_name,safe='')}"

    def load(self) -> tuple[SnapshotIdentity | None, SnapshotIdentity | None]:
        try:
            response = self.client.request_json("GET", self.path)
        except ApiError as exc:
            if exc.status == 404:
                return None, None
            raise NvidiaInventoryError(f"cannot read NVIDIA continuity checkpoint: {exc}") from None
        body = response.body
        if not isinstance(body, dict):
            raise NvidiaInventoryError("NVIDIA continuity Lease body is malformed")
        meta = body.get("metadata")
        if not isinstance(meta, dict):
            raise NvidiaInventoryError("NVIDIA continuity Lease metadata is malformed")
        annotations = meta.get("annotations") or {}
        if not isinstance(annotations, dict):
            raise NvidiaInventoryError("NVIDIA continuity Lease annotations are malformed")
        raw = annotations.get(ANNOTATION)
        if raw is None:
            return None, None
        return decode_checkpoint(raw)

    def save(self, baseline: SnapshotIdentity | None, candidate: SnapshotIdentity | None) -> None:
        raw = encode_checkpoint(baseline, candidate)
        for _attempt in range(2):
            try:
                current = self.client.request_json("GET", self.path)
            except ApiError as exc:
                raise NvidiaInventoryError(f"cannot read Lease before NVIDIA checkpoint write: {exc}") from None
            body = current.body
            if not isinstance(body, dict):
                raise NvidiaInventoryError("NVIDIA continuity Lease body is malformed")
            meta = body.get("metadata"); spec = body.get("spec")
            if not isinstance(meta, dict) or not isinstance(spec, dict):
                raise NvidiaInventoryError("NVIDIA continuity Lease identity is malformed")
            if spec.get("holderIdentity") != self.identity:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write requires current Lease leadership")
            rv = meta.get("resourceVersion")
            if not isinstance(rv, str) or not rv.strip():
                raise NvidiaInventoryError("NVIDIA continuity Lease resourceVersion is missing")
            patch = {"metadata": {"resourceVersion": rv, "annotations": {ANNOTATION: raw}}}
            try:
                updated = self.client.request_json("PATCH", self.path, patch, content_type="application/merge-patch+json")
            except ApiError as exc:
                if exc.status in {409, 412}:
                    continue
                raise NvidiaInventoryError(f"cannot write NVIDIA continuity checkpoint: {exc}") from None
            if not isinstance(updated.body, dict):
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write response is malformed")
            out_meta = updated.body.get("metadata")
            annotations = out_meta.get("annotations") if isinstance(out_meta, dict) else None
            out_rv = out_meta.get("resourceVersion") if isinstance(out_meta, dict) else None
            if not isinstance(out_rv, str) or not out_rv.strip() or not isinstance(annotations, dict) or annotations.get(ANNOTATION) != raw:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write was not verified")
            return
        raise NvidiaInventoryError("NVIDIA continuity checkpoint write conflicted twice")
