"""Stable v1 fleet configuration contract."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json

SCHEMA_VERSION = 1
_ALLOWED = {"schema_version","cluster","policy","controller","execution"}

@dataclass(frozen=True)
class ConfigReport:
    valid: bool
    fingerprint: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    config: dict
    def to_dict(self): return asdict(self)

def canonical_bytes(config: dict) -> bytes:
    return json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def fingerprint(config: dict) -> str:
    return hashlib.sha256(canonical_bytes(config)).hexdigest()

def validate(config: dict) -> ConfigReport:
    errors=[]; warnings=[]
    unknown=sorted(set(config)-_ALLOWED)
    if unknown: errors.append("unknown top-level keys: " + ", ".join(unknown))
    if config.get("schema_version") != SCHEMA_VERSION: errors.append("schema_version must be 1")
    cluster=config.get("cluster", {})
    if not isinstance(cluster, dict) or not cluster.get("name"): errors.append("cluster.name is required")
    policy=config.get("policy", {})
    if not isinstance(policy, dict): errors.append("policy must be an object")
    controller=config.get("controller", {})
    if controller and not isinstance(controller, dict): errors.append("controller must be an object")
    execution=config.get("execution", {})
    if execution and not isinstance(execution, dict): errors.append("execution must be an object")
    mode=(execution or {}).get("mode", "plan") if isinstance(execution, dict) else "plan"
    if mode not in {"plan","approved"}: errors.append("execution.mode must be plan or approved")
    if mode=="approved" and not (execution or {}).get("require_approval", True): warnings.append("approved mode without require_approval weakens the v1 safety model")
    return ConfigReport(not errors, fingerprint(config), tuple(errors), tuple(warnings), config)
