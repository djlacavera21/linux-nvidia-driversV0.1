import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import PROTECTIVE_FINALIZER
from nvlx.runtime_v1626 import Runtime


def meta(*, generation=4, finalizers=None):
    return {
        "name": "prod",
        "uid": "u1",
        "generation": generation,
        "resourceVersion": "10",
        "deletionTimestamp": "2026-08-30T00:00:00Z",
        "finalizers": list(finalizers if finalizers is not None else ["other.example/one", "other.example/two", PROTECTIVE_FINALIZER]),
        "annotations": {},
    }


class V1626Tests(unittest.TestCase):
    def response(self, finalizers, *, generation=4):
        return ApiResponse(200, {
            "metadata": {
                "name": "prod",
                "uid": "u1",
                "generation": generation,
                "resourceVersion": "11",
                "finalizers": list(finalizers),
            }
        })

    def test_reordered_unrelated_finalizers_are_semantically_preserved(self):
        expected = meta()
        response = self.response(["other.example/two", "other.example/one"])
        self.assertTrue(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/two"]
        ))

    def test_dropped_unrelated_finalizer_is_rejected(self):
        expected = meta()
        response = self.response(["other.example/one"])
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/two"]
        ))

    def test_injected_unrelated_finalizer_is_rejected(self):
        expected = meta()
        response = self.response(["other.example/one", "other.example/two", "unexpected.example/x"])
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/two"]
        ))

    def test_duplicate_returned_finalizer_is_rejected(self):
        expected = meta()
        response = self.response(["other.example/one", "other.example/one", "other.example/two"])
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/two"]
        ))

    def test_duplicate_expected_finalizer_is_rejected(self):
        expected = meta()
        response = self.response(["other.example/one", "other.example/two"])
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/one", "other.example/two"]
        ))

    def test_protective_finalizer_still_present_is_rejected(self):
        expected = meta()
        response = self.response(["other.example/one", "other.example/two", PROTECTIVE_FINALIZER])
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/two"]
        ))

    def test_generation_binding_is_retained(self):
        expected = meta(generation=4)
        response = self.response(["other.example/two", "other.example/one"], generation=5)
        self.assertFalse(Runtime._finalizer_response_verified_for_meta(
            response, expected, ["other.example/one", "other.example/two"]
        ))

    def test_duplicate_source_finalizers_fail_before_mutation_plan(self):
        obj = {
            "metadata": meta(finalizers=["other.example/one", "other.example/one", PROTECTIVE_FINALIZER]),
            "status": {"quarantined_nodes": 0},
        }
        self.assertEqual(Runtime._finalizer_plan(obj), (False, False, []))

    def test_normal_source_finalizers_still_plan_removal(self):
        obj = {
            "metadata": meta(),
            "status": {"quarantined_nodes": 0},
        }
        allowed, already_done, remaining = Runtime._finalizer_plan(obj)
        self.assertTrue(allowed)
        self.assertFalse(already_done)
        self.assertEqual(remaining, ["other.example/one", "other.example/two"])


if __name__ == "__main__":
    unittest.main()
