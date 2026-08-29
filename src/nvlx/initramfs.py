"""Distribution-aware initramfs regeneration planning and execution."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import os, shutil, subprocess
from .build import BuildError
from .system import read_os_release, running_kernel

@dataclass(frozen=True)
class InitramfsPlan:
    tool: str | None
    command: tuple[str, ...]
    supported: bool
    note: str
    def to_dict(self): return asdict(self)

def initramfs_plan(kernel: str | None = None, os_release: dict[str,str] | None = None) -> InitramfsPlan:
    kernel = kernel or running_kernel(); os_release = os_release or read_os_release(); distro=os_release.get('ID','').lower(); likes=set(os_release.get('ID_LIKE','').lower().split())
    if distro in {'ubuntu','debian'} or likes & {'ubuntu','debian'}:
        return InitramfsPlan(shutil.which('update-initramfs'), ('update-initramfs','-u','-k',kernel), True, 'Debian-family initramfs update')
    if distro in {'fedora','rhel'} or likes & {'fedora','rhel','centos'}:
        return InitramfsPlan(shutil.which('dracut'), ('dracut','--force',f'/boot/initramfs-{kernel}.img',kernel), True, 'dracut regeneration for selected kernel')
    if distro in {'arch','manjaro'} or 'arch' in likes:
        if shutil.which('mkinitcpio'):
            return InitramfsPlan(shutil.which('mkinitcpio'), ('mkinitcpio','-P'), True, 'Arch regenerates configured initramfs presets')
    if distro == 'nixos' or 'nixos' in likes:
        return InitramfsPlan(shutil.which('nixos-rebuild'), ('nixos-rebuild','boot'), True, 'NixOS rebuilds boot artifacts declaratively')
    return InitramfsPlan(None, (), False, 'No supported initramfs adapter detected')

def regenerate_initramfs(*, kernel: str | None=None, confirmed: bool=False) -> InitramfsPlan:
    if not confirmed: raise BuildError('initramfs regeneration requires --yes')
    if os.geteuid()!=0: raise BuildError('initramfs regeneration must run as root')
    plan=initramfs_plan(kernel)
    if not plan.supported or not plan.tool: raise BuildError(plan.note)
    command=list(plan.command); command[0]=plan.tool
    subprocess.run(command, check=True)
    return plan
