"""Compositional checkpoint-aware readiness for nvlx 1.6.4.3."""
from __future__ import annotations

from .nvidia_checkpoint_v1638 import LeaseCheckpointStore
from .runtime_v164 import Runtime as RuntimeV164
from .runtime_v1642 import Runtime as RuntimeV1642


class Runtime(RuntimeV1642):
    """Add checkpoint readiness without replacing the established readiness chain."""

    def ready(self) -> bool:
        # RuntimeV164 inherits the full pre-1.6.4.2 readiness stack, including
        # NVIDIA preflight state, inventory continuity, API reachability,
        # Lease leadership freshness and termination handling.  v1.6.4.2
        # rebuilt readiness from raw stats and accidentally bypassed some of
        # those inherited gates.  Compose checkpoint safety on top instead.
        return bool(RuntimeV164.ready(self) and self._checkpoint_ready())


__all__ = ["Runtime", "LeaseCheckpointStore"]
