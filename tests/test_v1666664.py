import http.client
import math
import socket
import time
import unittest

from nvlx.http_v1666664 import (
    HealthServer,
    _validate_request_header_deadline,
)


class _SlowMetricsRuntime:
    def metrics_diagnosis(self):
        time.sleep(0.15)
        raise RuntimeError("contained metrics failure")


class AbsoluteHeaderDeadlineTests(unittest.TestCase):
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

    def test_header_deadline_validation_matches_request_timeout_domain(self):
        self.assertEqual(_validate_request_header_deadline(5), 5.0)
        self.assertEqual(_validate_request_header_deadline(0.25), 0.25)
        with self.assertRaises(TypeError):
            _validate_request_header_deadline(True)
        with self.assertRaises(ValueError):
            _validate_request_header_deadline(0)
        with self.assertRaises(ValueError):
            _validate_request_header_deadline(-1)
        with self.assertRaises(ValueError):
            _validate_request_header_deadline(math.inf)
        with self.assertRaises(ValueError):
            _validate_request_header_deadline(math.nan)

    def test_default_header_deadline_is_exposed(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            self.assertEqual(server.request_header_deadline_seconds, 5.0)
            self.assertEqual(server.request_timeout_seconds, 5.0)
            self.assertEqual(server.max_concurrent_requests, 32)
        finally:
            server.httpd.server_close()

    def test_byte_trickle_expires_despite_continuous_idle_activity(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            request_timeout_seconds=0.20,
            request_header_deadline_seconds=0.20,
            max_concurrent_requests=1,
        ).start()
        sock = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        sock.settimeout(1.0)
        started = time.monotonic()
        closed = False
        try:
            for value in b"GET /livez HTTP/1.1\r\nHost: trickle":
                try:
                    sock.sendall(bytes((value,)))
                except OSError:
                    closed = True
                    break
                time.sleep(0.03)
            if not closed:
                try:
                    closed = sock.recv(4096) == b""
                except (ConnectionResetError, BrokenPipeError, OSError):
                    closed = True
            self.assertTrue(closed)
            self.assertLess(time.monotonic() - started, 0.9)
        finally:
            sock.close()
            server.close()

    def test_header_deadline_releases_capacity_and_server_recovers(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            request_timeout_seconds=1.0,
            request_header_deadline_seconds=0.10,
            max_concurrent_requests=1,
        ).start()
        slow = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        slow.settimeout(1.0)
        connection = None
        try:
            slow.sendall(b"GET /livez HTTP/1.1\r\nHost: slow")
            self.wait_for_slots(server, 0)
            try:
                self.assertEqual(slow.recv(4096), b"")
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass
            self.wait_for_slots(server, 1)

            connection = http.client.HTTPConnection(
                "127.0.0.1", server.httpd.server_port, timeout=2
            )
            connection.request("GET", "/livez")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"ok\n")
        finally:
            slow.close()
            if connection is not None:
                connection.close()
            server.close()

    def test_completed_headers_cancel_deadline_before_slow_runtime_work(self):
        server = HealthServer(
            _SlowMetricsRuntime(),
            "127.0.0.1",
            0,
            request_timeout_seconds=1.0,
            request_header_deadline_seconds=0.05,
            max_concurrent_requests=1,
        ).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request("GET", "/metrics")
            response = connection.getresponse()
            self.assertEqual(response.status, 500)
            self.assertEqual(response.read(), b"metrics unavailable\n")
        finally:
            connection.close()
            server.close()

    def test_ingress_idle_timeout_remains_configurable(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            request_timeout_seconds=0.25,
            request_header_deadline_seconds=0.75,
            max_concurrent_requests=2,
        )
        client = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        accepted = None
        try:
            accepted, _ = server.httpd.get_request()
            self.assertEqual(accepted.gettimeout(), 0.25)
        finally:
            if accepted is not None:
                accepted.close()
            client.close()
            server.httpd.server_close()

    def test_success_wire_contract_is_unchanged(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request("GET", "/livez")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"ok\n")
            self.assertEqual(response.getheader("Server"), "nvlx")
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            self.assertEqual(response.getheader("Content-Length"), "3")
        finally:
            connection.close()
            server.close()


if __name__ == "__main__":
    unittest.main()
