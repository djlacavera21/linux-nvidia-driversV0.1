import time
import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1643 import Runtime


class ReadinessTelemetryParityTests(unittest.TestCase):
    def runtime(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True, leader_fresh_seconds=25.0)
        r.stats.api_reachable = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        r.nvidia_preflight_ok = True
        self.assertTrue(r._leader())
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False
        return r

    @staticmethod
    def metrics_body(server):
        with urlopen(
            f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
        ) as response:
            return response.read().decode("utf-8")

    def test_renderer_defaults_unknown_controller_readiness_fail_closed(self):
        body = render(
            leader=True,
            reconcile_total=0,
            reconcile_failures=0,
            pending_approvals=0,
            rollback_required=0,
        )
        self.assertIn("nvlx_controller_ready 0\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)

    def test_metrics_report_full_controller_and_checkpoint_readiness_separately(self):
        r = self.runtime()
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 1\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)

            r.nvidia_preflight_ok = False
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)
            with self.assertRaises(HTTPError) as ctx:
                urlopen(
                    f"http://127.0.0.1:{server.httpd.server_port}/readyz", timeout=2
                )
            self.assertEqual(ctx.exception.code, 503)
        finally:
            server.close()

    def test_metrics_use_same_lease_freshness_decision_as_readyz(self):
        r = self.runtime()
        r._leader_verified_monotonic = time.monotonic() - r.leader_fresh_seconds - 1.0
        r.stats.leader = True
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_controller_leader 0\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)
            with self.assertRaises(HTTPError) as ctx:
                urlopen(
                    f"http://127.0.0.1:{server.httpd.server_port}/readyz", timeout=2
                )
            self.assertEqual(ctx.exception.code, 503)
        finally:
            server.close()

    def test_checkpoint_gate_can_be_the_only_unready_reason(self):
        r = self.runtime()
        r.nvidia_checkpoint_loaded = False
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 0\n", body)
        finally:
            server.close()

    def test_older_runtime_without_ready_method_uses_legacy_stats_fallback(self):
        stats = SimpleNamespace(
            api_reachable=True,
            leader=True,
            inventory_fresh=True,
            terminating=False,
            reconcile_total=0,
            reconcile_failures=0,
        )
        runtime = SimpleNamespace(stats=stats)
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 1\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)
        finally:
            server.close()

    def test_readiness_evaluator_exceptions_fail_closed_for_both_surfaces(self):
        stats = SimpleNamespace(
            api_reachable=True,
            leader=True,
            inventory_fresh=True,
            terminating=False,
            reconcile_total=0,
            reconcile_failures=0,
        )

        class BrokenRuntime:
            def __init__(self):
                self.stats = stats

            def ready(self):
                raise RuntimeError("boom")

            def _checkpoint_ready(self):
                raise RuntimeError("boom")

        server = HealthServer(BrokenRuntime(), "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 0\n", body)
            with self.assertRaises(HTTPError) as ctx:
                urlopen(
                    f"http://127.0.0.1:{server.httpd.server_port}/readyz", timeout=2
                )
            self.assertEqual(ctx.exception.code, 503)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
