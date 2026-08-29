"""Controller field ownership boundaries for GPUFleet reconciliation."""
from __future__ import annotations

OWNED_STATUS_FIELDS=("phase","observedGeneration","canaryWave","conditions")
OWNED_METADATA=("finalizers",)

def may_mutate(path: str) -> bool:
    p=path.strip(".")
    return any(p==f"status.{x}" or p.startswith(f"status.{x}.") for x in OWNED_STATUS_FIELDS) or p=="metadata.finalizers"

def validate(paths: list[str]|tuple[str,...]) -> tuple[bool,tuple[str,...]]:
    denied=tuple(p for p in paths if not may_mutate(p))
    return not denied,denied
