import http.client
import io
import socket
import time
import unittest

from nvlx.http_v1666665 import (
    HealthServer,
    _HeaderBudgetReader,
    _validate_request_header_bytes,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for oversized headers")


class AggregateHeaderBudgetTests(unittest.TestCase):
    @staticmethod
    def read_all(sock) -> bytes:
        data = b""
        while True:
            try:
                chunk = sock.recv(65536)
            except (ConnectionResetError, BrokenPipeError):
                break
            if not chunk:
                break
            data += chunk
        return data

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

    def test_header_budget_validation_is_strict(self):
        self.assertEqual(_validate_request_header_bytes(1), 1)
        self.assertEqual(_validate_request_header_bytes(32768), 32768)
        with self.assertRaises(TypeError):
            _validate_request_header_bytes(True)
        with self.assertRaises(TypeError):
            _validate_request_header_bytes(128.0)
        with self.assertRaises(TypeError):
            _validate_request_header_bytes("128")
        with self.assertRaises(ValueError):
            _validate_request_header_bytes(0)
        with self.assertRaises(ValueError):
            _validate_request_header_bytes(-1)

    def test_budget_reader_accepts_exact_budget_and_rejects_next_byte(self):
        reader = _HeaderBudgetReader(io.BytesIO(b"X: 1\r\n\r\n"), 8)
        self.assertEqual(reader.readline(), b"X: 1\r\n")
        self.assertEqual(reader.readline(), b"\r\n")
        self.assertEqual(reader.remaining, 0)
        with self.assertRaises(http.client.HTTPException):
            reader.readline()

    def test_aggregate_oversize_headers_return_contained_431_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(
            runtime,
            "127.0.0.1",
            0,
            max_request_header_bytes=128,
        ).start()
        try:
            with socket.create_connection(
                ("127.0.0.1", server.httpd.server_port), timeout=2
            ) as sock:
                request = (
                    b"GET /metrics HTTP/1.1\r\n"
                    b"Host: x\r\n"
                    + b"X-A: " + b"a" * 45 + b"\r\n"
                    + b"X-B: " + b"b" * 45 + b"\r\n"
                    + b"X-C: " + b"c" * 45 + b"\r\n\r\n"
                )
                sock.sendall(request)
                sock.shutdown(socket.SHUT_WR)
                response = self.read_all(sock)
            self.assertTrue(response.startswith(b"HTTP/1.0 431 Request Rejected\r\n"))
            self.assertIn(b"Server: nvlx\r\n", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_oversized_head_is_bodyless_with_representation_length(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_request_header_bytes=96
        ).start()
        try:
            with socket.create_connection(
                ("127.0.0.1", server.httpd.server_port), timeout=2
            ) as sock:
                request = (
                    b"HEAD /livez HTTP/1.1\r\n"
                    b"Host: x\r\n"
                    + b"X-A: " + b"a" * 85 + b"\r\n\r\n"
                )
                sock.sendall(request)
                sock.shutdown(socket.SHUT_WR)
                response = self.read_all(sock)
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 431 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_request_under_budget_keeps_success_contract(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_request_header_bytes=512
        ).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request("GET", "/livez", headers={"X-Test": "ok"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"ok\n")
            self.assertEqual(response.getheader("Server"), "nvlx")
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            self.assertEqual(response.getheader("Content-Length"), "3")
        finally:
            connection.close()
            server.close()

    def test_header_budget_rejection_releases_worker_slot(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_concurrent_requests=1,
            max_request_header_bytes=96,
        ).start()
        try:
            with socket.create_connection(
                ("127.0.0.1", server.httpd.server_port), timeout=2
            ) as sock:
                request = (
                    b"GET /livez HTTP/1.1\r\n"
                    b"Host: x\r\n"
                    + b"X-A: " + b"a" * 85 + b"\r\n\r\n"
                )
                sock.sendall(request)
                sock.shutdown(socket.SHUT_WR)
                response = self.read_all(sock)
            self.assertTrue(response.startswith(b"HTTP/1.0 431 Request Rejected\r\n"))
            self.wait_for_slots(server, 1)

            connection = http.client.HTTPConnection(
                "127.0.0.1", server.httpd.server_port, timeout=2
            )
            try:
                connection.request("GET", "/livez")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b"ok\n")
            finally:
                connection.close()
        finally:
            server.close()

    def test_existing_ingress_bounds_remain_exposed(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            request_timeout_seconds=0.25,
            request_header_deadline_seconds=0.75,
            max_concurrent_requests=2,
            max_request_header_bytes=4096,
        )
        try:
            self.assertEqual(server.request_timeout_seconds, 0.25)
            self.assertEqual(server.request_header_deadline_seconds, 0.75)
            self.assertEqual(server.max_concurrent_requests, 2)
            self.assertEqual(server.max_request_header_bytes, 4096)
        finally:
            server.httpd.server_close()


if __name__ == "__main__":
    unittest.main()
