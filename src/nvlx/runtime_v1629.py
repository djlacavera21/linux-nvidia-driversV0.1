"""Relist settlement barrier for nvlx 1.6.2.9."""
from __future__ import annotations

from .runtime_v1628 import Runtime as RuntimeV1628

_SETTLED = {
    "patched", "status-noop", "event-noop", "checkpoint", "finalized",
    "deleted-observed", "observe-delete",
}


class RelistSettlementDeferred(RuntimeError):
    """Internal control-flow signal: a trusted list snapshot did not settle."""


class Runtime(RuntimeV1628):
    """Never enter a watch continuity window from a partially settled relist."""

    def __post_init__(self):
        super().__post_init__()
        self._relist_deferred_in_cycle = False

    def reconcile_object(self, obj: dict, *, event_type: str = "MODIFIED") -> str:
        result = super().reconcile_object(obj, event_type=event_type)
        if event_type == "ADDED" and result not in _SETTLED:
            self._relist_deferred_in_cycle = True
        return result

    def _seed_watch_state_from_list(self, items: list[dict]) -> None:
        # v1.6.2.8 calls this after list reconciliation and immediately before
        # marking inventory fresh / opening the watch.  Treat it as a settlement
        # barrier: a partially reconciled snapshot cannot establish continuity.
        if self._relist_deferred_in_cycle:
            self._invalidate_inventory()
            raise RelistSettlementDeferred("GPUFleet relist contains deferred reconciliation")
        super()._seed_watch_state_from_list(items)

    def list_and_watch_once(self) -> str:
        self._relist_deferred_in_cycle = False
        try:
            return super().list_and_watch_once()
        except RelistSettlementDeferred:
            self._invalidate_inventory()
            return "relist"
