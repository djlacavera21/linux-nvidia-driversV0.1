"""Sanitized nvlx diagnostic bundles."""
from __future__ import annotations
from datetime import datetime, timezone
import json, re
from pathlib import Path
from .compat import compatibility_report
from .dcgm_telemetry import exporter_state, reliability_rows
from .distro import build_distro_plan
from .health import health_report
from .immutable import immutable_plan
from .mig import mig_fabric_report
from .nvsdm import nvsdm_report
from .prime import prime_report
from .rollback_preflight import check_rollback_availability
from .secureboot import secure_boot_plan, verify_installed_modules
from .session import session_report
from .system import host_snapshot
from .topology import topology_report
from .transaction import load_pending

_SECRET=re.compile(r"(?i)(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+")
_HOME=re.compile(r"/home/[^/\s]+")

def sanitize_text(value:str)->str:
    value=_SECRET.sub(lambda m:m.group(1)+"=<redacted>",value)
    return _HOME.sub("/home/<user>",value)

def _sanitize(value):
    if isinstance(value,str): return sanitize_text(value)
    if isinstance(value,dict): return {k:_sanitize(v) for k,v in value.items() if k.lower() not in {"serial","uuid","machine_id","machine-id"}}
    if isinstance(value,list): return [_sanitize(v) for v in value]
    if isinstance(value,tuple): return tuple(_sanitize(v) for v in value)
    return value

def build_report()->dict[str,object]:
    pending=load_pending(); exporter=exporter_state()
    payload={
        "schema":3,
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "host":host_snapshot(),
        "health":health_report(require_expected_version=False).to_dict(),
        "distro":build_distro_plan().to_dict(),
        "immutable":immutable_plan().to_dict(),
        "prime":prime_report().to_dict(),
        "session":session_report().to_dict(),
        "topology":topology_report().to_dict(),
        "mig_fabric":mig_fabric_report().to_dict(),
        "gpu_reliability":[v.to_dict() for v in reliability_rows()],
        "dcgm_exporter":exporter.to_dict(),
        "nvsdm":nvsdm_report().to_dict(),
        "rollback_preflight":check_rollback_availability().to_dict(),
        "secure_boot":secure_boot_plan().to_dict(),
        "module_signatures":[v.to_dict() for v in verify_installed_modules()],
        "compatibility":compatibility_report().to_dict(),
        "pending_transaction":pending.to_dict() if pending else None,
    }
    return _sanitize(payload)

def write_report_bundle(destination:Path)->Path:
    destination.mkdir(parents=True,exist_ok=False)
    (destination/"report.json").write_text(json.dumps(build_report(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (destination/"README.txt").write_text("Sanitized nvlx diagnostic report. Review before sharing; topology, package, and site-specific configuration can still be identifying.\n",encoding="utf-8")
    return destination
