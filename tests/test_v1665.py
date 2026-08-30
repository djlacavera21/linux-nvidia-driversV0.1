import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v1664 import HealthServer
from nvlx.runtime_v1664 import MetricsDiagnosis, ReadinessDiagnosis


class PartialTypedProviderClosureTests(unittest.TestCase):
    @staticmethod
    def request(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    @staticmethod
    def ready_diagnosis():
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

    def test_metrics_reuses_readiness_only_typed_provider(self):
        class Stats:
            api_reachable = False
            leader = False
            inventory_fresh = False
            terminating = True
            reconcile_total = 4
            reconcile_failures = 1

        class Runtime:
            stats = Stats()

            def readiness_diagnosis(self):
                return PartialTypedProviderClosureTests.ready_diagnosis()

            def ready(self):
                raise AssertionError("metrics must not re-read raw readiness")

            def _checkpoint_ready(self):
                raise AssertionError("metrics must not re-read checkpoint readiness")

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_ready 1\n", payload)
            self.assertIn(b"nvlx_controller_api_reachable 1\n", payload)
            self.assertIn(b"nvlx_controller_leader 1\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_ready 1\n", payload)
            self.assertIn(b"nvlx_controller_reconcile_total 4\n", payload)
        finally:
            server.close()

    def test_malformed_readiness_only_provider_makes_metrics_unavailable(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = 2
            reconcile_failures = 0

        class Runtime:
            stats = Stats()

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

            def ready(self):
                return True

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_full_metrics_provider_remains_preferred_without_second_readiness_call(self):
        readiness = self.ready_diagnosis()
        metrics = MetricsDiagnosis(
            readiness=readiness,
            reconcile_total=8,
            reconcile_failures=1,
            checkpoint_writes=2,
            checkpoint_idempotent_acks=3,
            checkpoint_reconciled_commits=1,
            checkpoint_rollbacks=0,
            checkpoint_transaction_mismatches=0,
            checkpoint_failures=0,
            checkpoint_restore_attempts=5,
            checkpoint_restore_successes=4,
            checkpoint_sequence=11,
            checkpoint_epoch=6,
        )

        class Runtime:
            def readiness_diagnosis(self):
                raise AssertionError("full metrics diagnosis must remain preferred")

            def metrics_diagnosis(self):
                return metrics

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 8\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_sequence 11\n", payload)
        finally:
            server.close()

    def test_legacy_metrics_values_keep_historical_normalization(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = -4
            reconcile_failures = -2

        class Runtime:
            stats = Stats()
            nvidia_checkpoint_writes = -3

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 0\n", payload)
            self.assertIn(b"nvlx_controller_reconcile_failures_total 0\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_writes_total 0\n", payload)
        finally:
            server.close()

    def test_readiness_only_typed_provider_keeps_readyz_behavior(self):
        class Stats:
            reconcile_total = 0
            reconcile_failures = 0

        class Runtime:
            stats = Stats()

            def readiness_diagnosis(self):
                return self_ready

        self_ready = self.ready_diagnosis()
        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ready\n")
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
