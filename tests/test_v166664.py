import contextlib
import http.client
import io
import socket
import unittest

from nvlx.http_v166664 import HealthServer


class SafeHttpLoggingTests(unittest.TestCase):
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

    def test_success_log_omits_request_line_and_path(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        stream = io.StringIO()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with contextlib.redirect_stderr(stream):
                connection.request("GET", "/livez")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
            log = stream.getvalue()
            self.assertIn("nvlx http status=200", log)
            self.assertNotIn("GET", log)
            self.assertNotIn("/livez", log)
        finally:
            connection.close()
            server.close()

    def test_method_rejection_log_omits_method_and_path(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        stream = io.StringIO()
        try:
            with contextlib.redirect_stderr(stream):
                response = self.raw_exchange(
                    server,
                    b"TRACESECRET /livez HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n",
                )
            self.assertIn(b" 405 ", response)
            log = stream.getvalue()
            self.assertIn("nvlx http status=405", log)
            self.assertNotIn("TRACESECRET", log)
            self.assertNotIn("/livez", log)
        finally:
            server.close()

    def test_parser_error_log_omits_malformed_request_and_control_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        stream = io.StringIO()
        try:
            with contextlib.redirect_stderr(stream):
                response = self.raw_exchange(
                    server,
                    b"GET /livez HTTP/1.1 LEAKMARK\x1b[31m\r\nHost: x\r\n\r\n",
                )
            self.assertTrue(response.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            log = stream.getvalue()
            self.assertIn("nvlx http status=400", log)
            self.assertNotIn("LEAKMARK", log)
            self.assertNotIn("\x1b", log)
            self.assertNotIn("GET", log)
        finally:
            server.close()

    def test_unknown_resource_log_omits_target(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        stream = io.StringIO()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with contextlib.redirect_stderr(stream):
                connection.request("GET", "/secret-log-marker")
                response = connection.getresponse()
                self.assertEqual(response.status, 404)
                response.read()
            log = stream.getvalue()
            self.assertIn("nvlx http status=404", log)
            self.assertNotIn("secret-log-marker", log)
        finally:
            connection.close()
            server.close()

    def test_log_line_is_bounded_for_long_unknown_target(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        stream = io.StringIO()
        target = "/" + ("x" * 4096)
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            with contextlib.redirect_stderr(stream):
                connection.request("GET", target)
                response = connection.getresponse()
                self.assertEqual(response.status, 404)
                response.read()
            log = stream.getvalue()
            self.assertLessEqual(len(log), 64)
            self.assertEqual(log, "nvlx http status=404\n")
        finally:
            connection.close()
            server.close()

    def test_parser_wire_contract_remains_canonical(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        stream = io.StringIO()
        try:
            with contextlib.redirect_stderr(stream):
                response = self.raw_exchange(
                    server,
                    b"GET /livez HTTP/2.0\r\nHost: x\r\n\r\n",
                )
            self.assertTrue(response.startswith(b"HTTP/1.0 505 Request Rejected\r\n"))
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertIn(b"Connection: close\r\n", response)
            self.assertEqual(stream.getvalue(), "nvlx http status=505\n")
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
