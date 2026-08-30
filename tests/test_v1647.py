import unittest
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1643 import Runtime


class PrometheusExpositionMetadataTests(unittest.TestCase):
    @staticmethod
    def render_body():
        return render(
            leader=True,
            reconcile_total=11,
            reconcile_failures=2,
            pending_approvals=3,
            rollback_required=1,
            preflight_stale=4,
            controller_ready=True,
            api_reachable=True,
            leadership_fresh=True,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_writes=5,
            checkpoint_idempotent_acks=6,
            checkpoint_rollbacks=7,
            checkpoint_transaction_mismatches=8,
            checkpoint_failures=9,
            checkpoint_restore_attempts=10,
            checkpoint_restore_successes=9,
            checkpoint_sequence=12,
            checkpoint_epoch=13,
            checkpoint_ready=True,
        )

    def test_every_metric_has_exactly_one_help_and_type_declaration(self):
        body = self.render_body()
        samples = [
            line.split(" ", 1)[0]
            for line in body.splitlines()
            if line and not line.startswith("#")
        ]
        self.assertTrue(samples)
        for name in samples:
            self.assertEqual(body.count(f"# HELP {name} "), 1)
            self.assertEqual(body.count(f"# TYPE {name} "), 1)

    def test_help_text_is_nonempty_and_ordered_before_type_and_sample(self):
        body = self.render_body()
        lines = body.splitlines()
        for index, line in enumerate(lines):
            if not line.startswith("# HELP "):
                continue
            parts = line.split(" ", 3)
            self.assertEqual(len(parts), 4)
            name = parts[2]
            self.assertTrue(parts[3].strip())
            self.assertLess(index + 2, len(lines))
            self.assertTrue(lines[index + 1].startswith(f"# TYPE {name} "))
            self.assertTrue(lines[index + 2].startswith(f"{name} "))

    def test_type_semantics_and_sample_values_remain_unchanged(self):
        body = self.render_body()
        self.assertIn("# TYPE nvlx_controller_reconcile_total counter\n", body)
        self.assertIn("# TYPE nvlx_nvidia_checkpoint_writes_total counter\n", body)
        self.assertIn("# TYPE nvlx_controller_ready gauge\n", body)
        self.assertIn("# TYPE nvlx_nvidia_checkpoint_sequence gauge\n", body)
        self.assertIn("nvlx_controller_reconcile_total 11\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_writes_total 5\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_sequence 12\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_epoch 13\n", body)

    def test_live_metrics_uses_utf8_prometheus_text_content_type_and_help(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True, leader_fresh_seconds=25.0)
        r.stats.api_reachable = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        r.nvidia_preflight_ok = True
        self.assertTrue(r._leader())
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False
        r.nvidia_checkpoint_writes = 2

        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
            ) as response:
                body = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")
            self.assertEqual(
                content_type, "text/plain; version=0.0.4; charset=utf-8"
            )
            self.assertIn(
                "# HELP nvlx_nvidia_checkpoint_writes_total Total successful NVIDIA continuity checkpoint writes.\n",
                body,
            )
            self.assertIn("# TYPE nvlx_nvidia_checkpoint_writes_total counter\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_writes_total 2\n", body)
        finally:
            server.close()

    def test_help_metadata_does_not_change_normalization(self):
        body = render(
            leader=False,
            reconcile_total=-3,
            reconcile_failures="bad",
            pending_approvals=-1,
            rollback_required=0,
        )
        self.assertIn("nvlx_controller_reconcile_total 0\n", body)
        self.assertIn("nvlx_controller_reconcile_failures_total 0\n", body)
        self.assertIn("nvlx_controller_pending_approvals 0\n", body)


if __name__ == "__main__":
    unittest.main()
