import http.client
import socket
import time
import unittest
from email.message import Message

from nvlx.http_v166666666632 import (
    HealthServer,
    _request_keep_alive_headers_are_safe,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for Keep-Alive request fields")


class KeepAliveFieldContainmentTests(unittest.TestCase):
    @staticmethod
    def raw_request(server, payload: bytes) -> bytes:
        with socket.create_connection(("127.0.0.1", server.httpd.server_port), timeout=2) as sock:
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
        raise AssertionError("request slot value did not recover")

    def test_helper_accepts_absent_keep_alive_field(self):
        for connection_value in (None, "close", "keep-alive", "keep-alive, x-custom"):
            with self.subTest(connection_value=connection_value):
                headers = Message()
                if connection_value is not None:
                    headers["Connection"] = connection_value
                self.assertTrue(_request_keep_alive_headers_are_safe(headers))

    def test_helper_rejects_any_keep_alive_field(self):
        for value in ("timeout=5", "max=100", "", "timeout=5, max=100"):
            with self.subTest(value=value):
                headers = Message()
                headers["Keep-Alive"] = value
                self.assertFalse(_request_keep_alive_headers_are_safe(headers))

        duplicated = Message()
        duplicated["Keep-Alive"] = "timeout=5"
        duplicated["Keep-Alive"] = "max=100"
        self.assertFalse(_request_keep_alive_headers_are_safe(duplicated))

    def test_helper_keeps_inherited_fail_closed_contracts(self):
        for value in ("", "close,", "close, keep-alive", "Host", "x, X"):
            with self.subTest(value=value):
                headers = Message()
                headers["Connection"] = value
                self.assertFalse(_request_keep_alive_headers_are_safe(headers))
        self.assertFalse(_request_keep_alive_headers_are_safe({}))

    def test_connection_keep_alive_token_without_field_remains_accepted(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n"
                b"Connection: keep-alive\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_keep_alive_field_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\nHost: localhost\r\n"
                b"Connection: keep-alive\r\nKeep-Alive: timeout=5\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_empty_keep_alive_field_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\nKeep-Alive:\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_http_10_keep_alive_field_is_also_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.0\r\nConnection: keep-alive\r\n"
                b"Keep-Alive: timeout=5\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
        finally:
            server.close()

    def test_expect_gate_retains_precedence(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n"
                b"Expect: 100-continue\r\nKeep-Alive: timeout=5\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 417 Request Rejected\r\n"))
            self.assertNotIn(b"100 Continue", response)
        finally:
            server.close()

    def test_singleton_connection_field_gate_remains_earlier(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n"
                b"Connection: x-one\r\nConnection: x-two\r\n"
                b"Keep-Alive: timeout=5\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
        finally:
            server.close()

    def test_keep_alive_rejection_head_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\r\nHost: localhost\r\n"
                b"Keep-Alive: timeout=5\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_keep_alive_rejection_terminates_pipeline(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n"
                b"Keep-Alive: timeout=5\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_keep_alive_releases_capacity_and_recovers(self):
        server = HealthServer(object(), "127.0.0.1", 0, max_concurrent_requests=1).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\nKeep-Alive: timeout=5\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.wait_for_slots(server, 1)
            connection = http.client.HTTPConnection("127.0.0.1", server.httpd.server_port, timeout=2)
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
