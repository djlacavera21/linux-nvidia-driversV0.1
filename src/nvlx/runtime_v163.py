"""Live NVIDIA inventory-gated runtime for nvlx 1.6.3."""
from __future__ import annotations

from .nvidia_inventory_v163 import NvidiaInventoryError, NvidiaPreflight
from .runtime_v1629 import Runtime as RuntimeV1629


class Runtime(RuntimeV1629):
    """Require a fresh, read-only NVIDIA preflight before GPUFleet continuity."""

    def __post_init__(self):
        super().__post_init__()
        self.nvidia_inventory_check = None
        self.nvidia_preflight_ok = True  # compatibility until a provider is attached
        self.nvidia_preflight_mode = "unchecked"
        self.nvidia_preflight_reasons: tuple[str, ...] = ()
        self.nvidia_preflight_failures = 0
        self.nvidia_snapshot = None

    def ready(self) -> bool:
        return bool(self.nvidia_preflight_ok and super().ready())

    def _record_preflight(self, result: NvidiaPreflight) -> None:
        self.nvidia_preflight_ok = bool(result.ready)
        self.nvidia_preflight_mode = result.mode
        self.nvidia_preflight_reasons = tuple(result.reasons)
        self.nvidia_snapshot = result.snapshot
        if not result.ready:
            self.nvidia_preflight_failures += 1
            self._invalidate_inventory()

    def list_and_watch_once(self) -> str:
        checker = self.nvidia_inventory_check
        if checker is not None:
            self.nvidia_preflight_ok = False
            self.nvidia_preflight_mode = "checking"
            self.nvidia_preflight_reasons = ()
            try:
                result = checker()
            except NvidiaInventoryError as exc:
                self.nvidia_preflight_failures += 1
                self.nvidia_preflight_mode = "error"
                self.nvidia_preflight_reasons = (str(exc),)
                self._invalidate_inventory()
                return "reconnect"
            except Exception:
                self.nvidia_preflight_failures += 1
                self.nvidia_preflight_mode = "error"
                self.nvidia_preflight_reasons = ("unexpected NVIDIA inventory failure",)
                self._invalidate_inventory()
                return "reconnect"
            if not isinstance(result, NvidiaPreflight):
                self.nvidia_preflight_failures += 1
                self.nvidia_preflight_mode = "error"
                self.nvidia_preflight_reasons = ("NVIDIA inventory provider returned invalid result",)
                self._invalidate_inventory()
                return "reconnect"
            self._record_preflight(result)
            if not result.ready:
                return "relist"
        return super().list_and_watch_once()
