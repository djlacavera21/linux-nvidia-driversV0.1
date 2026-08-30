import http.client
import socket
import time
import unittest

from nvlx.http_v1666663 import (
    HealthServer,
    _validate_max_concurrent_requests,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached while saturated")


class BoundedAdmissionTests(unittest.TestCase):
    @staticmethod
    def wait_for_slots(server, expected: int, timeout: float = 1.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if getattr(server._request_slots, "_value", None) == expected:
                return
            time.sleep(0.005)
        raise AssertionError(
            f"request slot value did not become {expected}; "
            f"got {getattr(server._request_slots, '_value', None)}"
        )

    def test_capacity_validation_is_strict(self):
        self.assertEqual(_validate_max_concurrent_requests(1), 1)
        self.assertEqual(_validate_max_concurrent_requests(32), 32)
        with self.assertRaises(TypeError):
            _validate_max_concurrent_requests(True)
        with self.assertRaises(TypeError):
            _validate_max_concurrent_requests(1.0)
        with self.assertRaises(TypeError):
            _validate_max_concurrent_requests("2")
        with self.assertRaises(ValueError):
            _validate_max_concurrent_requests(0)
        with self.assertRaises(ValueError):
            _validate_max_concurrent_requests(-1)

    def test_saturated_connection_is_closed_before_endpoint_logic(self):
        runtime = _MetricsRuntime()
        server = HealthServer(
            runtime,
            "127.0.0.1",
            0,
            request_timeout_seconds=1.0,
            max_concurrent_requests=1,
        ).start()
        slow = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        excess = None
        try:
            slow.sendall(b"GET /livez HTTP/1.1\r\nHost: slow")
            self.wait_for_slots(server, 0)

            excess = socket.create_connection(
                ("127.0.0.1", server.httpd.server_port), timeout=1
            )
            excess.settimeout(1)
            try:
                excess.sendall(
                    b"GET /metrics HTTP/1.1\r\nHost: excess\r\n\r\n"
                )
            except OSError:
                pass
            try:
                data = excess.recv(4096)
            except (ConnectionResetError, BrokenPipeError):
                data = b""
            self.assertEqual(data, b"")
            self.assertEqual(runtime.calls, 0)
        finally:
            slow.close()
            if excess is not None:
                excess.close()
            server.close()

    def test_slot_is_released_after_slow_connection_closes(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            request_timeout_seconds=1.0,
            max_concurrent_requests=1,
        ).start()
        slow = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        connection = None
        try:
            slow.sendall(b"GET /livez HTTP/1.1\r\nHost: slow")
            self.wait_for_slots(server, 0)
            slow.close()
            self.wait_for_slots(server, 1)

            connection = http.client.HTTPConnection(
                "127.0.0.1", server.httpd.server_port, timeout=2
            )
            connection.request("GET", "/livez")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"ok\n")
        finally:
            try:
                slow.close()
            except OSError:
                pass
            if connection is not None:
                connection.close()
            server.close()

    def test_slot_is_released_after_parser_rejection(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            with socket.create_connection(
                ("127.0.0.1", server.httpd.server_port), timeout=2
            ) as sock:
                sock.sendall(b"GET /livez HTTP/2.0\r\nHost: x\r\n\r\n")
                sock.shutdown(socket.SHUT_WR)
                while sock.recv(65536):
                    pass
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

    def test_default_capacity_is_exposed(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            self.assertEqual(server.max_concurrent_requests, 32)
            self.assertEqual(getattr(server._request_slots, "_value", None), 32)
        finally:
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

    def test_ingress_timeout_configuration_is_preserved(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            request_timeout_seconds=0.25,
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


if __name__ == "__main__":
    unittest.main()
