import http.client
import socket
import unittest

from nvlx.http_v16665 import HealthServer


class TerminalMethodRejectionTests(unittest.TestCase):
    @staticmethod
    def request(server, method, path, *, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.httpd.server_port, timeout=2
        )
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

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

    def test_live_method_rejection_is_explicitly_connection_close(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(
                server,
                "POST",
                "/metrics",
                body=b"payload",
                headers={"Content-Length": "7", "Connection": "keep-alive"},
            )
            self.assertEqual(status, 405)
            self.assertEqual(body, b"request rejected\n")
            self.assertEqual(headers.get("Allow"), "GET, HEAD")
            self.assertEqual(headers.get("Connection"), "close")
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_unknown_method_rejection_is_empty_404_and_connection_close(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(
                server,
                "DELETE",
                "/unknown",
                body=b"ignored",
                headers={"Content-Length": "7", "Connection": "keep-alive"},
            )
            self.assertEqual(status, 404)
            self.assertEqual(body, b"")
            self.assertEqual(headers.get("Connection"), "close")
            self.assertIsNone(headers.get("Allow"))
            self.assertIsNone(headers.get("Cache-Control"))
            self.assertIsNone(headers.get("Content-Length"))
            self.assertEqual(headers.get("Server"), "nvlx")
        finally:
            server.close()

    def test_arbitrary_method_rejection_is_terminal_and_non_reflective(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            status, headers, body = self.request(server, "BREW", "/livez")
            self.assertEqual(status, 405)
            self.assertEqual(headers.get("Connection"), "close")
            self.assertNotIn(b"BREW", body)
            self.assertNotIn(b"Unsupported method", body)
        finally:
            server.close()

    def test_body_bearing_rejection_cannot_process_pipelined_following_get(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            request = (
                b"POST /livez HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: 4\r\n"
                b"Connection: keep-alive\r\n"
                b"\r\n"
                b"JUNK"
                b"GET /livez HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            response = self.raw_exchange(server, request)
            self.assertEqual(response.count(b"HTTP/1."), 1)
            self.assertIn(b" 405 ", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertNotIn(b" 200 ", response)
            self.assertNotIn(b"ok\n", response)
        finally:
            server.close()

    def test_rejection_does_not_affect_new_connection_get(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            rejected_status, rejected_headers, _ = self.request(
                server, "POST", "/livez", body=b"x"
            )
            self.assertEqual(rejected_status, 405)
            self.assertEqual(rejected_headers.get("Connection"), "close")
            get_status, get_headers, get_body = self.request(server, "GET", "/livez")
            self.assertEqual((get_status, get_body), (200, b"ok\n"))
            self.assertIsNone(get_headers.get("Connection"))
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
