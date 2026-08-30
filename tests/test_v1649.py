import time
import unittest
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer, _readiness_snapshot


class LeadershipSnapshotClosureTests(unittest.TestCase):
    class FlappingStats:
        api_reachable = True
        inventory_fresh = True
        terminating = False
        reconcile_total = 0
        reconcile_failures = 0

        def __init__(self):
            self.leader_reads = 0

        @property
        def leader(self):
            self.leader_reads += 1
            return self.leader_reads == 1

    class StableRuntime:
        leader_fresh_seconds = 25.0
        _leader_verified_monotonic = time.monotonic()
        nvidia_preflight_ok = True

        def ready(self):
            return True

    @staticmethod
    def metrics_body(server):
        with urlopen(
            f"http://127.0.0.1:{server.httpd.server_port}/metrics", timeout=2
        ) as response:
            return response.read().decode("utf-8")

    def test_snapshot_captures_effective_leader_once(self):
        r = self.StableRuntime()
        r.stats = self.FlappingStats()

        snapshot = _readiness_snapshot(r, r.stats)

        self.assertTrue(snapshot.controller_ready)
        self.assertTrue(snapshot.leader)
        self.assertTrue(snapshot.leadership_fresh)
        self.assertEqual(r.stats.leader_reads, 1)

    def test_http_metrics_render_snapshot_leader_without_reread(self):
        r = self.StableRuntime()
        r.stats = self.FlappingStats()
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            body = self.metrics_body(server)
            self.assertIn("nvlx_controller_ready 1\n", body)
            self.assertIn("nvlx_controller_leader 1\n", body)
            self.assertIn("nvlx_controller_leadership_fresh 1\n", body)
            self.assertEqual(r.stats.leader_reads, 1)
        finally:
            server.close()

    def test_authoritative_readiness_mutation_is_captured_after_evaluation(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = 0
            reconcile_failures = 0

        class Runtime:
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            nvidia_preflight_ok = True

            def ready(self):
                self.stats.leader = False
                return False

        r = Runtime()
        r.stats = Stats()
        snapshot = _readiness_snapshot(r, r.stats)
        self.assertFalse(snapshot.controller_ready)
        self.assertFalse(snapshot.leader)
        self.assertFalse(snapshot.leadership_fresh)

    def test_legacy_runtime_uses_one_captured_leader_value(self):
        class Runtime:
            nvidia_preflight_ok = True

        r = Runtime()
        r.stats = self.FlappingStats()
        snapshot = _readiness_snapshot(r, r.stats)
        self.assertTrue(snapshot.controller_ready)
        self.assertTrue(snapshot.leader)
        self.assertTrue(snapshot.leadership_fresh)
        self.assertEqual(r.stats.leader_reads, 1)


if __name__ == "__main__":
    unittest.main()
