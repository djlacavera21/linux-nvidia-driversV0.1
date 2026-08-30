import unittest

from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError
from nvlx.runtime_v1639 import Runtime


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


class RuntimeIdempotentAcknowledgementTests(unittest.TestCase):
    def runtime(self):
        return Runtime(object(), "pod-a", leader_check=lambda: True)

    def test_proven_equal_sequence_is_idempotent_ack(self):
        r = self.runtime()
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = Store(4, 3)

        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)
        self.assertEqual(r.nvidia_checkpoint_writes, 0)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 1)

    def test_equal_sequence_without_store_proof_fails_closed(self):
        r = self.runtime()
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = UnprovenStore(4, 3)

        with self.assertRaisesRegex(NvidiaInventoryError, "lacks idempotent proof"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 0)

    def test_equal_sequence_in_different_epoch_fails_closed(self):
        r = self.runtime()
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = Store(5, 3)

        with self.assertRaisesRegex(NvidiaInventoryError, "Lease epoch mismatch"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_epoch, 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_sequence_rollback_fails_and_is_counted(self):
        r = self.runtime()
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = Store(4, 2)

        with self.assertRaisesRegex(NvidiaInventoryError, "rollback detected"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_rollbacks, 1)
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_advancing_sequence_remains_normal_write(self):
        r = self.runtime()
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        r.nvidia_checkpoint_store = Store(4, 4)

        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_sequence, 4)
        self.assertEqual(r.nvidia_checkpoint_writes, 1)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 0)


if __name__ == "__main__":
    unittest.main()
