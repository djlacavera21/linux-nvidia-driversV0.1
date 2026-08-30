import unittest
from datetime import datetime, timedelta, timezone
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.lease_v16 import LeaseElector
from nvlx.runtime_v1621 import Runtime

class EmptyClient:
    def __init__(self):
        self.watch_paths=[]
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"list-rv"},"items":[]})
    def watch_path(self,rv):
        path=f"/watch?rv={rv}"
        self.watch_paths.append(path)
        return path
    def watch_lines(self,path):
        if False:
            yield None

class V1621Tests(unittest.TestCase):
    def test_future_dated_lease_beyond_skew_is_not_fresh(self):
        elector=LeaseElector(object(),"pod-a",duration_seconds=30,max_clock_skew_seconds=5)
        now=datetime(2026,8,30,2,0,0,tzinfo=timezone.utc)
        spec={"renewTime":(now+timedelta(seconds=6)).isoformat().replace("+00:00","Z"),"leaseDurationSeconds":30}
        self.assertFalse(elector._fresh(spec,now))

    def test_small_clock_skew_is_tolerated(self):
        elector=LeaseElector(object(),"pod-a",duration_seconds=30,max_clock_skew_seconds=5)
        now=datetime(2026,8,30,2,0,0,tzinfo=timezone.utc)
        spec={"renewTime":(now+timedelta(seconds=4)).isoformat().replace("+00:00","Z"),"leaseDurationSeconds":30}
        self.assertTrue(elector._fresh(spec,now))

    def test_naive_lease_timestamp_fails_closed(self):
        elector=LeaseElector(object(),"pod-a")
        now=datetime(2026,8,30,2,0,0,tzinfo=timezone.utc)
        self.assertFalse(elector._fresh({"renewTime":"2026-08-30T02:00:00","leaseDurationSeconds":30},now))

    def test_empty_relist_still_verifies_leadership(self):
        calls=[]
        runtime=Runtime(EmptyClient(),"pod-a",leader_check=lambda:(calls.append("leader") or True),leader_fresh_seconds=25)
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(calls,["leader"])
        self.assertTrue(runtime.stats.inventory_fresh)
        self.assertTrue(runtime.ready())

    def test_readiness_expires_when_leadership_is_stale(self):
        runtime=Runtime(EmptyClient(),"pod-a",leader_check=lambda:True,leader_fresh_seconds=25)
        runtime.stats.api_reachable=True
        runtime.stats.inventory_fresh=True
        self.assertTrue(runtime._leader())
        self.assertTrue(runtime.ready())
        runtime._leader_verified_monotonic -= 26
        self.assertFalse(runtime.ready())
        self.assertFalse(runtime.stats.leader)

    def test_invalid_leader_fresh_window_fails_closed(self):
        for value in (0,-1,True):
            with self.assertRaises(ValueError):
                Runtime(EmptyClient(),"pod-a",leader_fresh_seconds=value)

if __name__=="__main__": unittest.main()
