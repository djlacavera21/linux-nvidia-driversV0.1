import unittest
from unittest.mock import patch

from nvlx.nvidia_continuity_v1632 import SnapshotIdentity
from nvlx.nvidia_inventory_v163 import NvidiaPreflight, NvidiaSnapshot
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError
from nvlx.runtime_v163 import Runtime as RuntimeV163
from nvlx.runtime_v1636 import Runtime


def ident(uid="u1"):
    return SnapshotIdentity(
        api_versions=(("nvidia.com", "v1"),),
        available_resources=(("nvidia.com", ("clusterpolicies",)),),
        gpuclusters=(),
        clusterpolicies=(("cluster-policy", uid, "nvidia.com/v1"),),
        drivers=(),
        computedomains=(),
        computedomaincliques=(),
        gpu_nodes=(),
    )


def snapshot(uid="u1"):
    obj = {
        "apiVersion": "nvidia.com/v1",
        "metadata": {"name": "cluster-policy", "uid": uid, "resourceVersion": "7"},
    }
    return NvidiaSnapshot(
        (), (obj,), (), (), (), (),
        (("nvidia.com", "v1"),),
        (("nvidia.com", ("clusterpolicies",)),),
    )


class FlakyStore:
    def __init__(self, failures=1, value=None):
        self.failures = failures
        self.value = value or (ident(), None, 4, False, 3)
        self.loads = 0

    def load(self):
        self.loads += 1
        if self.loads <= self.failures:
            raise NvidiaInventoryError("temporary checkpoint read failure")
        return self.value


class AlwaysFailStore:
    def __init__(self):
        self.loads = 0

    def load(self):
        self.loads += 1
        raise NvidiaInventoryError("corrupt checkpoint")


class AtomicRestoreTests(unittest.TestCase):
    def test_failed_restore_does_not_consume_loaded_guard(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_store = FlakyStore()
        with self.assertRaises(NvidiaInventoryError):
            r._restore_checkpoint_once()
        self.assertFalse(r.nvidia_checkpoint_loaded)
        self.assertEqual(r.nvidia_checkpoint_restore_attempts, 1)
        self.assertIsNone(r.nvidia_identity_baseline)

        r._restore_checkpoint_once()
        self.assertTrue(r.nvidia_checkpoint_loaded)
        self.assertEqual(r.nvidia_checkpoint_restore_attempts, 2)
        self.assertEqual(r.nvidia_checkpoint_restore_successes, 1)
        self.assertEqual(r.nvidia_identity_baseline, ident())
        self.assertEqual(r.nvidia_checkpoint_sequence, 3)

    def test_failed_restore_preserves_existing_in_memory_state(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        old = ident("old")
        r.nvidia_identity_baseline = old
        r.nvidia_checkpoint_epoch = 8
        r.nvidia_checkpoint_sequence = 9
        r.nvidia_checkpoint_store = AlwaysFailStore()
        with self.assertRaises(NvidiaInventoryError):
            r._restore_checkpoint_once()
        self.assertFalse(r.nvidia_checkpoint_loaded)
        self.assertEqual(r.nvidia_identity_baseline, old)
        self.assertEqual(r.nvidia_checkpoint_epoch, 8)
        self.assertEqual(r.nvidia_checkpoint_sequence, 9)

    def test_corrupt_restore_retries_every_preflight_and_never_first_observation_trusts(self):
        store = AlwaysFailStore()
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_store = store
        r.nvidia_inventory_check = lambda: NvidiaPreflight(True, "device-plugin", (), snapshot())

        self.assertEqual(r.list_and_watch_once(), "reconnect")
        self.assertEqual(r.list_and_watch_once(), "reconnect")
        self.assertEqual(store.loads, 2)
        self.assertFalse(r.nvidia_checkpoint_loaded)
        self.assertIsNone(r.nvidia_identity_baseline)

    def test_transient_restore_failure_recovers_on_next_preflight(self):
        store = FlakyStore()
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_store = store
        r.nvidia_inventory_check = lambda: NvidiaPreflight(True, "device-plugin", (), snapshot())

        self.assertEqual(r.list_and_watch_once(), "reconnect")
        self.assertFalse(r.nvidia_checkpoint_loaded)
        with patch.object(RuntimeV163, "list_and_watch_once", return_value="eof"):
            self.assertEqual(r.list_and_watch_once(), "eof")
        self.assertTrue(r.nvidia_checkpoint_loaded)
        self.assertEqual(store.loads, 2)
        self.assertEqual(r.nvidia_identity_baseline, ident())

    def test_successful_restore_is_read_only_once(self):
        store = FlakyStore(failures=0)
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_store = store
        r._restore_checkpoint_once()
        r._restore_checkpoint_once()
        self.assertEqual(store.loads, 1)
        self.assertEqual(r.nvidia_checkpoint_restore_successes, 1)


if __name__ == "__main__":
    unittest.main()
