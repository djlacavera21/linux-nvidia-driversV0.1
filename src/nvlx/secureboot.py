"""Secure Boot key generation, enrollment planning, and kernel-module signing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import shutil
import subprocess

from .build import BuildError
from .system import kernel_build_path, running_kernel, secure_boot_enabled


@dataclass(frozen=True)
class SecureBootPlan:
    enabled: bool | None
    sign_file: str | None
    mokutil: str | None
    openssl: str | None
    enrollment_required: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def sign_file_path(kernel: str | None = None) -> Path | None:
    candidate = kernel_build_path(kernel) / "scripts" / "sign-file"
    return candidate if candidate.is_file() else None


def secure_boot_plan() -> SecureBootPlan:
    sign_file = sign_file_path()
    return SecureBootPlan(
        enabled=secure_boot_enabled(),
        sign_file=str(sign_file) if sign_file else None,
        mokutil=shutil.which("mokutil"),
        openssl=shutil.which("openssl"),
        enrollment_required=bool(secure_boot_enabled()),
    )


def generate_mok(key_dir: Path, common_name: str, *, confirmed: bool) -> tuple[Path, Path]:
    if not confirmed:
        raise BuildError("MOK generation requires --yes")
    openssl = shutil.which("openssl")
    if not openssl:
        raise BuildError("openssl was not found in PATH")
    key_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_key = key_dir / "MOK.key"
    certificate = key_dir / "MOK.der"
    if private_key.exists() or certificate.exists():
        raise BuildError(f"refusing to overwrite existing MOK material in {key_dir}")
    command = [
        openssl,
        "req",
        "-new",
        "-x509",
        "-newkey",
        "rsa:3072",
        "-keyout",
        str(private_key),
        "-outform",
        "DER",
        "-out",
        str(certificate),
        "-nodes",
        "-days",
        "3650",
        "-subj",
        f"/CN={common_name}/",
    ]
    subprocess.run(command, check=True)
    os.chmod(private_key, 0o600)
    os.chmod(certificate, 0o644)
    return private_key, certificate


def enroll_command(certificate: Path) -> str:
    return f"sudo mokutil --import {certificate}"


def find_built_modules(source: Path) -> list[Path]:
    return sorted(path for path in source.rglob("*.ko") if path.is_file())


def sign_modules(source: Path, private_key: Path, certificate: Path, *, confirmed: bool, kernel: str | None = None) -> int:
    if not confirmed:
        raise BuildError("module signing requires --yes")
    if os.geteuid() != 0:
        raise BuildError("module signing must run as root")
    signer = sign_file_path(kernel)
    if not signer:
        raise BuildError(f"kernel sign-file helper not found for {kernel or running_kernel()}")
    if not private_key.is_file() or not certificate.is_file():
        raise BuildError("MOK private key or certificate is missing")
    modules = find_built_modules(source)
    if not modules:
        raise BuildError(f"no built .ko modules found under {source}")
    for module in modules:
        subprocess.run([str(signer), "sha256", str(private_key), str(certificate), str(module)], check=True)
    return len(modules)
