"""Rollback snapshots for installed NVIDIA kernel modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import shutil
import subprocess

from .build import BuildError
from .system import running_kernel


@dataclass(frozen=True)
class RollbackSnapshot:
    snapshot_id: str
    kernel: str
    created_at: str
    root: str
    files: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def default_rollback_root() -> Path:
    return Path("/var/lib/nvlx/rollback")


def _module_root(kernel: str) -> Path:
    return Path("/lib/modules") / kernel


def _nvidia_module_files(kernel: str) -> list[Path]:
    root = _module_root(kernel)
    patterns = ("nvidia*.ko", "nvidia*.ko.xz", "nvidia*.ko.zst", "nvidia*.ko.gz")
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(files)


def create_snapshot(root: Path | None = None, kernel: str | None = None) -> RollbackSnapshot:
    if os.geteuid() != 0:
        raise BuildError("rollback snapshots must run as root")
    kernel = kernel or running_kernel()
    storage = root or default_rollback_root()
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = storage / snapshot_id
    module_root = _module_root(kernel)
    files = _nvidia_module_files(kernel)
    destination.mkdir(parents=True, exist_ok=False)
    relative_files: list[str] = []
    for source in files:
        relative = source.relative_to(module_root)
        target = destination / "modules" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        relative_files.append(str(relative))
    snapshot = RollbackSnapshot(
        snapshot_id=snapshot_id,
        kernel=kernel,
        created_at=datetime.now(timezone.utc).isoformat(),
        root=str(destination),
        files=tuple(relative_files),
    )
    (destination / "manifest.json").write_text(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def list_snapshots(root: Path | None = None) -> list[RollbackSnapshot]:
    storage = root or default_rollback_root()
    if not storage.is_dir():
        return []
    snapshots: list[RollbackSnapshot] = []
    for manifest in sorted(storage.glob("*/manifest.json"), reverse=True):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["files"] = tuple(payload.get("files", ()))
            snapshots.append(RollbackSnapshot(**payload))
        except (OSError, ValueError, TypeError):
            continue
    return snapshots


def apply_snapshot(snapshot_dir: Path, *, confirmed: bool) -> RollbackSnapshot:
    if not confirmed:
        raise BuildError("rollback requires --yes")
    if os.geteuid() != 0:
        raise BuildError("rollback must run as root")
    manifest = snapshot_dir / "manifest.json"
    if not manifest.is_file():
        raise BuildError(f"rollback manifest not found: {manifest}")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["files"] = tuple(payload.get("files", ()))
    snapshot = RollbackSnapshot(**payload)
    module_root = _module_root(snapshot.kernel)

    # Remove only NVIDIA kernel-module files before restoring the known snapshot.
    # The caller must reboot or perform a controlled module transition afterward.
    for current in _nvidia_module_files(snapshot.kernel):
        current.unlink()
    for relative in snapshot.files:
        backup = snapshot_dir / "modules" / relative
        target = module_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
    depmod = shutil.which("depmod")
    if depmod:
        subprocess.run([depmod, "-a", snapshot.kernel], check=True)
    return snapshot
