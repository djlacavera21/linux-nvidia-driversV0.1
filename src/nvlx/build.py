"""Source acquisition, validation, build, and guarded installation."""
from __future__ import annotations
from pathlib import Path
import os, re, shutil, subprocess
from .config import DriverConfig
from .system import kernel_build_path, nvidia_smi_driver_version
_VERSION_RE=re.compile(r"^\s*NVIDIA_VERSION\s*[:?+]?=\s*([^\s#]+)",re.MULTILINE)
class BuildError(RuntimeError): pass

def _run(command:list[str],cwd:Path|None=None)->None:
    try: subprocess.run(command,cwd=cwd,check=True)
    except FileNotFoundError as exc: raise BuildError(f'required command not found: {command[0]}') from exc
    except subprocess.CalledProcessError as exc: raise BuildError(f"command failed with exit code {exc.returncode}: {' '.join(command)}") from exc

def source_version(source:Path)->str|None:
    f=source/'version.mk'
    if not f.is_file(): return None
    m=_VERSION_RE.search(f.read_text(encoding='utf-8',errors='replace')); return m.group(1) if m else None

def validate_source(source:Path,config:DriverConfig)->None:
    if not (source/'Makefile').is_file() or not (source/'kernel-open').is_dir(): raise BuildError(f'{source} does not look like NVIDIA open-gpu-kernel-modules source')
    detected=source_version(source)
    if detected and detected!=config.version: raise BuildError(f'source version {detected} does not match configured driver version {config.version}; kernel modules and user-space components must stay release-aligned')

def validate_runtime_alignment(config:DriverConfig)->None:
    existing=nvidia_smi_driver_version()
    if existing and existing!=config.version: raise BuildError(f'installed NVIDIA user-space reports {existing}, but configured kernel-module release is {config.version}; align user-space/GSP components before module installation')

def fetch_source(destination:Path,config:DriverConfig)->None:
    if destination.exists() and any(destination.iterdir()): raise BuildError(f'destination is not empty: {destination}')
    if not shutil.which('git'): raise BuildError('git was not found in PATH')
    destination.parent.mkdir(parents=True,exist_ok=True)
    _run(['git','clone','--depth','1','--branch',config.version,config.upstream_repo,str(destination)]); validate_source(destination,config)

def build_modules(source:Path,config:DriverConfig,jobs:int|None=None)->None:
    validate_source(source,config); headers=kernel_build_path()
    if not headers.exists(): raise BuildError(f'kernel headers/build tree missing: {headers}')
    _run(['make','modules',f'-j{max(1,jobs or (os.cpu_count() or 1))}'],cwd=source)

def install_modules(source:Path,config:DriverConfig,*,confirmed:bool,jobs:int|None=None,rollback_root:Path|None=None)->str:
    if not confirmed: raise BuildError('installation requires --yes')
    if os.geteuid()!=0: raise BuildError('module installation must run as root')
    validate_source(source,config); validate_runtime_alignment(config)
    # Local import avoids a build<->rollback import cycle. A snapshot is a hard
    # precondition: if backup creation fails, installation does not begin.
    from .rollback import create_snapshot
    snapshot=create_snapshot(root=rollback_root)
    _run(['make','modules_install',f'-j{max(1,jobs or (os.cpu_count() or 1))}'],cwd=source)
    if shutil.which('depmod'): _run(['depmod','-a'])
    return snapshot.snapshot_id
