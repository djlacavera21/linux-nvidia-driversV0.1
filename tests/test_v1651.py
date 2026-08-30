import unittest

from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.nvidia_checkpoint_v1651 import LeaseCheckpointStore
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError


class Client:
    def __init__(
        self,
        *,
        patch_transport_before=False,
        patch_transport_after=False,
        patch_http_500_after=False,
        bad_patch_response=False,
        readback_transport_once=False,
        corrupt_readback_once=False,
    ):
        self.rv = 1
        self.annotations = {}
        self.patch_transport_before = patch_transport_before
        self.patch_transport_after = patch_transport_after
        self.patch_http_500_after = patch_http_500_after
        self.bad_patch_response = bad_patch_response
        self.readback_transport_once = readback_transport_once
        self.corrupt_readback_once = corrupt_readback_once
        self.patch_calls = 0
        self.get_calls = 0
        self._readback_failed = False
        self._readback_corrupted = False

    def _body(self):
        return {
            "metadata": {
                "resourceVersion": str(self.rv),
                "annotations": dict(self.annotations),
            },
            "spec": {"holderIdentity": "pod-a", "leaseTransitions": 5},
        }

    def request_json(self, method, path, body=None, **kwargs):
        if method == "GET":
            self.get_calls += 1
            if self.patch_calls and self.readback_transport_once and not self._readback_failed:
                self._readback_failed = True
                raise ApiError(0, "request timed out")
            response = self._body()
            if self.patch_calls and self.corrupt_readback_once and not self._readback_corrupted:
                self._readback_corrupted = True
                response["metadata"]["annotations"][
                    "nvlx.io/nvidia-continuity-sequence-floor"
                ] = "999"
            return ApiResponse(200, response)

        if method == "PATCH":
            self.patch_calls += 1
            if self.patch_transport_before:
                raise ApiError(0, "request timed out")

            self.rv += 1
            self.annotations.update(body["metadata"]["annotations"])

            if self.patch_transport_after:
                raise ApiError(0, "request timed out")
            if self.patch_http_500_after:
                raise ApiError(500, "internal server error")

            response = self._body()
            if self.bad_patch_response:
                response["spec"]["holderIdentity"] = "pod-b"
            return ApiResponse(200, response)

        raise AssertionError(method)


class NarrowAmbiguousWriteTests(unittest.TestCase):
    def test_transport_failure_after_commit_reconciles(self):
        client = Client(patch_transport_after=True)
        store = LeaseCheckpointStore(client, "pod-a")
        receipt = store.save_receipt(None, None)
        self.assertEqual((receipt.lease_transition, receipt.sequence), (5, 1))
        self.assertTrue(receipt.idempotent)
        self.assertTrue(receipt.reconciled)
        self.assertEqual(client.patch_calls, 1)

    def test_transport_failure_before_commit_fails_closed(self):
        store = LeaseCheckpointStore(
            Client(patch_transport_before=True), "pod-a"
        )
        with self.assertRaisesRegex(
            NvidiaInventoryError, "cannot establish .* write outcome"
        ):
            store.save_receipt(None, None)

    def test_transport_failure_during_readback_reconciles(self):
        client = Client(readback_transport_once=True)
        store = LeaseCheckpointStore(client, "pod-a")
        receipt = store.save_receipt(None, None)
        self.assertTrue(receipt.idempotent)
        self.assertTrue(receipt.reconciled)
        self.assertEqual(receipt.sequence, 1)
        self.assertEqual(client.patch_calls, 1)

    def test_deterministic_patch_validation_failure_is_not_reconciled(self):
        client = Client(bad_patch_response=True)
        store = LeaseCheckpointStore(client, "pod-a")
        with self.assertRaisesRegex(
            NvidiaInventoryError, "Lease epoch changed during write"
        ):
            store.save_receipt(None, None)
        self.assertEqual(client.patch_calls, 1)
        self.assertEqual(client.get_calls, 2)

    def test_deterministic_readback_mismatch_is_not_reconciled(self):
        client = Client(corrupt_readback_once=True)
        store = LeaseCheckpointStore(client, "pod-a")
        with self.assertRaisesRegex(
            NvidiaInventoryError, "readback floor mismatch"
        ):
            store.save_receipt(None, None)
        self.assertEqual(client.patch_calls, 1)
        self.assertEqual(client.get_calls, 3)

    def test_explicit_http_error_is_not_reconciled_in_same_call(self):
        client = Client(patch_http_500_after=True)
        store = LeaseCheckpointStore(client, "pod-a")
        with self.assertRaisesRegex(
            NvidiaInventoryError, "cannot write NVIDIA continuity checkpoint"
        ):
            store.save_receipt(None, None)
        self.assertEqual(client.patch_calls, 1)
        self.assertEqual(client.get_calls, 2)

        # The next save may safely discover the already committed canonical state.
        receipt = store.save_receipt(None, None)
        self.assertTrue(receipt.idempotent)
        self.assertFalse(receipt.reconciled)
        self.assertEqual(receipt.sequence, 1)
        self.assertEqual(client.patch_calls, 1)


if __name__ == "__main__":
    unittest.main()
