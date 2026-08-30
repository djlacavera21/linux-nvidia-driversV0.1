import time
import unittest
from types import SimpleNamespace
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer, _readiness_snapshot


class ReadinessSnapshotConsistencyTests(unittest.TestCase):
    @staticmethod
    def stats():
        return SimpleNamespace(
            api_reachable=True,
            leader=True,
            inventory_fresh=True,
            terminating=False,
            reconcile_total=0,
            reconcile_failures=0,
        )

    @staticmethod
    def metrics_body(server):
        with urlopen(
            f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
        ) as response:
            return response.read().decode("utf-8")

    def test_snapshot_observes_leadership_after_authoritative_readiness_mutation(self):
        class Runtime:
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            nvidia_preflight_ok = True

            def ready(self):
                self.stats.leader = False
                return False

        r = Runtime()
        r.stats = self.stats()
        snapshot = _readiness_snapshot(r, r.stats)
        self.assertFalse(snapshot.controller_ready)
        self.assertFalse(snapshot.leadership_fresh)
        self.assertFalse(r.stats.leader)

    def test_snapshot_observes_checkpoint_after_authoritative_readiness_mutation(self):
        class Runtime:
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            nvidia_preflight_ok = True
            checkpoint_ok = True

            def ready(self):
                self.checkpoint_ok = False
                return False

            def _checkpoint_ready(self):
                return self.checkpoint_ok

        r = Runtime()
        r.stats = self.stats()
        snapshot = _readiness_snapshot(r, r.stats)
        self.assertFalse(snapshot.controller_ready)
        self.assertFalse(snapshot.checkpoint_ready)

    def test_http_metrics_do_not_mix_pre_and_post_readiness_leadership(self):
        class Runtime:
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            nvidia_preflight_ok = True

            def ready(self):
                self.stats.leader = False
                return False

        r = Runtime()
        r.stats = self.stats()
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_controller_leader 0\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 0\n", body)
        finally:
            server.close()

    def test_http_metrics_do_not_mix_pre_and_post_readiness_checkpoint_state(self):
        class Runtime:
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            nvidia_preflight_ok = True
            checkpoint_ok = True

            def ready(self):
                self.checkpoint_ok = False
                return False

            def _checkpoint_ready(self):
                return self.checkpoint_ok

        r = Runtime()
        r.stats = self.stats()
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 0\n", body)
            self.assertIn("nvlx_nvidia_checkpoint_ready 0\n", body)
        finally:
            server.close()

    def test_ready_exception_fails_closed_before_post_state_is_observed(self):
        class Runtime:
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            nvidia_preflight_ok = True

            def ready(self):
                self.stats.leader = False
                raise RuntimeError("readiness failed")

        r = Runtime()
        r.stats = self.stats()
        snapshot = _readiness_snapshot(r, r.stats)
        self.assertFalse(snapshot.controller_ready)
        self.assertFalse(snapshot.leadership_fresh)
        self.assertFalse(r.stats.leader)


if __name__ == "__main__":
    unittest.main()
