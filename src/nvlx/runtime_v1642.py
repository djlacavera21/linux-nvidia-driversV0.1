"""Checkpoint-aware readiness for nvlx 1.6.4.2."""
from __future__ import annotations

from .nvidia_checkpoint_v1638 import LeaseCheckpointStore
from .runtime_v164 import Runtime as RuntimeV164


class Runtime(RuntimeV164):
    """Advertise readiness only after persisted NVIDIA continuity state is safe to serve."""

    def _checkpoint_ready(self) -> bool:
        store = self.nvidia_checkpoint_store
        if store is None:
            return True
        if not self.nvidia_checkpoint_loaded:
            return False
        if self.nvidia_checkpoint_epoch_stale:
            return False
        return True

    def ready(self) -> bool:
        s = self.stats
        controller_ready = bool(
            s.api_reachable
            and s.leader
            and s.inventory_fresh
            and not s.terminating
        )
        return controller_ready and self._checkpoint_ready()


__all__ = ["Runtime", "LeaseCheckpointStore"]
