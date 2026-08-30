import http.client
import socket
import time
import unittest

from nvlx.http_v166666665 import HealthServer, _request_line_spacing_is_safe


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for rejected request-line spacing")


class RequestLineSpacingContainmentTests(unittest.TestCase):
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

    def test_spacing_helper_requires_exact_reconstruction(self):
        accepted = (
            ("GET /livez HTTP/1.1", "GET", "/livez", "HTTP/1.1"),
            ("HEAD /metrics HTTP/1.0", "HEAD", "/metrics", "HTTP/1.0"),
            ("BREW /livez HTTP/1.1", "BREW", "/livez", "HTTP/1.1"),
            ("GET /livez?probe=1 HTTP/1.1", "GET", "/livez?probe=1", "HTTP/1.1"),
        )
        for args in accepted:
            with self.subTest(args=args):
                self.assertTrue(_request_line_spacing_is_safe(*args))

        rejected = (
            ("GET  /livez HTTP/1.1", "GET", "/livez", "HTTP/1.1"),
            ("GET\t/livez HTTP/1.1", "GET", "/livez", "HTTP/1.1"),
            ("GET /livez\tHTTP/1.1", "GET", "/livez", "HTTP/1.1"),
            (" GET /livez HTTP/1.1", "GET", "/livez", "HTTP/1.1"),
            ("GET /livez HTTP/1.1 ", "GET", "/livez", "HTTP/1.1"),
            ("GET /readyz HTTP/1.1", "GET", "/livez", "HTTP/1.1"),
            ("GET /livez HTTP/1.1", "HEAD", "/livez", "HTTP/1.1"),
            ("GET /livez HTTP/1.1", "GET", "/livez", "HTTP/1.0"),
        )
        for args in rejected:
            with self.subTest(args=args):
                self.assertFalse(_request_line_spacing_is_safe(*args))

        self.assertFalse(
            _request_line_spacing_is_safe(None, "GET", "/livez", "HTTP/1.1")
        )
        self.assertFalse(_request_line_spacing_is_safe("", "", "", ""))

    def test_canonical_http_10_and_http_11_remain_accepted(self):
        requests = (
            b"GET /livez HTTP/1.0\r\n\r\n",
            b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
        )
        for payload in requests:
            with self.subTest(payload=payload):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(server, payload)
                    self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
                    self.assertTrue(response.endswith(b"ok\n"))
                finally:
                    server.close()

    def test_repeated_space_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET  /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_tab_separators_are_rejected(self):
        for line in (
            b"GET\t/livez HTTP/1.1",
            b"GET /livez\tHTTP/1.1",
            b"GET\t/livez\tHTTP/1.1",
        ):
            with self.subTest(line=line):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server, line + b"\r\nHost: localhost\r\n\r\n"
                    )
                    self.assertTrue(
                        response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
                    )
                finally:
                    server.close()

    def test_leading_and_trailing_request_line_whitespace_are_rejected(self):
        for line in (
            b" GET /livez HTTP/1.1",
            b"GET /livez HTTP/1.1 ",
        ):
            with self.subTest(line=line):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server, line + b"\r\nHost: localhost\r\n\r\n"
                    )
                    self.assertTrue(
                        response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
                    )
                finally:
                    server.close()

    def test_canonical_arbitrary_method_retains_existing_405_contract(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"BREW /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 405 Method Not Allowed\r\n"))
            self.assertIn(b"Allow: GET, HEAD\r\n", response)
        finally:
            server.close()

    def test_inherited_expect_gate_keeps_precedence(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET  /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Expect: 100-continue\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 417 Request Rejected\r\n")
            )
            self.assertNotIn(b"100 Continue", response)
        finally:
            server.close()

    def test_noncanonical_head_rejection_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD  /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_spacing_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET  /livez HTTP/1.1\r\nHost: localhost\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_spacing_rejection_releases_capacity_and_recovers(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET\t/livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
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
