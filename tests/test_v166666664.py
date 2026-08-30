import http.client
import socket
import time
import unittest
from email.message import Message

from nvlx.http_v166666664 import (
    HealthServer,
    _authority_value_is_safe,
    _port_is_safe,
    _reg_name_is_safe,
    _request_host_authority_is_safe,
)


class _MetricsRuntime:
    def __init__(self):
        self.calls = 0

    def metrics_diagnosis(self):
        self.calls += 1
        raise RuntimeError("should not be reached for rejected Host authority")


class HostAuthorityContainmentTests(unittest.TestCase):
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

    def test_port_policy_is_decimal_and_bounded(self):
        for value in ("1", "80", "443", "65535", "00080"):
            with self.subTest(value=value):
                self.assertTrue(_port_is_safe(value))
        for value in ("", "0", "65536", "999999", "+80", "-1", "8a"):
            with self.subTest(value=value):
                self.assertFalse(_port_is_safe(value))

    def test_reg_name_policy_covers_dns_and_kubernetes_names(self):
        accepted = (
            "localhost",
            "example.internal",
            "my-service.namespace.svc",
            "service_name.namespace",
            "example.internal.",
        )
        for value in accepted:
            with self.subTest(value=value):
                self.assertTrue(_reg_name_is_safe(value))

        rejected = (
            "",
            ".example",
            "example..internal",
            "-host",
            "host-",
            "bad@host",
            "bad host",
        )
        for value in rejected:
            with self.subTest(value=value):
                self.assertFalse(_reg_name_is_safe(value))

    def test_authority_policy_accepts_common_operational_forms(self):
        accepted = (
            "localhost",
            " localhost ",
            "my-service.namespace.svc:8080",
            "10.0.0.1",
            "10.0.0.1:443",
            "[::1]",
            "[2001:db8::1]:8443",
        )
        for value in accepted:
            with self.subTest(value=value):
                self.assertTrue(_authority_value_is_safe(value))

    def test_authority_policy_rejects_ambiguous_or_invalid_forms(self):
        rejected = (
            "user@host",
            "http://host",
            "host/path",
            "host\\path",
            "host?query",
            "host#fragment",
            "host name",
            "host\tname",
            "host:",
            "host:0",
            "host:65536",
            "host:abc",
            "::1",
            "[::1",
            "::1]",
            "[not-ipv6]",
            "[fe80::1%eth0]",
            "999.1.1.1",
        )
        for value in rejected:
            with self.subTest(value=value):
                self.assertFalse(_authority_value_is_safe(value))
        self.assertFalse(_authority_value_is_safe(None))

    def test_request_policy_validates_only_http_11_authority(self):
        headers = Message()
        headers["Host"] = "localhost:8080"
        self.assertTrue(_request_host_authority_is_safe("HTTP/1.1", headers))

        malformed = Message()
        malformed["Host"] = "user@host"
        self.assertFalse(_request_host_authority_is_safe("HTTP/1.1", malformed))
        self.assertTrue(_request_host_authority_is_safe("HTTP/1.0", malformed))
        self.assertFalse(_request_host_authority_is_safe("HTTP/1.2", headers))
        self.assertFalse(_request_host_authority_is_safe("HTTP/1.1", {}))

    def test_common_http_11_host_forms_remain_accepted(self):
        for host in (
            b"localhost",
            b"my-service.namespace.svc:8080",
            b"10.0.0.1:443",
            b"[::1]:8080",
        ):
            with self.subTest(host=host):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server,
                        b"GET /livez HTTP/1.1\r\nHost: " + host + b"\r\n\r\n",
                    )
                    self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
                    self.assertTrue(response.endswith(b"ok\n"))
                finally:
                    server.close()

    def test_userinfo_host_is_terminal_400_before_runtime(self):
        runtime = _MetricsRuntime()
        server = HealthServer(runtime, "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /metrics HTTP/1.1\r\nHost: user@localhost\r\n\r\n",
            )
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertIn(b"Connection: close\r\n", response)
            self.assertTrue(response.endswith(b"request rejected\n"))
            self.assertEqual(runtime.calls, 0)
        finally:
            server.close()

    def test_invalid_port_and_unbracketed_ipv6_are_rejected(self):
        for host in (b"localhost:65536", b"localhost:abc", b"::1"):
            with self.subTest(host=host):
                server = HealthServer(object(), "127.0.0.1", 0).start()
                try:
                    response = self.raw_request(
                        server,
                        b"GET /livez HTTP/1.1\r\nHost: " + host + b"\r\n\r\n",
                    )
                    self.assertTrue(
                        response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
                    )
                finally:
                    server.close()

    def test_http_10_host_syntax_remains_outside_this_gate(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.0\r\nHost: user@legacy\r\n\r\n",
            )
            self.assertTrue(response.startswith(b"HTTP/1.0 200 OK\r\n"))
        finally:
            server.close()

    def test_expect_repair_is_canonical_417_without_interim_100(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Expect: 100-continue\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 417 Request Rejected\r\n")
            )
            self.assertNotIn(b"100 Continue", response)
            self.assertIn(b"Connection: close\r\n", response)
        finally:
            server.close()

    def test_host_authority_rejection_head_is_bodyless(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"HEAD /livez HTTP/1.1\r\nHost: user@host\r\n\r\n",
            )
            head, body = response.split(b"\r\n\r\n", 1)
            self.assertTrue(head.startswith(b"HTTP/1.0 400 Request Rejected\r\n"))
            self.assertIn(b"Content-Length: 17\r\n", head + b"\r\n")
            self.assertIn(b"Connection: close\r\n", head + b"\r\n")
            self.assertEqual(body, b"")
        finally:
            server.close()

    def test_host_authority_rejection_terminates_pipeline(self):
        server = HealthServer(object(), "127.0.0.1", 0).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: host/path\r\n\r\n"
                b"GET /livez HTTP/1.1\r\nHost: localhost\r\n\r\n",
            )
            self.assertEqual(response.count(b"HTTP/1.0 "), 1)
            self.assertTrue(
                response.startswith(b"HTTP/1.0 400 Request Rejected\r\n")
            )
            self.assertNotIn(b"200 OK", response)
        finally:
            server.close()

    def test_host_authority_rejection_releases_capacity_and_recovers(self):
        server = HealthServer(
            object(), "127.0.0.1", 0, max_concurrent_requests=1
        ).start()
        try:
            response = self.raw_request(
                server,
                b"GET /livez HTTP/1.1\r\nHost: host:99999\r\n\r\n",
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
