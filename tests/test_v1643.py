import time
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1643 import Runtime


class CompositionalReadinessTests(unittest.TestCase):
    def runtime(self, leader_check=lambda: True):
        r = Runtime(object(), "pod-a", leader_check=leader_check, leader_fresh_seconds=25.0)
        r.stats.api_reachable = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        r.nvidia_preflight_ok = True
        self.assertTrue(r._leader())
        return r

    def checkpoint_safe(self, r):
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False
        return r

    def test_checkpoint_gate_composes_with_full_existing_readiness(self):
        r = self.checkpoint_safe(self.runtime())
        self.assertTrue(r.ready())

    def test_nvidia_preflight_failure_still_blocks_readiness(self):
        r = self.checkpoint_safe(self.runtime())
        r.nvidia_preflight_ok = False
        self.assertFalse(r.ready())

    def test_expired_leadership_proof_still_blocks_readiness(self):
        r = self.checkpoint_safe(self.runtime())
        r._leader_verified_monotonic = time.monotonic() - r.leader_fresh_seconds - 1.0
        r.stats.leader = True
        self.assertFalse(r.ready())
        self.assertFalse(r.stats.leader)

    def test_api_loss_still_invalidates_cached_leadership(self):
        r = self.checkpoint_safe(self.runtime())
        r.stats.api_reachable = False
        self.assertFalse(r.ready())
        self.assertFalse(r.stats.leader)
        self.assertEqual(r._leader_verified_monotonic, 0.0)

    def test_checkpoint_restore_gate_remains_required(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = False
        r.nvidia_checkpoint_epoch_stale = False
        self.assertFalse(r.ready())

    def test_checkpoint_epoch_stale_gate_remains_required(self):
        r = self.runtime()
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = True
        self.assertFalse(r.ready())

    def test_http_readyz_observes_preflight_and_leadership_freshness(self):
        r = self.checkpoint_safe(self.runtime())
        server = HealthServer(r, "127.0.0.1", 0).start()
        base = f"http://127.0.0.1:{server.httpd.server_port}"
        try:
            with urlopen(f"{base}/readyz", timeout=2) as response:
                self.assertEqual(response.status, 200)

            r.nvidia_preflight_ok = False
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"{base}/readyz", timeout=2)
            self.assertEqual(ctx.exception.code, 503)

            r.nvidia_preflight_ok = True
            self.assertTrue(r._leader())
            r._leader_verified_monotonic = time.monotonic() - r.leader_fresh_seconds - 1.0
            r.stats.leader = True
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"{base}/readyz", timeout=2)
            self.assertEqual(ctx.exception.code, 503)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
