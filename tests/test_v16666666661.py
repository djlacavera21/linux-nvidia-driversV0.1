import http.client
import socket
import time
import unittest
from email.message import Message

from nvlx.http_v16666666661 import HealthServer, _connection_lifecycle_is_safe


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for contradictory Connection lifecycle")


class ConnectionLifecycleContainmentTests(unittest.TestCase):
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

    def test_helper_accepts_non_conflicting_lifecycle_tokens(self):
        for value in (None, "close", "keep-alive", "close, close", "x-custom, keep-alive"):
            with self.subTest(value=value):
                headers = Message()
                if value is not None:
                    headers["Connection"] = value
                self.assertTrue(_connection_lifecycle_is_safe(headers))

        multiple = Message()
        multiple["Connection"] = "keep-alive"
        multiple["Connection"] = "x-custom"
        self.assertTrue(_connection_lifecycle_is_safe(multiple))

    def test_helper_rejects_close_keep_alive_conflicts(self):
        for value in (
            "close, keep-alive",
            "KEEP-ALIVE, CLOSE",
            " close ,\tKeep-Alive ",
        ):
            with self.subTest(value=value):
                headers = Message()
                headers["Connection"] = value
                self.assertFalse(_connection_lifecycle_is_safe(headers))

        split = Message()
        split["Connection"] = "close"
        split["Connection"] = "keep-alive"
        self.assertFalse(_connection_lifecycle_is_safe(split))

    def test_helper_keeps_inherited_syntax_fail_closed(self):
        for value in ("", "close,", '"close"'):
            with self.subTest(value=value):
                headers = Message()
                headers["Connection"] = value
                self.assertFalse(_connection_lifecycle_is_safe(headers))
        self.assertFalse(_connection_lifecycle_is_safe({}))

    def test_single_lifecycle_directives_remain_accepted(self):
        for value in (b"close", b"keep-alive", b"x-custom, keep-alive"):
            with self.subTest(value=value):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server,
                        b"GET /livez HTTP/1.1\r\n"
                        b"Host: localhost\r\n"
                        b"Connection: " + value + b"\r\n\r\n",
                    )
                    self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
                    self.assertTrue(response.endswith(b"ok\n"))
                finally:
                    server.close()

    def test_same_field_conflict_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Connection: keep-alive, close\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_split_field_conflict_is_terminal_400(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Connection: close\r\n"
                b"Connection: keep-alive\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_http_10_conflict_is_also_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.0\r\nConnection: close, keep-alive\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_expect_gate_retains_precedence(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Expect: 100-continue\r\n"
                b"Connection: close, keep-alive\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 417 Request Rejected\r\n"))
            self.assertNotIn(b"100 Continue", response)
        finally:
            server.close()

    def test_existing_te_gate_remains_earlier(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"TE: trailers\r\n"
                b"Connection: close, keep-alive\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
        finally:
            server.close()

    def test_conflict_rejection_head_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Connection: close, keep-alive\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_conflict_rejection_terminates_pipeline(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Connection: close, keep-alive\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_conflict_releases_capacity_and_recovers(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Connection: close, keep-alive\r\n\r\n",
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
