import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from nvlx.http_v16 import HealthServer
from nvlx.runtime_v1652 import Runtime


class LiveStateHttpCacheTests(unittest.TestCase):
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
                return (
                    response.status,
                    response.headers,
                    response.read().decode("utf-8"),
                )
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read().decode("utf-8")

    def test_livez_is_utf8_text_and_never_cacheable(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "/livez")
            self.assertEqual(status, 200)
            self.assertEqual(body, "ok\n")
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        finally:
            server.close()

    def test_readyz_ready_response_is_utf8_text_and_never_cacheable(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "/readyz")
            self.assertEqual(status, 200)
            self.assertEqual(body, "ready\n")
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        finally:
            server.close()

    def test_readyz_not_ready_response_is_utf8_text_and_never_cacheable(self):
        server = HealthServer(self.runtime(ready=False), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "/readyz")
            self.assertEqual(status, 503)
            self.assertEqual(body, "not ready\n")
            self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        finally:
            server.close()

    def test_metrics_preserves_prometheus_type_and_is_never_cacheable(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "/metrics")
            self.assertEqual(status, 200)
            self.assertEqual(
                headers.get("Content-Type"),
                "text/plain; version=0.0.4; charset=utf-8",
            )
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertIn("# HELP nvlx_controller_ready ", body)
            self.assertIn("# TYPE nvlx_controller_ready gauge\n", body)
        finally:
            server.close()

    def test_unknown_path_status_and_empty_body_remain_unchanged(self):
        server = HealthServer(self.runtime(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "/unknown")
            self.assertEqual(status, 404)
            self.assertEqual(body, "")
            self.assertIsNone(headers.get("Cache-Control"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
