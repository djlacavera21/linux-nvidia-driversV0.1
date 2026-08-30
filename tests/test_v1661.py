import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v166 import MetricsDiagnosis, ReadinessDiagnosis


class DiagnosisContractValidationTests(unittest.TestCase):
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

    def test_readiness_diagnosis_rejects_truthy_non_boolean_fields(self):
        with self.assertRaises(TypeError):
            ReadinessDiagnosis(
                controller_ready="false",
                api_reachable=True,
                leader=True,
                leadership_fresh=True,
                inventory_fresh=True,
                nvidia_preflight_ready=True,
                checkpoint_ready=True,
                terminating=False,
            )

    def test_metrics_diagnosis_rejects_non_integer_metric_fields(self):
        with self.assertRaises(TypeError):
            MetricsDiagnosis(
                readiness=self.valid_readiness(),
                reconcile_total="7",
                reconcile_failures=0,
                checkpoint_writes=0,
                checkpoint_idempotent_acks=0,
                checkpoint_reconciled_commits=0,
                checkpoint_rollbacks=0,
                checkpoint_transaction_mismatches=0,
                checkpoint_failures=0,
                checkpoint_restore_attempts=0,
                checkpoint_restore_successes=0,
                checkpoint_sequence=0,
                checkpoint_epoch=0,
            )

    def test_readyz_malformed_runtime_diagnosis_fails_closed_without_fallback(self):
        class MalformedRuntime:
            @property
            def stats(self):
                raise AssertionError("typed diagnosis must not fall back to stats")

            def readiness_diagnosis(self):
                return SimpleNamespace(
                    controller_ready="false",
                    api_reachable=True,
                    leader=True,
                    leadership_fresh=True,
                    inventory_fresh=True,
                    nvidia_preflight_ready=True,
                    checkpoint_ready=True,
                    terminating=False,
                )

        server = HealthServer(MalformedRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/readyz")
            self.assertEqual(status, 503)
            self.assertEqual(payload, b"not ready\n")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_metrics_malformed_integer_fails_static_500_without_fallback(self):
        readiness = self.valid_readiness()

        class MalformedRuntime:
            @property
            def stats(self):
                raise AssertionError("typed diagnosis must not fall back to stats")

            def metrics_diagnosis(self):
                return SimpleNamespace(
                    readiness=readiness,
                    reconcile_total="7",
                    reconcile_failures=0,
                    checkpoint_writes=0,
                    checkpoint_idempotent_acks=0,
                    checkpoint_reconciled_commits=0,
                    checkpoint_rollbacks=0,
                    checkpoint_transaction_mismatches=0,
                    checkpoint_failures=0,
                    checkpoint_restore_attempts=0,
                    checkpoint_restore_successes=0,
                    checkpoint_sequence=0,
                    checkpoint_epoch=0,
                )

        server = HealthServer(MalformedRuntime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_metrics_malformed_nested_readiness_fails_static_500(self):
        malformed_readiness = SimpleNamespace(
            controller_ready=True,
            api_reachable=True,
            leader="true",
            leadership_fresh=True,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_ready=True,
            terminating=False,
        )

        class MalformedRuntime:
            def metrics_diagnosis(self):
                return SimpleNamespace(
                    readiness=malformed_readiness,
                    reconcile_total=1,
                    reconcile_failures=0,
                    checkpoint_writes=0,
                    checkpoint_idempotent_acks=0,
                    checkpoint_reconciled_commits=0,
                    checkpoint_rollbacks=0,
                    checkpoint_transaction_mismatches=0,
                    checkpoint_failures=0,
                    checkpoint_restore_attempts=0,
                    checkpoint_restore_successes=0,
                    checkpoint_sequence=0,
                    checkpoint_epoch=0,
                )

        server = HealthServer(MalformedRuntime(), "127.0.0.1", 0).start()
        try:
            status, _, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
        finally:
            server.close()

    def test_valid_diagnosis_contract_remains_accepted(self):
        readiness = self.valid_readiness()
        metrics = MetricsDiagnosis(
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
            checkpoint_restore_successes=4,
            checkpoint_sequence=9,
            checkpoint_epoch=5,
        )

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
            self.assertIn(b"nvlx_controller_reconcile_total 7\n", metrics_payload)
            self.assertIn(b"nvlx_nvidia_checkpoint_sequence 9\n", metrics_payload)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
