import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1652 import Runtime


class HttpServerFingerprintTests(unittest.TestCase):
    def runtime(self, *, ready: bool = True):
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
        if not ready:
            r.stats.api_reachable = False
        return r

    @staticmethod
    def request(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def assert_minimal_server_header(self, headers):
        server = headers.get("Server")
        self.assertEqual(server, "nvlx")
        self.assertNotIn("Python/", server)
        self.assertNotIn("BaseHTTP", server)

    def test_livez_uses_stable_product_server_header(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/livez")
            self.assertEqual(status, 200)
            self.assertEqual(payload, b"ok\n")
            self.assert_minimal_server_header(headers)
        finally:
            server.close()

    def test_readyz_ready_and_not_ready_hide_python_fingerprint(self):
        for ready, expected_status, expected_body in (
            (True, 200, b"ready\n"),
            (False, 503, b"not ready\n"),
        ):
            server = HealthServer(self.runtime(ready=ready), "127.0.0.1", 0).start()
            try:
                status, headers, payload = self.request(server, "/readyz")
                self.assertEqual(status, expected_status)
                self.assertEqual(payload, expected_body)
                self.assert_minimal_server_header(headers)
            finally:
                server.close()

    def test_metrics_success_hides_python_fingerprint(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"# HELP nvlx_controller_ready ", payload)
            self.assert_minimal_server_header(headers)
        finally:
            server.close()

    def test_metrics_failure_hides_python_fingerprint(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            with patch(
                "nvlx.http_v16.render_metrics",
                side_effect=RuntimeError("schema mismatch"),
            ):
                status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 500)
            self.assertEqual(payload, b"metrics unavailable\n")
            self.assert_minimal_server_header(headers)
        finally:
            server.close()

    def test_unknown_path_hides_python_fingerprint_without_changing_404_body(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/unknown")
            self.assertEqual(status, 404)
            self.assertEqual(payload, b"")
            self.assert_minimal_server_header(headers)
            self.assertIsNone(headers.get("Content-Length"))
            self.assertIsNone(headers.get("Cache-Control"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
