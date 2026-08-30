import errno
import http.client
import io
import socket
import unittest

from nvlx.http_v166666 import HealthServer, _is_client_abort_error


class _FailingWriter:
    def __init__(self, exc):
        self.exc = exc
        self.closed = False

    def write(self, data):
        raise self.exc

    def flush(self):
        return None

    def close(self):
        self.closed = True


class _CloseFailingWriter:
    def __init__(self, exc):
        self.exc = exc
        self.closed = False

    def write(self, data):
        return len(data)

    def flush(self):
        return None

    def close(self):
        raise self.exc


class ClientAbortContainmentTests(unittest.TestCase):
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
    def synthetic_handler(server, exc):
        handler_cls = server.httpd.RequestHandlerClass
        handler = handler_cls.__new__(handler_cls)
        handler.rfile = io.BytesIO(
            b"GET /livez HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
        )
        handler.wfile = _FailingWriter(exc)
        handler.client_address = ("127.0.0.1", 12345)
        handler.server = server.httpd
        handler.request = object()
        return handler

    def test_abort_classifier_is_narrow(self):
        self.assertTrue(
            _is_client_abort_error(BrokenPipeError(errno.EPIPE, "closed"))
        )
        self.assertTrue(
            _is_client_abort_error(
                ConnectionResetError(errno.ECONNRESET, "reset")
            )
        )
        self.assertFalse(_is_client_abort_error(OSError(errno.EIO, "io")))
        self.assertFalse(_is_client_abort_error(RuntimeError("bug")))

    def test_broken_pipe_during_response_is_contained(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            handler = self.synthetic_handler(
                server, BrokenPipeError(errno.EPIPE, "closed")
            )
            handler.handle()
            self.assertTrue(handler.close_connection)
        finally:
            server.httpd.server_close()

    def test_connection_reset_during_response_is_contained(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            handler = self.synthetic_handler(
                server, ConnectionResetError(errno.ECONNRESET, "reset")
            )
            handler.handle()
            self.assertTrue(handler.close_connection)
        finally:
            server.httpd.server_close()

    def test_connection_abort_during_finish_is_contained(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            handler_cls = server.httpd.RequestHandlerClass
            handler = handler_cls.__new__(handler_cls)
            handler.wfile = _CloseFailingWriter(
                ConnectionResetError(errno.ECONNRESET, "reset")
            )
            handler.rfile = io.BytesIO(b"")
            handler.close_connection = False
            handler.finish()
            self.assertTrue(handler.close_connection)
        finally:
            server.httpd.server_close()

    def test_unrelated_oserror_during_response_propagates(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            handler = self.synthetic_handler(server, OSError(errno.EIO, "io"))
            with self.assertRaises(OSError):
                handler.handle()
        finally:
            server.httpd.server_close()

    def test_non_oserror_during_response_propagates(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            handler = self.synthetic_handler(server, RuntimeError("bug"))
            with self.assertRaises(RuntimeError):
                handler.handle()
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
