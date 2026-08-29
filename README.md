# Linux NVIDIA Drivers v0.3

`nvlx` is a Linux-first NVIDIA driver control plane for official GPU support classification, distro-aware deployment planning, open-kernel-module builds, Secure Boot signing, rollback, PRIME/hybrid graphics, CUDA/container compatibility, and diagnostics.

> [!IMPORTANT]
> This project does not redistribute NVIDIA proprietary user-space components. It orchestrates and validates NVIDIA's official Linux driver/open-kernel-module ecosystem.

## v0.3 highlights

- **Automatic pre-install rollback snapshots.** `nvlx install` snapshots the currently installed NVIDIA kernel modules before `modules_install`; installation aborts if the snapshot cannot be created.
- **Initramfs adapters.** Plans and explicit regeneration for Ubuntu/Debian (`update-initramfs`), Fedora/RHEL (`dracut`), Arch (`mkinitcpio`), and NixOS (`nixos-rebuild boot`).
- **NVIDIA repository/branch pinning.** Generates distro-aware plans and uses NVIDIA branch-pinning packages on APT systems where applicable.
- **PRIME / hybrid-laptop detection.** Detects integrated-display + NVIDIA topologies, inspects XRandR providers when available, and reports NVIDIA PRIME render-offload environment variables.
- **Signed-module verification.** Reports `modinfo` signer, signature ID, hash algorithm, module path, and Secure Boot state for installed NVIDIA modules.
- **Sanitized `nvlx report` bundles.** Collects host, distro, PRIME, signing, and compatibility state while redacting common secret assignments and home-directory usernames. Always review a bundle before sharing it.
- **Automatic NVIDIA release-update PRs.** A weekly GitHub Actions workflow checks numeric tags in NVIDIA/open-gpu-kernel-modules, validates a newer candidate, runs tests, and opens a reviewable baseline-bump PR. It never auto-merges a driver update.

## Current NVIDIA baseline

The configured baseline is **610.57.04**. The version is centralized in `config/driver-series.toml`. Kernel modules, NVIDIA user-space libraries, GSP firmware, and related branch packages must remain aligned.

## Main commands

```bash
# host / support
nvlx detect
nvlx doctor
nvlx plan
nvlx gpu-db-sync
nvlx gpu-support

# distro / repository / DKMS
nvlx distro-plan
nvlx repo-plan
nvlx dkms-status

# hybrid graphics
nvlx prime

# build and guarded install
nvlx fetch
nvlx build --source ./vendor/open-gpu-kernel-modules
sudo nvlx install --source ./vendor/open-gpu-kernel-modules --yes

# initramfs
nvlx initramfs-plan
sudo nvlx initramfs-regenerate --yes

# Secure Boot
nvlx secureboot-plan
sudo nvlx secureboot-keygen --key-dir /root/nvlx-mok --yes
sudo nvlx secureboot-sign --source ./vendor/open-gpu-kernel-modules --key /root/nvlx-mok/MOK.key --cert /root/nvlx-mok/MOK.der --yes
nvlx secureboot-verify

# rollback
sudo nvlx rollback-snapshot
nvlx rollback-list
sudo nvlx rollback-apply /var/lib/nvlx/rollback/<snapshot-id> --yes

# CUDA / NVIDIA Container Toolkit
nvlx compat

# sanitized support bundle
nvlx report ./nvlx-report
```

## PRIME behavior

On a muxless hybrid system, nvlx does **not** attempt to force the NVIDIA GPU to own the internal panel. It reports the integrated GPU as the likely display sink and NVIDIA as the render-offload source. For common PRIME render offload:

```bash
__NV_PRIME_RENDER_OFFLOAD=1 application
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia glx-application
```

## Safety invariants

1. NVIDIA support claims come from the pinned official upstream support table.
2. Kernel module and user-space driver versions stay release-aligned.
3. Direct install requires root and explicit `--yes`.
4. Direct install creates a rollback snapshot before module replacement.
5. Secure Boot is never disabled automatically and MOK enrollment remains explicit.
6. Initramfs regeneration is explicit and distro-specific.
7. Active graphics modules are never hot-unloaded automatically.
8. Automated NVIDIA release discovery opens PRs for review; it does not merge them.
9. Diagnostic bundles are sanitized but must still be reviewed before external sharing.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## License

Project-authored orchestration code is MIT licensed. NVIDIA source, firmware, user-space components, trademarks, and redistributable packages remain subject to their respective NVIDIA licenses.
