import http.client
import socket
import time
import unittest

from nvlx.http_v16666663 import (
    HealthServer,
    _request_version_is_supported,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for rejected request versions")


class RequestVersionContainmentTests(unittest.TestCase):
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

    def test_request_version_policy_is_exact(self):
        self.assertTrue(_request_version_is_supported("HTTP/1.0"))
        self.assertTrue(_request_version_is_supported("HTTP/1.1"))
        self.assertFalse(_request_version_is_supported("HTTP/0.9"))
        self.assertFalse(_request_version_is_supported("HTTP/1.01"))
        self.assertFalse(_request_version_is_supported("HTTP/1.2"))
        self.assertFalse(_request_version_is_supported("HTTP/2.0"))
        self.assertFalse(_request_version_is_supported(None))
        self.assertFalse(_request_version_is_supported(1.1))

    def test_http_10_remains_accepted_without_host(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(server, b"GET /livez HTTP/1.0\r\n\r\n")
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_http_11_remains_accepted_with_zero_content_length(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Content-Length: 0\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_http_09_is_canonical_terminal_505(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(server, b"GET /livez\r\n")
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertIn(b"Server: nvlx\r\n", response)
            self.assertIn(b"Cache-Control: no-store\r\n", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
        finally:
            server.close()

    def test_noncanonical_http_1x_is_rejected_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.2\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_noncanonical_version_spelling_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.01\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_unsupported_head_version_is_bodyless_505(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.2\r\nHost: x\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(
                head.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_http_09_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez\r\n"
                b"GET /livez HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_http_2_parser_rejection_stays_canonical(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/2.0\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
        finally:
            server.close()

    def test_body_framing_rejection_still_precedes_version_gate(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.2\r\n"
                b"Host: x\r\n"
                b"Content-Length: 1\r\n\r\nx",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_version_rejection_releases_capacity_and_server_recovers(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_concurrent_requests=1,
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.2\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
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
