import http.client
import io
import socket
import time
import unittest

from nvlx.http_v1666666661 import (
    HealthServer,
    _CanonicalCRLFTrackingReader,
    _line_uses_canonical_crlf,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for non-canonical line endings")


class CanonicalCRLFContainmentTests(unittest.TestCase):
    @staticmethod
    def raw_request(server, payload: bytes) -> bytes:
        with socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=2
        ) as sock:
            sock.settimeout(2)
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                response += chunk
            return response

    @staticmethod
    def wait_for_slots(server, expected: int, timeout: float = 1.5) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if getattr(server._request_slots, "_value", None) == expected:
                return
            time.sleep(0.005)
        raise AssertionError(
            f"request slot value did not become {expected}; "
            f"got {getattr(server._request_slots, '_value', None)}"
        )

    def test_line_helper_requires_bytes_ending_in_crlf(self):
        for line in (b"GET / HTTP/1.1\r\n", b"Host: localhost\r\n", b"\r\n"):
            with self.subTest(line=line):
                self.assertTrue(_line_uses_canonical_crlf(line))
        for line in (b"GET / HTTP/1.1\n", b"Host: localhost\r", b"\n", b"", "x", None):
            with self.subTest(line=line):
                self.assertFalse(_line_uses_canonical_crlf(line))

    def test_tracking_reader_observes_without_rewriting(self):
        stream = io.BytesIO(b"Host: localhost\r\nX-Test: ok\n\r\n")
        reader = _CanonicalCRLFTrackingReader(stream)
        self.assertEqual(reader.readline(), b"Host: localhost\r\n")
        self.assertFalse(reader.saw_noncanonical_line_ending)
        self.assertEqual(reader.readline(), b"X-Test: ok\n")
        self.assertTrue(reader.saw_noncanonical_line_ending)
        self.assertEqual(reader.readline(), b"\r\n")

    def test_canonical_crlf_requests_remain_accepted(self):
        cases = (
            b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            b"GET /livez HTTP/1.0\r\n\r\n",
        )
        for payload in cases:
            with self.subTest(payload=payload):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(server, payload)
                    self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
                    self.assertTrue(response.endswith(b"ok\n"))
                finally:
                    server.close()

    def test_lf_only_request_line_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_lf_only_header_field_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_lf_only_blank_header_terminator_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_eof_cannot_replace_blank_header_terminator(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.0\r\nX-Test: ok\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_expect_gate_retains_precedence(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\n"
                b"Host: localhost\r\n"
                b"Expect: 100-continue\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 417 Request Rejected\r\n"))
            self.assertNotIn(b"100 Continue", response)
        finally:
            server.close()

    def test_valid_percent_escape_remains_opaque(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /%6civez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 404 Not Found\r\n"))
        finally:
            server.close()

    def test_lf_only_head_rejection_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\nHost: localhost\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_line_ending_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\nHost: localhost\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_line_ending_rejection_releases_capacity_and_recovers(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.wait_for_slots(server, 1)

            connection = http.client.HTTPConnection(
                "127.0.0.1", server.httpd.server_port, timeout=2
            )
            try:
                connection.request("GET", "/livez")
                live = connection.getresponse()
                self.assertEqual(live.status, 200)
                self.assertEqual(live.read(), b"ok\n")
            finally:
                connection.close()
        finally:
            server.close()

    def test_inherited_ingress_defaults_are_unchanged(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            self.assertEqual(server.max_request_header_fields, 32)
            self.assertEqual(server.max_request_line_bytes, 8192)
            self.assertEqual(server.max_request_header_bytes, 32768)
            self.assertEqual(server.request_header_deadline_seconds, 5.0)
            self.assertEqual(server.request_timeout_seconds, 5.0)
            self.assertEqual(server.max_concurrent_requests, 32)
        finally:
            server.httpd.server_close()


if __name__ == "__main__":
    unittest.main()
