import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v1624 import Runtime

class WatchClient:
    def __init__(self, events):
        self.events=list(events)
        self.runtime=None
        self.observed_fresh=False
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"list-rv"},"items":[]})
    def watch_path(self,rv): return f"/watch?rv={rv}"
    def watch_lines(self,path):
        if self.runtime is not None:
            self.observed_fresh=self.runtime.stats.inventory_fresh
        yield from self.events

class V1624Tests(unittest.TestCase):
    def runtime(self, events):
        client=WatchClient(events)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        client.runtime=runtime
        return runtime,client

    def test_malformed_watch_line_forces_relist(self):
        runtime,client=self.runtime([None])
        self.assertEqual(runtime.list_and_watch_once(),"relist")
        self.assertTrue(client.observed_fresh)
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertEqual(runtime.stats.reconcile_failures,1)
        self.assertEqual(runtime.stats.last_resource_version,"list-rv")

    def test_malformed_added_object_forces_relist(self):
        event={"type":"ADDED","object":{"metadata":{"name":"prod","resourceVersion":"2"}}}
        runtime,_client=self.runtime([event])
        self.assertEqual(runtime.list_and_watch_once(),"relist")
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertEqual(runtime.stats.reconcile_failures,1)
        self.assertEqual(runtime.stats.last_resource_version,"list-rv")

    def test_malformed_modified_object_forces_relist(self):
        event={"type":"MODIFIED","object":{"metadata":{"name":"prod","uid":"u1","resourceVersion":""}}}
        runtime,_client=self.runtime([event])
        self.assertEqual(runtime.list_and_watch_once(),"relist")
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertEqual(runtime.stats.reconcile_failures,1)

    def test_malformed_deleted_object_forces_relist(self):
        event={"type":"DELETED","object":{}}
        runtime,_client=self.runtime([event])
        self.assertEqual(runtime.list_and_watch_once(),"relist")
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertEqual(runtime.stats.reconcile_failures,1)

    def test_unknown_future_event_type_is_ignored(self):
        runtime,_client=self.runtime([{"type":"FUTURE_EVENT","object":{"anything":True}}])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_failures,0)
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_malformed_bookmark_does_not_break_state_continuity(self):
        runtime,_client=self.runtime([{"type":"BOOKMARK","object":{"metadata":{"resourceVersion":123}}}])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_failures,0)
        self.assertEqual(runtime.stats.last_resource_version,"list-rv")

if __name__=="__main__": unittest.main()
