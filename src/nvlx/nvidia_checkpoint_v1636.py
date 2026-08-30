"""Holder-bound replay-fenced NVIDIA continuity checkpoint for nvlx 1.6.3.6."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from .k8s_api_v16 import ApiError
from .nvidia_checkpoint_v1633 import _identity_from
from .nvidia_checkpoint_v1635 import (
    ANNOTATION as LEGACY_V3,
    FLOOR_ANNOTATION,
    LEGACY_V2,
    LEGACY_V1,
    decode_checkpoint as decode_v3,
    LeaseCheckpointStore as StoreV1635,
    _valid_nonnegative_int,
)
from .nvidia_inventory_v1631 import NvidiaInventoryError

ANNOTATION = "nvlx.io/nvidia-continuity-v4"


def _holder(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NvidiaInventoryError("NVIDIA continuity checkpoint holder identity is invalid")
    return value.strip()


def encode_checkpoint(baseline, candidate, lease_transition: int, sequence: int, holder_identity: str) -> str:
    transition = _valid_nonnegative_int(lease_transition, "Lease transition")
    seq = _valid_nonnegative_int(sequence, "checkpoint sequence")
    holder = _holder(holder_identity)
    if seq < 1:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence must be positive")
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity candidate cannot exist without a baseline")
    payload = {
        "baseline": asdict(baseline) if baseline is not None else None,
        "candidate": asdict(candidate) if candidate is not None else None,
        "lease_transition": transition,
        "sequence": seq,
        "holder_identity": holder,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return json.dumps({"version": 4, "sha256": digest, "payload": payload}, sort_keys=True, separators=(",", ":"))


def decode_checkpoint(raw: object):
    if not isinstance(raw, str) or not raw:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint annotation is invalid")
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint is not valid JSON") from None
    if not isinstance(envelope, dict) or envelope.get("version") != 4:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint version is unsupported")
    payload = envelope.get("payload"); digest = envelope.get("sha256")
    if not isinstance(payload, dict) or not isinstance(digest, str):
        raise NvidiaInventoryError("NVIDIA continuity checkpoint envelope is malformed")
    if set(payload) != {"baseline", "candidate", "lease_transition", "sequence", "holder_identity"}:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint payload is malformed")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != digest:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint integrity mismatch")
    baseline = _identity_from(payload.get("baseline")); candidate = _identity_from(payload.get("candidate"))
    transition = _valid_nonnegative_int(payload.get("lease_transition"), "checkpoint Lease transition")
    sequence = _valid_nonnegative_int(payload.get("sequence"), "checkpoint sequence")
    holder = _holder(payload.get("holder_identity"))
    if sequence < 1:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence must be positive")
    if baseline is None and candidate is not None:
        raise NvidiaInventoryError("NVIDIA continuity checkpoint candidate lacks baseline")
    return baseline, candidate, transition, sequence, holder


class LeaseCheckpointStore(StoreV1635):
    """Bind accepted continuity state to both Lease epoch and actual holder."""

    def load(self):
        try:
            response = self.client.request_json("GET", self.path)
        except ApiError as exc:
            if exc.status == 404:
                return None, None, 0, False, 0
            raise NvidiaInventoryError(f"cannot read NVIDIA continuity checkpoint: {exc}") from None
        meta, spec, current_transition = self._lease_identity(response.body)
        current_holder = _holder(spec.get("holderIdentity"))
        anns = meta.get("annotations") or {}
        if not isinstance(anns, dict):
            raise NvidiaInventoryError("NVIDIA continuity Lease annotations are malformed")
        floor = self._floor(anns)
        raw = anns.get(ANNOTATION)
        if raw is not None:
            baseline, candidate, stored_transition, sequence, stored_holder = decode_checkpoint(raw)
            if sequence < floor:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint replay detected below retained sequence floor")
            if sequence > floor:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence exceeds retained floor")
            stale = stored_transition != current_transition or stored_holder != current_holder
            return baseline, candidate, current_transition, stale, sequence

        legacy_raw = anns.get(LEGACY_V3)
        if legacy_raw is not None:
            baseline, candidate, _stored_transition, sequence = decode_v3(legacy_raw)
            if sequence != floor:
                raise NvidiaInventoryError("legacy NVIDIA continuity checkpoint/floor mismatch")
            return baseline, candidate, current_transition, True, sequence

        legacy = anns.get(LEGACY_V2) is not None or anns.get(LEGACY_V1) is not None
        if floor != 0:
            raise NvidiaInventoryError("NVIDIA continuity sequence floor exists without current checkpoint")
        return None, None, current_transition, legacy, 0

    def save(self, baseline, candidate) -> tuple[int, int]:
        for _attempt in range(2):
            try:
                current = self.client.request_json("GET", self.path)
            except ApiError as exc:
                raise NvidiaInventoryError(f"cannot read Lease before NVIDIA checkpoint write: {exc}") from None
            meta, spec, transition = self._lease_identity(current.body)
            current_holder = _holder(spec.get("holderIdentity"))
            if current_holder != self.identity:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write requires current Lease leadership")
            rv = meta.get("resourceVersion")
            if not isinstance(rv, str) or not rv.strip():
                raise NvidiaInventoryError("NVIDIA continuity Lease resourceVersion is missing")
            anns = meta.get("annotations") or {}
            if not isinstance(anns, dict):
                raise NvidiaInventoryError("NVIDIA continuity Lease annotations are malformed")
            floor = self._floor(anns)
            current_raw = anns.get(ANNOTATION)
            if current_raw is not None:
                _b, _c, _t, current_sequence, stored_holder = decode_checkpoint(current_raw)
                if current_sequence != floor:
                    raise NvidiaInventoryError("NVIDIA continuity checkpoint/floor mismatch before write")
                if stored_holder != current_holder:
                    # A holder change is allowed only through the stale-revalidation
                    # path; do not silently advance a checkpoint written by another
                    # identity without first confirming the current snapshot.
                    raise NvidiaInventoryError("NVIDIA continuity checkpoint holder mismatch before write")
            else:
                legacy_raw = anns.get(LEGACY_V3)
                if legacy_raw is not None:
                    _b, _c, _t, legacy_sequence = decode_v3(legacy_raw)
                    if legacy_sequence != floor:
                        raise NvidiaInventoryError("legacy NVIDIA continuity checkpoint/floor mismatch before write")
                elif floor != 0:
                    raise NvidiaInventoryError("NVIDIA continuity sequence floor exists without current checkpoint")
            sequence = floor + 1
            raw = encode_checkpoint(baseline, candidate, transition, sequence, current_holder)
            patch = {"metadata": {"resourceVersion": rv, "annotations": {ANNOTATION: raw, FLOOR_ANNOTATION: str(sequence)}}}
            try:
                updated = self.client.request_json("PATCH", self.path, patch, content_type="application/merge-patch+json")
            except ApiError as exc:
                if exc.status in {409, 412}:
                    continue
                raise NvidiaInventoryError(f"cannot write NVIDIA continuity checkpoint: {exc}") from None
            out_meta, out_spec, out_transition = self._lease_identity(updated.body)
            out_holder = _holder(out_spec.get("holderIdentity"))
            out_anns = out_meta.get("annotations"); out_rv = out_meta.get("resourceVersion")
            if out_holder != current_holder or out_transition != transition:
                raise NvidiaInventoryError("NVIDIA continuity checkpoint Lease identity changed during write")
            if not isinstance(out_rv, str) or not out_rv.strip() or not isinstance(out_anns, dict):
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write response is malformed")
            if out_anns.get(ANNOTATION) != raw or out_anns.get(FLOOR_ANNOTATION) != str(sequence):
                raise NvidiaInventoryError("NVIDIA continuity checkpoint write was not verified")
            return transition, sequence
        raise NvidiaInventoryError("NVIDIA continuity checkpoint write conflicted twice")


__all__ = ["ANNOTATION", "FLOOR_ANNOTATION", "LeaseCheckpointStore", "encode_checkpoint", "decode_checkpoint"]
