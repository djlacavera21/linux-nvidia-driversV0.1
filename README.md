# Linux NVIDIA Drivers v0.4

`nvlx` is a Linux-first NVIDIA driver control plane for official GPU support classification, transactional driver upgrades, distro-aware deployment, open-kernel-module builds, Secure Boot, rollback, hybrid graphics, multi-GPU topology, MIG/Fabric Manager compatibility, CUDA/container checks, and health telemetry.

> [!IMPORTANT]
> This project does not redistribute NVIDIA proprietary user-space components. It orchestrates and validates NVIDIA's official Linux driver/open-kernel-module ecosystem.

## v0.4 highlights

- **Transactional driver upgrades.** `nvlx install` captures NVIDIA/CUDA package versions and a per-kernel NVIDIA module snapshot before installation, then arms a post-reboot transaction.
- **Boot health validation.** `nvlx boot-validate` checks the target driver version, `nvidia-smi`, and the loaded kernel module after a reboot boundary.
- **Automatic rollback guard.** `nvlx boot-guard-install --yes` installs a systemd oneshot that validates a pending transaction after boot and attempts package/module rollback when validation fails.
- **Package-state snapshots.** APT, RPM/DNF, pacman, and NixOS package/declarative state are inventoried. Exact automatic rollback is supported where the native package manager can request the captured version; Arch rollback reports when cached package archives are required.
- **Wayland / GBM diagnostics.** Reports session type, compositor hints, `nvidia_drm` modeset/fbdev state, DRM nodes, GBM, NVIDIA EGL-Wayland libraries, Xwayland, and actionable warnings.
- **Multi-GPU topology.** Parses `nvidia-smi topo -m`, GPU inventory, NVLink adjacency evidence, and NVSwitch evidence.
- **MIG / Fabric Manager / DCGM.** Reports MIG mode and instances, Fabric Manager service/version alignment, and R610 DCGM compatibility. For the pinned 610.57.04 baseline, Fabric Manager should match the driver release and DCGM should be 4.3.x or newer.
- **Prometheus + JSON health telemetry.** `nvlx telemetry` exposes overall health, GPU count, driver/module status, topology, NVLink/NVSwitch evidence, MIG instance count, Fabric Manager, and DCGM compatibility.
- **Expanded sanitized support bundles.** `nvlx report` now includes runtime health, Wayland/GBM, topology, MIG/Fabric Manager, signing, compatibility, and pending transaction state.

## Current NVIDIA baseline

The configured baseline is **610.57.04**. NVIDIA's R610 release notes pair driver 610.57.04 with Fabric Manager 610.57.04 and require DCGM 4.3.x or newer. The version remains centralized in `config/driver-series.toml`.

## Main commands

```bash
# host / support
nvlx detect
nvlx doctor
nvlx plan
nvlx gpu-db-sync
nvlx gpu-support

# distro / repositories / DKMS
nvlx distro-plan
nvlx repo-plan
nvlx dkms-status

# graphics/session topology
nvlx prime
nvlx session
nvlx topology
nvlx mig-fabric

# health / telemetry
nvlx health
nvlx telemetry --format json
nvlx telemetry --format prometheus

# transactional source build/install
nvlx fetch
nvlx build --source ./vendor/open-gpu-kernel-modules
sudo nvlx install --source ./vendor/open-gpu-kernel-modules --yes
nvlx transaction-pending
sudo nvlx boot-guard-install --yes
sudo nvlx boot-validate --auto-rollback

# package and initramfs state
nvlx package-state
nvlx initramfs-plan
sudo nvlx initramfs-regenerate --yes

# Secure Boot
nvlx secureboot-plan
sudo nvlx secureboot-keygen --key-dir /root/nvlx-mok --yes
sudo nvlx secureboot-sign --source ./vendor/open-gpu-kernel-modules --key /root/nvlx-mok/MOK.key --cert /root/nvlx-mok/MOK.der --yes
nvlx secureboot-verify

# explicit module rollback
sudo nvlx rollback-snapshot
nvlx rollback-list
sudo nvlx rollback-apply /var/lib/nvlx/rollback/<snapshot-id> --yes

# CUDA / Container Toolkit
nvlx compat

# sanitized support bundle
nvlx report ./nvlx-report
```

## Transaction lifecycle

```text
PREPARE
  capture package state
  snapshot installed NVIDIA kernel modules
        |
        v
INSTALL
  modules_install + depmod
        |
        v
ARM
  write /var/lib/nvlx/transactions/pending.json
        |
        v
REBOOT
        |
        v
VALIDATE
  nvidia module loaded?
  nvidia-smi enumerates GPUs?
  driver == target release?
        |
        +---- healthy ---> mark validated
        |
        +---- failure ---> package restore + module restore + initramfs rebuild
```

The boot guard is opt-in because enabling a systemd recovery action is a persistent host mutation. Once installed, it only runs when a pending transaction marker exists.

## Wayland / GBM model

NVIDIA's Wayland/GBM path requires DRM KMS plus the relevant GBM/EGL libraries. `nvlx session` therefore checks the active session and the NVIDIA DRM modeset parameter rather than treating the presence of `WAYLAND_DISPLAY` as proof of a correct GPU stack.

## Safety invariants

1. NVIDIA support claims come from a pinned official upstream support table.
2. Kernel module, user-space driver, GSP firmware, and Fabric Manager versions remain release-aligned where applicable.
3. Direct install requires root and explicit `--yes`.
4. Direct install cannot begin without recoverable module and package state capture.
5. A transaction is not considered healthy until it crosses a reboot boundary and passes post-boot validation.
6. Secure Boot is never disabled automatically and MOK enrollment remains explicit.
7. Active graphics modules are never hot-unloaded automatically.
8. Automatic package rollback is attempted only through supported native mechanisms; unsupported exact rollback paths fail visibly rather than guessing.
9. Automated NVIDIA release discovery opens PRs for review; it does not auto-merge driver updates.
10. Diagnostic bundles are sanitized but must still be reviewed before external sharing.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## License

Project-authored orchestration code is MIT licensed. NVIDIA source, firmware, user-space components, trademarks, and redistributable packages remain subject to their respective NVIDIA licenses.
