"""Idempotent Lease checkpoint commit reconciliation for nvlx 1.6.3.8."""
from __future__ import annotations

from .nvidia_checkpoint_v1635 import ANNOTATION, FLOOR_ANNOTATION, decode_checkpoint, encode_checkpoint
from .nvidia_checkpoint_v1637 import LeaseCheckpointStore as LeaseCheckpointStoreV1637
from .nvidia_inventory_v1631 import NvidiaInventoryError


class LeaseCheckpointStore(LeaseCheckpointStoreV1637):
    """Recover an already-committed identical checkpoint without rewriting it."""

    proves_idempotent_commits = True

    def _matching_current_commit(self, baseline, candidate):
        try:
            response = self.client.request_json("GET", self.path)
        except Exception as exc:
            raise NvidiaInventoryError(f"cannot reconcile NVIDIA continuity checkpoint: {exc}") from None

        meta, spec, transition = self._lease_identity(response.body)
        if spec.get("holderIdentity") != self.identity:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint reconciliation lost Lease leadership")

        rv = meta.get("resourceVersion")
        anns = meta.get("annotations")
        if not isinstance(rv, str) or not rv.strip() or not isinstance(anns, dict):
            raise NvidiaInventoryError("NVIDIA continuity checkpoint reconciliation Lease is malformed")

        floor = self._floor(anns)
        raw = anns.get(ANNOTATION)
        if raw is None:
            if floor != 0:
                raise NvidiaInventoryError("NVIDIA continuity sequence floor exists without current checkpoint")
            return None
        if not isinstance(raw, str):
            raise NvidiaInventoryError("NVIDIA continuity checkpoint annotation is invalid")

        current_baseline, current_candidate, stored_transition, sequence = decode_checkpoint(raw)
        if sequence != floor:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint/floor mismatch during reconciliation")
        if stored_transition != transition:
            return None

        expected = encode_checkpoint(baseline, candidate, transition, sequence)
        if current_baseline == baseline and current_candidate == candidate and raw == expected:
            return transition, sequence
        return None

    def save(self, baseline, candidate) -> tuple[int, int]:
        existing = self._matching_current_commit(baseline, candidate)
        if existing is not None:
            return existing

        try:
            return super().save(baseline, candidate)
        except Exception as write_error:
            try:
                existing = self._matching_current_commit(baseline, candidate)
            except NvidiaInventoryError:
                raise

            if existing is not None:
                return existing
            if isinstance(write_error, NvidiaInventoryError):
                raise write_error
            raise NvidiaInventoryError(
                f"cannot establish NVIDIA continuity checkpoint write outcome: {write_error}"
            ) from None


__all__ = ["LeaseCheckpointStore"]
