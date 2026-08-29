"""NVIDIA repository/driver-branch pinning plans."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from .config import DriverConfig
from .system import read_os_release

@dataclass(frozen=True)
class RepositoryPlan:
    family: str
    branch: str
    commands: tuple[str,...]
    notes: tuple[str,...]
    def to_dict(self): return asdict(self)

def driver_branch(version: str) -> str: return version.split('.',1)[0]

def repository_plan(config: DriverConfig, os_release: dict[str,str] | None=None) -> RepositoryPlan:
    os_release=os_release or read_os_release(); distro=os_release.get('ID','').lower(); likes=set(os_release.get('ID_LIKE','').lower().split()); branch=driver_branch(config.version)
    if distro in {'ubuntu','debian'} or likes & {'ubuntu','debian'}:
        return RepositoryPlan('apt',branch,(f'sudo apt install -y nvidia-driver-pinning-{branch}', 'sudo apt update', 'sudo apt install -y nvidia-open'),('Install NVIDIA repository using NVIDIA installation-guide instructions before pinning.','Branch pinning aligns NVIDIA packages and makes controlled downgrades easier.'))
    if distro in {'rhel','fedora'} or likes & {'rhel','fedora','centos'}:
        return RepositoryPlan('dnf',branch,(f'sudo dnf module enable -y nvidia-driver:{branch}-open' if distro=='rhel' and os_release.get('VERSION_ID','').split('.')[0] in {'8','9'} else 'sudo dnf install -y nvidia-open',),('Use the NVIDIA CUDA/driver repository appropriate for the distribution.','Do not mix packages from multiple NVIDIA branches.'))
    if distro in {'arch','manjaro'} or 'arch' in likes:
        return RepositoryPlan('pacman',branch,('sudo pacman -S --needed nvidia-open nvidia-utils',),('Arch follows rolling repository packaging; pin exact package versions through normal Arch tooling if reproducibility is required.',))
    if distro=='nixos' or 'nixos' in likes:
        return RepositoryPlan('nix',branch,('hardware.nvidia.package = config.boot.kernelPackages.nvidiaPackages.stable;',),('NixOS pins through the Nixpkgs revision/package expression rather than NVIDIA apt/dnf repository pinning.',))
    return RepositoryPlan('unknown',branch,(),('No repository pinning adapter detected.',))
