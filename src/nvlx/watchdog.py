"""Systemd retry policy for post-upgrade NVIDIA boot validation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import os, shutil, subprocess
from .build import BuildError

@dataclass(frozen=True)
class WatchdogPolicy:
    retries:int=3
    restart_sec:int=20
    timeout_sec:int=90
    start_limit_sec:int=300
    def to_dict(self): return asdict(self)

def render_service(policy:WatchdogPolicy)->str:
    return f"""[Unit]\nDescription=Validate pending NVIDIA driver transaction\nAfter=multi-user.target\nConditionPathExists=/var/lib/nvlx/transactions/pending.json\nStartLimitIntervalSec={policy.start_limit_sec}\nStartLimitBurst={policy.retries}\n\n[Service]\nType=oneshot\nTimeoutStartSec={policy.timeout_sec}\nExecStart=/usr/bin/env nvlx boot-validate --auto-rollback\nRestart=on-failure\nRestartSec={policy.restart_sec}\n\n[Install]\nWantedBy=multi-user.target\n"""

def install_watchdog(policy:WatchdogPolicy|None=None,*,confirmed:bool)->Path:
    if not confirmed: raise BuildError("watchdog installation requires --yes")
    if os.geteuid()!=0: raise BuildError("watchdog installation must run as root")
    systemctl=shutil.which("systemctl")
    if not systemctl: raise BuildError("systemd/systemctl is required")
    p=policy or WatchdogPolicy(); unit=Path("/etc/systemd/system/nvlx-boot-guard.service")
    unit.write_text(render_service(p),encoding="utf-8")
    subprocess.run([systemctl,"daemon-reload"],check=True)
    subprocess.run([systemctl,"enable","nvlx-boot-guard.service"],check=True)
    return unit
