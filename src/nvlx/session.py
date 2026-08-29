"""Wayland/GBM/NVIDIA graphics-session diagnostics."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import os, shutil, subprocess

@dataclass(frozen=True)
class SessionReport:
    session_type:str
    wayland_display:str|None
    compositor:str|None
    nvidia_drm_modeset:str|None
    nvidia_drm_fbdev:str|None
    gbm_library:bool
    egl_wayland_library:bool
    xwayland:bool
    drm_devices:tuple[str,...]
    warnings:tuple[str,...]
    def to_dict(self): return asdict(self)

def _param(name:str)->str|None:
    path=Path("/sys/module/nvidia_drm/parameters")/name
    try: return path.read_text(encoding="utf-8").strip()
    except OSError: return None

def _ldconfig_has(fragment:str)->bool:
    exe=shutil.which("ldconfig")
    if not exe: return False
    try: out=subprocess.run([exe,"-p"],capture_output=True,text=True,timeout=5,check=False).stdout
    except OSError: return False
    return fragment in out

def _compositor()->str|None:
    desktop=os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")
    if desktop: return desktop
    return None

def session_report()->SessionReport:
    session=os.environ.get("XDG_SESSION_TYPE","unknown").lower(); modeset=_param("modeset"); fbdev=_param("fbdev")
    gbm=_ldconfig_has("libgbm.so.1"); egl=_ldconfig_has("libnvidia-egl-wayland.so") or _ldconfig_has("libEGL_nvidia.so")
    xwayland=bool(shutil.which("Xwayland")); drm=tuple(sorted(str(p) for p in Path("/dev/dri").glob("*"))) if Path("/dev/dri").exists() else ()
    warnings=[]
    if session=="wayland" and modeset not in {"Y","1","y"}: warnings.append("Wayland is active but nvidia_drm modeset is not reported enabled")
    if session=="wayland" and not gbm: warnings.append("libgbm.so.1 was not found; NVIDIA GBM Wayland support requires GBM")
    if session=="wayland" and not egl: warnings.append("NVIDIA EGL/Wayland libraries were not detected")
    if session=="wayland" and not drm: warnings.append("no DRM devices found under /dev/dri")
    return SessionReport(session,os.environ.get("WAYLAND_DISPLAY"),_compositor(),modeset,fbdev,gbm,egl,xwayland,drm,tuple(warnings))
