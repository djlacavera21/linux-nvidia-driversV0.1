import contextlib
import errno
import http.client
import io
import socket
import unittest

from nvlx.http_v1666661 import HealthServer


class ServerAbortHookTests(unittest.TestCase):
    @staticmethod
    def invoke_error_hook(server, exc: BaseException) -> str:
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            try:
                raise exc
            except BaseException:
                server.httpd.handle_error(object(), ("127.0.0.1", 12345))
        return stream.getvalue()

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

    def test_server_hook_suppresses_connection_reset_traceback(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            log = self.invoke_error_hook(
                server, ConnectionResetError(errno.ECONNRESET, "reset")
            )
            self.assertEqual(log, "")
        finally:
            server.httpd.server_close()

    def test_server_hook_suppresses_broken_pipe_traceback(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            log = self.invoke_error_hook(
                server, BrokenPipeError(errno.EPIPE, "closed")
            )
            self.assertEqual(log, "")
        finally:
            server.httpd.server_close()

    def test_server_hook_suppresses_not_connected_oserror(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            err = getattr(errno, "ENOTCONN", errno.ECONNRESET)
            log = self.invoke_error_hook(server, OSError(err, "not connected"))
            self.assertEqual(log, "")
        finally:
            server.httpd.server_close()

    def test_server_hook_delegates_unrelated_oserror(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            log = self.invoke_error_hook(server, OSError(errno.EIO, "io failure"))
            self.assertIn("Exception occurred during processing of request", log)
            self.assertIn("OSError", log)
            self.assertIn("io failure", log)
        finally:
            server.httpd.server_close()

    def test_server_hook_delegates_runtime_error(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            log = self.invoke_error_hook(server, RuntimeError("implementation bug"))
            self.assertIn("Exception occurred during processing of request", log)
            self.assertIn("RuntimeError", log)
            self.assertIn("implementation bug", log)
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

    def test_parser_wire_contract_is_unchanged(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_exchange(
                server,
                b"GET /livez HTTP/2.0\r\nHost: x\r\n\r\n",
            )
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
