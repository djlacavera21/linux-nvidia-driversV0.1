from email.message import Message
import http.client
import socket
import time
import unittest

from nvlx.http_v16666662 import HealthServer, _request_body_framing_is_safe


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for rejected request framing")


class RequestBodyFramingContainmentTests(unittest.TestCase):
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

    def test_framing_helper_accepts_only_absent_or_single_zero_length(self):
        headers = Message()
        self.assertTrue(_request_body_framing_is_safe(headers))

        headers = Message()
        headers.add_header("Content-Length", "0")
        self.assertTrue(_request_body_framing_is_safe(headers))

        headers = Message()
        headers.add_header("Content-Length", " \t0\t ")
        self.assertTrue(_request_body_framing_is_safe(headers))

        for value in ("1", "-1", "+0", "00", "0, 0", "", "abc"):
            with self.subTest(content_length=value):
                headers = Message()
                headers.add_header("Content-Length", value)
                self.assertFalse(_request_body_framing_is_safe(headers))

        headers = Message()
        headers.add_header("Content-Length", "0")
        headers.add_header("Content-Length", "0")
        self.assertFalse(_request_body_framing_is_safe(headers))

        headers = Message()
        headers.add_header("Transfer-Encoding", "chunked")
        self.assertFalse(_request_body_framing_is_safe(headers))

        headers = Message()
        headers.add_header("Transfer-Encoding", "identity")
        headers.add_header("Content-Length", "0")
        self.assertFalse(_request_body_framing_is_safe(headers))

    def test_single_zero_content_length_preserves_liveness(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_transfer_encoding_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Transfer-Encoding: chunked\r\n"
                b"\r\n"
                b"0\r\n\r\n",
            )
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

    def test_nonzero_content_length_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Content-Length: 4\r\n"
                b"\r\n"
                b"boom",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_duplicate_content_length_is_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Content-Length: 0\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_rejected_head_framing_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Content-Length: 1\r\n"
                b"\r\n"
                b"x",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_rejected_framing_cannot_be_reinterpreted_as_pipeline(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Content-Length: 4\r\n"
                b"\r\n"
                b"boom"
                b"GET /livez HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_bodyless_unsupported_method_still_uses_405_contract(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"POST /livez HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 405 Method Not Allowed\r\n")
            )
            self.assertIn(b"Allow: GET, HEAD\r\n", response)
        finally:
            server.close()

    def test_framing_rejection_releases_capacity_and_server_recovers(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_concurrent_requests=1,
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: x\r\n"
                b"Transfer-Encoding: chunked\r\n"
                b"\r\n",
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
