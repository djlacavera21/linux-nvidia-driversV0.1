"""Source acquisition, validation, build, and guarded transactional installation."""
from __future__ import annotations
from pathlib import Path
import os, re, shutil, subprocess
from .config import DriverConfig
from .system import kernel_build_path, nvidia_smi_driver_version

_VERSION_RE=re.compile(r"^\s*NVIDIA_VERSION\s*[:?+]?=\s*([^\s#]+)",re.MULTILINE)

class BuildError(RuntimeError):
    pass

def _run(command:list[str],cwd:Path|None=None)->None:
    try:
        subprocess.run(command,cwd=cwd,check=True)
    except FileNotFoundError as exc:
        raise BuildError(f"required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise BuildError(f"command failed with exit code {exc.returncode}: {' '.join(command)}") from exc

def source_version(source:Path)->str|None:
    version_file=source/"version.mk"
    if not version_file.is_file(): return None
    match=_VERSION_RE.search(version_file.read_text(encoding="utf-8",errors="replace"))
    return match.group(1) if match else None

def validate_source(source:Path,config:DriverConfig)->None:
    if not (source/"Makefile").is_file() or not (source/"kernel-open").is_dir():
        raise BuildError(f"{source} does not look like NVIDIA open-gpu-kernel-modules source")
    detected=source_version(source)
    if detected and detected!=config.version:
        raise BuildError(f"source version {detected} does not match configured driver version {config.version}; kernel modules and user-space components must stay release-aligned")

def validate_runtime_alignment(config:DriverConfig)->None:
    existing=nvidia_smi_driver_version()
    if existing and existing!=config.version:
        raise BuildError(f"installed NVIDIA user-space reports {existing}, but configured kernel-module release is {config.version}; align user-space/GSP components before module installation")

def fetch_source(destination:Path,config:DriverConfig)->None:
    if destination.exists() and any(destination.iterdir()): raise BuildError(f"destination is not empty: {destination}")
    if not shutil.which("git"): raise BuildError("git was not found in PATH")
    destination.parent.mkdir(parents=True,exist_ok=True)
    _run(["git","clone","--depth","1","--branch",config.version,config.upstream_repo,str(destination)])
    validate_source(destination,config)

def build_modules(source:Path,config:DriverConfig,jobs:int|None=None)->None:
    validate_source(source,config)
    headers=kernel_build_path()
    if not headers.exists(): raise BuildError(f"kernel headers/build tree missing: {headers}")
    _run(["make","modules",f"-j{max(1,jobs or (os.cpu_count() or 1))}"],cwd=source)

def install_modules(source:Path,config:DriverConfig,*,confirmed:bool,jobs:int|None=None,rollback_root:Path|None=None,transaction_root:Path|None=None)->str:
    """Install modules only after creating a complete recoverable transaction.

    The transaction captures installed NVIDIA/CUDA package state and a kernel-module
    rollback snapshot before modules_install begins. After installation it is armed
    for post-reboot validation by `nvlx boot-validate` or the optional systemd guard.
    """
    if not confirmed: raise BuildError("installation requires --yes")
    if os.geteuid()!=0: raise BuildError("module installation must run as root")
    validate_source(source,config)
    validate_runtime_alignment(config)
    from .transaction import arm_transaction, begin_transaction
    tx=begin_transaction(config,rollback_root=rollback_root,root=transaction_root)
    try:
        _run(["make","modules_install",f"-j{max(1,jobs or (os.cpu_count() or 1))}"],cwd=source)
        if shutil.which("depmod"): _run(["depmod","-a"])
    except Exception:
        # Installation did not finish; leave the prepared transaction on disk for
        # operator recovery, but do not arm it as a reboot validation transaction.
        raise
    armed=arm_transaction(tx,root=transaction_root)
    return armed.transaction_id
