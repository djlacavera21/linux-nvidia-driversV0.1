import hashlib
import unittest
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer
from nvlx.nvidia_checkpoint_v1635 import encode_checkpoint
from nvlx.nvidia_checkpoint_v165 import CheckpointCommitReceipt
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError
from nvlx.runtime_v1652 import Runtime


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


class ReceiptStore:
    def __init__(self, value):
        self.value = value

    def save_receipt(self, baseline, candidate):
        return self.value


class ReconciliationTelemetryRuntimeTests(unittest.TestCase):
    def runtime(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.nvidia_checkpoint_epoch = 4
        r.nvidia_checkpoint_sequence = 3
        return r

    def test_advancing_reconciled_commit_counts_write_and_recovery(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(
            receipt(4, 4, idempotent=True, reconciled=True)
        )
        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_writes, 1)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 0)
        self.assertEqual(r.nvidia_checkpoint_reconciled_commits, 1)
        self.assertEqual(r.nvidia_checkpoint_sequence, 4)

    def test_normal_advancing_commit_does_not_count_recovery(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(
            receipt(4, 4, idempotent=False, reconciled=False)
        )
        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_writes, 1)
        self.assertEqual(r.nvidia_checkpoint_reconciled_commits, 0)

    def test_equal_reconciled_ack_counts_ack_and_recovery(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(
            receipt(4, 3, idempotent=True, reconciled=True)
        )
        self.assertEqual(r._save_epoch_state(), 4)
        self.assertEqual(r.nvidia_checkpoint_writes, 0)
        self.assertEqual(r.nvidia_checkpoint_idempotent_acks, 1)
        self.assertEqual(r.nvidia_checkpoint_reconciled_commits, 1)

    def test_digest_failure_does_not_increment_recovery(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(
            receipt(4, 4, idempotent=True, reconciled=True, digest="0" * 64)
        )
        with self.assertRaisesRegex(NvidiaInventoryError, "canonical digest mismatch"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_reconciled_commits, 0)
        self.assertEqual(r.nvidia_checkpoint_writes, 0)

    def test_rollback_failure_does_not_increment_recovery(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = ReceiptStore(
            receipt(4, 2, idempotent=True, reconciled=True)
        )
        with self.assertRaisesRegex(NvidiaInventoryError, "rollback detected"):
            r._save_epoch_state()
        self.assertEqual(r.nvidia_checkpoint_rollbacks, 1)
        self.assertEqual(r.nvidia_checkpoint_reconciled_commits, 0)


class ReconciliationTelemetryMetricsTests(unittest.TestCase):
    def test_renderer_exports_reconciled_commit_counter(self):
        body = render(
            leader=True,
            reconcile_total=1,
            reconcile_failures=0,
            pending_approvals=0,
            rollback_required=0,
            checkpoint_reconciled_commits=7,
        )
        self.assertIn(
            "# HELP nvlx_nvidia_checkpoint_reconciled_commits_total ", body
        )
        self.assertIn(
            "# TYPE nvlx_nvidia_checkpoint_reconciled_commits_total counter\n", body
        )
        self.assertIn("nvlx_nvidia_checkpoint_reconciled_commits_total 7\n", body)

    def test_renderer_defaults_reconciled_counter_to_zero(self):
        body = render(
            leader=False,
            reconcile_total=0,
            reconcile_failures=0,
            pending_approvals=0,
            rollback_required=0,
        )
        self.assertIn("nvlx_nvidia_checkpoint_reconciled_commits_total 0\n", body)

    def test_http_metrics_surface_exposes_runtime_recovery_count(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True, leader_fresh_seconds=25.0)
        r.stats.api_reachable = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        r.nvidia_preflight_ok = True
        self.assertTrue(r._leader())
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False
        r.nvidia_checkpoint_reconciled_commits = 2

        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
            ) as response:
                body = response.read().decode("utf-8")
            self.assertIn(
                "# TYPE nvlx_nvidia_checkpoint_reconciled_commits_total counter\n",
                body,
            )
            self.assertIn(
                "nvlx_nvidia_checkpoint_reconciled_commits_total 2\n", body
            )
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
