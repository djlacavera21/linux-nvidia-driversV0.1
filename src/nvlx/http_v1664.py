"""Live HTTP typed-diagnosis guard for nvlx 1.6.6.4."""
from __future__ import annotations

from .http_v16 import HealthServer as HealthServerV16


def _strict_bool(diagnosis, name: str) -> bool:
    value = getattr(diagnosis, name)
    if type(value) is not bool:
        raise TypeError(f"diagnosis field {name} must be bool")
    return value


def _validate_effective_leader(diagnosis) -> None:
    api_reachable = _strict_bool(diagnosis, "api_reachable")
    leader = _strict_bool(diagnosis, "leader")
    terminating = _strict_bool(diagnosis, "terminating")
    if leader and (not api_reachable or terminating):
        raise ValueError(
            "effective leadership requires API reachability and non-termination"
        )


class _ProxyBase:
    def __init__(self, runtime):
        self._runtime = runtime

    def __getattr__(self, name):
        return getattr(self._runtime, name)


class _ReadinessProxy(_ProxyBase):
    def readiness_diagnosis(self):
        diagnosis = self._runtime.readiness_diagnosis()
        _validate_effective_leader(diagnosis)
        return diagnosis


class _MetricsProxy(_ProxyBase):
    def metrics_diagnosis(self):
        diagnosis = self._runtime.metrics_diagnosis()
        _validate_effective_leader(diagnosis.readiness)
        return diagnosis


class _BothProxy(_ProxyBase):
    def readiness_diagnosis(self):
        diagnosis = self._runtime.readiness_diagnosis()
        _validate_effective_leader(diagnosis)
        return diagnosis

    def metrics_diagnosis(self):
        diagnosis = self._runtime.metrics_diagnosis()
        _validate_effective_leader(diagnosis.readiness)
        return diagnosis


def _guard_runtime(runtime):
    has_readiness = callable(getattr(runtime, "readiness_diagnosis", None))
    has_metrics = callable(getattr(runtime, "metrics_diagnosis", None))
    if has_readiness and has_metrics:
        return _BothProxy(runtime)
    if has_readiness:
        return _ReadinessProxy(runtime)
    if has_metrics:
        return _MetricsProxy(runtime)
    return runtime


class HealthServer(HealthServerV16):
    """Use the established HTTP transport with v1.6.6.4 typed guards."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        self.source_runtime = runtime
        super().__init__(_guard_runtime(runtime), host, port)


__all__ = ["HealthServer"]
