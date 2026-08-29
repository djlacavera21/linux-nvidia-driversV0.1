"""CUDA and NVIDIA Container Toolkit compatibility inspection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import shutil
import subprocess

from .system import nvidia_smi_driver_version

CUDA_MIN_DRIVER = {11: 450, 12: 525, 13: 580}
_CONTAINER_PACKAGES = (
    "nvidia-container-toolkit",
    "nvidia-container-toolkit-base",
    "libnvidia-container-tools",
    "libnvidia-container1",
)


@dataclass(frozen=True)
class CompatibilityReport:
    driver_version: str | None
    cuda_toolkit_version: str | None
    cuda_compatible: bool | None
    cuda_detail: str
    container_toolkit_version: str | None
    container_packages: tuple[tuple[str, str], ...]
    container_packages_aligned: bool | None
    container_detail: str
    docker_available: bool
    podman_available: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _run(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).strip() or None


def detect_cuda_toolkit_version() -> str | None:
    nvcc = shutil.which("nvcc")
    if not nvcc:
        return None
    output = _run([nvcc, "--version"])
    if not output:
        return None
    match = re.search(r"release\s+(\d+\.\d+)", output, re.IGNORECASE)
    return match.group(1) if match else None


def detect_container_toolkit_version() -> str | None:
    nvidia_ctk = shutil.which("nvidia-ctk")
    if not nvidia_ctk:
        return None
    output = _run([nvidia_ctk, "--version"])
    if not output:
        return None
    match = re.search(r"(?:version\s*)?v?(\d+\.\d+(?:\.\d+)?)", output, re.IGNORECASE)
    return match.group(1) if match else None


def _package_versions() -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    if shutil.which("dpkg-query"):
        for package in _CONTAINER_PACKAGES:
            version = _run(["dpkg-query", "-W", "-f=${Version}", package])
            if version:
                rows.append((package, version))
        return tuple(rows)
    if shutil.which("rpm"):
        for package in _CONTAINER_PACKAGES:
            version = _run(["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package])
            if version:
                rows.append((package, version))
        return tuple(rows)
    if shutil.which("pacman"):
        for package in _CONTAINER_PACKAGES:
            output = _run(["pacman", "-Q", package])
            if output and len(output.split()) >= 2:
                rows.append((package, output.split()[1]))
    return tuple(rows)


def _major(version: str | None) -> int | None:
    if not version:
        return None
    match = re.match(r"(\d+)", version)
    return int(match.group(1)) if match else None


def compatibility_report() -> CompatibilityReport:
    driver = nvidia_smi_driver_version()
    cuda = detect_cuda_toolkit_version()
    driver_major = _major(driver)
    cuda_major = _major(cuda)
    cuda_compatible: bool | None = None
    if cuda_major in CUDA_MIN_DRIVER and driver_major is not None:
        minimum = CUDA_MIN_DRIVER[cuda_major]
        cuda_compatible = driver_major >= minimum
        cuda_detail = f"CUDA {cuda_major}.x requires driver >= {minimum} for minor-version compatibility; detected {driver}."
    elif cuda is None:
        cuda_detail = "CUDA Toolkit (nvcc) was not detected."
    elif cuda_major not in CUDA_MIN_DRIVER:
        cuda_detail = f"CUDA {cuda} is outside the encoded CUDA 11/12/13 compatibility table."
    else:
        cuda_detail = "NVIDIA driver version could not be determined with nvidia-smi."

    toolkit = detect_container_toolkit_version()
    packages = _package_versions()
    aligned: bool | None = None
    if packages:
        versions = {version for _, version in packages}
        aligned = len(versions) == 1 and len(packages) == len(_CONTAINER_PACKAGES)
    if toolkit == "1.20.0":
        container_detail = (
            "Container Toolkit 1.20.0 detected. NVIDIA documents a known cuda-compat-mode issue for direct "
            "nvidia-container-cli use and mixed old/new component packages; keep all four packages aligned."
        )
    elif toolkit:
        container_detail = f"NVIDIA Container Toolkit {toolkit} detected."
    else:
        container_detail = "NVIDIA Container Toolkit was not detected."
    if packages and aligned is False:
        container_detail += " Installed NVIDIA container package versions are incomplete or not aligned."

    return CompatibilityReport(
        driver_version=driver,
        cuda_toolkit_version=cuda,
        cuda_compatible=cuda_compatible,
        cuda_detail=cuda_detail,
        container_toolkit_version=toolkit,
        container_packages=packages,
        container_packages_aligned=aligned,
        container_detail=container_detail,
        docker_available=bool(shutil.which("docker")),
        podman_available=bool(shutil.which("podman")),
    )
