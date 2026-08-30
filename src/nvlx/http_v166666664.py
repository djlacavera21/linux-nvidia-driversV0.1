"""Strict HTTP/1.1 Host authority syntax containment for nvlx 1.6.6.6.6.6.6.6.4."""
from __future__ import annotations

import ipaddress

from .http_v166666663 import HealthServer as HealthServerV166666663


_REG_NAME_BYTES = frozenset(
    b"-._0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


def _port_is_safe(value: str) -> bool:
    """Accept one explicit decimal TCP/UDP port in the usable range."""
    if not value or not value.isascii() or not value.isdigit():
        return False
    if len(value) > 5:
        return False
    port = int(value, 10)
    return 1 <= port <= 65535


def _reg_name_is_safe(value: str) -> bool:
    """Accept a conservative DNS/Kubernetes-compatible ASCII reg-name."""
    if not value or not value.isascii():
        return False

    # A final root dot is harmless; internal empty labels are ambiguous.
    candidate = value[:-1] if value.endswith(".") else value
    if not candidate or len(candidate) > 253:
        return False
    labels = candidate.split(".")
    if any(not label or len(label) > 63 for label in labels):
        return False

    for label in labels:
        raw = label.encode("ascii")
        if any(byte not in _REG_NAME_BYTES for byte in raw):
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return True


def _authority_value_is_safe(value: str) -> bool:
    """Validate one Host field value as a conservative authority."""
    if type(value) is not str:
        return False
    authority = value.strip(" \t")
    if not authority or not authority.isascii():
        return False

    # Reject authority forms that can be interpreted as userinfo, URI syntax,
    # path/query/fragment data, or internal whitespace by intermediaries.
    if any(char in authority for char in "@/\\?#"):
        return False
    if any(char in authority for char in " \t\r\n"):
        return False
    if "://" in authority:
        return False

    if authority.startswith("["):
        closing = authority.find("]")
        if closing <= 1 or authority.find("]", closing + 1) != -1:
            return False
        literal = authority[1:closing]
        if "%" in literal:
            return False
        try:
            ipaddress.IPv6Address(literal)
        except ValueError:
            return False

        suffix = authority[closing + 1 :]
        if not suffix:
            return True
        if not suffix.startswith(":"):
            return False
        return _port_is_safe(suffix[1:])

    if "[" in authority or "]" in authority:
        return False
    if authority.count(":") > 1:
        # IPv6 literals must be bracketed in Host authority form.
        return False

    if ":" in authority:
        host, port = authority.rsplit(":", 1)
        if not _port_is_safe(port):
            return False
    else:
        host = authority

    if not host:
        return False

    try:
        ipaddress.IPv4Address(host)
        return True
    except ValueError:
        pass

    # Numeric dotted spellings that are not valid IPv4 are rejected rather
    # than falling through to reg-name interpretation.
    if "." in host and all(char.isdigit() or char == "." for char in host):
        return False
    return _reg_name_is_safe(host)


def _request_host_authority_is_safe(request_version, headers) -> bool:
    """Validate the required HTTP/1.1 Host authority; leave HTTP/1.0 unchanged."""
    if request_version == "HTTP/1.0":
        return True
    if request_version != "HTTP/1.1":
        return False

    get_all = getattr(headers, "get_all", None)
    if not callable(get_all):
        return False
    hosts = get_all("Host", [])
    if len(hosts) != 1:
        return False
    return _authority_value_is_safe(hosts[0])


class HealthServer(HealthServerV166666663):
    """Reject ambiguous HTTP/1.1 Host authorities before endpoint dispatch."""

    def __init__(
        self,
        runtime,
        host: str = "0.0.0.0",
        port: int = 8080,
        *,
        request_timeout_seconds: float = 5.0,
        max_concurrent_requests: int = 32,
        request_header_deadline_seconds: float = 5.0,
        max_request_header_bytes: int = 32768,
        max_request_line_bytes: int = 8192,
        max_request_header_fields: int = 32,
    ):
        super().__init__(
            runtime,
            host,
            port,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            request_header_deadline_seconds=request_header_deadline_seconds,
            max_request_header_bytes=max_request_header_bytes,
            max_request_line_bytes=max_request_line_bytes,
            max_request_header_fields=max_request_header_fields,
        )
        base_handler = self.httpd.RequestHandlerClass

        class Handler(base_handler):
            def parse_request(self):
                parsed = super().parse_request()
                if not parsed:
                    return False
                if _request_host_authority_is_safe(
                    self.request_version, self.headers
                ):
                    return True

                # The singleton Host gate already established field cardinality.
                # This final authority gate removes URI/userinfo/whitespace,
                # malformed literal and invalid-port ambiguity before dispatch.
                self.close_connection = True
                self.send_error(400)
                return False

        self.httpd.RequestHandlerClass = Handler


__all__ = [
    "HealthServer",
    "_REG_NAME_BYTES",
    "_authority_value_is_safe",
    "_port_is_safe",
    "_reg_name_is_safe",
    "_request_host_authority_is_safe",
]
