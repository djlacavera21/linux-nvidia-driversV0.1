"""Verify that package rollback artifacts are actually available before upgrade."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import shutil, subprocess
from .package_state import PackageSnapshot, capture_package_state

@dataclass(frozen=True)
class RollbackPreflight:
    manager:str
    available:bool
    checked:int
    missing:tuple[str,...]
    notes:tuple[str,...]
    def to_dict(self): return asdict(self)

def _out(cmd:list[str])->str:
    try: return subprocess.run(cmd,capture_output=True,text=True,timeout=20,check=False).stdout
    except OSError: return ""

def check_rollback_availability(snapshot:PackageSnapshot|None=None)->RollbackPreflight:
    snap=snapshot or capture_package_state(); missing:list[str]=[]; notes:list[str]=[]
    if not snap.packages: return RollbackPreflight(snap.manager,True,0,(),("no relevant packages installed",))
    if snap.manager=="apt":
        for p in snap.packages:
            text=_out(["apt-cache","policy",p.name]) if shutil.which("apt-cache") else ""
            if p.version not in text: missing.append(f"{p.name}={p.version}")
    elif snap.manager=="dnf":
        tool=shutil.which("dnf")
        for p in snap.packages:
            text=_out([tool,"repoquery","--show-duplicates","--qf","%{name}-%{evr}",p.name]) if tool else ""
            if p.version not in text: missing.append(f"{p.name}-{p.version}")
    elif snap.manager=="pacman":
        cache=Path("/var/cache/pacman/pkg")
        for p in snap.packages:
            if not any(cache.glob(f"{p.name}-{p.version}-*.pkg.tar.*")): missing.append(f"{p.name}={p.version}")
    elif snap.manager=="nixos":
        for p in snap.packages:
            if p.name=="nixos-system" and not Path(p.version).exists(): missing.append(p.version)
    else:
        missing.extend(f"{p.name}={p.version}" for p in snap.packages); notes.append("no deterministic rollback availability probe for this package manager")
    if missing: notes.append("upgrade should not begin until every recorded rollback version is locally or repository-available")
    return RollbackPreflight(snap.manager,not missing,len(snap.packages),tuple(missing),tuple(notes))
