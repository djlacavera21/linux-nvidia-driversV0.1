import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v1666 import HealthServer
from nvlx.runtime_v1664 import MetricsDiagnosis, ReadinessDiagnosis


class MetricsOnlyProviderSymmetryTests(unittest.TestCase):
    @staticmethod
    def request(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    @staticmethod
    def readiness(*, ready=True, checkpoint_ready=True):
        return ReadinessDiagnosis(
            controller_ready=ready,
            api_reachable=True,
            leader=True,
            leadership_fresh=True,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_ready=checkpoint_ready,
            terminating=False,
        )

    @staticmethod
    def metrics(readiness):
        return MetricsDiagnosis(
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

    def test_readyz_reuses_metrics_only_typed_readiness(self):
        diagnosis = self.metrics(self.readiness())

        class Runtime:
            calls = 0

            @property
            def stats(self):
                raise AssertionError("readyz must not fall back to raw stats")

            def metrics_diagnosis(self):
                self.calls += 1
                return diagnosis

            def ready(self):
                raise AssertionError("readyz must not call raw ready()")

        runtime = Runtime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ready\n")
            self.assertEqual(runtime.calls, 1)
        finally:
            server.close()

    def test_readyz_uses_not_ready_metrics_only_snapshot(self):
        diagnosis = self.metrics(self.readiness(ready=False, checkpoint_ready=False))

        class Runtime:
            def metrics_diagnosis(self):
                return diagnosis

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/readyz")
            self.assertEqual(status, 503)
            self.assertEqual(payload, b"not ready\n")
        finally:
            server.close()

    def test_malformed_metrics_only_readiness_fails_closed_without_fallback(self):
        contradictory = SimpleNamespace(
            controller_ready=False,
            api_reachable=False,
            leader=True,
            leadership_fresh=False,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_ready=True,
            terminating=False,
        )

        class Runtime:
            @property
            def stats(self):
                raise AssertionError("malformed typed readiness must not fall back")

            def metrics_diagnosis(self):
                return SimpleNamespace(readiness=contradictory)

            def ready(self):
                return True

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/readyz")
            self.assertEqual(status, 503)
            self.assertEqual(payload, b"not ready\n")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_readyz_validates_only_nested_readiness_not_unrelated_metrics(self):
        readiness = self.readiness()

        class Runtime:
            def metrics_diagnosis(self):
                return SimpleNamespace(
                    readiness=readiness,
                    reconcile_total="invalid for metrics",
                )

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            ready_status, _, ready_payload = self.request(server, "/readyz")
            metrics_status, _, metrics_payload = self.request(server, "/metrics")
            self.assertEqual(ready_status, 200)
            self.assertEqual(ready_payload, b"ready\n")
            self.assertEqual(metrics_status, 500)
            self.assertEqual(metrics_payload, b"metrics unavailable\n")
        finally:
            server.close()

    def test_dedicated_readiness_remains_preferred_when_both_exist(self):
        readiness = self.readiness()

        class Runtime:
            def readiness_diagnosis(self):
                return readiness

            def metrics_diagnosis(self):
                raise AssertionError("readyz must prefer dedicated readiness")

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ready\n")
        finally:
            server.close()

    def test_legacy_runtime_without_diagnosis_methods_is_unchanged(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = 0
            reconcile_failures = 0

        class Runtime:
            stats = Stats()

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ready\n")
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
