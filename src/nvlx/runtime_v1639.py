"""Runtime idempotent checkpoint acknowledgements for nvlx 1.6.3.9."""
from __future__ import annotations

from .nvidia_checkpoint_v1638 import LeaseCheckpointStore
from .nvidia_inventory_v1631 import NvidiaInventoryError
from .runtime_v1636 import Runtime as RuntimeV1636


class Runtime(RuntimeV1636):
    """Accept proven idempotent checkpoint acknowledgements without weakening replay fencing."""

    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_idempotent_acks = 0
        self.nvidia_checkpoint_rollbacks = 0

    def _save_epoch_state(self) -> int:
        store = self.nvidia_checkpoint_store
        if store is None:
            return self.nvidia_checkpoint_epoch
        if not self._leader():
            raise NvidiaInventoryError("NVIDIA continuity checkpoint persistence requires Lease leadership")

        previous_epoch = self.nvidia_checkpoint_epoch
        previous_sequence = self.nvidia_checkpoint_sequence
        epoch, sequence = store.save(self.nvidia_identity_baseline, self.nvidia_identity_candidate)

        if sequence < previous_sequence:
            self.nvidia_checkpoint_rollbacks += 1
            raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence rollback detected")

        if sequence == previous_sequence:
            if sequence < 1:
                raise NvidiaInventoryError("NVIDIA continuity idempotent checkpoint sequence is invalid")
            if not getattr(store, "proves_idempotent_commits", False):
                raise NvidiaInventoryError(
                    "NVIDIA continuity non-advancing checkpoint sequence lacks idempotent proof"
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


__all__ = ["Runtime", "LeaseCheckpointStore"]
