import http.client
import io
import socket
import time
import unittest

from nvlx.http_v1666666 import (
    HealthServer,
    _RequestLineBudgetReader,
    _RequestLineTooLong,
    _validate_request_line_bytes,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for oversized request line")


class RequestLineBudgetTests(unittest.TestCase):
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

    def test_request_line_limit_validation_is_strict_and_bounded(self):
        self.assertEqual(_validate_request_line_bytes(1), 1)
        self.assertEqual(_validate_request_line_bytes(8192), 8192)
        self.assertEqual(_validate_request_line_bytes(65536), 65536)
        with self.assertRaises(TypeError):
            _validate_request_line_bytes(True)
        with self.assertRaises(TypeError):
            _validate_request_line_bytes(8192.0)
        with self.assertRaises(TypeError):
            _validate_request_line_bytes("8192")
        with self.assertRaises(ValueError):
            _validate_request_line_bytes(0)
        with self.assertRaises(ValueError):
            _validate_request_line_bytes(-1)
        with self.assertRaises(ValueError):
            _validate_request_line_bytes(65537)

    def test_reader_allows_exact_budget_and_only_checks_first_line(self):
        request_line = b"GET /x HTTP/1.1\r\n"
        header_line = b"X-Test: " + (b"a" * 128) + b"\r\n"
        reader = _RequestLineBudgetReader(
            io.BytesIO(request_line + header_line), len(request_line)
        )
        self.assertEqual(reader.readline(65537), request_line)
        self.assertEqual(reader.readline(65537), header_line)

    def test_reader_marks_head_prefix_when_budget_is_exceeded(self):
        reader = _RequestLineBudgetReader(
            io.BytesIO(b"HEAD /this-target-is-too-long HTTP/1.1\r\n"), 8
        )
        with self.assertRaises(_RequestLineTooLong) as context:
            reader.readline(65537)
        self.assertTrue(context.exception.is_head)

    def test_oversized_get_line_uses_canonical_414_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(
            runtime,
            "127.0.0.1",
            0,
            max_request_line_bytes=64,
        ).start()
        try:
            target = b"/metrics?" + (b"x" * 96)
            response = self.raw_request(
                server,
                b"GET " + target + b" HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 414 Request Rejected\r\n")
            )
            self.assertIn(b"Server: nvlx\r\n", response)
            self.assertIn(b"Cache-Control: no-store\r\n", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_oversized_head_line_is_bodyless_414(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_request_line_bytes=64
        ).start()
        try:
            target = b"/livez?" + (b"x" * 96)
            response = self.raw_request(
                server,
                b"HEAD " + target + b" HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 414 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_request_line_rejection_releases_capacity_and_server_recovers(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_concurrent_requests=1,
            max_request_line_bytes=64,
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /" + (b"x" * 100) + b" HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 414 Request Rejected\r\n")
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

    def test_header_budget_remains_independent_of_request_line_budget(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_request_line_bytes=64,
            max_request_header_bytes=256,
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                + b"Host: x\r\n"
                + b"X-Pad: "
                + (b"a" * 120)
                + b"\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_defaults_and_inherited_ingress_controls_are_exposed(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            self.assertEqual(server.max_request_line_bytes, 8192)
            self.assertEqual(server.max_request_header_bytes, 32768)
            self.assertEqual(server.request_header_deadline_seconds, 5.0)
            self.assertEqual(server.request_timeout_seconds, 5.0)
            self.assertEqual(server.max_concurrent_requests, 32)
        finally:
            server.httpd.server_close()


if __name__ == "__main__":
    unittest.main()
