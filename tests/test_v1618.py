import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import Runtime

class Client:
    def __init__(self, items=None, events=None):
        self.items=items or []
        self.events=events or []
        self.patches=0
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"list-rv"},"items":self.items})
    def watch_path(self,rv): return "/watch"
    def watch_lines(self,path): yield from self.events
    def patch_status(self,name,rv,status):
        self.patches += 1
        return ApiResponse(200,{"metadata":{"name":name,"uid":"u1","generation":1,"resourceVersion":"next"},"status":status})
    def create_event(self,namespace,event):
        return ApiResponse(201,{"metadata":{"resourceVersion":"e1"},"regarding":event["regarding"],"reportingController":event["reportingController"],"reportingInstance":event["reportingInstance"]})

class V1618Tests(unittest.TestCase):
    def obj(self, name="prod", rv="10", generation=1, uid="u1"):
        return {"metadata":{"name":name,"uid":uid,"resourceVersion":rv,"generation":generation,"annotations":{"nvlx.io/approved":"true"}}}

    def test_deferred_list_item_is_not_seeded_and_watch_can_retry(self):
        obj=self.obj()
        client=Client([obj],[{"type":"MODIFIED","object":obj}])
        states=iter([False,True,True,True])
        runtime=Runtime(client,"pod-a",leader_check=lambda:next(states,True))
        runtime.list_and_watch_once()
        self.assertEqual(runtime.stats.relist_deferred_objects,1)
        self.assertEqual(runtime.stats.relist_seeded_objects,0)
        self.assertEqual(runtime.stats.duplicate_watch_events,0)
        self.assertEqual(client.patches,1)

    def test_settled_list_item_seeds_watch_cache(self):
        obj=self.obj()
        client=Client([obj],[])
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        runtime.list_and_watch_once()
        self.assertEqual(runtime.stats.relist_seeded_objects,1)
        self.assertEqual(len(runtime._watch_seen),1)

    def test_relist_prunes_absent_object_cache_entries(self):
        runtime=Runtime(Client(),"pod-a")
        first=self.obj(name="one",uid="u1")
        second=self.obj(name="two",uid="u2")
        runtime._seed_watch_state_from_list([first,second])
        runtime._prune_watch_state_from_list([second])
        self.assertNotIn("u1",runtime._watch_seen)
        self.assertIn("u2",runtime._watch_seen)
        self.assertEqual(runtime.stats.watch_cache_pruned,1)

    def test_watch_cache_is_bounded_with_deterministic_eviction(self):
        runtime=Runtime(Client(),"pod-a",watch_cache_limit=2)
        a=self.obj(name="a",uid="a",rv="a")
        b=self.obj(name="b",uid="b",rv="b")
        c=self.obj(name="c",uid="c",rv="c")
        self.assertEqual(runtime._watch_event_disposition(a,"MODIFIED"),"reconcile")
        self.assertEqual(runtime._watch_event_disposition(b,"MODIFIED"),"reconcile")
        self.assertEqual(runtime._watch_event_disposition(c,"MODIFIED"),"reconcile")
        self.assertEqual(len(runtime._watch_seen),2)
        self.assertNotIn("a",runtime._watch_seen)
        self.assertEqual(runtime.stats.watch_cache_evictions,1)

    def test_invalid_watch_cache_limits_fail_closed(self):
        for value in (0,-1,True,1.5):
            with self.assertRaises(ValueError):
                Runtime(Client(),"pod-a",watch_cache_limit=value)

    def test_generation_regression_fencing_survives_cache_lifecycle(self):
        runtime=Runtime(Client(),"pod-a",watch_cache_limit=2)
        current=self.obj(uid="u1",generation=4,rv="opaque-a")
        runtime._seed_watch_state_from_list([current])
        stale=self.obj(uid="u1",generation=3,rv="opaque-b")
        self.assertEqual(runtime._watch_event_disposition(stale,"MODIFIED"),"stale-generation")
        self.assertEqual(runtime.stats.stale_generation_events,1)

if __name__=="__main__": unittest.main()
