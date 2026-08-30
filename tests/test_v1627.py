import unittest
from unittest.mock import patch

from nvlx.runtime_v1626 import Runtime as RuntimeV1626
from nvlx.runtime_v1627 import Runtime


def fleet(*, generation=4, rv="10"):
    return {
        "metadata": {
            "name": "prod",
            "uid": "u1",
            "generation": generation,
            "resourceVersion": rv,
            "annotations": {"nvlx.io/approved": "true"},
        }
    }


class V1627Tests(unittest.TestCase):
    def runtime(self):
        return Runtime(object(), "pod-a", leader_check=lambda: True)

    def test_deferred_watch_reconcile_does_not_commit_duplicate_state(self):
        runtime = self.runtime()
        obj = fleet()
        with patch.object(RuntimeV1626, "reconcile_object", return_value="standby"):
            self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "reconcile")
            self.assertIn("u1", runtime._watch_seen)
            self.assertEqual(runtime.reconcile_object(obj, event_type="MODIFIED"), "standby")
        self.assertNotIn("u1", runtime._watch_seen)
        self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "reconcile")

    def test_settled_watch_reconcile_commits_duplicate_state(self):
        runtime = self.runtime()
        obj = fleet()
        with patch.object(RuntimeV1626, "reconcile_object", return_value="patched"):
            self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "reconcile")
            self.assertEqual(runtime.reconcile_object(obj, event_type="MODIFIED"), "patched")
        self.assertIn("u1", runtime._watch_seen)
        self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "duplicate")

    def test_deferred_reconcile_restores_prior_settled_state(self):
        runtime = self.runtime()
        runtime._watch_seen["u1"] = ("MODIFIED", "u1", 3, "9")
        obj = fleet(generation=4, rv="10")
        with patch.object(RuntimeV1626, "reconcile_object", return_value="fenced"):
            self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "reconcile")
            self.assertEqual(runtime._watch_seen["u1"], ("MODIFIED", "u1", 4, "10"))
            self.assertEqual(runtime.reconcile_object(obj, event_type="MODIFIED"), "fenced")
        self.assertEqual(runtime._watch_seen["u1"], ("MODIFIED", "u1", 3, "9"))
        self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "reconcile")

    def test_deferred_delete_restores_non_deleted_state_for_retry(self):
        runtime = self.runtime()
        runtime._watch_seen["u1"] = ("MODIFIED", "u1", 4, "10")
        obj = fleet()
        with patch.object(RuntimeV1626, "reconcile_object", return_value="finalizer-hold"):
            self.assertEqual(runtime._watch_event_disposition(obj, "DELETED"), "reconcile-delete")
            self.assertEqual(runtime._watch_seen["u1"], ("DELETED", "u1", 4, "10"))
            self.assertEqual(runtime.reconcile_object(obj, event_type="DELETED"), "finalizer-hold")
        self.assertEqual(runtime._watch_seen["u1"], ("MODIFIED", "u1", 4, "10"))
        self.assertEqual(runtime._watch_event_disposition(obj, "DELETED"), "reconcile-delete")

    def test_reconcile_exception_rolls_back_staged_watch_state(self):
        runtime = self.runtime()
        obj = fleet()
        with patch.object(RuntimeV1626, "reconcile_object", side_effect=RuntimeError("boom")):
            self.assertEqual(runtime._watch_event_disposition(obj, "MODIFIED"), "reconcile")
            with self.assertRaises(RuntimeError):
                runtime.reconcile_object(obj, event_type="MODIFIED")
        self.assertNotIn("u1", runtime._watch_seen)

    def test_unrelated_reconcile_cannot_consume_staged_watch_state(self):
        runtime = self.runtime()
        watched = fleet(generation=4, rv="10")
        other = {
            "metadata": {
                "name": "other",
                "uid": "u2",
                "generation": 1,
                "resourceVersion": "20",
                "annotations": {},
            }
        }
        runtime._watch_event_disposition(watched, "MODIFIED")
        with patch.object(RuntimeV1626, "reconcile_object", return_value="standby"):
            runtime.reconcile_object(other, event_type="MODIFIED")
        self.assertNotIn("u1", runtime._watch_seen)


if __name__ == "__main__":
    unittest.main()
