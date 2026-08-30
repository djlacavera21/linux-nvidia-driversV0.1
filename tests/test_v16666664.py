from email.message import Message
import http.client
import socket
import time
import unittest

from nvlx.http_v16666662 import _request_body_framing_is_safe
from nvlx.http_v16666664 import HealthServer, _request_host_is_safe


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for rejected Host framing")


class HostContainmentTests(unittest.TestCase):
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

    @staticmethod
    def headers(*pairs):
        message = Message()
        for name, value in pairs:
            message[name] = value
        return message

    def test_legacy_headerless_mapping_repair_is_narrow(self):
        self.assertTrue(_request_body_framing_is_safe({}))
        self.assertFalse(_request_body_framing_is_safe({"Content-Length": "0"}))
        self.assertFalse(_request_body_framing_is_safe({"Host": "x"}))
        self.assertFalse(_request_body_framing_is_safe(None))

    def test_host_policy_requires_single_http_11_host(self):
        self.assertTrue(_request_host_is_safe("HTTP/1.0", self.headers()))
        self.assertTrue(
            _request_host_is_safe("HTTP/1.1", self.headers(("Host", "example")))
        )
        self.assertFalse(_request_host_is_safe("HTTP/1.1", self.headers()))
        self.assertFalse(
            _request_host_is_safe(
                "HTTP/1.1",
                self.headers(("Host", "a"), ("Host", "b")),
            )
        )
        self.assertFalse(
            _request_host_is_safe("HTTP/1.1", self.headers(("Host", "   ")))
        )
        self.assertFalse(
            _request_host_is_safe("HTTP/1.1", self.headers(("Host", "a,b")))
        )
        self.assertFalse(_request_host_is_safe("HTTP/1.1", {}))
        self.assertFalse(_request_host_is_safe("HTTP/1.2", self.headers(("Host", "x"))))

    def test_http_09_compatibility_path_is_repaired_and_rejected_505(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(server, b"GET /livez\r\n")
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
        finally:
            server.close()

    def test_http_10_without_host_remains_accepted(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(server, b"GET /livez HTTP/1.0\r\n\r\n")
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_http_11_with_single_host_remains_accepted(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_missing_http_11_host_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(server, b"GET /metrics HTTP/1.1\r\n\r\n")
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Server: nvlx\r\n", response)
            self.assertIn(b"Cache-Control: no-store\r\n", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_duplicate_http_11_host_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_empty_http_11_host_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost:\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_folded_http_11_host_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: example\r\n continuation\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_list_like_http_11_host_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: a, b\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_missing_host_head_rejection_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(server, b"HEAD /livez HTTP/1.1\r\n\r\n")
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_host_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_invalid_body_framing_still_fails_before_host_dispatch(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\nContent-Length: 1\r\n\r\nx",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_host_rejection_releases_capacity_and_server_recovers(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_concurrent_requests=1,
        ).start()
        try:
            response = self.raw_request(server, b"GET /livez HTTP/1.1\r\n\r\n")
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
