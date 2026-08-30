"""Replay-fenced Lease-backed NVIDIA continuity checkpoint for nvlx 1.6.3.5."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from urllib import parse

from .k8s_api_v16 import ApiError
from .nvidia_checkpoint_v1633 import _identity_from
from .nvidia_inventory_v1631 import NvidiaInventoryError

ANNOTATION = "nvlx.io/nvidia-continuity-v3"
FLOOR_ANNOTATION = "nvlx.io/nvidia-continuity-sequence-floor"
LEGACY_V2 = "nvlx.io/nvidia-continuity-v2"
LEGACY_V1 = "nvlx.io/nvidia-continuity-v1"


def _valid_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NvidiaInventoryError(f"NVIDIA continuity {label} is invalid")
    return value


def encode_checkpoint(baseline, candidate, lease_transition: int, sequence: int) -> str:
    transition = _valid_nonnegative_int(lease_transition, "Lease transition")
    seq = _valid_nonnegative_int(sequence, "checkpoint sequence")
    if seq < 1:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence must be positive")
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity candidate cannot exist without a baseline")
    payload = {
        "baseline": asdict(baseline) if baseline is not None else None,
        "candidate": asdict(candidate) if candidate is not None else None,
        "lease_transition": transition,
        "sequence": seq,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return json.dumps({"version": 3, "sha256": digest, "payload": payload}, sort_keys=True, separators=(",", ":"))


def decode_checkpoint(raw: object):
    if not isinstance(raw, str) or not raw:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint annotation is invalid")
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint is not valid JSON") from None
    if not isinstance(envelope, dict) or envelope.get("version") != 3:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint version is unsupported")
    payload = envelope.get("payload"); digest = envelope.get("sha256")
    if not isinstance(payload, dict) or not isinstance(digest, str):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint envelope is malformed")
    if set(payload) != {"baseline", "candidate", "lease_transition", "sequence"}:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint payload is malformed")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != digest:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint integrity mismatch")
    baseline = _identity_from(payload.get("baseline")); candidate = _identity_from(payload.get("candidate"))
    transition = _valid_nonnegative_int(payload.get("lease_transition"), "checkpoint Lease transition")
    sequence = _valid_nonnegative_int(payload.get("sequence"), "checkpoint sequence")
    if sequence < 1:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence must be positive")
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint candidate lacks baseline")
    return baseline, candidate, transition, sequence


class LeaseCheckpointStore:
    def __init__(self, client, identity: str, *, namespace: str = "nvlx-system", lease_name: str = "nvlx-controller"):
        if not isinstance(identity, str) or not identity.strip(): raise ValueError("identity required")
        self.client=client; self.identity=identity.strip(); self.namespace=namespace; self.lease_name=lease_name

    @property
    def path(self) -> str:
        return f"/apis/coordination.k8s.io/v1/namespaces/{parse.quote(self.namespace,safe='')}/leases/{parse.quote(self.lease_name,safe='')}"

    @staticmethod
    def _lease_identity(body: object):
        if not isinstance(body, dict): raise NvidiaInventoryError("NVIDIA continuity Lease body is malformed")
        meta=body.get("metadata"); spec=body.get("spec")
        if not isinstance(meta, dict) or not isinstance(spec, dict): raise NvidiaInventoryError("NVIDIA continuity Lease identity is malformed")
        transition=spec.get("leaseTransitions",0)
        if isinstance(transition,bool): raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid")
        try: transition=int(transition or 0)
        except (TypeError,ValueError): raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid") from None
        if transition < 0: raise NvidiaInventoryError("NVIDIA continuity Lease transition is invalid")
        return meta,spec,transition

    @staticmethod
    def _floor(annotations: dict) -> int:
        raw = annotations.get(FLOOR_ANNOTATION)
        if raw is None: return 0
        if not isinstance(raw, str) or not raw.isdigit():
            raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence floor is malformed")
        value=int(raw)
        if value < 0: raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence floor is invalid")
        return value

    def load(self):
        try: response=self.client.request_json("GET",self.path)
        except ApiError as exc:
            if exc.status==404: return None,None,0,False,0
            raise NvidiaInventoryError(f"cannot read NVIDIA continuity checkpoint: {exc}") from None
        meta,_spec,current_transition=self._lease_identity(response.body)
        anns=meta.get("annotations") or {}
        if not isinstance(anns,dict): raise NvidiaInventoryError("NVIDIA continuity Lease annotations are malformed")
        floor=self._floor(anns)
        raw=anns.get(ANNOTATION)
        if raw is None:
            legacy = anns.get(LEGACY_V2) is not None or anns.get(LEGACY_V1) is not None
            return None,None,current_transition,legacy,floor
        baseline,candidate,stored_transition,sequence=decode_checkpoint(raw)
        if sequence < floor:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint replay detected below retained sequence floor")
        if sequence > floor:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence exceeds retained floor")
        return baseline,candidate,current_transition,stored_transition != current_transition,sequence

    def save(self, baseline, candidate) -> tuple[int,int]:
        for _attempt in range(2):
            try: current=self.client.request_json("GET",self.path)
            except ApiError as exc: raise NvidiaInventoryError(f"cannot read Lease before NVIDIA checkpoint write: {exc}") from None
            meta,spec,transition=self._lease_identity(current.body)
            if spec.get("holderIdentity") != self.identity:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write requires current Lease leadership")
            rv=meta.get("resourceVersion")
            if not isinstance(rv,str) or not rv.strip(): raise NvidiaInventoryError("NVIDIA continuity Lease resourceVersion is missing")
            anns=meta.get("annotations") or {}
            if not isinstance(anns,dict): raise NvidiaInventoryError("NVIDIA continuity Lease annotations are malformed")
            floor=self._floor(anns)
            current_raw=anns.get(ANNOTATION)
            current_sequence=0
            if current_raw is not None:
                _b,_c,_t,current_sequence=decode_checkpoint(current_raw)
                if current_sequence != floor:
                    raise NvidiaInventoryError("NVIDIA continuity checkpoint/floor mismatch before write")
            elif floor != 0:
                raise NvidiaInventoryError("NVIDIA continuity sequence floor exists without current checkpoint")
            sequence=floor+1
            raw=encode_checkpoint(baseline,candidate,transition,sequence)
            patch={"metadata":{"resourceVersion":rv,"annotations":{ANNOTATION:raw,FLOOR_ANNOTATION:str(sequence)}}}
            try: updated=self.client.request_json("PATCH",self.path,patch,content_type="application/merge-patch+json")
            except ApiError as exc:
                if exc.status in {409,412}: continue
                raise NvidiaInventoryError(f"cannot write NVIDIA continuity checkpoint: {exc}") from None
            out_meta,out_spec,out_transition=self._lease_identity(updated.body)
            out_anns=out_meta.get("annotations"); out_rv=out_meta.get("resourceVersion")
            if out_spec.get("holderIdentity") != self.identity or out_transition != transition:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint Lease epoch changed during write")
            if not isinstance(out_rv,str) or not out_rv.strip() or not isinstance(out_anns,dict):
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write response is malformed")
            if out_anns.get(ANNOTATION) != raw or out_anns.get(FLOOR_ANNOTATION) != str(sequence):
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write was not verified")
            return transition,sequence
        raise NvidiaInventoryError("NVIDIA continuity checkpoint write conflicted twice")
