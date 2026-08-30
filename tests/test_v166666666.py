import http.client
import socket
import time
import unittest

from nvlx.http_v166666666 import (
    HealthServer,
    _request_target_percent_escapes_are_safe,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for malformed percent escape")


class PercentEscapeContainmentTests(unittest.TestCase):
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

    def test_percent_escape_helper_accepts_absent_and_complete_hex_escapes(self):
        accepted = (
            "/livez",
            "/%41",
            "/%4a%4A",
            "/livez%2F",
            "/livez?x=%2f&y=%25",
            "/%23",
        )
        for target in accepted:
            with self.subTest(target=target):
                self.assertTrue(_request_target_percent_escapes_are_safe(target))

    def test_percent_escape_helper_rejects_truncated_and_non_hex_escapes(self):
        rejected = (
            "/%",
            "/%2",
            "/%GG",
            "/%G0",
            "/%0G",
            "/%%20",
            "/livez?x=%2?",
        )
        for target in rejected:
            with self.subTest(target=target):
                self.assertFalse(_request_target_percent_escapes_are_safe(target))
        self.assertFalse(_request_target_percent_escapes_are_safe(None))

    def test_canonical_livez_remains_accepted(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_valid_percent_encoding_remains_opaque_and_unknown(self):
        for target in (b"/%6civez", b"/livez%2F", b"/%23"):
            with self.subTest(target=target):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server,
                        b"GET " + target + b" HTTP/1.1\r\nHost: localhost\r\n\r\n",
                    )
                    head, body = response.split(b"\r\n\r\n", 1)
                    self.assertTrue(head.startswith(b"HTTP/1.0 404 Not Found\r\n"))
                    self.assertEqual(body, b"")
                finally:
                    server.close()

    def test_valid_query_percent_escape_remains_syntactically_admitted_but_unknown(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez?x=%2F HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 404 Not Found\r\n"))
        finally:
            server.close()

    def test_malformed_percent_escape_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics%GG HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_truncated_percent_escape_in_query_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez?x=% HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_http_10_malformed_percent_escape_is_also_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez%2 HTTP/1.0\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_expect_gate_retains_precedence_over_percent_escape_gate(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez%GG HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Expect: 100-continue\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 417 Request Rejected\r\n")
            )
            self.assertNotIn(b"100 Continue", response)
        finally:
            server.close()

    def test_malformed_percent_escape_head_rejection_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez%GG HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_percent_escape_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez%GG HTTP/1.1\r\nHost: localhost\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_percent_escape_rejection_releases_capacity_and_recovers(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez% HTTP/1.1\r\nHost: localhost\r\n\r\n",
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
