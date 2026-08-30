import unittest

from nvlx.k8s_api_v16 import ApiResponse
from nvlx.nvidia_checkpoint_v1638 import LeaseCheckpointStore
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError


class Client:
    def __init__(self, *, timeout_after_commit=False, timeout_before_commit=False, lose_leader_after_patch=False):
        self.rv = 1
        self.annotations = {}
        self.timeout_after_commit = timeout_after_commit
        self.timeout_before_commit = timeout_before_commit
        self.lose_leader_after_patch = lose_leader_after_patch
        self.patch_calls = 0

    def _body(self):
        holder = "pod-b" if self.lose_leader_after_patch and self.patch_calls else "pod-a"
        return {
            "metadata": {"resourceVersion": str(self.rv), "annotations": dict(self.annotations)},
            "spec": {"holderIdentity": holder, "leaseTransitions": 3},
        }

    def request_json(self, method, path, body=None, **kwargs):
        if method == "GET":
            return ApiResponse(200, self._body())
        if method == "PATCH":
            self.patch_calls += 1
            if self.timeout_before_commit:
                raise TimeoutError("write timed out before commit")
            self.rv += 1
            self.annotations.update(body["metadata"]["annotations"])
            if self.timeout_after_commit:
                self.timeout_after_commit = False
                raise TimeoutError("write timed out after commit")
            return ApiResponse(200, self._body())
        raise AssertionError(method)


class CheckpointCommitReconciliationTests(unittest.TestCase):
    def test_identical_current_checkpoint_is_idempotent(self):
        client = Client()
        store = LeaseCheckpointStore(client, "pod-a")
        self.assertEqual(store.save(None, None), (3, 1))
        self.assertEqual(store.save(None, None), (3, 1))
        self.assertEqual(client.patch_calls, 1)

    def test_timeout_after_commit_recovers_existing_sequence(self):
        client = Client(timeout_after_commit=True)
        store = LeaseCheckpointStore(client, "pod-a")
        self.assertEqual(store.save(None, None), (3, 1))
        self.assertEqual(client.patch_calls, 1)

    def test_timeout_before_commit_fails_closed(self):
        store = LeaseCheckpointStore(Client(timeout_before_commit=True), "pod-a")
        with self.assertRaisesRegex(NvidiaInventoryError, "cannot establish .* write outcome"):
            store.save(None, None)

    def test_reconciliation_requires_current_leadership(self):
        store = LeaseCheckpointStore(Client(timeout_after_commit=True, lose_leader_after_patch=True), "pod-a")
        with self.assertRaisesRegex(NvidiaInventoryError, "reconciliation lost Lease leadership"):
            store.save(None, None)


if __name__ == "__main__":
    unittest.main()
