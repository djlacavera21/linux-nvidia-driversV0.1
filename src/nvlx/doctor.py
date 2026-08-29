"""Preflight diagnostics for building and installing NVIDIA kernel modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .system import (
    detect_nvidia_devices,
    find_compiler,
    find_make,
    kernel_build_path,
    loaded_modules,
    nvidia_smi_driver_version,
    running_kernel,
    secure_boot_enabled,
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def run_doctor() -> list[Check]:
    checks: list[Check] = []
    kernel = running_kernel()
    devices = detect_nvidia_devices()

    checks.append(
        Check(
            "nvidia-pci",
            "pass" if devices else "warn",
            f"detected {len(devices)} NVIDIA PCI function(s)" if devices else "no NVIDIA PCI functions detected",
        )
    )

    headers = kernel_build_path(kernel)
    checks.append(
        Check(
            "kernel-headers",
            "pass" if headers.exists() else "fail",
            f"kernel build tree: {headers}" if headers.exists() else f"missing kernel build tree: {headers}",
        )
    )

    make = find_make()
    checks.append(Check("make", "pass" if make else "fail", make or "make was not found in PATH"))

    compiler = find_compiler()
    checks.append(Check("compiler", "pass" if compiler else "fail", compiler or "no C compiler found in PATH"))

    secure_boot = secure_boot_enabled()
    if secure_boot is True:
        checks.append(
            Check(
                "secure-boot",
                "warn",
                "Secure Boot is enabled; locally built modules may require signing and key enrollment",
            )
        )
    elif secure_boot is False:
        checks.append(Check("secure-boot", "pass", "Secure Boot is disabled"))
    else:
        checks.append(Check("secure-boot", "info", "Secure Boot state is not exposed by EFI sysfs"))

    modules = loaded_modules()
    if "nouveau" in modules:
        checks.append(
            Check(
                "nouveau",
                "warn",
                "nouveau is loaded; do not replace the active graphics stack without leaving the graphical session",
            )
        )
    else:
        checks.append(Check("nouveau", "pass", "nouveau is not currently loaded"))

    nvidia_modules = sorted(module for module in modules if module.startswith("nvidia"))
    checks.append(
        Check(
            "loaded-nvidia-modules",
            "info",
            ", ".join(nvidia_modules) if nvidia_modules else "no NVIDIA kernel modules currently loaded",
        )
    )

    userspace_version = nvidia_smi_driver_version()
    checks.append(
        Check(
            "nvidia-smi",
            "info" if userspace_version else "warn",
            f"reported driver version(s): {userspace_version}" if userspace_version else "nvidia-smi unavailable or unable to query the driver",
        )
    )

    return checks


def has_failures(checks: list[Check]) -> bool:
    return any(check.status == "fail" for check in checks)
