"""Checkpoint reconciliation telemetry for nvlx 1.6.5.2."""
from __future__ import annotations

from .nvidia_checkpoint_v165 import CheckpointCommitReceipt
from .nvidia_checkpoint_v1651 import LeaseCheckpointStore
from .nvidia_inventory_v1631 import NvidiaInventoryError
from .runtime_v165 import Runtime as RuntimeV165


class Runtime(RuntimeV165):
    """Count accepted checkpoint commits recovered from transport ambiguity."""

    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_reconciled_commits = 0

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

        reconciled = bool(receipt is not None and receipt.reconciled)

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
            if reconciled:
                self.nvidia_checkpoint_reconciled_commits += 1
            return epoch

        self.nvidia_checkpoint_writes += 1
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_sequence = sequence
        if reconciled:
            self.nvidia_checkpoint_reconciled_commits += 1
        return epoch


__all__ = ["Runtime", "LeaseCheckpointStore", "CheckpointCommitReceipt"]
