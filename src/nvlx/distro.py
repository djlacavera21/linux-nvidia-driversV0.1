"""Distribution adapters for NVIDIA open-driver prerequisites and packaging plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import platform

from .system import read_os_release, running_kernel


@dataclass(frozen=True)
class DistroPlan:
    adapter: str
    distribution_id: str
    version_id: str
    package_manager: str
    nvidia_validated: bool
    prerequisites: tuple[str, ...]
    open_driver: tuple[str, ...]
    dkms: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _family(os_release: dict[str, str]) -> str:
    distro = os_release.get("ID", "").lower()
    likes = set(os_release.get("ID_LIKE", "").lower().split())
    if distro in {"ubuntu", "debian"} or likes & {"ubuntu", "debian"}:
        return "apt"
    if distro in {"fedora", "rhel"} or likes & {"fedora", "rhel", "centos"}:
        return "dnf"
    if distro in {"arch", "manjaro"} or "arch" in likes:
        return "pacman"
    if distro == "nixos" or "nixos" in likes:
        return "nixos"
    return "unknown"


def build_distro_plan(os_release: dict[str, str] | None = None) -> DistroPlan:
    os_release = os_release or read_os_release()
    distro = os_release.get("ID", "unknown").lower()
    version = os_release.get("VERSION_ID", "unknown")
    kernel = running_kernel()
    arch = platform.machine()
    family = _family(os_release)

    if family == "apt":
        validated = (distro == "ubuntu" and version in {"22.04", "24.04", "26.04"}) or (
            distro == "debian" and version in {"12", "13"}
        )
        dkms_pkg = "nvidia-dkms-open" if distro == "ubuntu" else "nvidia-kernel-open-dkms"
        return DistroPlan(
            adapter=distro if distro in {"ubuntu", "debian"} else "debian-compatible",
            distribution_id=distro,
            version_id=version,
            package_manager="apt",
            nvidia_validated=validated,
            prerequisites=(
                "sudo apt update",
                f"sudo apt install -y build-essential dkms linux-headers-{kernel} mokutil openssl",
            ),
            open_driver=("sudo apt install -y nvidia-open",),
            dkms=(f"sudo apt install -y {dkms_pkg}",),
            notes=(
                "NVIDIA recommends distribution package managers for driver installation.",
                "Branch 590+ Ubuntu/Debian packaging uses unversioned package names plus optional pinning packages.",
            ),
        )

    if family == "dnf":
        validated = (distro == "fedora" and version == "44") or (distro == "rhel" and version.split(".")[0] in {"8", "9", "10"})
        module_cmd = ()
        if distro == "rhel" and version.split(".")[0] in {"8", "9"}:
            module_cmd = ("sudo dnf module enable -y nvidia-driver:open-dkms",)
        return DistroPlan(
            adapter=distro if distro in {"fedora", "rhel"} else "rhel-compatible",
            distribution_id=distro,
            version_id=version,
            package_manager="dnf",
            nvidia_validated=validated,
            prerequisites=(
                f"sudo dnf install -y gcc gcc-c++ make dkms kernel-devel-{kernel} kernel-headers mokutil openssl",
            ),
            open_driver=module_cmd + ("sudo dnf install -y nvidia-open",),
            dkms=module_cmd + ("sudo dnf install -y kmod-nvidia-open-dkms",),
            notes=(
                "RHEL 8/9 uses NVIDIA's open-dkms module stream; RHEL 10 and Fedora use the unversioned nvidia-open package convention.",
                "Precompiled RHEL streams can simplify Secure Boot but are intentionally separate from this source-build path.",
            ),
        )

    if family == "pacman":
        return DistroPlan(
            adapter="arch",
            distribution_id=distro,
            version_id=version,
            package_manager="pacman",
            nvidia_validated=False,
            prerequisites=("sudo pacman -S --needed base-devel dkms linux-headers mokutil openssl",),
            open_driver=("sudo pacman -S --needed nvidia-open nvidia-utils",),
            dkms=("sudo pacman -S --needed nvidia-open-dkms nvidia-utils",),
            notes=(
                "Arch is supported by this adapter but is not in NVIDIA's current validated distribution matrix.",
                "Replace linux-headers with the headers package matching a non-default Arch kernel when needed.",
            ),
        )

    if family == "nixos":
        snippet = """{ config, ... }: {
  nixpkgs.config.allowUnfree = true;
  hardware.graphics.enable = true;
  services.xserver.videoDrivers = [ \"nvidia\" ];
  hardware.nvidia.open = true;
  hardware.nvidia.modesetting.enable = true;
  hardware.nvidia.package = config.boot.kernelPackages.nvidiaPackages.stable;
}"""
        return DistroPlan(
            adapter="nixos",
            distribution_id=distro,
            version_id=version,
            package_manager="nix",
            nvidia_validated=False,
            prerequisites=("nix-shell -p git gnumake gcc openssl mokutil",),
            open_driver=(snippet, "sudo nixos-rebuild test", "sudo nixos-rebuild switch"),
            dkms=("NixOS manages kernel-specific NVIDIA modules declaratively; do not layer a conventional DKMS install over the NixOS module.",),
            notes=(
                "NixOS 26.05 documents services.xserver.videoDrivers and the official NixOS NVIDIA wiki documents hardware.nvidia.open for 560+.",
                f"Detected architecture: {arch}.",
            ),
        )

    return DistroPlan(
        adapter="unknown",
        distribution_id=distro,
        version_id=version,
        package_manager="unknown",
        nvidia_validated=False,
        prerequisites=(),
        open_driver=(),
        dkms=(),
        notes=("No safe distribution adapter matched /etc/os-release; use the upstream source build path or add an adapter.",),
    )
