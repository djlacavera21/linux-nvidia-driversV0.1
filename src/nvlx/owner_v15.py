"""Controller field ownership boundaries for GPUFleet reconciliation."""
from __future__ import annotations

OWNED_STATUS_FIELDS=("phase","observedGeneration","canaryWave","conditions")


def _normalize(path: str) -> str:
    p=(path or "").strip()
    if not p or p.startswith(".") or p.endswith(".") or ".." in p or "[" in p or "]" in p:
        return ""
    return p


def may_mutate(path: str) -> bool:
    p=_normalize(path)
    if not p:
        return False
    if p=="metadata.finalizers":
        return True
    return any(p==f"status.{x}" or p.startswith(f"status.{x}.") for x in OWNED_STATUS_FIELDS)


def validate(paths: list[str]|tuple[str,...]) -> tuple[bool,tuple[str,...]]:
    denied=tuple(p for p in paths if not may_mutate(p))
    return not denied,denied
