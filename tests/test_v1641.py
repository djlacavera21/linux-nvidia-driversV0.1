import unittest
from types import SimpleNamespace
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer


class CheckpointTelemetryTests(unittest.TestCase):
    def test_renderer_keeps_checkpoint_metrics_backward_compatible(self):
        body = render(
            leader=True,
            reconcile_total=2,
            reconcile_failures=1,
            pending_approvals=0,
            rollback_required=0,
        )
        self.assertIn("nvlx_controller_reconcile_total 2\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_writes_total 0\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_sequence 0\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_epoch 0\n", body)

    def test_http_metrics_exports_unified_checkpoint_transaction_state(self):
        stats = SimpleNamespace(
            leader=True,
            reconcile_total=7,
            reconcile_failures=2,
            api_reachable=True,
            inventory_fresh=True,
            terminating=False,
        )
        runtime = SimpleNamespace(
            stats=stats,
            nvidia_checkpoint_writes=11,
            nvidia_checkpoint_idempotent_acks=3,
            nvidia_checkpoint_rollbacks=2,
            nvidia_checkpoint_transaction_mismatches=4,
            nvidia_checkpoint_failures=5,
            nvidia_checkpoint_restore_attempts=6,
            nvidia_checkpoint_restore_successes=5,
            nvidia_checkpoint_sequence=17,
            nvidia_checkpoint_epoch=9,
        )
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
            ) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("text/plain; version=0.0.4", response.headers.get("Content-Type", ""))
        finally:
            server.close()

        expected = {
            "nvlx_nvidia_checkpoint_writes_total": 11,
            "nvlx_nvidia_checkpoint_idempotent_acks_total": 3,
            "nvlx_nvidia_checkpoint_rollbacks_total": 2,
            "nvlx_nvidia_checkpoint_transaction_mismatches_total": 4,
            "nvlx_nvidia_checkpoint_failures_total": 5,
            "nvlx_nvidia_checkpoint_restore_attempts_total": 6,
            "nvlx_nvidia_checkpoint_restore_successes_total": 5,
            "nvlx_nvidia_checkpoint_sequence": 17,
            "nvlx_nvidia_checkpoint_epoch": 9,
        }
        for name, value in expected.items():
            self.assertIn(f"{name} {value}\n", body)

    def test_http_metrics_defaults_missing_checkpoint_fields_to_zero(self):
        stats = SimpleNamespace(
            leader=False,
            reconcile_total=0,
            reconcile_failures=0,
            api_reachable=False,
            inventory_fresh=False,
            terminating=False,
        )
        runtime = SimpleNamespace(stats=stats)
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
            ) as response:
                body = response.read().decode("utf-8")
        finally:
            server.close()
        self.assertIn("nvlx_nvidia_checkpoint_transaction_mismatches_total 0\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_restore_successes_total 0\n", body)


if __name__ == "__main__":
    unittest.main()
