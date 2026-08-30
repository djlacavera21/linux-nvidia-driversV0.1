import unittest
from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.runtime_v1623 import Runtime

class WatchClient:
    def __init__(self, *, events=None, watch_error=None, malformed_list=False):
        self.events=list(events or [])
        self.watch_error=watch_error
        self.malformed_list=malformed_list
        self.runtime=None
        self.observed_fresh=False
    def list_fleets(self):
        if self.malformed_list:
            return ApiResponse(200,{"metadata":{},"items":[]})
        return ApiResponse(200,{"metadata":{"resourceVersion":"list-rv"},"items":[]})
    def watch_path(self,rv): return f"/watch?rv={rv}"
    def watch_lines(self,path):
        if self.runtime is not None:
            self.observed_fresh=self.runtime.stats.inventory_fresh
        if self.watch_error is not None:
            raise self.watch_error
        yield from self.events

class V1623Tests(unittest.TestCase):
    def runtime(self, client):
        runtime=Runtime(client,"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        client.runtime=runtime
        return runtime

    def test_clean_watch_eof_invalidates_inventory(self):
        client=WatchClient()
        runtime=self.runtime(client)
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertTrue(client.observed_fresh)
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertFalse(runtime.ready())

    def test_410_relist_invalidates_inventory_after_valid_snapshot(self):
        client=WatchClient(events=[{"type":"ERROR","object":{"code":410}}])
        runtime=self.runtime(client)
        self.assertEqual(runtime.list_and_watch_once(),"relist")
        self.assertTrue(client.observed_fresh)
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_transient_watch_transport_failure_invalidates_inventory(self):
        client=WatchClient(watch_error=ApiError(0,"connection failed"))
        runtime=self.runtime(client)
        self.assertEqual(runtime.list_and_watch_once(),"reconnect")
        self.assertTrue(client.observed_fresh)
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertFalse(runtime.stats.api_reachable)
        self.assertFalse(runtime.stats.leader)

    def test_nonretryable_watch_error_invalidates_inventory(self):
        client=WatchClient(events=[{"type":"ERROR","object":{"code":403}}])
        runtime=self.runtime(client)
        self.assertEqual(runtime.list_and_watch_once(),"watch-error")
        self.assertTrue(client.observed_fresh)
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_malformed_replacement_list_cannot_reuse_old_freshness(self):
        client=WatchClient(malformed_list=True)
        runtime=self.runtime(client)
        runtime.stats.inventory_fresh=True
        with self.assertRaises(RuntimeError):
            runtime.list_and_watch_once()
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertFalse(runtime.stats.leader)

    def test_stop_invalidates_inventory_and_leadership(self):
        client=WatchClient()
        runtime=self.runtime(client)
        runtime.stats.inventory_fresh=True
        self.assertTrue(runtime._leader())
        runtime.stop()
        self.assertFalse(runtime.stats.inventory_fresh)
        self.assertFalse(runtime.stats.leader)
        self.assertFalse(runtime.ready())

if __name__=="__main__": unittest.main()
