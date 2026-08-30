import hashlib
import unittest

from nvlx.k8s_api_v16 import ApiResponse
from nvlx.nvidia_checkpoint_v1635 import encode_checkpoint
from nvlx.nvidia_checkpoint_v165 import CheckpointCommitReceipt, LeaseCheckpointStore
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError
from nvlx.runtime_v165 import Runtime


class Client:
    def __init__(self, *, timeout_after_commit=False, timeout_before_commit=False):
        self.rv = 1
        self.annotations = {}
        self.timeout_after_commit = timeout_after_commit
        self.timeout_before_commit = timeout_before_commit
        self.patch_calls = 0

    def _body(self):
        return {
            "metadata": {"resourceVersion": str(self.rv), "annotations": dict(self.annotations)},
            "spec": {"holderIdentity": "pod-a", "leaseTransitions": 4},
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


def receipt(epoch, sequence, *, idempotent, reconciled=False, digest=None):
    if digest is None:
        raw = encode_checkpoint(None, None, epoch, sequence)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return CheckpointCommitReceipt(
        lease_transition=epoch,
        sequence=sequence,
        idempotent=idempotent,
        reconciled=reconciled,
        canonical_sha256=digest,
    )


class TupleStore:
    proves_idempotent_commits = True

    def __init__(self, epoch, sequence):
        self.epoch = epoch
        self.sequence = sequence

    def save(self, baseline, candidate):
        return self.epoch, self.sequence


class ReceiptStore:
    def __init__(self, value):
        self.value = value

    def save_receipt(self, baseline, candidate):
        return self.value


class CheckpointReceiptTests(unittest.TestCase):
    def test_new_write_returns_non_idempotent_receipt(self):
        client = Client()
        store = LeaseCheckpointStore(client, "pod-a")
        out = store.save_receipt(None, None)
        self.assertEqual((out.lease_transition, out.sequence), (4, 1))
        self.assertFalse(out.idempotent)
        self.assertFalse(out.reconciled)
        self.assertEqual(len(out.canonical_sha256), 64)
        self.assertEqual(client.patch_calls, 1)

    def test_exact_existing_commit_returns_idempotent_receipt_without_rewrite(self):
        client = Client()
        store = LeaseCheckpointStore(client, "pod-a")
        first = store.save_receipt(None, None)
        second = store.save_receipt(None, None)
        self.assertFalse(first.idempotent)
        self.assertTrue(second.idempotent)
        self.assertFalse(second.reconciled)
        self.assertEqual(second.sequence, first.sequence)
        self.assertEqual(second.canonical_sha256, first.canonical_sha256)
        self.assertEqual(client.patch_calls, 1)

    def test_ambiguous_write_reconciliation_is_explicit_in_receipt(self):
        client = Client(timeout_after_commit=True)
        store = LeaseCheckpointStore(client, "pod-a")
        out = store.save_receipt(None, None)
        self.assertEqual((out.lease_transition, out.sequence), (4, 1))
        self.assertTrue(out.idempotent)
        self.assertTrue(out.reconciled)
        self.assertEqual(client.patch_calls, 1)

    def test_timeout_before_commit_still_fails_closed(self):
        store = LeaseCheckpointStore(Client(timeout_before_commit=True), "pod-a")
        with self.assertRaisesRegex(NvidiaInventoryError, "cannot establish .* write outcome"):
            store.save_receipt(None, None)

    def test_tuple_save_api_remains_compatible(self):
        store = LeaseCheckpointStore(Client(), "pod-a")
        self.assertEqual(store.save(None, None), (4, 1))

    def test_receipt_rejects_reconciled_without_idempotence(self):
        digest = hashlib.sha256(b"x").hexdigest()
        with self.assertRaisesRegex(ValueError, "must be idempotent"):
            CheckpointCommitReceipt(4, 1, False, True, digest)


class RuntimeReceiptValidationTests(unittest.TestCase):
    def runtime(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        return r

    def test_equal_sequence_requires_per_call_receipt_not_class_flag(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = TupleStore(4, 3)
        with self.assertRaisesRegex(NvidiaInventoryError, "lacks per-call idempotent proof"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 0)

    def test_equal_sequence_accepts_exact_idempotent_receipt(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(receipt(4, 3, idempotent=True))
        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)
        self.assertEqual(r.nvidia_checkpoint_writes, 0)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 1)

    def test_equal_sequence_rejects_non_idempotent_receipt(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(receipt(4, 3, idempotent=False))
        with self.assertRaisesRegex(NvidiaInventoryError, "lacks per-call idempotent proof"):
            r._save_epoch_state()

    def test_receipt_digest_must_match_exact_runtime_state(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(
            receipt(4, 3, idempotent=True, digest="0" * 64)
        )
        with self.assertRaisesRegex(NvidiaInventoryError, "canonical digest mismatch"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 0)

    def test_equal_sequence_cross_epoch_receipt_fails_closed(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(receipt(5, 3, idempotent=True))
        with self.assertRaisesRegex(NvidiaInventoryError, "Lease epoch mismatch"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_epoch, 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_advancing_tuple_store_remains_compatible(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = TupleStore(4, 4)
        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 4)
        self.assertEqual(r.nvidia_checkpoint_writes, 1)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 0)

    def test_rollback_is_still_rejected_and_counted(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(receipt(4, 2, idempotent=True))
        with self.assertRaisesRegex(NvidiaInventoryError, "rollback detected"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_rollbacks, 1)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_invalid_receipt_type_fails_closed(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore((4, 3))
        with self.assertRaisesRegex(NvidiaInventoryError, "invalid commit receipt"):
            r._save_epoch_state()


if __name__ == "__main__":
    unittest.main()
