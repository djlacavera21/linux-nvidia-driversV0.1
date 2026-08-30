import unittest
from unittest.mock import patch

from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v1628 import Runtime as RuntimeV1628
from nvlx.runtime_v1629 import Runtime


def fleet(name="prod", uid="u1", rv="10", generation=1):
    return {"metadata":{"name":name,"uid":uid,"resourceVersion":rv,"generation":generation,"annotations":{}}}


class FakeClient:
    def __init__(self, items, watch=None):
        self.items=items
        self.watch=list(watch or [])
        self.watch_calls=0
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"100"},"items":self.items},{})
    def watch_path(self, rv):
        return "/watch?resourceVersion="+rv
    def watch_lines(self, path):
        self.watch_calls += 1
        yield from self.watch


class RelistSettlementBarrierTests(unittest.TestCase):
    def test_deferred_list_object_returns_relist_without_opening_watch(self):
        c=FakeClient([fleet()],[{"type":"BOOKMARK","object":{"metadata":{"resourceVersion":"999"}}}])
        r=Runtime(c,"pod-a",leader_check=lambda:False)
        self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertEqual(c.watch_calls,0)
        self.assertFalse(r.stats.inventory_fresh)
        self.assertEqual(r.stats.last_resource_version,"")
        self.assertEqual(r.stats.relist_deferred_objects,1)
        self.assertNotIn("u1",r._watch_seen)

    def test_mixed_settled_and_deferred_snapshot_is_atomic(self):
        c=FakeClient([fleet("a","u1","10"),fleet("b","u2","11")])
        r=Runtime(c,"pod-a",leader_check=lambda:True)
        results=iter(["patched","fenced"])
        with patch.object(RuntimeV1628,"reconcile_object",side_effect=lambda *a,**k: next(results)):
            self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertEqual(c.watch_calls,0)
        self.assertFalse(r.stats.inventory_fresh)
        self.assertEqual(r._watch_seen,{})

    def test_fully_settled_snapshot_can_open_watch(self):
        c=FakeClient([fleet()])
        r=Runtime(c,"pod-a",leader_check=lambda:True)
        with patch.object(RuntimeV1628,"reconcile_object",return_value="patched"):
            self.assertEqual(r.list_and_watch_once(),"eof")
        self.assertEqual(c.watch_calls,1)
        self.assertIn("u1",r._watch_seen)

    def test_barrier_resets_each_cycle(self):
        c=FakeClient([fleet()])
        r=Runtime(c,"pod-a",leader_check=lambda:True)
        with patch.object(RuntimeV1628,"reconcile_object",return_value="standby"):
            self.assertEqual(r.list_and_watch_once(),"relist")
        c.items=[fleet(rv="12")]
        with patch.object(RuntimeV1628,"reconcile_object",return_value="patched"):
            self.assertEqual(r.list_and_watch_once(),"eof")
        self.assertEqual(c.watch_calls,1)


if __name__=="__main__": unittest.main()
