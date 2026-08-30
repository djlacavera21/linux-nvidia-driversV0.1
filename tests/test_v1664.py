import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v1664 import HealthServer
from nvlx.runtime_v1664 import MetricsDiagnosis, ReadinessDiagnosis, Runtime


class EffectiveLeadershipDomainTests(unittest.TestCase):
    @staticmethod
    def request(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    @staticmethod
    def valid_readiness():
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

    @staticmethod
    def valid_metrics(readiness):
        return MetricsDiagnosis(
            readiness=readiness,
            reconcile_total=7,
            reconcile_failures=1,
            checkpoint_writes=2,
            checkpoint_idempotent_acks=3,
            checkpoint_reconciled_commits=1,
            checkpoint_rollbacks=0,
            checkpoint_transaction_mismatches=0,
            checkpoint_failures=0,
            checkpoint_restore_attempts=4,
            checkpoint_restore_successes=3,
            checkpoint_sequence=9,
            checkpoint_epoch=5,
        )

    def test_diagnosis_rejects_leader_without_api(self):
        with self.assertRaises(ValueError):
            ReadinessDiagnosis(
                controller_ready=False,
                api_reachable=False,
                leader=True,
                leadership_fresh=False,
                inventory_fresh=True,
                nvidia_preflight_ready=True,
                checkpoint_ready=True,
                terminating=False,
            )

    def test_diagnosis_rejects_leader_while_terminating(self):
        with self.assertRaises(ValueError):
            ReadinessDiagnosis(
                controller_ready=False,
                api_reachable=True,
                leader=True,
                leadership_fresh=False,
                inventory_fresh=True,
                nvidia_preflight_ready=True,
                checkpoint_ready=True,
                terminating=True,
            )

    def test_runtime_normalizes_terminating_leader_capture_without_mutating_stats(self):
        class TornRuntime(Runtime):
            def ready(self):
                return False

        runtime = TornRuntime(
            object(),
            "pod-a",
            leader_check=lambda: True,
            leader_fresh_seconds=25.0,
        )
        runtime.stats.api_reachable = True
        runtime.stats.leader = True
        runtime.stats.inventory_fresh = True
        runtime.stats.terminating = True
        runtime.nvidia_preflight_ok = True

        diagnosis = runtime.readiness_diagnosis()
        self.assertFalse(diagnosis.controller_ready)
        self.assertFalse(diagnosis.leader)
        self.assertFalse(diagnosis.leadership_fresh)
        self.assertTrue(diagnosis.terminating)
        self.assertTrue(runtime.stats.leader)

    def test_readyz_rejects_typed_leader_without_api_without_fallback(self):
        class ContradictoryRuntime:
            @property
            def stats(self):
                raise AssertionError("typed diagnosis must not fall back to stats")

            def readiness_diagnosis(self):
                return SimpleNamespace(
                    controller_ready=False,
                    api_reachable=False,
                    leader=True,
                    leadership_fresh=False,
                    inventory_fresh=True,
                    nvidia_preflight_ready=True,
                    checkpoint_ready=True,
                    terminating=False,
                )

        server = HealthServer(ContradictoryRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/readyz")
            self.assertEqual(status, 503)
            self.assertEqual(payload, b"not ready\n")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_metrics_rejects_nested_typed_leader_while_terminating(self):
        contradictory = SimpleNamespace(
            controller_ready=False,
            api_reachable=True,
            leader=True,
            leadership_fresh=False,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_ready=True,
            terminating=True,
        )

        class ContradictoryRuntime:
            def metrics_diagnosis(self):
                return SimpleNamespace(
                    readiness=contradictory,
                    reconcile_total=7,
                    reconcile_failures=1,
                    checkpoint_writes=2,
                    checkpoint_idempotent_acks=3,
                    checkpoint_reconciled_commits=1,
                    checkpoint_rollbacks=0,
                    checkpoint_transaction_mismatches=0,
                    checkpoint_failures=0,
                    checkpoint_restore_attempts=4,
                    checkpoint_restore_successes=3,
                    checkpoint_sequence=9,
                    checkpoint_epoch=5,
                )

        server = HealthServer(ContradictoryRuntime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
        finally:
            server.close()

    def test_legacy_runtime_keeps_historical_fallback(self):
        class Stats:
            api_reachable = False
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = 0
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
            status, _, payload = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ready\n")
        finally:
            server.close()

    def test_valid_typed_readiness_and_metrics_remain_accepted(self):
        readiness = self.valid_readiness()
        metrics = self.valid_metrics(readiness)

        class ValidRuntime:
            def readiness_diagnosis(self):
                return readiness

            def metrics_diagnosis(self):
                return metrics

        server = HealthServer(ValidRuntime(), "127.0.0.1", 0).start()
        try:
            ready_status, _, ready_payload = self.request(server, "/readyz")
            metrics_status, _, metrics_payload = self.request(server, "/metrics")
            self.assertEqual(ready_status, 200)
            self.assertEqual(ready_payload, b"ready\n")
            self.assertEqual(metrics_status, 200)
            self.assertIn(b"nvlx_controller_leader 1\n", metrics_payload)
            self.assertIn(b"nvlx_controller_ready 1\n", metrics_payload)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
