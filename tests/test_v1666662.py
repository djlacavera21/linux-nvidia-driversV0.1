import contextlib
import errno
import http.client
import io
import math
import socket
import unittest

from nvlx.http_v1666662 import (
    HealthServer,
    _is_request_timeout_error,
    _validate_request_timeout,
)


class IngressIdleTimeoutTests(unittest.TestCase):
    def test_timeout_validation_is_strict(self):
        self.assertEqual(_validate_request_timeout(5), 5.0)
        self.assertEqual(_validate_request_timeout(0.25), 0.25)
        with self.assertRaises(TypeError):
            _validate_request_timeout(True)
        with self.assertRaises(ValueError):
            _validate_request_timeout(0)
        with self.assertRaises(ValueError):
            _validate_request_timeout(-1)
        with self.assertRaises(ValueError):
            _validate_request_timeout(math.inf)
        with self.assertRaises(ValueError):
            _validate_request_timeout(math.nan)

    def test_timeout_classifier_is_narrow(self):
        self.assertTrue(_is_request_timeout_error(TimeoutError("idle")))
        timed_out = getattr(errno, "ETIMEDOUT", None)
        if timed_out is not None:
            self.assertTrue(
                _is_request_timeout_error(OSError(timed_out, "timed out"))
            )
        self.assertFalse(_is_request_timeout_error(OSError(errno.EIO, "io")))
        self.assertFalse(_is_request_timeout_error(RuntimeError("bug")))

    def test_accepted_socket_receives_configured_timeout(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, request_timeout_seconds=0.25
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

    def test_partial_request_expires_without_traceback_or_reflection(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, request_timeout_seconds=0.1
        ).start()
        sock = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        sock.settimeout(1.5)
        stream = io.StringIO()
        try:
            sock.sendall(b"GET /livez HTTP/1.1\r\nHost: attacker")
            with contextlib.redirect_stderr(stream):
                self.assertEqual(sock.recv(4096), b"")
            log = stream.getvalue()
            self.assertNotIn("Traceback", log)
            self.assertNotIn("attacker", log)
            self.assertNotIn("GET /livez", log)
        finally:
            sock.close()
            server.close()

    def test_server_remains_usable_after_idle_request_timeout(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, request_timeout_seconds=0.1
        ).start()
        slow = socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=1
        )
        slow.settimeout(1.5)
        connection = None
        try:
            slow.sendall(b"GET /livez HTTP/1.1\r\nHost:")
            self.assertEqual(slow.recv(4096), b"")

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

    def test_parser_wire_contract_is_unchanged(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            with socket.create_connection(
                ("127.0.0.1", server.httpd.server_port), timeout=2
            ) as sock:
                sock.sendall(b"GET /livez HTTP/2.0\r\nHost: x\r\n\r\n")
                sock.shutdown(socket.SHUT_WR)
                response = b""
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    response += chunk
            self.assertTrue(
                response.startswith(b"HTTP/1.0 505 Request Rejected\r\n")
            )
            self.assertIn(b"Server: nvlx\r\n", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
