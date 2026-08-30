import time
import unittest
from dataclasses import FrozenInstanceError
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import (
    HealthServer,
    _metrics_snapshot,
    _render_metrics_snapshot,
)
from nvlx.runtime_v1652 import Runtime


class MetricsSnapshotClosureTests(unittest.TestCase):
    def runtime(self):
        r = Runtime(
            object(),
            "pod-a",
            leader_check=lambda: True,
            leader_fresh_seconds=25.0,
        )
        r.stats.api_reachable = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        r.nvidia_preflight_ok = True
        self.assertTrue(r._leader())
        return r

    @staticmethod
    def request(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_snapshot_is_frozen_and_retains_captured_values(self):
        r = self.runtime()
        r.stats.reconcile_total = 3
        r.stats.reconcile_failures = 1
        r.nvidia_checkpoint_writes = 5
        r.nvidia_checkpoint_sequence = 11

        snapshot = _metrics_snapshot(r, r.stats)

        r.stats.reconcile_total = 99
        r.stats.reconcile_failures = 88
        r.nvidia_checkpoint_writes = 77
        r.nvidia_checkpoint_sequence = 66

        body = _render_metrics_snapshot(snapshot)
        self.assertIn("nvlx_controller_reconcile_total 3\n", body)
        self.assertIn("nvlx_controller_reconcile_failures_total 1\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_writes_total 5\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_sequence 11\n", body)
        self.assertNotIn("nvlx_controller_reconcile_total 99\n", body)
        with self.assertRaises(FrozenInstanceError):
            snapshot.reconcile_total = 4

    def test_http_metrics_reads_mutable_sources_once(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_failures = 0

            def __init__(self):
                self.reconcile_reads = 0

            @property
            def reconcile_total(self):
                self.reconcile_reads += 1
                if self.reconcile_reads > 1:
                    raise RuntimeError("reconcile_total reread")
                return 7

        class ProbeRuntime:
            nvidia_preflight_ok = True
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()

            def __init__(self):
                self.stats = Stats()
                self.checkpoint_reads = 0

            @property
            def nvidia_checkpoint_writes(self):
                self.checkpoint_reads += 1
                if self.checkpoint_reads > 1:
                    raise RuntimeError("checkpoint_writes reread")
                return 9

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        r = ProbeRuntime()
        server = HealthServer(r, "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 7\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_writes_total 9\n", payload)
            self.assertEqual(r.stats.reconcile_reads, 1)
            self.assertEqual(r.checkpoint_reads, 1)
            self.assertEqual(headers.get("Server"), "nvlx")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        finally:
            server.close()

    def test_snapshot_capture_failure_uses_existing_static_500_contract(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_failures = 0

            @property
            def reconcile_total(self):
                raise RuntimeError("sensitive-capture-detail")

        class ProbeRuntime:
            nvidia_preflight_ok = True
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            stats = Stats()

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        server = HealthServer(ProbeRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assertNotIn(b"sensitive-capture-detail", payload)
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_readiness_endpoint_remains_independent_of_metrics_capture_failure(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_failures = 0

            @property
            def reconcile_total(self):
                raise RuntimeError("metrics only")

        class ProbeRuntime:
            nvidia_preflight_ok = True
            leader_fresh_seconds = 25.0
            _leader_verified_monotonic = time.monotonic()
            stats = Stats()

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        server = HealthServer(ProbeRuntime(), "127.0.0.1", 0).start()
        try:
            metrics_status, _, _ = self.request(server, "/metrics")
            ready_status, ready_headers, ready_payload = self.request(server, "/readyz")
            self.assertEqual(metrics_status, 500)
            self.assertEqual(ready_status, 200)
            self.assertEqual(ready_payload, b"ready\n")
            self.assertEqual(ready_headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_successful_metrics_transport_contract_is_unchanged(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertEqual(
                headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
            self.assertEqual(headers.get("Server"), "nvlx")
            self.assertIn(b"# HELP nvlx_controller_ready ", payload)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
