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
        self.nvidia_identity_baseline = baseline
        self.nvidia_identity_candidate = candidate

    def _save_epoch_state(self) -> int:
        store = self.nvidia_checkpoint_store
        if store is None:
            return self.nvidia_checkpoint_epoch
        if not self._leader():
            raise NvidiaInventoryError("NVIDIA continuity checkpoint persistence requires Lease leadership")
        epoch = store.save(self.nvidia_identity_baseline, self.nvidia_identity_candidate)
        self.nvidia_checkpoint_writes += 1
        self.nvidia_checkpoint_epoch = epoch
        return epoch

    def _continuity_accepts(self, result: NvidiaPreflight) -> bool:
        try:
            self._restore_checkpoint_once()
        except NvidiaInventoryError:
            self.nvidia_checkpoint_failures += 1
            raise

        if not self.nvidia_checkpoint_epoch_stale:
            return super()._continuity_accepts(result)

        # A Lease transition invalidates direct inheritance of the persisted
        # baseline. Preserve the old baseline, persist the first healthy
        # observation as a candidate under the new epoch, then require an
        # identical second observation before promoting it.
        identity = snapshot_identity(result.snapshot)
        old_baseline = self.nvidia_identity_baseline
        old_candidate = self.nvidia_identity_candidate
        old_changes = self.nvidia_continuity_changes

        if old_candidate is not None and identity == old_candidate:
            self.nvidia_identity_baseline = identity
            self.nvidia_identity_candidate = None
            self.nvidia_continuity_changes = ()
            try:
                self._save_epoch_state()
            except NvidiaInventoryError:
                self.nvidia_checkpoint_failures += 1
                self.nvidia_identity_baseline = old_baseline
                self.nvidia_identity_candidate = old_candidate
                self.nvidia_continuity_changes = old_changes
                self.nvidia_preflight_ok = False
                self.nvidia_preflight_mode = "checkpoint-error"
                self.nvidia_preflight_reasons = ("NVIDIA continuity checkpoint revalidation persistence failed",)
                self._invalidate_inventory()
                raise
            self.nvidia_checkpoint_epoch_stale = False
            self.nvidia_checkpoint_revalidations += 1
            return True

        self.nvidia_identity_candidate = identity
        self.nvidia_continuity_changes = ()
        self.nvidia_preflight_ok = False
        self.nvidia_preflight_mode = "checkpoint-revalidation"
        self.nvidia_preflight_reasons = ("Lease transition detected; identical NVIDIA snapshot confirmation required",)
        self.nvidia_continuity_fences += 1
        self._invalidate_inventory()
        try:
            self._save_epoch_state()
        except NvidiaInventoryError:
            self.nvidia_checkpoint_failures += 1
            self.nvidia_identity_baseline = old_baseline
            self.nvidia_identity_candidate = old_candidate
            self.nvidia_continuity_changes = old_changes
            self.nvidia_preflight_mode = "checkpoint-error"
            self.nvidia_preflight_reasons = ("NVIDIA continuity checkpoint revalidation persistence failed",)
            raise
        # The checkpoint is now physically stored in the current Lease epoch,
        # but this running process still owes confirmation #2.
        self.nvidia_checkpoint_epoch_stale = True
        return False


__all__ = ["Runtime", "LeaseCheckpointStore", "SnapshotIdentity"]
