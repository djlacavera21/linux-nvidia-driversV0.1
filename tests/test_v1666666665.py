import http.client
import socket
import time
import unittest
from email.message import Message

from nvlx.http_v1666666665 import HealthServer, _request_proxy_connection_is_safe


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for rejected Proxy-Connection")


class ProxyConnectionContainmentTests(unittest.TestCase):
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

    def test_helper_accepts_absent_and_non_proxy_connection_tokens(self):
        for value in (
            None,
            "close",
            "keep-alive",
            "proxy-connection-token",
            "upgrade-token",
        ):
            with self.subTest(value=value):
                headers = Message()
                if value is not None:
                    headers["Connection"] = value
                self.assertTrue(_request_proxy_connection_is_safe(headers))

    def test_helper_rejects_any_proxy_connection_field(self):
        for value in ("keep-alive", "close", "", "legacy"):
            with self.subTest(value=value):
                headers = Message()
                headers["Proxy-Connection"] = value
                self.assertFalse(_request_proxy_connection_is_safe(headers))

        duplicate = Message()
        duplicate["Proxy-Connection"] = "keep-alive"
        duplicate["Proxy-Connection"] = "close"
        self.assertFalse(_request_proxy_connection_is_safe(duplicate))

    def test_helper_rejects_proxy_connection_token_case_insensitively(self):
        for value in (
            "Proxy-Connection",
            "proxy-connection",
            "keep-alive, Proxy-Connection",
            "PROXY-CONNECTION, close",
        ):
            with self.subTest(value=value):
                headers = Message()
                headers["Connection"] = value
                self.assertFalse(_request_proxy_connection_is_safe(headers))
        self.assertFalse(_request_proxy_connection_is_safe({}))

    def test_non_proxy_connection_values_remain_accepted(self):
        for value in (b"close", b"keep-alive", b"proxy-connection-token"):
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

    def test_proxy_connection_field_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Proxy-Connection: keep-alive\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_connection_proxy_connection_token_is_terminal_400(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Connection: keep-alive, Proxy-Connection\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_empty_and_duplicate_proxy_connection_fields_are_rejected(self):
        payloads = (
            b"GET /livez HTTP/1.1\r\nHost: localhost\r\nProxy-Connection:\r\n\r\n",
            b"GET /livez HTTP/1.1\r\nHost: localhost\r\n"
            b"Proxy-Connection: keep-alive\r\n"
            b"Proxy-Connection: close\r\n\r\n",
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(server, payload)
                    self.assertTrue(
                        response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
                    )
                finally:
                    server.close()

    def test_http_10_proxy_connection_is_also_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.0\r\nProxy-Connection: keep-alive\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_expect_gate_retains_precedence_over_proxy_connection_gate(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Expect: 100-continue\r\n"
                b"Proxy-Connection: keep-alive\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 417 Request Rejected\r\n")
            )
            self.assertNotIn(b"100 Continue", response)
        finally:
            server.close()

    def test_te_gate_remains_earlier_than_proxy_connection_gate(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"TE: trailers\r\n"
                b"Proxy-Connection: keep-alive\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
        finally:
            server.close()

    def test_proxy_connection_rejection_head_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Proxy-Connection: keep-alive\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_proxy_connection_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Proxy-Connection: keep-alive\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_proxy_connection_rejection_releases_capacity_and_recovers(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Proxy-Connection: keep-alive\r\n\r\n",
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
