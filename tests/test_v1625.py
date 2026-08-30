import unittest
from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.runtime_v16 import PROTECTIVE_FINALIZER
from nvlx.runtime_v1625 import Runtime


def fleet(*, generation=4, rv="10"):
    return {
        "metadata": {
            "name": "prod",
            "uid": "u1",
            "generation": generation,
            "resourceVersion": rv,
            "deletionTimestamp": "2026-08-30T00:00:00Z",
            "finalizers": ["other.example/one", PROTECTIVE_FINALIZER],
            "annotations": {},
        },
        "status": {"quarantined_nodes": 0},
    }


class FinalizerClient:
    def __init__(self, responses, fresh=None):
        self.responses=list(responses)
        self.fresh=fresh
        self.patches=[]
    def patch_finalizers(self,name,rv,finalizers):
        self.patches.append((name,rv,list(finalizers)))
        value=self.responses.pop(0)
        if isinstance(value,Exception):
            raise value
        return value
    def get_fleet(self,name):
        return ApiResponse(200,self.fresh)


class V1625Tests(unittest.TestCase):
    def test_status_response_requires_generation_presence(self):
        expected={"name":"prod","uid":"u1","generation":4}
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertFalse(Runtime._status_response_verified(response,expected,{"phase":"Ready"}))

    def test_status_response_requires_exact_generation(self):
        expected={"name":"prod","uid":"u1","generation":4}
        good=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":4,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        bad=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":5,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertTrue(Runtime._status_response_verified(good,expected,{"phase":"Ready"}))
        self.assertFalse(Runtime._status_response_verified(bad,expected,{"phase":"Ready"}))

    def test_status_response_rejects_missing_expected_generation(self):
        expected={"name":"prod","uid":"u1"}
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":0,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertFalse(Runtime._status_response_verified(response,expected,{"phase":"Ready"}))

    def test_finalizer_response_requires_generation_presence_and_equality(self):
        expected=fleet()["metadata"]
        missing=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","resourceVersion":"11","finalizers":["other.example/one"]}})
        wrong=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":5,"resourceVersion":"11","finalizers":["other.example/one"]}})
        good=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":4,"resourceVersion":"11","finalizers":["other.example/one"]}})
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(missing,expected,["other.example/one"]))
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(wrong,expected,["other.example/one"]))
        self.assertTrue(Runtime._finalizer_response_verified_for_meta(good,expected,["other.example/one"]))

    def test_finalizer_success_without_generation_fails_closed(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","resourceVersion":"11","finalizers":["other.example/one"]}})
        runtime=Runtime(FinalizerClient([response]),"pod-a",leader_check=lambda:True)
        self.assertFalse(runtime._finalize(fleet()))

    def test_finalizer_conflict_retry_binds_fresh_generation(self):
        fresh=fleet(generation=5,rv="20")
        retry=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":5,"resourceVersion":"21","finalizers":["other.example/one"]}})
        client=FinalizerClient([ApiError(409,"conflict"),retry],fresh=fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertTrue(runtime._finalize(fleet(generation=4,rv="10")))
        self.assertEqual(client.patches,[
            ("prod","10",["other.example/one"]),
            ("prod","20",["other.example/one"]),
        ])
        self.assertEqual(runtime.stats.finalizer_conflict_recomputes,1)

    def test_finalizer_conflict_retry_rejects_stale_generation_echo(self):
        fresh=fleet(generation=5,rv="20")
        retry=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":4,"resourceVersion":"21","finalizers":["other.example/one"]}})
        client=FinalizerClient([ApiError(409,"conflict"),retry],fresh=fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertFalse(runtime._finalize(fleet(generation=4,rv="10")))
        self.assertEqual(runtime.stats.finalizer_conflict_fenced,1)


if __name__=="__main__": unittest.main()
