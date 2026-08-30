import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import Runtime

class Client:
    def __init__(self, items=None, events=None):
        self.items=items or []
        self.events=events or []
        self.patches=0
    def list_fleets(self): return ApiResponse(200,{"metadata":{"resourceVersion":"list-rv"},"items":self.items})
    def watch_path(self,rv): return "/watch"
    def watch_lines(self,path): yield from self.events
    def patch_status(self,name,rv,status):
        self.patches += 1
        return ApiResponse(200,{"metadata":{"name":name,"uid":"u1","generation":1,"resourceVersion":"next"},"status":status})
    def create_event(self,namespace,event):
        return ApiResponse(201,{"metadata":{"resourceVersion":"e1"},"regarding":event["regarding"],"reportingController":event["reportingController"],"reportingInstance":event["reportingInstance"]})

class V1617Tests(unittest.TestCase):
    def obj(self, rv="10", generation=1, uid="u1"):
        return {"metadata":{"name":"prod","uid":uid,"resourceVersion":rv,"generation":generation,"annotations":{"nvlx.io/approved":"true"}}}

    def test_list_seed_suppresses_exact_first_watch_duplicate(self):
        obj=self.obj()
        client=Client([obj],[{"type":"MODIFIED","object":obj}])
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        runtime.list_and_watch_once()
        self.assertEqual(runtime.stats.duplicate_watch_events,1)
        self.assertEqual(runtime.stats.relist_seeded_objects,1)

    def test_deleted_same_state_is_not_swallowed_by_list_seed(self):
        obj=self.obj()
        runtime=Runtime(Client(),"pod-a")
        runtime._seed_watch_state_from_list([obj])
        self.assertEqual(runtime._watch_event_disposition(obj,"DELETED"),"reconcile-delete")
        self.assertEqual(runtime.stats.deleted_watch_events,1)

    def test_deleted_without_deletion_timestamp_is_observe_only(self):
        runtime=Runtime(Client(),"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.obj(),event_type="DELETED"),"deleted-observed")

    def test_same_uid_generation_regression_remains_fenced_after_list_seed(self):
        runtime=Runtime(Client(),"pod-a")
        runtime._seed_watch_state_from_list([self.obj(rv="20",generation=4)])
        older=self.obj(rv="opaque-x",generation=3)
        self.assertEqual(runtime._watch_event_disposition(older,"MODIFIED"),"stale-generation")

    def test_new_uid_lower_generation_is_new_incarnation(self):
        runtime=Runtime(Client(),"pod-a")
        runtime._seed_watch_state_from_list([self.obj(rv="20",generation=4,uid="old")])
        replacement=self.obj(rv="r1",generation=1,uid="new")
        self.assertEqual(runtime._watch_event_disposition(replacement,"MODIFIED"),"reconcile")

if __name__=="__main__": unittest.main()
