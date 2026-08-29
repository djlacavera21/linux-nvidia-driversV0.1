"""DKMS state inspection and integration helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import shutil
import subprocess

from .distro import DistroPlan


@dataclass(frozen=True)
class DkmsState:
    available: bool
    nvidia_entries: tuple[str, ...]
    all_entries: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def dkms_state() -> DkmsState:
    executable = shutil.which("dkms")
    if not executable:
        return DkmsState(False, (), ())
    try:
        result = subprocess.run([executable, "status"], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return DkmsState(True, (), ())
    entries = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
    nvidia = tuple(line for line in entries if "nvidia" in line.lower())
    return DkmsState(True, nvidia, entries)


def dkms_install_plan(plan: DistroPlan) -> tuple[str, ...]:
    """Return the distro-native DKMS plan.

    nvlx intentionally uses distribution NVIDIA DKMS packages instead of
    synthesizing an unofficial dkms.conf for NVIDIA's source snapshot.
    """
    return plan.dkms
