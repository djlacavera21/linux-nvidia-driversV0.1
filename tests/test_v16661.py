import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from nvlx.http_v16661 import HealthServer
from nvlx.runtime_v1664 import MetricsDiagnosis, ReadinessDiagnosis


class HeadParityTests(unittest.TestCase):
    @staticmethod
    def request(server, path, method="GET"):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        request = Request(url, method=method)
        try:
            with urlopen(request, timeout=2) as response:
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

    @staticmethod
    def assert_representation_headers_match(testcase, get_headers, head_headers):
        for name in ("Content-Type", "Cache-Control", "Content-Length", "Server"):
            testcase.assertEqual(head_headers.get(name), get_headers.get(name))

    def test_livez_head_matches_get_metadata_without_body(self):
        class Runtime:
            pass

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/livez")
            head_status, head_headers, head_body = self.request(
                server, "/livez", method="HEAD"
            )
            self.assertEqual(get_status, 200)
            self.assertEqual(head_status, get_status)
            self.assertEqual(get_body, b"ok\n")
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
            self.assertEqual(head_headers.get("Content-Length"), str(len(get_body)))
        finally:
            server.close()

    def test_readyz_head_matches_ready_get_for_metrics_only_provider(self):
        diagnosis = self.metrics(self.readiness())

        class Runtime:
            @property
            def stats(self):
                raise AssertionError("typed HEAD readiness must not fall back to raw stats")

            def metrics_diagnosis(self):
                return diagnosis

            def ready(self):
                raise AssertionError("typed HEAD readiness must not call raw ready()")

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/readyz")
            head_status, head_headers, head_body = self.request(
                server, "/readyz", method="HEAD"
            )
            self.assertEqual(get_status, 200)
            self.assertEqual(head_status, get_status)
            self.assertEqual(get_body, b"ready\n")
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
            self.assertEqual(head_headers.get("Content-Length"), str(len(get_body)))
        finally:
            server.close()

    def test_readyz_head_matches_not_ready_get(self):
        diagnosis = self.metrics(self.readiness(ready=False, checkpoint_ready=False))

        class Runtime:
            def metrics_diagnosis(self):
                return diagnosis

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/readyz")
            head_status, head_headers, head_body = self.request(
                server, "/readyz", method="HEAD"
            )
            self.assertEqual(get_status, 503)
            self.assertEqual(head_status, get_status)
            self.assertEqual(get_body, b"not ready\n")
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
            self.assertEqual(head_headers.get("Content-Length"), str(len(get_body)))
        finally:
            server.close()

    def test_metrics_head_matches_successful_get_metadata_without_body(self):
        diagnosis = self.metrics(self.readiness())

        class Runtime:
            def metrics_diagnosis(self):
                return diagnosis

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/metrics")
            head_status, head_headers, head_body = self.request(
                server, "/metrics", method="HEAD"
            )
            self.assertEqual(get_status, 200)
            self.assertEqual(head_status, get_status)
            self.assertIn(b"# HELP ", get_body)
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
            self.assertEqual(
                head_headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
            self.assertEqual(head_headers.get("Content-Length"), str(len(get_body)))
        finally:
            server.close()

    def test_metrics_head_preserves_static_failure_containment(self):
        readiness = self.readiness()

        class Runtime:
            def metrics_diagnosis(self):
                return SimpleNamespace(
                    readiness=readiness,
                    reconcile_total="invalid",
                )

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/metrics")
            head_status, head_headers, head_body = self.request(
                server, "/metrics", method="HEAD"
            )
            self.assertEqual(get_status, 500)
            self.assertEqual(head_status, get_status)
            self.assertEqual(get_body, b"metrics unavailable\n")
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
            self.assertEqual(head_headers.get("Content-Length"), str(len(get_body)))
        finally:
            server.close()

    def test_unknown_head_matches_get_empty_404_contract(self):
        class Runtime:
            pass

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/unknown")
            head_status, head_headers, head_body = self.request(
                server, "/unknown", method="HEAD"
            )
            self.assertEqual(get_status, 404)
            self.assertEqual(head_status, get_status)
            self.assertEqual(get_body, b"")
            self.assertEqual(head_body, b"")
            self.assertEqual(head_headers.get("Server"), get_headers.get("Server"))
            self.assertIsNone(head_headers.get("Cache-Control"))
            self.assertIsNone(head_headers.get("Content-Length"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
