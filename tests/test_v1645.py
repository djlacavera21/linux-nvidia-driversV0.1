import time
import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1643 import Runtime


class StructuredReadinessDiagnosticsTests(unittest.TestCase):
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

    def test_renderer_exports_all_readiness_gates(self):
        body = render(
            leader=True,
            reconcile_total=0,
            reconcile_failures=0,
            pending_approvals=0,
            rollback_required=0,
            controller_ready=True,
            api_reachable=True,
            leadership_fresh=True,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            terminating=False,
            checkpoint_ready=True,
        )
        for line in (
            "nvlx_controller_ready 1\n",
            "nvlx_controller_api_reachable 1\n",
            "nvlx_controller_leadership_fresh 1\n",
            "nvlx_controller_inventory_fresh 1\n",
            "nvlx_nvidia_preflight_ready 1\n",
            "nvlx_nvidia_checkpoint_ready 1\n",
            "nvlx_controller_terminating 0\n",
        ):
            self.assertIn(line, body)

    def test_healthy_controller_exports_every_positive_gate(self):
        r = self.runtime()
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            for line in (
                "nvlx_controller_ready 1\n",
                "nvlx_controller_api_reachable 1\n",
                "nvlx_controller_leadership_fresh 1\n",
                "nvlx_controller_inventory_fresh 1\n",
                "nvlx_nvidia_preflight_ready 1\n",
                "nvlx_nvidia_checkpoint_ready 1\n",
                "nvlx_controller_terminating 0\n",
            ):
                self.assertIn(line, body)
        finally:
            server.close()

    def test_preflight_failure_is_isolated_from_other_gates(self):
        r = self.runtime()
        r.nvidia_preflight_ok = False
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_nvidia_preflight_ready 0\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 1\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)
        finally:
            server.close()

    def test_expired_lease_proof_has_its_own_diagnostic_gate(self):
        r = self.runtime()
        r._leader_verified_monotonic = time.monotonic() - r.leader_fresh_seconds - 1.0
        r.stats.leader = True
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 0\n", body)
            self.assertIn("nvlx_controller_leader 0\n", body)
            self.assertIn("nvlx_controller_api_reachable 1\n", body)
        finally:
            server.close()

    def test_api_loss_reports_api_and_effective_leadership_unready(self):
        r = self.runtime()
        r.stats.api_reachable = False
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_controller_api_reachable 0\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 0\n", body)
            self.assertIn("nvlx_controller_leader 0\n", body)
        finally:
            server.close()

    def test_checkpoint_restore_gate_is_reported_independently(self):
        r = self.runtime()
        r.nvidia_checkpoint_loaded = False
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 0\n", body)
            self.assertIn("nvlx_nvidia_preflight_ready 1\n", body)
            self.assertIn("nvlx_controller_inventory_fresh 1\n", body)
        finally:
            server.close()

    def test_termination_state_has_explicit_diagnostic_gauge(self):
        r = self.runtime()
        r.stats.terminating = True
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_controller_terminating 1\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 0\n", body)
        finally:
            server.close()

    def test_older_runtime_uses_stats_and_safe_gate_defaults(self):
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
            self.assertIn("nvlx_controller_api_reachable 1\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 1\n", body)
            self.assertIn("nvlx_controller_inventory_fresh 1\n", body)
            self.assertIn("nvlx_nvidia_preflight_ready 1\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)
        finally:
            server.close()

    def test_readyz_still_uses_authoritative_composite_result(self):
        r = self.runtime()
        r.nvidia_preflight_ok = False
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            with self.assertRaises(HTTPError) as ctx:
                urlopen(
                    f"http://127.0.0.1:{server.httpd.server_port}/readyz", timeout=2
                )
            self.assertEqual(ctx.exception.code, 503)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
