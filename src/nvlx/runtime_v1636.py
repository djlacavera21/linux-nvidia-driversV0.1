"""Atomic persistent NVIDIA checkpoint restore for nvlx 1.6.3.6."""
from __future__ import annotations

from .nvidia_checkpoint_v1635 import LeaseCheckpointStore
from .runtime_v1635 import Runtime as RuntimeV1635


class Runtime(RuntimeV1635):
    """Never mark persisted NVIDIA continuity state loaded until restore succeeds."""

    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_restore_attempts = 0
        self.nvidia_checkpoint_restore_successes = 0

    def _restore_checkpoint_once(self) -> None:
        if self.nvidia_checkpoint_loaded:
            return
        store = self.nvidia_checkpoint_store
        if store is None:
            self.nvidia_checkpoint_loaded = True
            return

        self.nvidia_checkpoint_restore_attempts += 1

        # Load into locals first.  A failed read/validation must not alter the
        # existing in-memory baseline/candidate/epoch/sequence, and must not
        # consume the one-time restore guard.  The next preflight therefore
        # retries the persisted checkpoint instead of falling back to
        # first-observation trust.
        baseline, candidate, epoch, stale, sequence = store.load()

        self.nvidia_identity_baseline = baseline
        self.nvidia_identity_candidate = candidate
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_epoch_stale = bool(stale)
        self.nvidia_checkpoint_sequence = sequence
        self.nvidia_checkpoint_loaded = True
        self.nvidia_checkpoint_restore_successes += 1


__all__ = ["Runtime", "LeaseCheckpointStore"]
