# Architecture

## Mission

`nvlx` is an auditable Linux NVIDIA driver control plane. It does not recreate NVIDIA's proprietary user-space stack or silently replace an active graphics session. The project coordinates official support metadata, reproducible open-kernel-module builds, distribution-native integration, transactional upgrade state, Secure Boot, rollback, graphics-session diagnostics, data-center fabric validation, and health telemetry.

## Core invariant

```text
kernel module release
    == NVIDIA user-space release
    == required GSP firmware release
    == Fabric Manager release (when Fabric Manager is required)
```

A v0.4 transaction captures enough pre-change state to either validate that invariant after reboot or restore the prior state.

## Trust boundaries

### Official NVIDIA metadata and source

`gpu-db-sync` reads the Compatible GPUs table from the exact NVIDIA `open-gpu-kernel-modules` tag pinned in `config/driver-series.toml`. Source builds validate `version.mk` before compilation or installation. An unrecognized PCI ID is reported as `unknown`, not guessed unsupported.

### Package ownership

Distribution package managers continue to own distro-installed NVIDIA/CUDA packages. v0.4 records relevant package names and exact installed versions before a transaction. Automatic restoration is attempted only where the native package manager has a deterministic exact-version path. Unsupported exact rollback (for example Arch without cached package archives) fails visibly instead of approximating a version.

### Kernel modules and initramfs

Rollback snapshots preserve NVIDIA module files for one kernel tree. Initramfs regeneration stays distro-specific and explicit except during an already-authorized automatic rollback, where nvlx attempts to rebuild the restored kernel image after package/module restoration.

### Secure Boot

nvlx can generate and use a Machine Owner Key but never disables Secure Boot or auto-enrolls a certificate. Signature presence and signer metadata are reported separately from trust/enrollment assumptions.

### Persistent boot guard

The boot guard is opt-in. `boot-guard-install --yes` installs and enables a systemd oneshot that only runs when `/var/lib/nvlx/transactions/pending.json` exists. It invokes post-reboot validation with automatic rollback enabled.

## Transaction state machine

```text
prepared
  |  package-state.json captured
  |  module rollback snapshot captured
  v
modules_install
  |
  v
pending-reboot
  |  pending.json armed
  |  boot_id_before recorded
  v
post-reboot validation
  |\
  | healthy
  |  -> validated -> pending marker removed
  |
  | failed
  |  -> package restore
  |  -> module restore
  |  -> depmod
  |  -> initramfs regeneration (best effort)
  |  -> rolled-back -> pending marker removed
  |
  ` rollback error -> rollback-failed (marker retained for operator recovery)
```

Calling validation before a reboot does **not** trigger rollback; the transaction remains `pending-reboot`.

## Health validation

A pending transaction is healthy only after crossing a reboot boundary and satisfying:

1. `nvidia-smi` can communicate with the driver;
2. the detected driver version equals the transaction target;
3. the core `nvidia` kernel module is loaded.

The broader `nvlx health` command additionally reports GPU count, installed module-signature state, session warnings, topology availability, and Fabric Manager/DCGM compatibility.

## Graphics-session diagnostics

`session.py` inspects:

- `XDG_SESSION_TYPE` / Wayland display hints;
- `nvidia_drm` `modeset` and `fbdev` module parameters;
- GBM library availability;
- NVIDIA EGL-Wayland/EGL library availability;
- Xwayland presence;
- DRM device nodes.

This reflects NVIDIA's GBM/Wayland requirement that DRM KMS and the appropriate GBM/EGL components be present rather than assuming a Wayland environment variable proves driver readiness.

## Multi-GPU topology

`topology.py` consumes the official `nvidia-smi topo -m` interface. It preserves the raw matrix and derives GPU count, parsed matrix rows, symmetric NVLink adjacency count, and NVSwitch evidence. The raw output remains available because future hardware generations can introduce topology labels not yet modeled by nvlx.

## MIG / Fabric Manager / DCGM

`mig.py` treats these as separate but related layers:

- MIG mode and visible MIG instances come from `nvidia-smi`;
- Fabric Manager version comes from `nv-fabricmanager -v`;
- Fabric Manager service state comes from systemd when available;
- DCGM version is detected from `dcgmi` or `nv-hostengine`.

For the pinned R610 610.57.04 baseline, Fabric Manager is expected to match 610.57.04 and DCGM must be 4.3.x or newer.

## Telemetry

`telemetry.py` exposes the same health model as:

- structured JSON for automation;
- Prometheus text exposition for scraping or node-level collection.

Metrics include overall health, NVIDIA GPU count, module and `nvidia-smi` status, topology availability, NVLink adjacency, NVSwitch evidence, MIG instance count, Fabric Manager service/alignment, and DCGM compatibility.

## Component map

```text
system.py          host, PCI, modules, driver version
config.py          pinned NVIDIA release policy
gpu_db.py          official PCI support classification
distro.py          distro-native package/DKMS plans
repository.py      branch/repository pinning plans
dkms.py            DKMS inspection
build.py           fetch/build + transactional install
package_state.py   NVIDIA/CUDA package inventory + restore strategy
rollback.py        kernel-module snapshots + explicit restore
transaction.py     transaction journal + post-boot guard
initramfs.py       distro-specific initramfs actions
secureboot.py      MOK generation/signing/signature inspection
prime.py           hybrid/PRIME classification
session.py         Wayland/GBM/DRM session checks
topology.py        multi-GPU/NVLink/NVSwitch topology
mig.py             MIG/Fabric Manager/DCGM compatibility
compat.py          CUDA and Container Toolkit compatibility
health.py          boot/runtime health aggregation
telemetry.py       JSON + Prometheus health surfaces
report.py          sanitized support bundle
cli.py             command surface
```

## Safety rules

- Never hot-unload an active graphics stack automatically.
- Never disable Secure Boot or auto-enroll a signing key.
- Never start a direct module install without package and module recovery state.
- Never treat a pre-reboot transaction as a failed boot.
- Never guess a package downgrade when an exact restore path is unavailable.
- Never auto-merge an NVIDIA release bump.
- Preserve raw diagnostic evidence where parsing may be generation-specific.
- Treat report sanitization as risk reduction, not a guarantee of anonymity.

## v0.5 candidate targets

- package-manager transaction plugins that validate repository availability of rollback versions before upgrade;
- systemd watchdog/timeout policy and rollback retry limits;
- DCGM-exporter integration and per-GPU performance/error counters;
- NVSDM/NVSwitch monitoring for Blackwell-class systems;
- MIG profile lifecycle planning and Kubernetes GPU Operator integration;
- immutable host adapters (rpm-ostree, transactional-update, image-based systems);
- signed release artifacts and reproducible package builds.
