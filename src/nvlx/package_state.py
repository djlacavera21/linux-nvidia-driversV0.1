"""Snapshot and restore NVIDIA/CUDA package state for transactional upgrades."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import json, shutil, subprocess
from .build import BuildError
from .system import read_os_release

PREFIXES=("nvidia","libnvidia","cuda","xserver-xorg-video-nvidia")

@dataclass(frozen=True)
class PackageRecord:
    name:str
    version:str

@dataclass(frozen=True)
class PackageSnapshot:
    manager:str
    distribution_id:str
    packages:tuple[PackageRecord,...]
    def to_dict(self): return {"manager":self.manager,"distribution_id":self.distribution_id,"packages":[asdict(x) for x in self.packages]}

def _run_output(command:list[str])->str:
    try: return subprocess.run(command,check=True,capture_output=True,text=True,timeout=30).stdout
    except (FileNotFoundError,subprocess.SubprocessError) as exc: raise BuildError(f"package inventory failed: {command[0]}") from exc

def _relevant(name:str)->bool:
    lower=name.lower(); return lower.startswith(PREFIXES) or "fabricmanager" in lower or lower.startswith("dcgm") or lower.startswith("datacenter-gpu-manager")

def capture_package_state()->PackageSnapshot:
    distro=read_os_release().get("ID","unknown").lower(); rows:list[PackageRecord]=[]; manager="unknown"
    if shutil.which("dpkg-query"):
        manager="apt"
        for line in _run_output(["dpkg-query","-W","-f=${binary:Package}\t${Version}\n"]).splitlines():
            if "\t" in line:
                name,version=line.split("\t",1)
                if _relevant(name): rows.append(PackageRecord(name,version))
    elif shutil.which("rpm"):
        manager="dnf"
        for line in _run_output(["rpm","-qa","--qf","%{NAME}\t%{EVR}\n"]).splitlines():
            if "\t" in line:
                name,version=line.split("\t",1)
                if _relevant(name): rows.append(PackageRecord(name,version))
    elif shutil.which("pacman"):
        manager="pacman"
        for line in _run_output(["pacman","-Q"]).splitlines():
            parts=line.split(maxsplit=1)
            if len(parts)==2 and _relevant(parts[0]): rows.append(PackageRecord(*parts))
    elif distro=="nixos":
        manager="nixos"
        current=Path("/run/current-system")
        if current.exists(): rows.append(PackageRecord("nixos-system",str(current.resolve())))
    return PackageSnapshot(manager,distro,tuple(sorted(rows,key=lambda x:x.name)))

def write_package_snapshot(path:Path)->PackageSnapshot:
    snap=capture_package_state(); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(snap.to_dict(),indent=2,sort_keys=True)+"\n",encoding="utf-8"); return snap

def load_package_snapshot(path:Path)->PackageSnapshot:
    raw=json.loads(path.read_text(encoding="utf-8")); return PackageSnapshot(raw["manager"],raw["distribution_id"],tuple(PackageRecord(**r) for r in raw.get("packages",[])))

def restore_commands(snapshot:PackageSnapshot)->list[list[str]]:
    if snapshot.manager=="apt": return [["apt-get","install","-y",*(f"{p.name}={p.version}" for p in snapshot.packages)]] if snapshot.packages else []
    if snapshot.manager=="dnf": return [["dnf","install","-y",*(f"{p.name}-{p.version}" for p in snapshot.packages)]] if snapshot.packages else []
    if snapshot.manager=="pacman": return []
    if snapshot.manager=="nixos": return [["nixos-rebuild","--rollback","boot"]]
    return []

def restore_package_state(snapshot:PackageSnapshot)->None:
    commands=restore_commands(snapshot)
    if snapshot.manager=="pacman" and snapshot.packages:
        raise BuildError("automatic pacman rollback needs cached package archives; restore package state manually from /var/cache/pacman/pkg")
    if snapshot.packages and not commands: raise BuildError(f"no automatic package rollback strategy for {snapshot.manager}")
    for command in commands: subprocess.run(command,check=True)
