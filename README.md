# Linux NVIDIA Drivers v0.2

A Linux-first toolkit for detecting NVIDIA GPUs, classifying PCI devices against NVIDIA's official supported-GPU table, planning distro-native driver deployment, building and signing NVIDIA's open GPU kernel modules, preserving rollback points, and validating CUDA/container compatibility.

> [!IMPORTANT]
> This repository is **not** a redistribution of NVIDIA's proprietary user-space driver stack. It is an orchestration, validation, build, signing, rollback, and packaging layer designed to work with NVIDIA's official Linux driver releases and open GPU kernel modules.

## v0.2 capabilities

- Detect NVIDIA PCI devices directly from Linux sysfs, including subsystem IDs.
- Sync the **official NVIDIA Compatible GPUs table** from the pinned upstream release and classify hardware by PCI ID.
- Distinguish exact subsystem matches from generic device-ID matches.
- Provide adapters for Ubuntu, Debian, Fedora, RHEL, Arch Linux, and NixOS.
- Mark NVIDIA-validated distro/version combinations separately from community adapters.
- Inspect distro-native NVIDIA DKMS state instead of generating an unofficial DKMS recipe.
- Generate a local Secure Boot Machine Owner Key, print the enrollment step, and sign built `.ko` modules with the kernel `sign-file` helper.
- Snapshot installed NVIDIA kernel modules and explicitly restore a snapshot for rollback.
- Check CUDA 11/12/13 minor-version driver compatibility.
- Detect NVIDIA Container Toolkit, inspect its component package versions, and flag misalignment / known 1.20.0 compatibility-mode concerns.
- Preserve the v0.1 pinned-source fetch/build/install workflow and release-alignment guardrails.

## Current upstream baseline

The configured baseline is NVIDIA open GPU kernel modules **610.57.04**. NVIDIA documents the open modules for Turing-or-newer GPUs, x86_64 and aarch64, and Linux 4.15+. The kernel modules must remain release-aligned with the corresponding NVIDIA user-space components and GSP firmware.

The version is centralized in `config/driver-series.toml`.

## CLI

### Inspect and build

```bash
nvlx detect
nvlx doctor
nvlx plan
nvlx fetch
nvlx build --source ./vendor/open-gpu-kernel-modules
```

### Official GPU support classification

```bash
nvlx gpu-db-sync
nvlx gpu-support
```

`gpu-db-sync` downloads only the pinned NVIDIA upstream README and stores the parsed official support table under `~/.cache/nvlx/` by default. `gpu-support` performs local PCI matching against that cached table.

### Distribution and DKMS planning

```bash
nvlx distro-plan
nvlx dkms-status
```

The distro plan is advisory JSON. It does not silently add repositories, install packages, or rewrite NixOS configuration.

### Secure Boot

```bash
nvlx secureboot-plan
sudo nvlx secureboot-keygen --key-dir /root/nvlx-mok --yes
sudo mokutil --import /root/nvlx-mok/MOK.der
# reboot and enroll the key in the firmware MOK interface
sudo nvlx secureboot-sign \
  --source ./vendor/open-gpu-kernel-modules \
  --key /root/nvlx-mok/MOK.key \
  --cert /root/nvlx-mok/MOK.der \
  --yes
```

The private key is generated mode `0600`; existing key material is never overwritten.

### Rollback

```bash
sudo nvlx rollback-snapshot
nvlx rollback-list
sudo nvlx rollback-apply /var/lib/nvlx/rollback/<snapshot-id> --yes
```

Rollback operates on NVIDIA kernel-module files for one kernel release and runs `depmod` after restoration. It does **not** hot-unload an active graphics stack; reboot or use a controlled maintenance transition afterward.

### CUDA / Container Toolkit compatibility

```bash
nvlx compat
```

For CUDA minor-version compatibility, the tool currently encodes NVIDIA's documented family floors:

| CUDA family | Minimum NVIDIA driver |
| --- | ---: |
| 11.x | 450 |
| 12.x | 525 |
| 13.x | 580 |

The compatibility command also detects `nvidia-ctk`, Docker/Podman, and installed NVIDIA container package versions where the native package database is available.

### Guarded module install

```bash
sudo nvlx install --source ./vendor/open-gpu-kernel-modules --yes
```

Installation still refuses a known mixed NVIDIA kernel/user-space release and does not automatically unload Nouveau or active NVIDIA display modules.

## Distribution adapter model

| Adapter | Strategy |
| --- | --- |
| Ubuntu | APT + `nvidia-open` / `nvidia-dkms-open` |
| Debian | APT + `nvidia-open` / `nvidia-kernel-open-dkms` |
| Fedora | DNF + `nvidia-open` / open DKMS packages |
| RHEL | NVIDIA open-DKMS stream where applicable + `nvidia-open` |
| Arch | pacman + `nvidia-open` or `nvidia-open-dkms` |
| NixOS | declarative `hardware.nvidia.open = true` configuration |

Arch and NixOS are intentionally identified as community adapters rather than falsely labeled as NVIDIA-validated platforms.

## Safety model

Kernel-driver installation can make a graphical Linux host temporarily unusable if modules, firmware, user-space libraries, Secure Boot trust, or kernel ABI expectations do not match. nvlx therefore follows these rules:

1. inspect before changing;
2. classify hardware from a pinned official NVIDIA source;
3. keep kernel, GSP, and user-space NVIDIA release versions aligned;
4. prefer distribution-native package/DKMS mechanisms where documented;
5. never disable Secure Boot automatically;
6. never overwrite signing keys automatically;
7. create explicit rollback points rather than treating module replacement as irreversible;
8. require acknowledgement for signing, installation, and rollback mutations.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

See `docs/ARCHITECTURE.md` for implementation boundaries and future work.

## License

Project-authored orchestration code is MIT licensed. NVIDIA source, firmware, user-space components, trademarks, and redistributable packages remain subject to their respective NVIDIA licenses.
