"""Persistent NVIDIA continuity runtime for nvlx 1.6.3.3."""
from __future__ import annotations

from .nvidia_inventory_v163 import NvidiaInventoryError, NvidiaPreflight
from .runtime_v1632 import Runtime as RuntimeV1632


class Runtime(RuntimeV1632):
    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_store = None
        self.nvidia_checkpoint_loaded = False
        self.nvidia_checkpoint_writes = 0
        self.nvidia_checkpoint_failures = 0

    def _restore_checkpoint_once(self) -> None:
        if self.nvidia_checkpoint_loaded:
            return
        store = self.nvidia_checkpoint_store
        if store is None:
            self.nvidia_checkpoint_loaded = True
            return
        baseline, candidate = store.load()
        self.nvidia_identity_baseline = baseline
        self.nvidia_identity_candidate = candidate
        self.nvidia_checkpoint_loaded = True

    def _persist_checkpoint(self, baseline, candidate) -> None:
        store = self.nvidia_checkpoint_store
        if store is None:
            return
        if not self._leader():
            raise NvidiaInventoryError("NVIDIA continuity checkpoint persistence requires Lease leadership")
        store.save(baseline, candidate)
        self.nvidia_checkpoint_writes += 1

    def _continuity_accepts(self, result: NvidiaPreflight) -> bool:
        try:
            self._restore_checkpoint_once()
        except NvidiaInventoryError:
            self.nvidia_checkpoint_failures += 1
            raise
        old_baseline = self.nvidia_identity_baseline
        old_candidate = self.nvidia_identity_candidate
        old_changes = self.nvidia_continuity_changes
        accepted = super()._continuity_accepts(result)
        changed = old_baseline != self.nvidia_identity_baseline or old_candidate != self.nvidia_identity_candidate
        if not changed:
            return accepted
        try:
            self._persist_checkpoint(self.nvidia_identity_baseline, self.nvidia_identity_candidate)
        except NvidiaInventoryError:
            self.nvidia_checkpoint_failures += 1
            self.nvidia_identity_baseline = old_baseline
            self.nvidia_identity_candidate = old_candidate
            self.nvidia_continuity_changes = old_changes
            self.nvidia_preflight_ok = False
            self.nvidia_preflight_mode = "continuity-checkpoint-error"
            self.nvidia_preflight_reasons = ("NVIDIA continuity checkpoint could not be persisted",)
            self._invalidate_inventory()
            raise
        return accepted
