"""Replay-fenced persistent NVIDIA continuity runtime for nvlx 1.6.3.5."""
from __future__ import annotations

from .nvidia_checkpoint_v1635 import LeaseCheckpointStore
from .nvidia_inventory_v163 import NvidiaInventoryError
from .runtime_v1634 import Runtime as RuntimeV1634


class Runtime(RuntimeV1634):
    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_sequence = 0
        self.nvidia_checkpoint_replays = 0

    def _restore_checkpoint_once(self) -> None:
        if self.nvidia_checkpoint_loaded:
            return
        self.nvidia_checkpoint_loaded = True
        store = self.nvidia_checkpoint_store
        if store is None:
            return
        try:
            baseline, candidate, epoch, stale, sequence = store.load()
        except NvidiaInventoryError as exc:
            if "replay detected" in str(exc):
                self.nvidia_checkpoint_replays += 1
            raise
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_epoch_stale = bool(stale)
        self.nvidia_checkpoint_sequence = sequence
        self.nvidia_identity_baseline = baseline
        self.nvidia_identity_candidate = candidate

    def _save_epoch_state(self) -> int:
        store = self.nvidia_checkpoint_store
        if store is None:
            return self.nvidia_checkpoint_epoch
        if not self._leader():
            raise NvidiaInventoryError("NVIDIA continuity checkpoint persistence requires Lease leadership")
        epoch, sequence = store.save(self.nvidia_identity_baseline, self.nvidia_identity_candidate)
        if sequence <= self.nvidia_checkpoint_sequence:
            raise NvidiaInventoryError("NVIDIA continuity checkpoint sequence did not advance")
        self.nvidia_checkpoint_writes += 1
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_sequence = sequence
        return epoch


__all__ = ["Runtime", "LeaseCheckpointStore"]
