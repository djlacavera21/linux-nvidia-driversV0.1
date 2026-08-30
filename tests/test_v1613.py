import unittest
from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.runtime_v16 import Runtime, PROTECTIVE_FINALIZER

class ConflictClient:
    def __init__(self, fresh_meta):
        self.fresh_meta=fresh_meta
        self.patches=0
        self.gets=0
    def patch_status(self,name,rv,status):
        self.patches += 1
        if self.patches == 1:
            raise ApiError(409,"conflict")
        generation=int(self.fresh_meta.get("generation",4) or 0)
        return ApiResponse(200,{"metadata":{"name":name,"uid":"u1","generation":generation,"resourceVersion":"12"},"status":status})
    def get_fleet(self,name):
        self.gets += 1
        return ApiResponse(200,{"metadata":self.fresh_meta})

class V1613Tests(unittest.TestCase):
    def obj(self):
        return {"metadata":{"name":"prod","uid":"u1","resourceVersion":"10","generation":4}}

    def test_conflict_refetch_same_identity_and_generation_can_retry(self):
        client=ConflictClient({"name":"prod","uid":"u1","resourceVersion":"11","generation":4})
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertTrue(runtime._patch_status(self.obj(),{"phase":"Ready"}))
        self.assertEqual(client.patches,2)
        self.assertEqual(client.gets,1)

    def test_conflict_refetch_new_generation_recomputes_before_retry(self):
        client=ConflictClient({"name":"prod","uid":"u1","resourceVersion":"11","generation":5})
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertTrue(runtime._patch_status(self.obj(),{"phase":"Ready"}))
        self.assertEqual(client.patches,2)
        self.assertEqual(runtime.stats.status_conflict_recomputes,1)

    def test_conflict_refetch_uid_change_blocks_old_plan_retry(self):
        client=ConflictClient({"name":"prod","uid":"replacement","resourceVersion":"11","generation":4})
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertFalse(runtime._patch_status(self.obj(),{"phase":"Ready"}))
        self.assertEqual(client.patches,1)

    def test_status_success_must_echo_planned_status_fields(self):
        expected={"name":"prod","uid":"u1","generation":4}
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":4,"resourceVersion":"11"},"status":{"phase":"Degraded"}})
        self.assertFalse(Runtime._status_response_verified(response,expected,{"phase":"Ready"}))

    def test_finalizer_success_requires_protective_finalizer_absent(self):
        still_present=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"11","finalizers":[PROTECTIVE_FINALIZER]}})
        cleared=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"12","finalizers":["other.example/finalizer"]}})
        self.assertFalse(Runtime._finalizer_response_verified(still_present,"prod",[]))
        self.assertTrue(Runtime._finalizer_response_verified(cleared,"prod",["other.example/finalizer"]))

    def test_finalizer_success_requires_finalizer_list(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"11"}})
        self.assertFalse(Runtime._finalizer_response_verified(response,"prod",[]))

if __name__=="__main__": unittest.main()
