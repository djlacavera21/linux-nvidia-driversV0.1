"""Lease-fresh runtime wrapper for nvlx 1.6.2.1."""
from __future__ import annotations
from dataclasses import dataclass, field
import time
from .runtime_v16 import Runtime as RuntimeV162

@dataclass
class Runtime(RuntimeV162):
    leader_fresh_seconds: float=25.0
    _leader_verified_monotonic: float=field(default=0.0,init=False,repr=False)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.leader_fresh_seconds,bool) or not isinstance(self.leader_fresh_seconds,(int,float)) or self.leader_fresh_seconds <= 0:
            raise ValueError("leader_fresh_seconds must be positive")
        self.leader_fresh_seconds=float(self.leader_fresh_seconds)

    def stop(self):
        super().stop()
        self._leader_verified_monotonic=0.0

    def _leader(self) -> bool:
        ok=super()._leader()
        if ok:
            self._leader_verified_monotonic=time.monotonic()
        else:
            self._leader_verified_monotonic=0.0
        return ok

    def leadership_fresh(self) -> bool:
        if self.stats.terminating or not self.stats.leader or self._leader_verified_monotonic <= 0:
            return False
        age=time.monotonic()-self._leader_verified_monotonic
        if age < 0 or age > self.leader_fresh_seconds:
            self.stats.leader=False
            return False
        return True

    def ready(self) -> bool:
        s=self.stats
        return bool(s.api_reachable and s.inventory_fresh and self.leadership_fresh() and not s.terminating)

    def list_and_watch_once(self) -> str:
        # Refresh Lease state once per relist even when the cluster has zero GPUFleet objects.
        self._leader()
        return super().list_and_watch_once()
