import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import nvlx.http_v16662 as http_v16662
from nvlx.http_v16662 import HealthServer
from nvlx.runtime_v1664 import MetricsDiagnosis, ReadinessDiagnosis


class UnifiedGetHeadDispatcherTests(unittest.TestCase):
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

    def test_get_and_head_share_the_same_live_resolver(self):
        original = http_v16662._resolve_live_response

        class Runtime:
            pass

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            with patch.object(
                http_v16662,
                "_resolve_live_response",
                wraps=original,
            ) as resolver:
                self.request(server, "/livez", method="GET")
                self.request(server, "/livez", method="HEAD")
                self.assertEqual(resolver.call_count, 2)
                self.assertEqual(resolver.call_args_list[0].args[1], "/livez")
                self.assertEqual(resolver.call_args_list[1].args[1], "/livez")
        finally:
            server.close()

    def test_livez_get_head_parity(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/livez")
            head_status, head_headers, head_body = self.request(
                server, "/livez", method="HEAD"
            )
            self.assertEqual((get_status, get_body), (200, b"ok\n"))
            self.assertEqual(head_status, get_status)
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
        finally:
            server.close()

    def test_ready_and_not_ready_get_head_parity(self):
        for ready, checkpoint_ready, expected_status, expected_body in (
            (True, True, 200, b"ready\n"),
            (False, False, 503, b"not ready\n"),
        ):
            diagnosis = self.metrics(
                self.readiness(ready=ready, checkpoint_ready=checkpoint_ready)
            )

            class Runtime:
                def metrics_diagnosis(self):
                    return diagnosis

            server = HealthServer(Runtime(), "127.0.0.1", 0).start()
            try:
                get_status, get_headers, get_body = self.request(server, "/readyz")
                head_status, head_headers, head_body = self.request(
                    server, "/readyz", method="HEAD"
                )
                self.assertEqual(get_status, expected_status)
                self.assertEqual(get_body, expected_body)
                self.assertEqual(head_status, get_status)
                self.assertEqual(head_body, b"")
                self.assert_representation_headers_match(
                    self, get_headers, head_headers
                )
            finally:
                server.close()

    def test_metrics_success_get_head_parity(self):
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
            self.assertIn(b"# HELP ", get_body)
            self.assertEqual(head_status, get_status)
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
            self.assertEqual(
                head_headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
        finally:
            server.close()

    def test_metrics_failure_get_head_parity(self):
        readiness = self.readiness()

        class Runtime:
            def metrics_diagnosis(self):
                return SimpleNamespace(readiness=readiness, reconcile_total="invalid")

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/metrics")
            head_status, head_headers, head_body = self.request(
                server, "/metrics", method="HEAD"
            )
            self.assertEqual(get_status, 500)
            self.assertEqual(get_body, b"metrics unavailable\n")
            self.assertEqual(head_status, get_status)
            self.assertEqual(head_body, b"")
            self.assert_representation_headers_match(self, get_headers, head_headers)
        finally:
            server.close()

    def test_unknown_get_head_share_empty_404_contract(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "/unknown")
            head_status, head_headers, head_body = self.request(
                server, "/unknown", method="HEAD"
            )
            self.assertEqual(get_status, 404)
            self.assertEqual(head_status, 404)
            self.assertEqual(get_body, b"")
            self.assertEqual(head_body, b"")
            self.assertEqual(head_headers.get("Server"), get_headers.get("Server"))
            self.assertIsNone(get_headers.get("Cache-Control"))
            self.assertIsNone(head_headers.get("Cache-Control"))
            self.assertIsNone(get_headers.get("Content-Length"))
            self.assertIsNone(head_headers.get("Content-Length"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
