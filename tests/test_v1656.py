import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1652 import Runtime


class MetricsExporterFaultContainmentTests(unittest.TestCase):
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

    def test_renderer_failure_returns_deterministic_framed_500(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            with patch(
                "nvlx.http_v16.render_metrics",
                side_effect=RuntimeError("schema drift: sensitive-internal-detail"),
            ):
                status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
            self.assertNotIn(b"sensitive-internal-detail", payload)
            self.assertNotIn(b"# HELP", payload)
            self.assertNotIn(b"# TYPE", payload)
        finally:
            server.close()

    def test_non_schema_renderer_exception_is_contained_the_same_way(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            with patch(
                "nvlx.http_v16.render_metrics",
                side_effect=ValueError("unexpected render failure"),
            ):
                status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
        finally:
            server.close()

    def test_metrics_failure_does_not_change_readiness_endpoint(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            with patch(
                "nvlx.http_v16.render_metrics",
                side_effect=RuntimeError("schema mismatch"),
            ):
                metrics_status, _, metrics_payload = self.request(server, "/metrics")
            ready_status, ready_headers, ready_payload = self.request(server, "/readyz")
            self.assertEqual(metrics_status, 500)
            self.assertEqual(metrics_payload, b"metrics unavailable\n")
            self.assertEqual(ready_status, 200)
            self.assertEqual(ready_payload, b"ready\n")
            self.assertEqual(ready_headers.get("Cache-Control"), "no-store")
            self.assertEqual(
                ready_headers.get("Content-Length"), str(len(ready_payload))
            )
        finally:
            server.close()

    def test_successful_metrics_response_preserves_prometheus_contract(self):
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
            self.assertIn(b"# HELP nvlx_controller_ready ", payload)
            self.assertIn(b"# TYPE nvlx_controller_ready gauge\n", payload)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
