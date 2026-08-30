import unittest
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1643 import Runtime


class PrometheusMetricTypeTests(unittest.TestCase):
    def render_body(self):
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

    def test_cumulative_total_series_are_counters(self):
        body = self.render_body()
        counters = (
            "nvlx_controller_reconcile_total",
            "nvlx_controller_reconcile_failures_total",
            "nvlx_controller_preflight_stale_total",
            "nvlx_nvidia_checkpoint_writes_total",
            "nvlx_nvidia_checkpoint_idempotent_acks_total",
            "nvlx_nvidia_checkpoint_rollbacks_total",
            "nvlx_nvidia_checkpoint_transaction_mismatches_total",
            "nvlx_nvidia_checkpoint_failures_total",
            "nvlx_nvidia_checkpoint_restore_attempts_total",
            "nvlx_nvidia_checkpoint_restore_successes_total",
        )
        for name in counters:
            self.assertIn(f"# TYPE {name} counter\n", body)
            self.assertNotIn(f"# TYPE {name} gauge\n", body)

    def test_instantaneous_state_series_remain_gauges(self):
        body = self.render_body()
        gauges = (
            "nvlx_controller_leader",
            "nvlx_controller_ready",
            "nvlx_controller_api_reachable",
            "nvlx_controller_leadership_fresh",
            "nvlx_controller_inventory_fresh",
            "nvlx_controller_terminating",
            "nvlx_nvidia_preflight_ready",
            "nvlx_controller_pending_approvals",
            "nvlx_controller_rollback_required",
            "nvlx_controller_circuit_open",
            "nvlx_controller_rollout_slots",
            "nvlx_controller_completed_executions",
            "nvlx_controller_canary_wave",
            "nvlx_nvidia_checkpoint_sequence",
            "nvlx_nvidia_checkpoint_epoch",
            "nvlx_nvidia_checkpoint_ready",
        )
        for name in gauges:
            self.assertIn(f"# TYPE {name} gauge\n", body)

    def test_type_correction_does_not_change_metric_values(self):
        body = self.render_body()
        expected = (
            "nvlx_controller_reconcile_total 11\n",
            "nvlx_controller_reconcile_failures_total 2\n",
            "nvlx_controller_pending_approvals 3\n",
            "nvlx_controller_preflight_stale_total 4\n",
            "nvlx_nvidia_checkpoint_writes_total 5\n",
            "nvlx_nvidia_checkpoint_idempotent_acks_total 6\n",
            "nvlx_nvidia_checkpoint_rollbacks_total 7\n",
            "nvlx_nvidia_checkpoint_transaction_mismatches_total 8\n",
            "nvlx_nvidia_checkpoint_failures_total 9\n",
            "nvlx_nvidia_checkpoint_restore_attempts_total 10\n",
            "nvlx_nvidia_checkpoint_restore_successes_total 9\n",
            "nvlx_nvidia_checkpoint_sequence 12\n",
            "nvlx_nvidia_checkpoint_epoch 13\n",
        )
        for line in expected:
            self.assertIn(line, body)

    def test_http_metrics_surface_uses_correct_prometheus_types(self):
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
        r.nvidia_checkpoint_sequence = 3

        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
            ) as response:
                body = response.read().decode("utf-8")
            self.assertIn("# TYPE nvlx_nvidia_checkpoint_writes_total counter\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_writes_total 2\n", body)
            self.assertIn("# TYPE nvlx_nvidia_checkpoint_sequence gauge\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_sequence 3\n", body)
            self.assertIn("# TYPE nvlx_controller_ready gauge\n", body)
        finally:
            server.close()

    def test_every_metric_has_exactly_one_type_declaration(self):
        body = self.render_body()
        samples = [
            line.split(" ", 1)[0]
            for line in body.splitlines()
            if line and not line.startswith("#")
        ]
        for name in samples:
            self.assertEqual(body.count(f"# TYPE {name} "), 1)


if __name__ == "__main__":
    unittest.main()
