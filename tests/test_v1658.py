import http.client
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1652 import Runtime


class HttpFrameworkErrorContainmentTests(unittest.TestCase):
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
    def get(server, path):
        url = f"http://127.0.0.1:{server.httpd.server_port}{path}"
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    @staticmethod
    def request(server, method, path):
        conn = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            conn.request(method, path)
            response = conn.getresponse()
            return response.status, response.headers, response.read()
        finally:
            conn.close()

    def assert_contained(self, status, headers, payload):
        self.assertEqual(status, 501)
        self.assertEqual(payload, b"request rejected\n")
        self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(headers.get("Content-Length"), str(len(payload)))
        self.assertEqual(headers.get("Server"), "nvlx")
        self.assertNotIn(b"Unsupported method", payload)
        self.assertNotIn(b"Python", payload)
        self.assertNotIn(b"BaseHTTP", payload)
        self.assertNotIn(b"<!DOCTYPE", payload)
        self.assertNotIn(b"<html", payload)

    def test_post_is_contained_without_reflecting_method_details(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            self.assert_contained(*self.request(server, "POST", "/metrics"))
        finally:
            server.close()

    def test_delete_is_contained_the_same_way(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            self.assert_contained(*self.request(server, "DELETE", "/readyz"))
        finally:
            server.close()

    def test_head_error_has_no_body_but_declares_static_error_length(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.request(server, "HEAD", "/livez")
            self.assertEqual(status, 501)
            self.assertEqual(payload, b"")
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(
                headers.get("Content-Length"), str(len(b"request rejected\n"))
            )
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_framework_error_does_not_change_following_get_behavior(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            self.assert_contained(*self.request(server, "POST", "/metrics"))
            status, headers, payload = self.get(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertIn(b"# HELP nvlx_controller_ready ", payload)
            self.assertEqual(headers.get("Server"), "nvlx")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        finally:
            server.close()

    def test_unknown_get_path_preserves_existing_empty_404_contract(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, payload = self.get(server, "/unknown")
            self.assertEqual(status, 404)
            self.assertEqual(payload, b"")
            self.assertEqual(headers.get("Server"), "nvlx")
            self.assertIsNone(headers.get("Content-Length"))
            self.assertIsNone(headers.get("Cache-Control"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
