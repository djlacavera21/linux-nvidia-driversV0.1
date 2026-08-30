import http.client
import socket
import unittest

from nvlx.http_v166662 import HealthServer


_REJECTION_BODY = b"request rejected\n"
_REJECTION_LENGTH = len(_REJECTION_BODY)


class TerminalParserErrorTests(unittest.TestCase):
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

    @staticmethod
    def assert_terminal_error(testcase, response: bytes, status: int):
        testcase.assertIn(f" {status} ".encode("ascii"), response)
        testcase.assertIn(b"Server: nvlx\r\n", response)
        testcase.assertIn(b"Content-Type: text/plain; charset=utf-8\r\n", response)
        testcase.assertIn(b"Cache-Control: no-store\r\n", response)
        testcase.assertIn(
            f"Content-Length: {_REJECTION_LENGTH}\r\n".encode("ascii"),
            response,
        )
        testcase.assertIn(b"Connection: close\r\n", response)
        testcase.assertTrue(response.endswith(_REJECTION_BODY))

    def test_malformed_request_syntax_is_fixed_and_terminal(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_exchange(
                server,
                b"GET /livez HTTP/1.1 EXTRA\r\nHost: 127.0.0.1\r\n\r\n",
            )
            self.assert_terminal_error(self, response, 400)
            self.assertNotIn(b"Bad request syntax", response)
            self.assertNotIn(b"EXTRA", response)
        finally:
            server.close()

    def test_overlong_request_line_is_fixed_terminal_414(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_exchange(
                server,
                b"GET /" + (b"a" * 65536) + b" HTTP/1.1\r\nHost: x\r\n\r\n",
            )
            self.assert_terminal_error(self, response, 414)
            self.assertNotIn(b"a" * 128, response)
        finally:
            server.close()

    def test_header_overflow_is_fixed_terminal_431(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            headers = b"".join(
                f"X-Test-{index}: value\r\n".encode("ascii") for index in range(110)
            )
            response = self.raw_exchange(
                server,
                b"GET /livez HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                + headers
                + b"\r\n",
            )
            self.assert_terminal_error(self, response, 431)
            self.assertNotIn(b"Too many headers", response)
        finally:
            server.close()

    def test_unsupported_http_version_is_fixed_terminal_505(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_exchange(
                server,
                b"GET /livez HTTP/2.0\r\nHost: 127.0.0.1\r\n\r\n",
            )
            self.assert_terminal_error(self, response, 505)
            self.assertNotIn(b"Invalid HTTP version", response)
        finally:
            server.close()

    def test_parser_error_cannot_process_pipelined_following_get(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_exchange(
                server,
                b"GET /livez HTTP/1.1 EXTRA\r\nHost: 127.0.0.1\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1."), 1)
            self.assertIn(b" 400 ", response)
            self.assertNotIn(b" 200 ", response)
            self.assertNotIn(b"ok\n", response)
        finally:
            server.close()

    def test_live_method_contract_remains_405(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request("POST", "/livez")
            response = connection.getresponse()
            body = response.read()
            self.assertEqual(response.status, 405)
            self.assertEqual(response.getheader("Allow"), "GET, HEAD")
            self.assertEqual(response.getheader("Connection"), "close")
            self.assertEqual(body, _REJECTION_BODY)
        finally:
            connection.close()
            server.close()


if __name__ == "__main__":
    unittest.main()
