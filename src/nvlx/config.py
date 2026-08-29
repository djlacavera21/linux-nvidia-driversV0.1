"""Configuration loading for the pinned NVIDIA driver baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib


@dataclass(frozen=True)
class DriverConfig:
    version: str
    upstream_repo: str
    minimum_kernel: str
    architectures: tuple[str, ...]
    open_module_gpu_floor: str


DEFAULT = DriverConfig(
    version="610.57.04",
    upstream_repo="https://github.com/NVIDIA/open-gpu-kernel-modules.git",
    minimum_kernel="4.15",
    architectures=("x86_64", "aarch64"),
    open_module_gpu_floor="Turing or newer",
)


def load_driver_config(path: Path | None = None) -> DriverConfig:
    candidates: list[Path] = []
    if path is not None:
        candidates.append(path)
    env_path = os.environ.get("NVLX_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.cwd() / "config" / "driver-series.toml")

    selected = next((candidate for candidate in candidates if candidate.is_file()), None)
    if selected is None:
        return DEFAULT

    with selected.open("rb") as handle:
        raw = tomllib.load(handle)
    driver = raw.get("driver", {})
    return DriverConfig(
        version=str(driver.get("version", DEFAULT.version)),
        upstream_repo=str(driver.get("upstream_repo", DEFAULT.upstream_repo)),
        minimum_kernel=str(driver.get("minimum_kernel", DEFAULT.minimum_kernel)),
        architectures=tuple(driver.get("architectures", DEFAULT.architectures)),
        open_module_gpu_floor=str(driver.get("open_module_gpu_floor", DEFAULT.open_module_gpu_floor)),
    )
