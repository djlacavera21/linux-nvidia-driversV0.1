"""Settlement-bound watch cursor semantics for nvlx 1.6.2.8."""
from __future__ import annotations

from .k8s_api_v16 import ApiError
from .runtime_guard_v161 import classify_watch_line
from .runtime_v16 import _LIST_SETTLED_RESULTS
from .runtime_v1627 import Runtime as RuntimeV1627

_CONTINUITY_BREAK_RESULTS = {"relist", "reconnect", "watch-error", "eof", "stopped"}


class Runtime(RuntimeV1627):
    """Advance the watch cursor only after trusted, settled work."""

    def reconcile_object(self, obj: dict, *, event_type: str = "MODIFIED") -> str:
        previous_cursor = self.stats.last_resource_version
        try:
            result = super().reconcile_object(obj, event_type=event_type)
        except Exception:
            self.stats.last_resource_version = previous_cursor
            raise
        if result not in _LIST_SETTLED_RESULTS:
            self.stats.last_resource_version = previous_cursor
        return result

    def _finish_watch_cycle(self, result: str) -> str:
        if result in _CONTINUITY_BREAK_RESULTS:
            self._invalidate_inventory()
        return result

    def _corrupt_watch_relist(self) -> str:
        self.stats.reconcile_failures += 1
        self._invalidate_inventory()
        return "relist"

    def _advance_cursor_from_object(self, obj: object) -> bool:
        if not self._object_identity_valid(obj):
            return False
        rv = obj["metadata"]["resourceVersion"]
        self.stats.last_resource_version = rv
        return True

    def list_and_watch_once(self) -> str:
        self._invalidate_inventory()
        self._leader()
        try:
            listing = self.client.list_fleets()
            self.stats.api_reachable = True
            body = listing.body
            if not isinstance(body, dict):
                raise RuntimeError("GPUFleet list body must be an object")
            metadata = body.get("metadata")
            if not isinstance(metadata, dict):
                raise RuntimeError("GPUFleet list metadata must be an object")
            rv = metadata.get("resourceVersion", "")
            if not isinstance(rv, str) or not rv:
                raise RuntimeError("GPUFleet list did not return resourceVersion")
            items = body.get("items", [])
            if not isinstance(items, list):
                raise RuntimeError("GPUFleet list items must be a list")
            if not all(self._object_identity_valid(item) for item in items):
                raise RuntimeError("GPUFleet list contains invalid object identity")

            self._prune_watch_state_from_list(items)
            settled = []
            for item in items:
                if self._stop.is_set():
                    return self._finish_watch_cycle("stopped")
                result = self.reconcile_object(item, event_type="ADDED")
                if result in _LIST_SETTLED_RESULTS:
                    settled.append(item)
                else:
                    self.stats.relist_deferred_objects += 1
            self._seed_watch_state_from_list(settled)
            self.stats.inventory_fresh = True
            self.stats.last_resource_version = rv

            try:
                for event in self.client.watch_lines(self.client.watch_path(rv)):
                    if self._stop.is_set():
                        return self._finish_watch_cycle("stopped")
                    decision = classify_watch_line(event)
                    if decision.action == "ignore-malformed":
                        return self._corrupt_watch_relist()
                    if decision.action == "ignore-unknown":
                        continue
                    if decision.action in {"relist", "reconnect", "watch-error"}:
                        return self._finish_watch_cycle(decision.action)

                    obj = event.get("object") or {}
                    if decision.action == "bookmark":
                        if isinstance(obj, dict):
                            bookmark_meta = obj.get("metadata")
                            if isinstance(bookmark_meta, dict):
                                bookmark_rv = bookmark_meta.get("resourceVersion")
                                if isinstance(bookmark_rv, str) and bookmark_rv:
                                    self.stats.last_resource_version = bookmark_rv
                        continue

                    event_type = decision.action.upper()
                    disposition = self._watch_event_disposition(obj, event_type)
                    if disposition == "invalid":
                        return self._corrupt_watch_relist()
                    if disposition == "duplicate":
                        self._advance_cursor_from_object(obj)
                        continue
                    if disposition == "stale-generation":
                        self.stats.reconcile_failures += 1
                        self._invalidate_inventory()
                        return "relist"

                    previous_cursor = self.stats.last_resource_version
                    try:
                        result = self.reconcile_object(obj, event_type=event_type)
                    except Exception:
                        self.stats.last_resource_version = previous_cursor
                        raise
                    if result not in _LIST_SETTLED_RESULTS:
                        self.stats.last_resource_version = previous_cursor
                        self.stats.relist_deferred_objects += 1
                        self._invalidate_inventory()
                        return "relist"
                    self._advance_cursor_from_object(obj)

                return self._finish_watch_cycle("eof")
            except ApiError as e:
                self.stats.api_reachable = False
                self._invalidate_leadership()
                if e.status == 410:
                    return self._finish_watch_cycle("relist")
                if e.status == 0 or e.status in {408, 425, 429} or 500 <= e.status <= 599:
                    return self._finish_watch_cycle("reconnect")
                raise
        except Exception:
            self._invalidate_inventory()
            self._invalidate_leadership()
            raise
