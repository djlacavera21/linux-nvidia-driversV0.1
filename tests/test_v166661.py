import http.client
import socket
import unittest

from nvlx.http_v166661 import HealthServer


class CanonicalZeroLengthFramingTests(unittest.TestCase):
    @staticmethod
    def request(server, method, path, *, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

    @staticmethod
    def raw_exchange(server, payload: bytes) -> bytes:
        with socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=2
        ) as sock:
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)

    @staticmethod
    def assert_bad_live_request(testcase, status, headers, body, *, head=False):
        testcase.assertEqual(status, 400)
        testcase.assertEqual(body, b"" if head else b"request rejected\n")
        testcase.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
        testcase.assertEqual(headers.get("Cache-Control"), "no-store")
        testcase.assertEqual(headers.get("Content-Length"), str(len(b"request rejected\n")))
        testcase.assertEqual(headers.get("Connection"), "close")
        testcase.assertEqual(headers.get("Server"), "nvlx")

    def test_exact_single_zero_remains_valid(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(
                server, "GET", "/livez", headers={"Content-Length": "0"}
            )
            self.assertEqual((status, body), (200, b"ok\n"))
            self.assertIsNone(headers.get("Connection"))
        finally:
            server.close()

    def test_no_content_length_remains_valid(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, _, body = self.request(server, "GET", "/livez")
            self.assertEqual((status, body), (200, b"ok\n"))
        finally:
            server.close()

    def test_noncanonical_zero_spellings_are_rejected_before_readiness(self):
        calls = []

        class Runtime:
            def readiness_diagnosis(self):
                calls.append("readiness")
                raise AssertionError("readiness must not be evaluated")

        server = HealthServer(Runtime(), "127.0.0.1", 0).start()
        try:
            for value in ("00", "000", "+0", "-0", "0,0", "0x0"):
                with self.subTest(value=value):
                    status, headers, body = self.request(
                        server,
                        "GET",
                        "/readyz",
                        headers={"Content-Length": value},
                    )
                    self.assert_bad_live_request(self, status, headers, body)
            self.assertEqual(calls, [])
        finally:
            server.close()

    def test_head_noncanonical_zero_is_bodyless_400(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(
                server, "HEAD", "/livez", headers={"Content-Length": "00"}
            )
            self.assert_bad_live_request(self, status, headers, body, head=True)
        finally:
            server.close()

    def test_transfer_encoding_remains_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(
                server, "GET", "/livez", headers={"Transfer-Encoding": "chunked"}
            )
            self.assert_bad_live_request(self, status, headers, body)
        finally:
            server.close()

    def test_unknown_target_keeps_existing_404_with_noncanonical_length(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(
                server, "GET", "/unknown", headers={"Content-Length": "00"}
            )
            self.assertEqual(status, 404)
            self.assertEqual(body, b"")
            self.assertIsNone(headers.get("Cache-Control"))
            self.assertIsNone(headers.get("Content-Length"))
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_noncanonical_zero_closes_before_pipelined_following_get(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            payload = (
                b"GET /livez HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: 00\r\n"
                b"Connection: keep-alive\r\n"
                b"\r\n"
                b"GET /livez HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            response = self.raw_exchange(server, payload)
            self.assertEqual(response.count(b"HTTP/1."), 1)
            self.assertIn(b" 400 ", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertNotIn(b" 200 ", response)
            self.assertNotIn(b"ok\n", response)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
