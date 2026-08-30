"""Cycle-scoped watch checkpoint integrity for nvlx 1.6.2.9."""
from __future__ import annotations

from .runtime_v1628 import Runtime as RuntimeV1628


class Runtime(RuntimeV1628):
    """Keep the trusted cursor anchored to the active list/watch cycle."""

    def __post_init__(self):
        super().__post_init__()
        self._watch_cycle_anchor = ""
        self._watch_cycle_cursor = ""

    def _begin_watch_cycle(self, rv: str) -> None:
        if not isinstance(rv, str) or not rv:
            raise ValueError("watch cycle resourceVersion must be nonempty")
        self._watch_cycle_anchor = rv
        self._watch_cycle_cursor = rv
        self.stats.last_resource_version = rv

    def _advance_cycle_cursor(self, rv: object) -> bool:
        if not isinstance(rv, str) or not rv:
            return False
        self._watch_cycle_cursor = rv
        self.stats.last_resource_version = rv
        return True

    def _advance_cursor_from_object(self, obj: object) -> bool:
        if not self._object_identity_valid(obj):
            return False
        return self._advance_cycle_cursor(obj["metadata"]["resourceVersion"])

    def _finish_watch_cycle(self, result: str) -> str:
        if result in {"relist", "reconnect", "watch-error", "eof", "stopped"}:
            # The last trusted cycle cursor remains diagnostic state only. A new
            # list is mandatory before another watch starts; no opaque RV is
            # carried into a fresh continuity window.
            self._invalidate_inventory()
            self._watch_cycle_anchor = ""
            self._watch_cycle_cursor = ""
        return result

    def list_and_watch_once(self) -> str:
        # v1.6.2.8 already forces a list before every watch.  Intercept cursor
        # writes so BOOKMARK/object advancement is mirrored into a cycle-local
        # checkpoint and assert that no stale checkpoint survives a new call.
        self._watch_cycle_anchor = ""
        self._watch_cycle_cursor = ""
        return super().list_and_watch_once()

    def reconcile_object(self, obj: dict, *, event_type: str = "MODIFIED") -> str:
        previous_stats_cursor = self.stats.last_resource_version
        previous_cycle_cursor = self._watch_cycle_cursor
        result = super().reconcile_object(obj, event_type=event_type)
        if result not in {"patched", "status-noop", "event-noop", "checkpoint", "finalized", "deleted-observed", "observe-delete"}:
            self.stats.last_resource_version = previous_stats_cursor
            self._watch_cycle_cursor = previous_cycle_cursor
        return result
