import unittest

from nvlx.nvidia_inventory_v163 import NvidiaPreflight, NvidiaSnapshot
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError
from nvlx.runtime_v164 import Runtime


class Store:
    proves_idempotent_commits = True

    def __init__(self, epoch, sequence):
        self.epoch = epoch
        self.sequence = sequence
        self.calls = 0

    def save(self, baseline, candidate):
        self.calls += 1
        return self.epoch, self.sequence


class UnprovenStore(Store):
    proves_idempotent_commits = False


def snapshot(uid="u1"):
    policy = {
        "apiVersion": "nvidia.com/v1",
        "metadata": {"name": "cluster-policy", "uid": uid, "resourceVersion": "7"},
    }
    return NvidiaSnapshot(
        (),
        (policy,),
        (),
        (),
        (),
        (),
        (("nvidia.com", "v1"),),
        (("nvidia.com", ("clusterpolicies",)),),
    )


class UnifiedCheckpointTransactionTests(unittest.TestCase):
    def runtime(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_loaded = True
        return r

    def test_normal_first_observation_uses_sequence_transaction_gate(self):
        r = self.runtime()
        store = Store(4, 1)
        r.nvidia_checkpoint_store = store

        result = NvidiaPreflight(True, "device-plugin", (), snapshot())
        self.assertTrue(r._continuity_accepts(result))
        self.assertEqual(store.calls, 1)
        self.assertEqual(r.nvidia_checkpoint_epoch, 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 1)
        self.assertEqual(r.nvidia_checkpoint_writes, 1)

    def test_normal_persist_accepts_proven_idempotent_ack(self):
        r = self.runtime()
        state = object()
        r.nvidia_identity_baseline = state
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = Store(4, 3)

        r._persist_checkpoint(state, None)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 1)
        self.assertEqual(r.nvidia_checkpoint_writes, 0)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_normal_persist_rejects_sequence_rollback(self):
        r = self.runtime()
        state = object()
        r.nvidia_identity_baseline = state
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = Store(4, 2)

        with self.assertRaisesRegex(NvidiaInventoryError, "rollback detected"):
            r._persist_checkpoint(state, None)
        self.assertEqual(r.nvidia_checkpoint_rollbacks, 1)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_normal_persist_rejects_unproven_equal_sequence(self):
        r = self.runtime()
        state = object()
        r.nvidia_identity_baseline = state
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = UnprovenStore(4, 3)

        with self.assertRaisesRegex(NvidiaInventoryError, "lacks idempotent proof"):
            r._persist_checkpoint(state, None)

    def test_transaction_arguments_must_match_runtime_state(self):
        r = self.runtime()
        current = object()
        stale = object()
        store = Store(4, 1)
        r.nvidia_identity_baseline = current
        r.nvidia_checkpoint_store = store

        with self.assertRaisesRegex(NvidiaInventoryError, "does not match runtime state"):
            r._persist_checkpoint(stale, None)
        self.assertEqual(r.nvidia_checkpoint_transaction_mismatches, 1)
        self.assertEqual(store.calls, 0)


if __name__ == "__main__":
    unittest.main()
