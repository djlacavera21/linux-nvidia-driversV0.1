"""Partial typed-provider symmetry closure for nvlx 1.6.6.6."""
from __future__ import annotations

from .http_v1664 import HealthServer as HealthServerV1664


class _MetricsReadinessBridge:
    """Expose metrics-owned readiness when no dedicated readiness provider exists."""

    def __init__(self, runtime):
        self._runtime = runtime

    def __getattr__(self, name):
        return getattr(self._runtime, name)

    def readiness_diagnosis(self):
        diagnosis = self._runtime.metrics_diagnosis()
        return diagnosis.readiness

    def metrics_diagnosis(self):
        return self._runtime.metrics_diagnosis()


def _complete_partial_typed_provider(runtime):
    has_readiness = callable(getattr(runtime, "readiness_diagnosis", None))
    has_metrics = callable(getattr(runtime, "metrics_diagnosis", None))
    if has_metrics and not has_readiness:
        return _MetricsReadinessBridge(runtime)
    return runtime


class HealthServer(HealthServerV1664):
    """Close metrics-only typed-provider readiness fallback asymmetry."""

    def __init__(self, runtime, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(_complete_partial_typed_provider(runtime), host, port)
        self.source_runtime = runtime


__all__ = ["HealthServer"]
