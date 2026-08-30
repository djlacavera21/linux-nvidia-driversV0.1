import unittest
from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.runtime_v1622 import Runtime

class EmptyClient:
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"list-rv"},"items":[]})
    def watch_path(self,rv): return f"/watch?rv={rv}"
    def watch_lines(self,path):
        if False: yield None

class ReconnectClient(EmptyClient):
    def watch_lines(self,path):
        raise ApiError(0,"connection failed")
        yield None

class ListFailClient(EmptyClient):
    def list_fleets(self):
        raise ApiError(0,"list failed")

class V1622Tests(unittest.TestCase):
    def ready_runtime(self, client=None):
        runtime=Runtime(client or EmptyClient(),"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        runtime.stats.api_reachable=True
        runtime.stats.inventory_fresh=True
        self.assertTrue(runtime._leader())
        self.assertGreater(runtime._leader_verified_monotonic,0)
        return runtime

    def test_failed_probe_clears_previous_leadership_proof(self):
        answers=iter([True,False])
        runtime=Runtime(EmptyClient(),"pod-a",leader_check=lambda:next(answers),leader_fresh_seconds=25)
        self.assertTrue(runtime._leader())
        self.assertGreater(runtime._leader_verified_monotonic,0)
        self.assertFalse(runtime._leader())
        self.assertFalse(runtime.stats.leader)
        self.assertEqual(runtime._leader_verified_monotonic,0.0)

    def test_api_unreachable_readiness_clears_cached_proof(self):
        runtime=self.ready_runtime()
        runtime.stats.api_reachable=False
        self.assertFalse(runtime.ready())
        self.assertFalse(runtime.stats.leader)
        self.assertEqual(runtime._leader_verified_monotonic,0.0)

    def test_stale_readiness_clears_cached_timestamp(self):
        runtime=self.ready_runtime()
        runtime._leader_verified_monotonic -= 26
        self.assertFalse(runtime.ready())
        self.assertFalse(runtime.stats.leader)
        self.assertEqual(runtime._leader_verified_monotonic,0.0)

    def test_watch_transport_loss_invalidates_leadership_before_return(self):
        runtime=Runtime(ReconnectClient(),"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        self.assertEqual(runtime.list_and_watch_once(),"reconnect")
        self.assertFalse(runtime.stats.api_reachable)
        self.assertFalse(runtime.stats.leader)
        self.assertEqual(runtime._leader_verified_monotonic,0.0)

    def test_list_exception_invalidates_leadership_before_propagating(self):
        runtime=Runtime(ListFailClient(),"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        with self.assertRaises(ApiError): runtime.list_and_watch_once()
        self.assertFalse(runtime.stats.leader)
        self.assertEqual(runtime._leader_verified_monotonic,0.0)

    def test_successful_empty_relist_keeps_recent_verified_leadership(self):
        runtime=Runtime(EmptyClient(),"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertTrue(runtime.stats.api_reachable)
        self.assertTrue(runtime.ready())
        self.assertGreater(runtime._leader_verified_monotonic,0)

if __name__=="__main__": unittest.main()
