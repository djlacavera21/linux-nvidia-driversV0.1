"""Per-call checkpoint receipt validation for nvlx 1.6.5."""
from __future__ import annotations

import hashlib

from .nvidia_checkpoint_v1635 import encode_checkpoint
from .nvidia_checkpoint_v165 import CheckpointCommitReceipt, LeaseCheckpointStore
from .nvidia_inventory_v1631 import NvidiaInventoryError
from .runtime_v1643 import Runtime as RuntimeV1643


class Runtime(RuntimeV1643):
    """Require exact per-call proof before accepting a non-advancing checkpoint save."""

    @staticmethod
    def _receipt_digest(baseline, candidate, epoch: int, sequence: int) -> str:
        raw = encode_checkpoint(baseline, candidate, epoch, sequence)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _save_epoch_state(self) -> int:
        store = self.nvidia_checkpoint_store
        if store is None:
            return self.nvidia_checkpoint_epoch
        if not self._leader():
            raise NvidiaInventoryError(
                "NVIDIA continuity checkpoint persistence requires Lease leadership"
            )

        previous_epoch = self.nvidia_checkpoint_epoch
        previous_sequence = self.nvidia_checkpoint_sequence
        receipt = None
        save_receipt = getattr(store, "save_receipt", None)

        if callable(save_receipt):
            receipt = save_receipt(
                self.nvidia_identity_baseline, self.nvidia_identity_candidate
            )
            if not isinstance(receipt, CheckpointCommitReceipt):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint store returned an invalid commit receipt"
                )
            epoch = receipt.lease_transition
            sequence = receipt.sequence
            expected_digest = self._receipt_digest(
                self.nvidia_identity_baseline,
                self.nvidia_identity_candidate,
                epoch,
                sequence,
            )
            if receipt.canonical_sha256 != expected_digest:
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint commit receipt canonical digest mismatch"
                )
        else:
            epoch, sequence = store.save(
                self.nvidia_identity_baseline, self.nvidia_identity_candidate
            )

        if sequence < previous_sequence:
            self.nvidia_checkpoint_rollbacks += 1
            raise NvidiaInventoryError(
                "NVIDIA continuity checkpoint sequence rollback detected"
            )

        if sequence == previous_sequence:
            if sequence < 1:
                raise NvidiaInventoryError(
                    "NVIDIA continuity idempotent checkpoint sequence is invalid"
                )
            if receipt is None or not receipt.idempotent:
                raise NvidiaInventoryError(
                    "NVIDIA continuity non-advancing checkpoint sequence lacks per-call idempotent proof"
                )
            if epoch != previous_epoch:
                raise NvidiaInventoryError(
                    "NVIDIA continuity idempotent checkpoint Lease epoch mismatch"
                )
            self.nvidia_checkpoint_idempotent_acks += 1
            return epoch

        self.nvidia_checkpoint_writes += 1
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_sequence = sequence
        return epoch


__all__ = ["Runtime", "LeaseCheckpointStore", "CheckpointCommitReceipt"]
