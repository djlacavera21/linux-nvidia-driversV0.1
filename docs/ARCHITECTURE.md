# Architecture

## Mission

`nvlx` provides a small, auditable control plane around NVIDIA's Linux driver deployment path. It does not recreate the proprietary user-space stack or silently replace a running graphics driver. The project focuses on hardware classification, compatibility checks, reproducible open-kernel-module builds, distro-native packaging/DKMS guidance, Secure Boot signing, rollback, and diagnostics.

## Trust boundaries

### Official NVIDIA GPU metadata

`gpu-db-sync` retrieves the `README.md` from the exact NVIDIA `open-gpu-kernel-modules` tag pinned by `config/driver-series.toml`. Only the `Compatible GPUs` table is parsed. PCI classification prefers a three-field device/subsystem match over a generic device-ID match. An ID absent from that pinned table is reported as `unknown`, not automatically declared unsupported.

### Upstream NVIDIA source

The open GPU kernel modules are fetched from NVIDIA's official repository at the release pinned by this project. `version.mk` is validated before build or install, protecting against compiling one kernel-module release while configuring another.

### Host kernel

The running kernel owns the ABI and build environment used for the module interface layer. Source builds require `/lib/modules/<kernel>/build` and a compatible compiler/toolchain.

### User-space driver and GSP firmware

The open kernel modules are one layer of the NVIDIA Linux driver. Matching user-space components and GSP firmware remain external requirements. nvlx detects an existing `nvidia-smi` version and refuses a known kernel/user-space release mismatch during guarded installation.

### Distribution package managers

Ubuntu, Debian, Fedora, RHEL, Arch, and NixOS adapters return explicit plans rather than mutating package repositories or host configuration. NVIDIA-validated distro/version combinations are marked separately from community-supported adapters. DKMS integration uses distro-native NVIDIA packages rather than generating an unofficial `dkms.conf` for the source snapshot.

### Secure Boot key material

nvlx can generate a local RSA Machine Owner Key pair and sign built `.ko` files through the kernel's `scripts/sign-file`. Private keys are created mode `0600`, existing key material is never overwritten, and firmware enrollment remains an explicit `mokutil` + reboot operation.

### Rollback storage

Rollback snapshots live under `/var/lib/nvlx/rollback` by default and preserve NVIDIA kernel module files relative to one `/lib/modules/<kernel>` tree. Restoration requires root and `--yes`, runs `depmod`, and intentionally does not hot-unload the active graphics stack.

## Components

```text
src/nvlx/system.py
    sysfs PCI + subsystem detection
    kernel and distro snapshot
    Secure Boot state
    loaded module state
    nvidia-smi discovery

src/nvlx/gpu_db.py
    pinned official NVIDIA support-table retrieval
    Markdown parsing
    exact/generic PCI classification

src/nvlx/distro.py
    Ubuntu/Debian adapters
    Fedora/RHEL adapters
    Arch and NixOS community adapters
    package/DKMS plans

src/nvlx/dkms.py
    DKMS status inspection
    distro-native NVIDIA DKMS integration boundary

src/nvlx/secureboot.py
    MOK key generation
    enrollment command generation
    built-module signing

src/nvlx/rollback.py
    installed-module snapshots
    manifest discovery
    explicit restore + depmod

src/nvlx/compat.py
    NVIDIA driver discovery
    CUDA family compatibility
    NVIDIA Container Toolkit/component alignment
    Docker/Podman presence

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
    JSON automation output
```

## Command lifecycle

### Read-only inspection

`detect`, `doctor`, `plan`, `gpu-support`, `distro-plan`, `dkms-status`, `secureboot-plan`, `rollback-list`, and `compat` are read-only against the host. `gpu-db-sync` writes only the selected cache file.

### Source build

`fetch` clones the exact configured NVIDIA release. `build` compiles it. `secureboot-sign` can then sign the built `.ko` files with an explicitly supplied key/certificate before `install` runs `modules_install`.

### Distribution-native path

`distro-plan` emits package-manager/declarative commands. `dkms-status` inspects the current DKMS state. nvlx does not mix a custom source-DKMS recipe with package-manager owned driver files.

### Rollback path

Before a manual driver transition, `rollback-snapshot` preserves the current NVIDIA modules. `rollback-apply` removes NVIDIA module files for that same kernel tree, restores the snapshot paths, and regenerates dependency metadata. A reboot or controlled module transition is still required.

## Version-alignment invariant

```text
open kernel module release == NVIDIA user-space release == required GSP firmware release
```

Package manager integration, CUDA validation, signing, and rollback must preserve or restore this invariant.

## CUDA compatibility model

nvlx encodes NVIDIA's minor-version compatibility family floors:

```text
CUDA 11.x -> driver >= 450
CUDA 12.x -> driver >= 525
CUDA 13.x -> driver >= 580
```

This is a minimum-driver check, not a claim that every CUDA feature works on every GPU. GPU architecture support remains a separate concern.

## Container Toolkit model

The toolkit layer is deliberately separate from kernel-driver installation. nvlx detects `nvidia-ctk`, checks the four core container package versions where native package metadata is available, and warns on incomplete/mixed component versions. Version-specific known-issue notices are kept in compatibility logic rather than hidden in installer behavior.

## Next targets

1. Add sanitized `nvlx report` diagnostic bundles.
2. Add optional automatic rollback snapshot creation immediately before guarded installation.
3. Add initramfs regeneration adapters with explicit preview/confirmation.
4. Add package-repository validation and branch pinning helpers.
5. Add openSUSE/SLES and immutable/container-host adapters.
6. Add PRIME/hybrid-laptop classification and configuration guidance.
7. Add signed-module verification through `modinfo`/kernel keyring inspection.
8. Add release automation that opens version-bump PRs when NVIDIA publishes a new stable open-module release.

## Non-goals

- reimplementing CUDA;
- redistributing NVIDIA proprietary libraries;
- automatically bypassing or disabling Secure Boot;
- silently blacklisting Nouveau;
- hot-swapping the active display driver;
- patching around NVIDIA product restrictions;
- claiming GPU support without upstream evidence.
