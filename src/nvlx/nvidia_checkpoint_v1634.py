"""Lease-generation-bound NVIDIA continuity checkpoint for nvlx 1.6.3.4."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from urllib import parse

from .k8s_api_v16 import ApiError
from .nvidia_checkpoint_v1633 import _identity_from
from .nvidia_continuity_v1632 import SnapshotIdentity
from .nvidia_inventory_v1631 import NvidiaInventoryError

ANNOTATION = "nvlx.io/nvidia-continuity-v2"
LEGACY_ANNOTATION = "nvlx.io/nvidia-continuity-v1"


def _payload(baseline: SnapshotIdentity | None, candidate: SnapshotIdentity | None, lease_transition: int) -> dict:
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity candidate cannot exist without a baseline")
    if isinstance(lease_transition, bool) or not isinstance(lease_transition, int) or lease_transition < 0:
        raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid")
    return {"baseline": asdict(baseline) if baseline is not None else None, "candidate": asdict(candidate) if candidate is not None else None, "lease_transition": lease_transition}


def encode_checkpoint(baseline: SnapshotIdentity | None, candidate: SnapshotIdentity | None, lease_transition: int) -> str:
    payload = _payload(baseline, candidate, lease_transition)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return json.dumps({"version": 2, "sha256": digest, "payload": payload}, sort_keys=True, separators=(",", ":"))


def decode_checkpoint(raw: object) -> tuple[SnapshotIdentity | None, SnapshotIdentity | None, int]:
    if not isinstance(raw, str) or not raw:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint annotation is invalid")
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint is not valid JSON") from None
    if not isinstance(envelope, dict) or envelope.get("version") != 2:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint version is unsupported")
    payload = envelope.get("payload"); digest = envelope.get("sha256")
    if not isinstance(payload, dict) or not isinstance(digest, str):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint envelope is malformed")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != digest:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint integrity mismatch")
    if set(payload) != {"baseline", "candidate", "lease_transition"}:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint payload is malformed")
    baseline = _identity_from(payload.get("baseline")); candidate = _identity_from(payload.get("candidate")); transition = payload.get("lease_transition")
    if isinstance(transition, bool) or not isinstance(transition, int) or transition < 0:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint Lease transition is invalid")
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint candidate lacks baseline")
    return baseline, candidate, transition


class LeaseCheckpointStore:
    def __init__(self, client, identity: str, *, namespace: str = "nvlx-system", lease_name: str = "nvlx-controller"):
        if not isinstance(identity, str) or not identity.strip(): raise ValueError("identity required")
        self.client=client; self.identity=identity.strip(); self.namespace=namespace; self.lease_name=lease_name

    @property
    def path(self) -> str:
        return f"/apis/coordination.k8s.io/v1/namespaces/{parse.quote(self.namespace,safe='')}/leases/{parse.quote(self.lease_name,safe='')}"

    @staticmethod
    def _lease_identity(body: object) -> tuple[dict, dict, int]:
        if not isinstance(body, dict): raise NvidiaInventoryError("NVIDIA continuity Lease body is malformed")
        meta=body.get("metadata"); spec=body.get("spec")
        if not isinstance(meta, dict) or not isinstance(spec, dict): raise NvidiaInventoryError("NVIDIA continuity Lease identity is malformed")
        transition=spec.get("leaseTransitions",0)
        if isinstance(transition,bool): raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid")
        try: transition=int(transition or 0)
        except (TypeError,ValueError): raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid") from None
        if transition < 0: raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid")
        return meta,spec,transition

    def load(self) -> tuple[SnapshotIdentity | None, SnapshotIdentity | None, int, bool]:
        try: response=self.client.request_json("GET",self.path)
        except ApiError as exc:
            if exc.status==404: return None,None,0,False
            raise NvidiaInventoryError(f"cannot read NVIDIA continuity checkpoint: {exc}") from None
        meta,_spec,current_transition=self._lease_identity(response.body)
        anns=meta.get("annotations") or {}
        if not isinstance(anns,dict): raise NvidiaInventoryError("NVIDIA continuity Lease annotations are malformed")
        raw=anns.get(ANNOTATION)
        if raw is None:
            return None,None,current_transition,anns.get(LEGACY_ANNOTATION) is not None
        baseline,candidate,stored_transition=decode_checkpoint(raw)
        return baseline,candidate,current_transition,stored_transition != current_transition

    def save(self, baseline: SnapshotIdentity | None, candidate: SnapshotIdentity | None) -> int:
        for _attempt in range(2):
            try: current=self.client.request_json("GET",self.path)
            except ApiError as exc: raise NvidiaInventoryError(f"cannot read Lease before NVIDIA checkpoint write: {exc}") from None
            meta,spec,transition=self._lease_identity(current.body)
            if spec.get("holderIdentity") != self.identity:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write requires current Lease leadership")
            rv=meta.get("resourceVersion")
            if not isinstance(rv,str) or not rv.strip(): raise NvidiaInventoryError("NVIDIA continuity Lease resourceVersion is missing")
            raw=encode_checkpoint(baseline,candidate,transition)
            patch={"metadata":{"resourceVersion":rv,"annotations":{ANNOTATION:raw}}}
            try: updated=self.client.request_json("PATCH",self.path,patch,content_type="application/merge-patch+json")
            except ApiError as exc:
                if exc.status in {409,412}: continue
                raise NvidiaInventoryError(f"cannot write NVIDIA continuity checkpoint: {exc}") from None
            out_meta,out_spec,out_transition=self._lease_identity(updated.body)
            anns=out_meta.get("annotations"); out_rv=out_meta.get("resourceVersion")
            if out_spec.get("holderIdentity") != self.identity or out_transition != transition:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint Lease epoch changed during write")
            if not isinstance(out_rv,str) or not out_rv.strip() or not isinstance(anns,dict) or anns.get(ANNOTATION) != raw:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write was not verified")
            return transition
        raise NvidiaInventoryError("NVIDIA continuity checkpoint write conflicted twice")
