"""Lease-transition-aware persistent NVIDIA continuity runtime for nvlx 1.6.3.4."""
from __future__ import annotations

from .nvidia_checkpoint_v1634 import LeaseCheckpointStore
from .nvidia_continuity_v1632 import SnapshotIdentity, snapshot_identity
from .nvidia_inventory_v163 import NvidiaInventoryError, NvidiaPreflight
from .runtime_v1633 import Runtime as RuntimeV1633


class Runtime(RuntimeV1633):
    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_epoch = 0
        self.nvidia_checkpoint_epoch_stale = False
        self.nvidia_checkpoint_revalidations = 0

    def _restore_checkpoint_once(self) -> None:
        if self.nvidia_checkpoint_loaded:
            return
        self.nvidia_checkpoint_loaded = True
        store = self.nvidia_checkpoint_store
        if store is None:
            return
        baseline, candidate, epoch, stale = store.load()
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_epoch_stale = bool(stale)
        if stale:
            # Never inherit a prior holder's accepted baseline directly. The
            # current leader must establish and persist a fresh baseline.
            self.nvidia_identity_baseline = None
            self.nvidia_identity_candidate = baseline
            return
        self.nvidia_identity_baseline = baseline
        self.nvidia_identity_candidate = candidate

    def _persist_state(self) -> bool:
        store = self.nvidia_checkpoint_store
        if store is None:
            return True
        epoch = store.save(self.nvidia_identity_baseline, self.nvidia_identity_candidate)
        self.nvidia_checkpoint_epoch = epoch
        self.nvidia_checkpoint_epoch_stale = False
        return True

    def _continuity_accepts(self, result: NvidiaPreflight) -> bool:
        # If takeover made the persisted checkpoint stale, require the new
        # holder to observe the same healthy snapshot twice before accepting
        # it as its own epoch-bound baseline.
        if self.nvidia_checkpoint_epoch_stale:
            identity = snapshot_identity(result.snapshot)
            candidate = self.nvidia_identity_candidate
            if candidate is None or identity != candidate:
                self.nvidia_identity_candidate = identity
                self.nvidia_preflight_ok = False
                self.nvidia_preflight_mode = "checkpoint-revalidation"
                self.nvidia_preflight_reasons = ("Lease holder changed; identical NVIDIA snapshot confirmation required",)
                self.nvidia_continuity_fences += 1
                self._invalidate_inventory()
                try:
                    self._persist_state()
                except NvidiaInventoryError:
                    return False
                self.nvidia_checkpoint_epoch_stale = True
                return False
            old_baseline = self.nvidia_identity_baseline
            old_candidate = self.nvidia_identity_candidate
            self.nvidia_identity_baseline = identity
            self.nvidia_identity_candidate = None
            try:
                self._persist_state()
            except NvidiaInventoryError:
                self.nvidia_identity_baseline = old_baseline
                self.nvidia_identity_candidate = old_candidate
                self.nvidia_preflight_ok = False
                self.nvidia_preflight_mode = "checkpoint-error"
                self.nvidia_preflight_reasons = ("NVIDIA continuity checkpoint revalidation persistence failed",)
                self._invalidate_inventory()
                return False
            self.nvidia_checkpoint_revalidations += 1
            return True
        return super()._continuity_accepts(result)


__all__ = ["Runtime", "LeaseCheckpointStore", "SnapshotIdentity"]
