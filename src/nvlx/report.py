"""Sanitized nvlx diagnostic bundles."""
from __future__ import annotations
from datetime import datetime, timezone
import json, re
from pathlib import Path
from .compat import compatibility_report
from .distro import build_distro_plan
from .prime import prime_report
from .secureboot import secure_boot_plan, verify_installed_modules
from .system import host_snapshot

_SECRET=re.compile(r'(?i)(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+')
_HOME=re.compile(r'/home/[^/\s]+')

def sanitize_text(value: str) -> str:
    value=_SECRET.sub(lambda m: m.group(1)+'=<redacted>', value)
    return _HOME.sub('/home/<user>', value)

def _sanitize(value):
    if isinstance(value,str): return sanitize_text(value)
    if isinstance(value,dict): return {k:_sanitize(v) for k,v in value.items() if k.lower() not in {'serial','uuid','machine_id'}}
    if isinstance(value,list): return [_sanitize(v) for v in value]
    return value

def build_report() -> dict[str,object]:
    return _sanitize({'schema':1,'generated_at':datetime.now(timezone.utc).isoformat(),'host':host_snapshot(),'distro':build_distro_plan().to_dict(),'prime':prime_report().to_dict(),'secure_boot':secure_boot_plan().to_dict(),'module_signatures':[v.to_dict() for v in verify_installed_modules()],'compatibility':compatibility_report().to_dict()})

def write_report_bundle(destination: Path) -> Path:
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'report.json').write_text(json.dumps(build_report(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (destination/'README.txt').write_text('Sanitized nvlx diagnostic report. Review before sharing; site-specific configuration may still be identifying.\n',encoding='utf-8')
    return destination
