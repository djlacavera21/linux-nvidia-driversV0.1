import http.client
import socket
import sys
import unittest
from unittest import mock

from nvlx.http_v166665 import HealthServer


_REJECTION_BODY = b"request rejected\n"


class _RaisingSink:
    def __init__(self, exc: Exception):
        self.exc = exc

    def write(self, text):
        raise self.exc


class BestEffortHttpLoggingTests(unittest.TestCase):
    @staticmethod
    def raw_exchange(server, payload: bytes) -> bytes:
        with socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=2
        ) as sock:
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)

    def test_livez_survives_oserror_from_stderr(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with mock.patch.object(sys, "stderr", _RaisingSink(OSError("closed"))):
                connection.request("GET", "/livez")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b"ok\n")
        finally:
            connection.close()
            server.close()

    def test_head_livez_survives_valueerror_from_stderr(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with mock.patch.object(sys, "stderr", _RaisingSink(ValueError("closed"))):
                connection.request("HEAD", "/livez")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.getheader("Content-Length"), "3")
                self.assertEqual(response.read(), b"")
        finally:
            connection.close()
            server.close()

    def test_parser_error_survives_runtimeerror_from_stderr(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            with mock.patch.object(
                sys, "stderr", _RaisingSink(RuntimeError("sink failure"))
            ):
                response = self.raw_exchange(
                    server,
                    b"GET /livez HTTP/1.1 EXTRA\r\nHost: x\r\n\r\n",
                )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertTrue(response.endswith(_REJECTION_BODY))
            self.assertIn(b"Connection: close\r\n", response)
        finally:
            server.close()

    def test_method_rejection_survives_missing_stderr(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with mock.patch.object(sys, "stderr", None):
                connection.request("POST", "/livez")
                response = connection.getresponse()
                self.assertEqual(response.status, 405)
                self.assertEqual(response.getheader("Allow"), "GET, HEAD")
                self.assertEqual(response.getheader("Connection"), "close")
                self.assertEqual(response.read(), _REJECTION_BODY)
        finally:
            connection.close()
            server.close()

    def test_unknown_resource_survives_broken_stderr(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with mock.patch.object(sys, "stderr", _RaisingSink(BrokenPipeError())):
                connection.request("GET", "/unknown")
                response = connection.getresponse()
                self.assertEqual(response.status, 404)
                self.assertEqual(response.read(), b"")
        finally:
            connection.close()
            server.close()

    def test_metrics_failure_survives_broken_stderr(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with mock.patch.object(sys, "stderr", _RaisingSink(OSError("broken"))):
                connection.request("GET", "/metrics")
                response = connection.getresponse()
                self.assertEqual(response.status, 500)
                self.assertEqual(response.read(), b"metrics unavailable\n")
        finally:
            connection.close()
            server.close()


if __name__ == "__main__":
    unittest.main()
