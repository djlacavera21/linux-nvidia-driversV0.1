"""Unified checkpoint transaction runtime for nvlx 1.6.4."""
from __future__ import annotations

from .nvidia_checkpoint_v1638 import LeaseCheckpointStore
from .nvidia_inventory_v1631 import NvidiaInventoryError
from .runtime_v1639 import Runtime as RuntimeV1639


class Runtime(RuntimeV1639):
    """Route every continuity checkpoint persistence path through one fenced transaction."""

    def __post_init__(self):
        super().__post_init__()
        self.nvidia_checkpoint_transaction_mismatches = 0

    def _persist_checkpoint(self, baseline, candidate) -> None:
        """Persist the runtime's current continuity state through the v1.6.3.9 transaction gate.

        RuntimeV1633 calls this method for normal baseline/candidate changes. Earlier
        releases wrote directly through the store here, bypassing the sequence and
        epoch acknowledgement logic used by Lease-transition revalidation. v1.6.4
        makes both paths converge on ``_save_epoch_state``.
        """
        if baseline != self.nvidia_identity_baseline or candidate != self.nvidia_identity_candidate:
            self.nvidia_checkpoint_transaction_mismatches += 1
            raise NvidiaInventoryError(
                "NVIDIA continuity checkpoint transaction state does not match runtime state"
            )
        self._save_epoch_state()


__all__ = ["Runtime", "LeaseCheckpointStore"]
