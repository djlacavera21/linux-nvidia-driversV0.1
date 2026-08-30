"""Retry-safe watch dedupe for nvlx 1.6.2.7."""
from __future__ import annotations

from .runtime_v16 import _LIST_SETTLED_RESULTS
from .runtime_v1626 import Runtime as RuntimeV1626

_MISSING = object()


class Runtime(RuntimeV1626):
    """Commit watch dedupe state only after a settled reconciliation."""

    def _watch_event_disposition(self, obj: object, event_type: str) -> str:
        # A staged watch fingerprint is visible to duplicate detection during the
        # current reconciliation, but must be rolled back if reconciliation is
        # deferred or raises so an identical delivery can retry later.
        self._pending_watch_state = None
        if not self._object_identity_valid(obj):
            return "invalid"

        name, uid, generation, rv = self._watch_key(obj)
        key = self._watch_cache_key(name, uid)
        previous = self._watch_seen.get(key, _MISSING)
        disposition = super()._watch_event_disposition(obj, event_type)
        if disposition in {"reconcile", "reconcile-delete"}:
            self._pending_watch_state = (
                key,
                previous,
                event_type,
                uid,
                generation,
                rv,
            )
        return disposition

    def _restore_pending_watch_state(self) -> None:
        pending = getattr(self, "_pending_watch_state", None)
        self._pending_watch_state = None
        if pending is None:
            return
        key, previous, _event_type, _uid, _generation, _rv = pending
        if previous is _MISSING:
            self._watch_seen.pop(key, None)
        else:
            self._watch_seen[key] = previous

    def _clear_pending_watch_state(self) -> None:
        self._pending_watch_state = None

    def _pending_matches(self, obj: object, event_type: str) -> bool:
        pending = getattr(self, "_pending_watch_state", None)
        if pending is None or not self._object_identity_valid(obj):
            return False
        key, _previous, pending_type, uid, generation, rv = pending
        name, current_uid, current_generation, current_rv = self._watch_key(obj)
        return (
            pending_type == event_type
            and key == self._watch_cache_key(name, current_uid)
            and uid == current_uid
            and generation == current_generation
            and rv == current_rv
        )

    def reconcile_object(self, obj: dict, event_type: str = "MODIFIED") -> str:
        pending = getattr(self, "_pending_watch_state", None)
        if pending is not None and not self._pending_matches(obj, event_type):
            # Never let a staged fingerprint leak across an unrelated reconcile.
            self._restore_pending_watch_state()
            pending = None

        try:
            result = super().reconcile_object(obj, event_type=event_type)
        except Exception:
            if pending is not None:
                self._restore_pending_watch_state()
            raise

        if pending is not None:
            if result in _LIST_SETTLED_RESULTS:
                self._clear_pending_watch_state()
            else:
                self._restore_pending_watch_state()
        return result
