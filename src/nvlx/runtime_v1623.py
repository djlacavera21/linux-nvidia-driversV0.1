"""Inventory-freshness runtime wrapper for nvlx 1.6.2.3."""
from __future__ import annotations
from .runtime_v1622 import Runtime as RuntimeV1622

_CONTINUITY_BREAK_RESULTS={"relist","reconnect","watch-error","eof","stopped"}

class Runtime(RuntimeV1622):
    """Treat inventory freshness as valid only while list/watch continuity holds."""

    def _invalidate_inventory(self) -> None:
        self.stats.inventory_fresh=False

    def stop(self):
        super().stop()
        self._invalidate_inventory()

    def ready(self) -> bool:
        if not self.stats.inventory_fresh:
            return False
        return super().ready()

    def list_and_watch_once(self) -> str:
        # A new relist starts a new inventory proof. Do not carry the prior
        # snapshot's freshness while the replacement snapshot is in flight.
        self._invalidate_inventory()
        try:
            result=super().list_and_watch_once()
        except Exception:
            self._invalidate_inventory()
            raise
        if result in _CONTINUITY_BREAK_RESULTS:
            # EOF, reconnect/relist signals and shutdown all end the continuity
            # window for the validated list that preceded this watch.
            self._invalidate_inventory()
        return result
