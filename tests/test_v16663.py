import http.client
import unittest

from nvlx.http_v16663 import HealthServer


class ExplicitMethodContractTests(unittest.TestCase):
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
    def assert_method_rejection(testcase, status, headers, body):
        testcase.assertEqual(status, 405)
        testcase.assertEqual(body, b"request rejected\n")
        testcase.assertEqual(headers.get("Allow"), "GET, HEAD")
        testcase.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
        testcase.assertEqual(headers.get("Cache-Control"), "no-store")
        testcase.assertEqual(headers.get("Content-Length"), str(len(body)))
        testcase.assertEqual(headers.get("Server"), "nvlx")

    def test_post_is_explicit_405_with_allow_header(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "POST", "/metrics")
            self.assert_method_rejection(self, status, headers, body)
            self.assertNotIn(b"POST", body)
            self.assertNotIn(b"Unsupported method", body)
        finally:
            server.close()

    def test_options_is_explicit_405_with_allow_header(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "OPTIONS", "/readyz")
            self.assert_method_rejection(self, status, headers, body)
        finally:
            server.close()

    def test_arbitrary_method_is_explicit_405_without_reflection(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "BREW", "/livez")
            self.assert_method_rejection(self, status, headers, body)
            self.assertNotIn(b"BREW", body)
        finally:
            server.close()

    def test_supported_get_and_head_do_not_advertise_allow(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            get_status, get_headers, get_body = self.request(server, "GET", "/livez")
            head_status, head_headers, head_body = self.request(server, "HEAD", "/livez")
            self.assertEqual((get_status, get_body), (200, b"ok\n"))
            self.assertEqual((head_status, head_body), (200, b""))
            self.assertIsNone(get_headers.get("Allow"))
            self.assertIsNone(head_headers.get("Allow"))
        finally:
            server.close()

    def test_unknown_get_keeps_existing_empty_404_contract(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "GET", "/unknown")
            self.assertEqual(status, 404)
            self.assertEqual(body, b"")
            self.assertIsNone(headers.get("Allow"))
            self.assertIsNone(headers.get("Cache-Control"))
            self.assertIsNone(headers.get("Content-Length"))
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_method_rejection_does_not_poison_following_get(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            rejected_status, rejected_headers, rejected_body = self.request(
                server, "DELETE", "/livez"
            )
            self.assert_method_rejection(
                self, rejected_status, rejected_headers, rejected_body
            )
            get_status, _, get_body = self.request(server, "GET", "/livez")
            self.assertEqual((get_status, get_body), (200, b"ok\n"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
