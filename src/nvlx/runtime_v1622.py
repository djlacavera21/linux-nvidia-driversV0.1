"""Leadership-invalidation runtime wrapper for nvlx 1.6.2.2."""
from __future__ import annotations
from .runtime_v1621 import Runtime as RuntimeV1621

class Runtime(RuntimeV1621):
    """Fail closed by invalidating cached leadership on transport/readiness loss."""

    def _invalidate_leadership(self) -> None:
        self.stats.leader=False
        self._leader_verified_monotonic=0.0

    def stop(self):
        super().stop()
        self._invalidate_leadership()

    def leadership_fresh(self) -> bool:
        fresh=super().leadership_fresh()
        if not fresh:
            self._invalidate_leadership()
        return fresh

    def ready(self) -> bool:
        # API loss invalidates the cached proof immediately rather than merely
        # relying on api_reachable to make readiness false.
        if not self.stats.api_reachable:
            self._invalidate_leadership()
            return False
        return super().ready()

    def list_and_watch_once(self) -> str:
        try:
            result=super().list_and_watch_once()
        except Exception:
            # A failed list/relist may bypass the base watch error path; never
            # retain a previous successful Lease verification across it.
            self._invalidate_leadership()
            raise
        if not self.stats.api_reachable:
            # The base runtime marks watch transport/API failures unreachable
            # before returning reconnect/relist outcomes. Clear cached Lease
            # freshness in the same call boundary.
            self._invalidate_leadership()
        return result
