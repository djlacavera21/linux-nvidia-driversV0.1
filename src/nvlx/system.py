"""Linux host inspection helpers used by nvlx."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import platform
import shutil
import subprocess

NVIDIA_VENDOR_ID = "0x10de"


@dataclass(frozen=True)
class NvidiaDevice:
    address: str
    vendor_id: str
    device_id: str
    class_code: str
    subsystem_vendor_id: str = ""
    subsystem_device_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return default


def detect_nvidia_devices(sysfs_root: Path = Path("/sys/bus/pci/devices")) -> list[NvidiaDevice]:
    """Return NVIDIA PCI functions discovered through sysfs."""
    devices: list[NvidiaDevice] = []
    if not sysfs_root.exists():
        return devices

    for entry in sorted(sysfs_root.iterdir()):
        vendor = _read_text(entry / "vendor").lower()
        if vendor != NVIDIA_VENDOR_ID:
            continue
        devices.append(
            NvidiaDevice(
                address=entry.name,
                vendor_id=vendor,
                device_id=_read_text(entry / "device").lower(),
                class_code=_read_text(entry / "class").lower(),
                subsystem_vendor_id=_read_text(entry / "subsystem_vendor").lower(),
                subsystem_device_id=_read_text(entry / "subsystem_device").lower(),
            )
        )
    return devices


def running_kernel() -> str:
    return platform.release()


def kernel_build_path(kernel: str | None = None) -> Path:
    return Path("/lib/modules") / (kernel or running_kernel()) / "build"


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in _read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value.strip().strip('"').strip("'")
    return data


def secure_boot_enabled(efivar_root: Path = Path("/sys/firmware/efi/efivars")) -> bool | None:
    """Return Secure Boot state when EFI exposes it, otherwise None."""
    try:
        candidates = list(efivar_root.glob("SecureBoot-*"))
    except OSError:
        return None
    if not candidates:
        return None
    try:
        raw = candidates[0].read_bytes()
    except OSError:
        return None
    return bool(raw and raw[-1] == 1)


def loaded_modules(path: Path = Path("/proc/modules")) -> set[str]:
    modules: set[str] = set()
    for line in _read_text(path).splitlines():
        fields = line.split()
        if fields:
            modules.add(fields[0])
    return modules


def find_compiler() -> str | None:
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


def find_make() -> str | None:
    return shutil.which("make")


def nvidia_smi_driver_version() -> str | None:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "--query-gpu=driver_version", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    versions = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return ",".join(sorted(versions)) or None


def host_snapshot(sysfs_root: Path = Path("/sys/bus/pci/devices")) -> dict[str, object]:
    os_release = read_os_release()
    modules = loaded_modules()
    return {
        "kernel": running_kernel(),
        "distribution": os_release.get("PRETTY_NAME") or os_release.get("NAME") or "unknown",
        "distribution_id": os_release.get("ID", "unknown"),
        "distribution_version": os_release.get("VERSION_ID", "unknown"),
        "architecture": platform.machine(),
        "secure_boot": secure_boot_enabled(),
        "nvidia_devices": [device.to_dict() for device in detect_nvidia_devices(sysfs_root)],
        "loaded_nvidia_modules": sorted(m for m in modules if m.startswith("nvidia")),
        "nouveau_loaded": "nouveau" in modules,
        "nvidia_smi_driver_version": nvidia_smi_driver_version(),
    }
