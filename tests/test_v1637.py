import unittest

from nvlx.k8s_api_v16 import ApiResponse
from nvlx.nvidia_checkpoint_v1637 import LeaseCheckpointStore
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError


class Client:
    def __init__(self, *, corrupt_readback=False, lose_leader=False):
        self.rv = 1
        self.annotations = {}
        self.corrupt_readback = corrupt_readback
        self.lose_leader = lose_leader
        self.gets = 0

    def _body(self):
        anns = dict(self.annotations)
        holder = "pod-a"
        if self.gets >= 2 and self.lose_leader:
            holder = "pod-b"
        if self.gets >= 2 and self.corrupt_readback and "nvlx.io/nvidia-continuity-sequence-floor" in anns:
            anns["nvlx.io/nvidia-continuity-sequence-floor"] = "999"
        return {
            "metadata": {"resourceVersion": str(self.rv), "annotations": anns},
            "spec": {"holderIdentity": holder, "leaseTransitions": 3},
        }

    def request_json(self, method, path, body=None, **kwargs):
        if method == "GET":
            self.gets += 1
            return ApiResponse(200, self._body())
        if method == "PATCH":
            self.rv += 1
            self.annotations.update(body["metadata"]["annotations"])
            return ApiResponse(200, self._body())
        raise AssertionError(method)


class CheckpointReadbackTests(unittest.TestCase):
    def test_success_requires_independent_get(self):
        client = Client()
        store = LeaseCheckpointStore(client, "pod-a")
        self.assertEqual(store.save(None, None), (3, 1))
        self.assertEqual(client.gets, 2)

    def test_readback_floor_mismatch_fails_closed(self):
        store = LeaseCheckpointStore(Client(corrupt_readback=True), "pod-a")
        with self.assertRaisesRegex(NvidiaInventoryError, "readback floor mismatch"):
            store.save(None, None)

    def test_readback_leadership_loss_fails_closed(self):
        store = LeaseCheckpointStore(Client(lose_leader=True), "pod-a")
        with self.assertRaisesRegex(NvidiaInventoryError, "lost Lease leadership"):
            store.save(None, None)


if __name__ == "__main__": unittest.main()
