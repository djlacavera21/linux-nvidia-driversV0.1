import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.controller_metrics import render
from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1642 import Runtime


class CheckpointAwareReadinessTests(unittest.TestCase):
    def runtime(self):
        r = Runtime(object(), "pod-a", leader_check=lambda: True)
        r.stats.api_reachable = True
        r.stats.leader = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        return r

    def test_no_checkpoint_store_does_not_add_readiness_gate(self):
        r = self.runtime()
        self.assertTrue(r.ready())
        self.assertTrue(r._checkpoint_ready())

    def test_configured_store_requires_completed_restore(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = False
        self.assertFalse(r._checkpoint_ready())
        self.assertFalse(r.ready())

    def test_stale_lease_epoch_blocks_readiness(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = True
        self.assertFalse(r._checkpoint_ready())
        self.assertFalse(r.ready())

    def test_current_restored_checkpoint_allows_readiness(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False
        r.nvidia_checkpoint_failures = 9
        self.assertTrue(r._checkpoint_ready())
        self.assertTrue(r.ready())

    def test_generic_controller_gate_still_blocks_readiness(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False
        r.stats.inventory_fresh = False
        self.assertFalse(r.ready())

    def test_renderer_exports_checkpoint_ready_gauge(self):
        body = render(
            leader=True,
            reconcile_total=0,
            reconcile_failures=0,
            pending_approvals=0,
            rollback_required=0,
            checkpoint_ready=False,
        )
        self.assertIn("nvlx_nvidia_checkpoint_ready 0\n", body)

    def test_http_readyz_tracks_checkpoint_gate_and_metrics(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = False
        server = HealthServer(r, "127.0.0.1", 0).start()
        base = f"http://127.0.0.1:{server.httpd.server_port}"
        try:
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"{base}/readyz", timeout=2)
            self.assertEqual(ctx.exception.code, 503)

            with urlopen(f"{base}/metrics", timeout=2) as response:
                body = response.read().decode("utf-8")
            self.assertIn("nvlx_nvidia_checkpoint_ready 0\n", body)

            r.nvidia_checkpoint_loaded = True
            r.nvidia_checkpoint_epoch_stale = False
            with urlopen(f"{base}/readyz", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b"ready\n")
            with urlopen(f"{base}/metrics", timeout=2) as response:
                body = response.read().decode("utf-8")
            self.assertIn("nvlx_nvidia_checkpoint_ready 1\n", body)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
