import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1652 import Runtime


class HttpResponseFramingTests(unittest.TestCase):
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

    def assert_framed(self, server, path, *, status, body, content_type):
        actual_status, headers, payload = self.request(server, path)
        self.assertEqual(actual_status, status)
        self.assertEqual(payload, body)
        self.assertEqual(headers.get("Content-Type"), content_type)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(headers.get("Content-Length"), str(len(payload)))

    def test_livez_declares_exact_utf8_payload_length(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            self.assert_framed(
                server,
                "/livez",
                status=200,
                body=b"ok\n",
                content_type="text/plain; charset=utf-8",
            )
        finally:
            server.close()

    def test_readyz_ready_declares_exact_utf8_payload_length(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            self.assert_framed(
                server,
                "/readyz",
                status=200,
                body=b"ready\n",
                content_type="text/plain; charset=utf-8",
            )
        finally:
            server.close()

    def test_readyz_not_ready_declares_exact_utf8_payload_length(self):
        server = HealthServer(self.runtime(ready=False), "127.0.0.1", 0).start()
        try:
            self.assert_framed(
                server,
                "/readyz",
                status=503,
                body=b"not ready\n",
                content_type="text/plain; charset=utf-8",
            )
        finally:
            server.close()

    def test_metrics_content_length_matches_actual_exposition_bytes(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertTrue(payload)
            self.assertEqual(
                headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
            self.assertIn(b"# HELP nvlx_controller_ready ", payload)
        finally:
            server.close()

    def test_content_length_uses_encoded_utf8_bytes_not_character_count(self):
        body = "nvlx_test_info café\n"
        payload = body.encode("utf-8")
        self.assertNotEqual(len(body), len(payload))
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            with patch("nvlx.http_v16.render_metrics", return_value=body):
                status, headers, actual = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertEqual(actual, payload)
            self.assertEqual(headers.get("Content-Length"), str(len(payload)))
        finally:
            server.close()

    def test_unknown_path_framing_remains_unchanged(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "/unknown")
            self.assertEqual(status, 404)
            self.assertEqual(payload, b"")
            self.assertIsNone(headers.get("Content-Length"))
            self.assertIsNone(headers.get("Cache-Control"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
