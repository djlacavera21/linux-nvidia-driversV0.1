import unittest
from dataclasses import FrozenInstanceError
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v166 import MetricsDiagnosis, ReadinessDiagnosis, Runtime


class RuntimeOwnedDiagnosisTests(unittest.TestCase):
    @staticmethod
    def configured_runtime(runtime_cls=Runtime):
        r = runtime_cls(
            object(),
            "pod-a",
            leader_check=lambda: True,
            leader_fresh_seconds=25.0,
        )
        r.stats.api_reachable = True
        r.stats.inventory_fresh = True
        r.stats.terminating = False
        r.nvidia_preflight_ok = True
        if not r._leader():
            raise AssertionError("leader setup failed")
        return r

    @staticmethod
    def request(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_readiness_diagnosis_is_frozen_and_authoritative(self):
        r = self.configured_runtime()
        diagnosis = r.readiness_diagnosis()
        self.assertIsInstance(diagnosis, ReadinessDiagnosis)
        self.assertTrue(diagnosis.controller_ready)
        self.assertTrue(diagnosis.api_reachable)
        self.assertTrue(diagnosis.leader)
        self.assertTrue(diagnosis.leadership_fresh)
        self.assertTrue(diagnosis.inventory_fresh)
        self.assertTrue(diagnosis.nvidia_preflight_ready)
        self.assertTrue(diagnosis.checkpoint_ready)
        self.assertFalse(diagnosis.terminating)
        with self.assertRaises(FrozenInstanceError):
            diagnosis.leader = False

    def test_checkpoint_gate_is_not_invoked_twice_for_one_diagnosis(self):
        class CountingRuntime(Runtime):
            def __post_init__(self):
                super().__post_init__()
                self.checkpoint_ready_calls = 0

            def _checkpoint_ready(self):
                self.checkpoint_ready_calls += 1
                return super()._checkpoint_ready()

        r = self.configured_runtime(CountingRuntime)
        r.nvidia_checkpoint_store = object()
        r.nvidia_checkpoint_loaded = True
        r.nvidia_checkpoint_epoch_stale = False

        diagnosis = r.readiness_diagnosis()
        self.assertTrue(diagnosis.controller_ready)
        self.assertTrue(diagnosis.checkpoint_ready)
        self.assertEqual(r.checkpoint_ready_calls, 1)

    def test_metrics_diagnosis_evaluates_ready_once_and_freezes_sources(self):
        class CountingRuntime(Runtime):
            def __post_init__(self):
                super().__post_init__()
                self.ready_calls = 0

            def ready(self):
                self.ready_calls += 1
                return super().ready()

        r = self.configured_runtime(CountingRuntime)
        r.stats.reconcile_total = 4
        r.nvidia_checkpoint_writes = 6
        diagnosis = r.metrics_diagnosis()

        self.assertIsInstance(diagnosis, MetricsDiagnosis)
        self.assertEqual(r.ready_calls, 1)
        self.assertEqual(diagnosis.reconcile_total, 4)
        self.assertEqual(diagnosis.checkpoint_writes, 6)

        r.stats.reconcile_total = 44
        r.nvidia_checkpoint_writes = 66
        self.assertEqual(diagnosis.reconcile_total, 4)
        self.assertEqual(diagnosis.checkpoint_writes, 6)
        with self.assertRaises(FrozenInstanceError):
            diagnosis.reconcile_total = 5

    def test_http_readyz_uses_runtime_diagnosis_without_stats_or_private_fields(self):
        class DiagnosisOnlyRuntime:
            def readiness_diagnosis(self):
                return ReadinessDiagnosis(
                    controller_ready=True,
                    api_reachable=True,
                    leader=True,
                    leadership_fresh=True,
                    inventory_fresh=True,
                    nvidia_preflight_ready=True,
                    checkpoint_ready=True,
                    terminating=False,
                )

        server = HealthServer(DiagnosisOnlyRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ready\n")
            self.assertEqual(headers.get("Server"), "nvlx")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        finally:
            server.close()

    def test_http_metrics_uses_runtime_diagnosis_without_live_runtime_rereads(self):
        readiness = ReadinessDiagnosis(
            controller_ready=True,
            api_reachable=True,
            leader=True,
            leadership_fresh=True,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_ready=True,
            terminating=False,
        )

        class DiagnosisOnlyRuntime:
            def metrics_diagnosis(self):
                return MetricsDiagnosis(
                    readiness=readiness,
                    reconcile_total=7,
                    reconcile_failures=2,
                    checkpoint_writes=9,
                    checkpoint_idempotent_acks=1,
                    checkpoint_reconciled_commits=1,
                    checkpoint_rollbacks=0,
                    checkpoint_transaction_mismatches=0,
                    checkpoint_failures=0,
                    checkpoint_restore_attempts=3,
                    checkpoint_restore_successes=3,
                    checkpoint_sequence=12,
                    checkpoint_epoch=5,
                )

        server = HealthServer(DiagnosisOnlyRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 7\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_writes_total 9\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_sequence 12\n", payload)
            self.assertEqual(
                headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
        finally:
            server.close()

    def test_legacy_runtime_fallback_still_serves_readyz_and_metrics(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = 2
            reconcile_failures = 0

        class LegacyRuntime:
            stats = Stats()
            nvidia_preflight_ok = True

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        server = HealthServer(LegacyRuntime(), "127.0.0.1", 0).start()
        try:
            ready_status, _, ready_payload = self.request(server, "/readyz")
            metrics_status, _, metrics_payload = self.request(server, "/metrics")
            self.assertEqual(ready_status, 200)
            self.assertEqual(ready_payload, b"ready\n")
            self.assertEqual(metrics_status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 2\n", metrics_payload)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
