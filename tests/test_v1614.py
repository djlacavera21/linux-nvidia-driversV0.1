import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import Runtime, PROTECTIVE_FINALIZER

class V1614Tests(unittest.TestCase):
    def test_status_response_uid_mismatch_fails_closed(self):
        expected={"name":"prod","uid":"u1","generation":4}
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u2","generation":4,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertFalse(Runtime._status_response_verified(response,expected,{"phase":"Ready"}))

    def test_status_response_generation_mismatch_fails_closed(self):
        expected={"name":"prod","uid":"u1","generation":4}
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":5,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertFalse(Runtime._status_response_verified(response,expected,{"phase":"Ready"}))

    def test_status_response_same_incarnation_and_generation_is_verified(self):
        expected={"name":"prod","uid":"u1","generation":4}
        response=ApiResponse(200,{"metadata":{"name":"prod","uid":"u1","generation":4,"resourceVersion":"11"},"status":{"phase":"Ready"}})
        self.assertTrue(Runtime._status_response_verified(response,expected,{"phase":"Ready"}))

    def test_finalizer_response_must_preserve_unrelated_finalizers_exactly(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"11","finalizers":["other.example/two"]}})
        self.assertFalse(Runtime._finalizer_response_verified(response,"prod",["other.example/one","other.example/two"]))

    def test_finalizer_response_reordering_is_not_accepted(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"11","finalizers":["other.example/two","other.example/one"]}})
        self.assertFalse(Runtime._finalizer_response_verified(response,"prod",["other.example/one","other.example/two"]))

    def test_finalizer_response_exact_preservation_is_verified(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"11","finalizers":["other.example/one","other.example/two"]}})
        self.assertTrue(Runtime._finalizer_response_verified(response,"prod",["other.example/one","other.example/two"]))

    def test_protective_finalizer_still_present_is_rejected(self):
        response=ApiResponse(200,{"metadata":{"name":"prod","resourceVersion":"11","finalizers":["other.example/one",PROTECTIVE_FINALIZER]}})
        self.assertFalse(Runtime._finalizer_response_verified(response,"prod",["other.example/one"]))

if __name__=="__main__": unittest.main()
