import http.client
import unittest

from nvlx.http_v16664 import HealthServer


class ResourceAwareMethodContractTests(unittest.TestCase):
    @staticmethod
    def request(server, method, path):
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

    @staticmethod
    def assert_live_method_rejection(testcase, status, headers, body):
        testcase.assertEqual(status, 405)
        testcase.assertEqual(body, b"request rejected\n")
        testcase.assertEqual(headers.get("Allow"), "GET, HEAD")
        testcase.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
        testcase.assertEqual(headers.get("Cache-Control"), "no-store")
        testcase.assertEqual(headers.get("Content-Length"), str(len(body)))
        testcase.assertEqual(headers.get("Server"), "nvlx")

    @staticmethod
    def assert_unknown_contract(testcase, status, headers, body):
        testcase.assertEqual(status, 404)
        testcase.assertEqual(body, b"")
        testcase.assertIsNone(headers.get("Allow"))
        testcase.assertIsNone(headers.get("Cache-Control"))
        testcase.assertIsNone(headers.get("Content-Length"))
        testcase.assertEqual(headers.get("Server"), "nvlx")

    def test_post_to_live_resource_keeps_explicit_405(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "POST", "/metrics")
            self.assert_live_method_rejection(self, status, headers, body)
        finally:
            server.close()

    def test_arbitrary_method_to_live_resource_keeps_explicit_405(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "BREW", "/livez")
            self.assert_live_method_rejection(self, status, headers, body)
            self.assertNotIn(b"BREW", body)
        finally:
            server.close()

    def test_post_to_unknown_resource_matches_empty_404(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "POST", "/unknown")
            self.assert_unknown_contract(self, status, headers, body)
        finally:
            server.close()

    def test_arbitrary_method_to_unknown_resource_matches_empty_404(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "BREW", "/unknown")
            self.assert_unknown_contract(self, status, headers, body)
        finally:
            server.close()

    def test_query_target_uses_same_resource_identity_for_get_and_post(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(
                server, "GET", "/livez?probe=1"
            )
            post_status, post_headers, post_body = self.request(
                server, "POST", "/livez?probe=1"
            )
            self.assert_unknown_contract(self, get_status, get_headers, get_body)
            self.assert_unknown_contract(self, post_status, post_headers, post_body)
        finally:
            server.close()

    def test_trailing_slash_target_does_not_advertise_live_methods(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "OPTIONS", "/readyz/")
            self.assert_unknown_contract(self, status, headers, body)
        finally:
            server.close()

    def test_known_resource_still_serves_get_after_unknown_method_probe(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            unknown_status, unknown_headers, unknown_body = self.request(
                server, "DELETE", "/unknown"
            )
            self.assert_unknown_contract(
                self, unknown_status, unknown_headers, unknown_body
            )
            get_status, _, get_body = self.request(server, "GET", "/livez")
            self.assertEqual((get_status, get_body), (200, b"ok\n"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
