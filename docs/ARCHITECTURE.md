# Architecture

## Mission

`nvlx` provides a small, auditable control plane around NVIDIA's Linux driver deployment path. It does not attempt to recreate the proprietary user-space stack or silently replace a running graphics driver. The project focuses on detection, compatibility checks, reproducible open-kernel-module builds, guarded installation, packaging, and diagnostics.

## Trust boundaries

### Upstream NVIDIA source

The open GPU kernel modules are fetched from NVIDIA's official `open-gpu-kernel-modules` repository at the release pinned by this project. v0.1 validates `version.mk` before a build or install. This protects against accidentally compiling one kernel-module release while using a different configured user-space driver release.

### Host kernel

The running kernel owns the ABI and build environment used for the module interface layer. v0.1 requires `/lib/modules/<kernel>/build` and a compiler/toolchain to exist before building.

### User-space driver and GSP firmware

The open kernel modules are only one layer of the NVIDIA Linux driver. Matching user-space components and GSP firmware remain an explicit external requirement. v0.1 detects an existing `nvidia-smi` version when possible but does not download or replace proprietary user-space libraries.

## Components

```text
src/nvlx/system.py
    sysfs PCI detection
    kernel and distro snapshot
    Secure Boot state
    loaded module state
    nvidia-smi discovery

src/nvlx/doctor.py
    preflight checks
    build readiness
    conflict warnings

src/nvlx/config.py
    pinned driver release
    supported build architectures
    upstream repository

src/nvlx/build.py
    upstream source fetch
    source version validation
    module build
    guarded modules_install

src/nvlx/cli.py
    command surface
    human-readable planning
    JSON detection output
```

## Command lifecycle

### `nvlx detect`

Read-only. Produces a machine-readable host snapshot suitable for bug reports, automation, or future front ends.

### `nvlx doctor`

Read-only. Validates build prerequisites and reports environmental risks. A failed compiler or kernel-header check returns a non-zero status.

### `nvlx plan`

Read-only. Combines pinned release policy with the live host state. It intentionally does not infer GPU-generation support from a guessed PCI-ID range; the roadmap calls for consuming NVIDIA's official supported-GPU metadata.

### `nvlx fetch`

Clones the exact configured release tag from the official NVIDIA open-kernel-module repository and validates its source version.

### `nvlx build`

Builds `modules` from a validated source tree. It does not install them.

### `nvlx install`

Requires root and `--yes`, validates the source again, runs `modules_install`, and updates module dependency metadata. It does **not** unload Nouveau, stop a display manager, unload an active NVIDIA stack, modify an initramfs, enroll signing keys, or reboot the system automatically.

## Version-alignment invariant

The central rule is:

```text
open kernel module release == NVIDIA user-space release == required GSP firmware release
```

Any future package manager integration must preserve this invariant rather than treating the kernel module as an independently upgradeable component.

## v0.2 targets

1. Import NVIDIA's supported-GPU metadata and classify detected PCI IDs.
2. Add distro adapters for Ubuntu/Debian, Fedora/RHEL, openSUSE/SLES, Arch, NixOS, and immutable/container-host variants.
3. Add DKMS package generation and precompiled-kernel-module strategies where appropriate.
4. Add Secure Boot signing workflow generation without auto-enrolling keys.
5. Add explicit kernel/user-space runtime mismatch detection.
6. Add initramfs and bootloader integration as opt-in, distro-specific actions.
7. Add a rollback manifest recording files/modules changed by an installation.
8. Add `nvlx report` for sanitized diagnostics bundles.
9. Add NVIDIA Container Toolkit and CUDA compatibility checks as separate layers.
10. Add release automation that opens a version-bump PR when NVIDIA publishes a new stable open-module release.

## Non-goals for v0.1

- reimplementing CUDA;
- redistributing NVIDIA proprietary libraries;
- automatically bypassing Secure Boot;
- silently blacklisting Nouveau;
- hot-swapping the active display driver;
- patching around NVIDIA feature or product restrictions;
- claiming support for a GPU without upstream evidence.
