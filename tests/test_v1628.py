import unittest

from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.runtime_v1628 import Runtime


def fleet(*, rv="11", generation=1, deleting=False, approved=False, finalizers=None):
    meta = {
        "name": "prod",
        "uid": "u1",
        "generation": generation,
        "resourceVersion": rv,
        "annotations": {"nvlx.io/approved": "true"} if approved else {},
        "finalizers": list(finalizers or []),
    }
    if deleting:
        meta["deletionTimestamp"] = "2026-08-30T00:00:00Z"
    return {"metadata": meta, "status": {"quarantined_nodes": 0}}


class WatchClient:
    def __init__(self, *, items=None, events=None, list_rv="list-rv"):
        self.items = list(items or [])
        self.events = list(events or [])
        self.list_rv = list_rv
        self.consumed = 0

    def list_fleets(self):
        return ApiResponse(200, {"metadata": {"resourceVersion": self.list_rv}, "items": self.items})

    def watch_path(self, rv):
        return f"/watch?resourceVersion={rv}"

    def watch_lines(self, path):
        for event in self.events:
            self.consumed += 1
            yield event


class FailingPatchClient:
    def patch_status(self, name, rv, status):
        raise ApiError(403, "forbidden")


class V1628Tests(unittest.TestCase):
    def test_deferred_reconcile_rolls_back_cursor(self):
        runtime = Runtime(WatchClient(), "pod-a", leader_check=lambda: False)
        runtime.stats.last_resource_version = "prior-rv"
        result = runtime.reconcile_object(fleet(rv="11"), event_type="MODIFIED")
        self.assertEqual(result, "standby")
        self.assertEqual(runtime.stats.last_resource_version, "prior-rv")

    def test_reconcile_exception_rolls_back_cursor(self):
        runtime = Runtime(FailingPatchClient(), "pod-a", leader_check=lambda: True)
        runtime.stats.last_resource_version = "prior-rv"
        with self.assertRaises(ApiError):
            runtime.reconcile_object(fleet(rv="11", approved=True), event_type="MODIFIED")
        self.assertEqual(runtime.stats.last_resource_version, "prior-rv")

    def test_deferred_watch_event_forces_relist_before_bookmark(self):
        obj = fleet(rv="11")
        client = WatchClient(events=[
            {"type": "MODIFIED", "object": obj},
            {"type": "BOOKMARK", "object": {"metadata": {"resourceVersion": "12"}}},
        ])
        runtime = Runtime(client, "pod-a", leader_check=lambda: False)
        self.assertEqual(runtime.list_and_watch_once(), "relist")
        self.assertEqual(client.consumed, 1)
        self.assertEqual(runtime.stats.last_resource_version, "list-rv")
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertEqual(runtime.stats.relist_deferred_objects, 1)
        self.assertNotIn("u1", runtime._watch_seen)

    def test_settled_deleted_event_advances_cursor(self):
        obj = fleet(rv="11")
        client = WatchClient(events=[{"type": "DELETED", "object": obj}])
        runtime = Runtime(client, "pod-a", leader_check=lambda: False)
        self.assertEqual(runtime.list_and_watch_once(), "eof")
        self.assertEqual(runtime.stats.last_resource_version, "11")
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_duplicate_settled_delivery_can_advance_cursor(self):
        obj = fleet(rv="11", generation=2, deleting=True)
        client = WatchClient(items=[obj], events=[{"type": "MODIFIED", "object": obj}], list_rv="list-rv")
        runtime = Runtime(client, "pod-a", leader_check=lambda: False)
        self.assertEqual(runtime.list_and_watch_once(), "eof")
        self.assertEqual(runtime.stats.duplicate_watch_events, 1)
        self.assertEqual(runtime.stats.last_resource_version, "11")

    def test_stale_generation_breaks_watch_continuity_without_cursor_advance(self):
        listed = fleet(rv="10", generation=2, deleting=True)
        stale = fleet(rv="11", generation=1, deleting=True)
        client = WatchClient(items=[listed], events=[{"type": "MODIFIED", "object": stale}], list_rv="list-rv")
        runtime = Runtime(client, "pod-a", leader_check=lambda: False)
        self.assertEqual(runtime.list_and_watch_once(), "relist")
        self.assertEqual(runtime.stats.last_resource_version, "list-rv")
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertEqual(runtime.stats.stale_generation_events, 1)

    def test_valid_bookmark_advances_cursor_when_no_work_is_deferred(self):
        client = WatchClient(events=[
            {"type": "BOOKMARK", "object": {"metadata": {"resourceVersion": "20"}}},
        ])
        runtime = Runtime(client, "pod-a", leader_check=lambda: True)
        self.assertEqual(runtime.list_and_watch_once(), "eof")
        self.assertEqual(runtime.stats.last_resource_version, "20")

    def test_malformed_bookmark_does_not_replace_cursor(self):
        client = WatchClient(events=[
            {"type": "BOOKMARK", "object": {"metadata": {"resourceVersion": 20}}},
        ])
        runtime = Runtime(client, "pod-a", leader_check=lambda: True)
        self.assertEqual(runtime.list_and_watch_once(), "eof")
        self.assertEqual(runtime.stats.last_resource_version, "list-rv")


if __name__ == "__main__":
    unittest.main()
