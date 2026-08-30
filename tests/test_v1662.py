import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1662 import MetricsDiagnosis, ReadinessDiagnosis


class DiagnosisValueDomainTests(unittest.TestCase):
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

    def metrics(self, **overrides):
        values = dict(
            readiness=self.valid_readiness(),
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
        values.update(overrides)
        return MetricsDiagnosis(**values)

    def namespace_metrics(self, **overrides):
        values = dict(
            readiness=self.valid_readiness(),
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
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_metrics_diagnosis_rejects_negative_values(self):
        with self.assertRaises(ValueError):
            self.metrics(checkpoint_sequence=-1)

    def test_metrics_diagnosis_rejects_reconcile_failures_above_attempts(self):
        with self.assertRaises(ValueError):
            self.metrics(reconcile_total=2, reconcile_failures=3)

    def test_metrics_diagnosis_rejects_restore_successes_above_attempts(self):
        with self.assertRaises(ValueError):
            self.metrics(
                checkpoint_restore_attempts=2,
                checkpoint_restore_successes=3,
            )

    def test_metrics_diagnosis_rejects_reconciled_commits_above_accepted_commits(self):
        with self.assertRaises(ValueError):
            self.metrics(
                checkpoint_writes=1,
                checkpoint_idempotent_acks=1,
                checkpoint_reconciled_commits=3,
            )

    def test_http_typed_negative_metric_fails_static_500_without_fallback(self):
        class MalformedRuntime:
            @property
            def stats(self):
                raise AssertionError("typed diagnosis must not fall back to stats")

            def metrics_diagnosis(self):
                return self_outer.namespace_metrics(checkpoint_writes=-1)

        self_outer = self
        server = HealthServer(MalformedRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_http_typed_relational_violation_fails_static_500(self):
        class MalformedRuntime:
            def metrics_diagnosis(self):
                return self_outer.namespace_metrics(
                    checkpoint_restore_attempts=1,
                    checkpoint_restore_successes=2,
                )

        self_outer = self
        server = HealthServer(MalformedRuntime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
        finally:
            server.close()

    def test_legacy_runtime_negative_metric_still_uses_historical_clamp(self):
        class Stats:
            api_reachable = True
            leader = True
            inventory_fresh = True
            terminating = False
            reconcile_total = -7
            reconcile_failures = -2

        class LegacyRuntime:
            stats = Stats()
            nvidia_preflight_ok = True
            nvidia_checkpoint_writes = -9

            def ready(self):
                return True

            def _checkpoint_ready(self):
                return True

        server = HealthServer(LegacyRuntime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 0\n", payload)
            self.assertIn(b"nvlx_controller_reconcile_failures_total 0\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_writes_total 0\n", payload)
        finally:
            server.close()

    def test_valid_domain_diagnosis_remains_accepted(self):
        metrics = self.metrics()

        class ValidRuntime:
            def metrics_diagnosis(self):
                return metrics

        server = HealthServer(ValidRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"nvlx_controller_reconcile_total 7\n", payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_restore_successes_total 3\n", payload)
            self.assertEqual(
                headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
