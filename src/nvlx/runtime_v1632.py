"""NVIDIA snapshot continuity-gated runtime for nvlx 1.6.3.2."""
from __future__ import annotations

from .nvidia_continuity_v1632 import SnapshotIdentity, changed_sections, snapshot_identity
from .nvidia_inventory_v163 import NvidiaInventoryError, NvidiaPreflight
from .runtime_v163 import Runtime as RuntimeV163


class Runtime(RuntimeV163):
    def __post_init__(self):
        super().__post_init__()
        self.nvidia_identity_baseline: SnapshotIdentity | None = None
        self.nvidia_identity_candidate: SnapshotIdentity | None = None
        self.nvidia_continuity_changes: tuple[str, ...] = ()
        self.nvidia_continuity_fences = 0
        self.nvidia_continuity_promotions = 0

    def _continuity_accepts(self, result: NvidiaPreflight) -> bool:
        identity = snapshot_identity(result.snapshot)
        baseline = self.nvidia_identity_baseline
        candidate = self.nvidia_identity_candidate
        if baseline is None:
            self.nvidia_identity_baseline = identity
            self.nvidia_identity_candidate = None
            self.nvidia_continuity_changes = ()
            return True
        if identity == baseline:
            self.nvidia_identity_candidate = None
            self.nvidia_continuity_changes = ()
            return True
        changes = changed_sections(baseline, identity)
        if candidate is not None and identity == candidate:
            self.nvidia_identity_baseline = identity
            self.nvidia_identity_candidate = None
            self.nvidia_continuity_changes = ()
            self.nvidia_continuity_promotions += 1
            return True
        self.nvidia_identity_candidate = identity
        self.nvidia_continuity_changes = changes
        self.nvidia_continuity_fences += 1
        self.nvidia_preflight_ok = False
        self.nvidia_preflight_mode = "continuity-fenced"
        self.nvidia_preflight_reasons = ("NVIDIA snapshot identity changed; identical confirmation required",) + tuple(
            f"changed:{name}" for name in changes
        )
        self._invalidate_inventory()
        return False

    def list_and_watch_once(self) -> str:
        checker = self.nvidia_inventory_check
        if checker is None:
            return super().list_and_watch_once()
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
        try:
            if not self._continuity_accepts(result):
                return "relist"
        except NvidiaInventoryError as exc:
            self.nvidia_preflight_failures += 1
            self.nvidia_preflight_ok = False
            self.nvidia_preflight_mode = "continuity-error"
            self.nvidia_preflight_reasons = (str(exc),)
            self._invalidate_inventory()
            return "reconnect"
        checker_saved = self.nvidia_inventory_check
        self.nvidia_inventory_check = None
        try:
            return super().list_and_watch_once()
        finally:
            self.nvidia_inventory_check = checker_saved
