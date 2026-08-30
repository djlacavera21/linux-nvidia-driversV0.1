import http.client
import io
import socket
import time
import unittest

from nvlx.http_v166666662 import (
    HealthServer,
    _HeaderFieldValueTrackingReader,
    _header_field_value_is_safe,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for unsafe header field values")


class HeaderFieldValueContainmentTests(unittest.TestCase):
    @staticmethod
    def raw_request(server, payload: bytes) -> bytes:
        with socket.create_connection(
            ("127.0.0.1", server.httpd.server_port), timeout=2
        ) as sock:
            sock.settimeout(2)
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                response += chunk
            return response

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

    def test_field_value_helper_accepts_ows_visible_ascii_and_empty_values(self):
        accepted = (
            b"Host: localhost\r\n",
            b"X-Test:\r\n",
            b"X-Test:   \t \r\n",
            b"X-Test: alpha beta\tgamma\r\n",
            b"X-Test: a:b:c!?[]{}\r\n",
        )
        for line in accepted:
            with self.subTest(line=line):
                self.assertTrue(_header_field_value_is_safe(line))

    def test_field_value_helper_rejects_controls_del_and_raw_non_ascii(self):
        rejected = (
            b"X-Test: a\x00b\r\n",
            b"X-Test: a\x07b\r\n",
            b"X-Test: a\x0bb\r\n",
            b"X-Test: a\x0cb\r\n",
            b"X-Test: a\x1fb\r\n",
            b"X-Test: a\x7fb\r\n",
            b"X-Test: a\x80b\r\n",
            b"X-Test: a\xffb\r\n",
            b"NoColon\r\n",
        )
        for line in rejected:
            with self.subTest(line=line):
                self.assertFalse(_header_field_value_is_safe(line))
        self.assertFalse(_header_field_value_is_safe(None))
        self.assertFalse(_header_field_value_is_safe("X-Test: value"))

    def test_tracking_reader_defers_obs_fold_and_tracks_bad_values(self):
        stream = io.BytesIO(
            b"Host: localhost\r\n"
            b" continuation\r\n"
            b"X-Test: a\x00b\r\n"
            b"\r\n"
        )
        reader = _HeaderFieldValueTrackingReader(stream)
        self.assertEqual(reader.readline(), b"Host: localhost\r\n")
        self.assertFalse(reader.saw_invalid_field_value)
        self.assertEqual(reader.readline(), b" continuation\r\n")
        self.assertFalse(reader.saw_invalid_field_value)
        self.assertEqual(reader.readline(), b"X-Test: a\x00b\r\n")
        self.assertTrue(reader.saw_invalid_field_value)

    def test_canonical_ascii_field_values_remain_accepted(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"X-Test: alpha beta\tgamma:delta\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
            self.assertTrue(response.endswith(b"ok\n"))
        finally:
            server.close()

    def test_empty_field_value_remains_accepted(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\nX-Empty:\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
        finally:
            server.close()

    def test_nul_field_value_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"X-Test: alpha\x00beta\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Server: nvlx\r\n", response)
            self.assertIn(b"Cache-Control: no-store\r\n", response)
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_del_and_raw_non_ascii_field_values_are_rejected(self):
        for value in (b"alpha\x7fbeta", b"alpha\x80beta", b"alpha\xffbeta"):
            with self.subTest(value=value):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server,
                        b"GET /livez HTTP/1.1\r\nHost: localhost\r\nX-Test: "
                        + value
                        + b"\r\n\r\n",
                    )
                    self.assertTrue(
                        response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
                    )
                finally:
                    server.close()

    def test_http_10_control_value_is_also_rejected(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.0\r\nX-Test: alpha\x01beta\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
        finally:
            server.close()

    def test_unsafe_value_head_rejection_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"X-Test: alpha\x00beta\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_value_rejection_terminates_pipelined_bytes(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"X-Test: alpha\x00beta\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_value_rejection_releases_capacity_and_server_recovers(self):
        server = HealthServer(
            object(),
            "127.0.0.1",
            0,
            max_concurrent_requests=1,
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"X-Test: alpha\x00beta\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.wait_for_slots(server, 1)

            connection = http.client.HTTPConnection(
                "127.0.0.1", server.httpd.server_port, timeout=2
            )
            try:
                connection.request("GET", "/livez")
                live = connection.getresponse()
                self.assertEqual(live.status, 200)
                self.assertEqual(live.read(), b"ok\n")
            finally:
                connection.close()
        finally:
            server.close()

    def test_inherited_ingress_defaults_are_unchanged(self):
        server = HealthServer(object(), "127.0.0.1", 0)
        try:
            self.assertEqual(server.max_request_header_fields, 32)
            self.assertEqual(server.max_request_line_bytes, 8192)
            self.assertEqual(server.max_request_header_bytes, 32768)
            self.assertEqual(server.request_header_deadline_seconds, 5.0)
            self.assertEqual(server.request_timeout_seconds, 5.0)
            self.assertEqual(server.max_concurrent_requests, 32)
        finally:
            server.httpd.server_close()


if __name__ == "__main__":
    unittest.main()
