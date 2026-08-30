import unittest
from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.runtime_v16 import Runtime, PROTECTIVE_FINALIZER

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

class ConflictClient:
    def __init__(self,fresh):
        self.fresh=fresh
        self.patches=0
    def patch_status(self,name,rv,status):
        self.patches += 1
        raise ApiError(409,"conflict")
    def get_fleet(self,name):
        return ApiResponse(200,self.fresh)

class V1619Tests(unittest.TestCase):
    def fleet(self, **meta):
        m={"name":"prod","uid":"u1","resourceVersion":"10","generation":1,"annotations":{"nvlx.io/approved":"true"}}
        m.update(meta)
        return {"metadata":m}

    def test_missing_uid_is_invalid_identity(self):
        obj=self.fleet(); obj["metadata"].pop("uid")
        self.assertFalse(Runtime._object_identity_valid(obj))
        runtime=Runtime(Client(),"pod-a")
        self.assertEqual(runtime.reconcile_object(obj),"invalid")

    def test_blank_uid_is_invalid_identity(self):
        self.assertFalse(Runtime._object_identity_valid(self.fleet(uid="")))
        self.assertFalse(Runtime._object_identity_valid(self.fleet(uid="   ")))

    def test_list_missing_uid_aborts_before_reconcile(self):
        obj=self.fleet(); obj["metadata"].pop("uid")
        client=Client(items=[obj])
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        with self.assertRaises(RuntimeError): runtime.list_and_watch_once()
        self.assertEqual(client.patches,0)
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_watch_missing_uid_is_ignored_and_counted(self):
        obj=self.fleet(); obj["metadata"].pop("uid")
        client=Client(events=[{"type":"MODIFIED","object":obj}])
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_failures,1)
        self.assertEqual(client.patches,0)

    def test_status_response_requires_exact_uid_echo(self):
        expected={"name":"prod","uid":"u1","generation":1}
        missing=ApiResponse(200,{"metadata":{"name":"prod","generation":1,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        wrong=ApiResponse(200,{"metadata":{"name":"prod","uid":"u2","generation":1,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        good=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":1,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertFalse(Runtime._status_response_verified(missing,expected,{"phase":"Ready"}))
        self.assertFalse(Runtime._status_response_verified(wrong,expected,{"phase":"Ready"}))
        self.assertTrue(Runtime._status_response_verified(good,expected,{"phase":"Ready"}))

    def test_conflict_refetch_requires_uid(self):
        original=self.fleet()["metadata"]
        fresh={"metadata":{"name":"prod","resourceVersion":"11","generation":1}}
        self.assertFalse(Runtime._same_incarnation(fresh,original))

    def test_conflict_retry_stops_when_refetch_uid_missing(self):
        client=ConflictClient({"metadata":{"name":"prod","resourceVersion":"11","generation":1}})
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertFalse(runtime._patch_status(self.fleet(),{"phase":"Ready"}))
        self.assertEqual(client.patches,1)

    def test_finalizer_response_is_bound_to_expected_uid(self):
        wrong=ApiResponse(200,{"metadata":{"name":"prod","uid":"u2","resourceVersion":"11","finalizers":["other.example/finalizer"]}})
        good=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","resourceVersion":"12","finalizers":["other.example/finalizer"]}})
        self.assertFalse(Runtime._finalizer_response_verified(wrong,"prod",["other.example/finalizer"],"u1"))
        self.assertTrue(Runtime._finalizer_response_verified(good,"prod",["other.example/finalizer"],"u1"))

    def test_finalizer_still_rejects_protective_finalizer_with_uid(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","resourceVersion":"11","finalizers":[PROTECTIVE_FINALIZER]}})
        self.assertFalse(Runtime._finalizer_response_verified(response,"prod",[],"u1"))

if __name__=="__main__": unittest.main()
