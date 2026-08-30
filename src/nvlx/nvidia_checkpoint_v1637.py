"""Independent Lease checkpoint readback verification for nvlx 1.6.3.7."""
from __future__ import annotations

from .nvidia_checkpoint_v1635 import (
    ANNOTATION,
    FLOOR_ANNOTATION,
    LeaseCheckpointStore as LeaseCheckpointStoreV1635,
    decode_checkpoint,
    encode_checkpoint,
)
from .nvidia_inventory_v1631 import NvidiaInventoryError


class LeaseCheckpointStore(LeaseCheckpointStoreV1635):
    """Require a fresh GET to prove every successful checkpoint write."""

    def save(self, baseline, candidate) -> tuple[int, int]:
        transition, sequence = super().save(baseline, candidate)
        try:
            readback = self.client.request_json("GET", self.path)
        except Exception as exc:
            raise NvidiaInventoryError(f"cannot read back NVIDIA continuity checkpoint: {exc}") from None

        meta, spec, read_transition = self._lease_identity(readback.body)
        if spec.get("holderIdentity") != self.identity:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint readback lost Lease leadership")
        if read_transition != transition:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint Lease epoch changed before readback")
        rv = meta.get("resourceVersion")
        anns = meta.get("annotations")
        if not isinstance(rv, str) or not rv.strip() or not isinstance(anns, dict):
            raise NvidiaInventoryError("NVIDIA continuity checkpoint readback is malformed")
        if anns.get(FLOOR_ANNOTATION) != str(sequence):
            raise NvidiaInventoryError("NVIDIA continuity checkpoint readback floor mismatch")
        raw = anns.get(ANNOTATION)
        if not isinstance(raw, str):
            raise NvidiaInventoryError("NVIDIA continuity checkpoint missing on readback")
        rb, rc, rt, rs = decode_checkpoint(raw)
        if rt != transition or rs != sequence or rb != baseline or rc != candidate:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint readback does not match committed state")
        expected = encode_checkpoint(baseline, candidate, transition, sequence)
        if raw != expected:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint canonical readback mismatch")
        return transition, sequence


__all__ = ["LeaseCheckpointStore"]
