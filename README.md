# Linux NVIDIA Drivers v0.5

`nvlx` is a Linux-first NVIDIA driver control plane for transactional upgrades, rollback safety, GPU health, MIG/NVLink/NVSwitch operations, Kubernetes GPU Operator planning, immutable hosts, and reproducible signed releases.

> [!IMPORTANT]
> This project does not redistribute NVIDIA proprietary user-space components. It orchestrates and validates NVIDIA's official Linux driver/open-kernel-module ecosystem.

## v0.5 highlights

- **Rollback-version availability preflight.** Before a transaction starts, nvlx verifies the captured NVIDIA/CUDA/Fabric/DCGM package versions are still recoverable through APT/DNF repositories, the pacman cache, or the current NixOS generation. Missing rollback artifacts abort the upgrade.
- **Systemd retry policy.** The boot guard now supports bounded restart attempts, restart delay, validation timeout, and start-limit windows instead of a single one-shot recovery attempt.
- **Per-GPU ECC + Xid telemetry.** `nvlx dcgm-telemetry` queries volatile corrected/uncorrected ECC counters per GPU, associates current-boot Xid events with PCI bus IDs, and detects DCGM Exporter Xid/ECC Prometheus series.
- **NVSDM / Blackwell NVSwitch readiness.** `nvlx nvsdm` verifies the driver-major-aligned `libnvsdm-<branch>` package and DCGM NVSwitch discovery. The experimental `nvsdm_cli` is reported but not relied on as a stable interface.
- **MIG profile lifecycle.** `mig-profile-plan` previews disruptive commands. `mig-profile-apply` requires root, `--maintenance`, `--yes`, confirmed MIG capability, and zero active compute processes.
- **GPU Operator integration.** `gpu-operator-plan` generates a pinned NVIDIA GPU Operator 26.7 Helm plan using the configured driver release and `none`, `single`, or `mixed` MIG strategy.
- **Immutable-host support.** `immutable-plan` prevents conventional mutation assumptions on RHCOS/CoreOS/Flatcar/Bottlerocket/Talos/COS-class hosts. RHCOS is identified as the NVIDIA-validated OpenShift path; other immutable systems remain advisory unless NVIDIA/platform validation exists.
- **Signed reproducible releases.** Tagged releases build a deterministic source archive twice, require matching SHA-256 manifests, create a GitHub provenance attestation using OIDC, and publish the attested artifacts.
- **Telemetry/report schema expansion.** JSON/Prometheus telemetry and sanitized support bundles now include ECC/Xid, DCGM Exporter, NVSDM, immutable-host, and rollback-preflight state.

## Current NVIDIA ecosystem baseline

The driver baseline remains **610.57.04** in `config/driver-series.toml`. The current GPU Operator 26.7 component matrix supports driver 610.57.04 and includes DCGM Exporter 4.6.0-4.8.3, DCGM 4.6.0-1, and MIG Manager 0.15.0. NVSDM packages are aligned by driver major, e.g. `libnvsdm-610` for R610.

## Main commands

```bash
# rollback / transaction safety
nvlx package-state
nvlx rollback-preflight
sudo nvlx install --source ./vendor/open-gpu-kernel-modules --yes
nvlx transaction-pending
nvlx watchdog-plan --retries 3 --restart-sec 20 --timeout-sec 90
sudo nvlx boot-guard-install --yes
sudo nvlx boot-validate --auto-rollback

# fleet reliability / switching
nvlx health
nvlx dcgm-telemetry
nvlx nvsdm
nvlx topology
nvlx mig-fabric
nvlx telemetry --format prometheus

# MIG lifecycle
nvlx mig-profile-plan 1g.10gb
sudo nvlx mig-profile-apply 1g.10gb --maintenance --yes
nvlx mig-profile-plan disabled

# Kubernetes / immutable hosts
nvlx gpu-operator-plan --mig-strategy mixed
nvlx immutable-plan

# graphics / compatibility
nvlx prime
nvlx session
nvlx compat
nvlx secureboot-verify

# sanitized support bundle
nvlx report ./nvlx-report
```

## Transaction safety model

```text
PACKAGE SNAPSHOT
      |
      v
ROLLBACK AVAILABILITY PREFLIGHT ---- unavailable ---> ABORT
      |
      v
MODULE SNAPSHOT
      |
      v
INSTALL + DEPMOD
      |
      v
PENDING REBOOT
      |
      v
BOOT GUARD (bounded retry policy)
      |
      +---- healthy ---> VALIDATED
      |
      +---- failed ----> restore exact packages + modules + initramfs
```

A package manifest alone is not treated as rollback capability. v0.5 requires evidence that the recorded versions can actually be restored before module replacement begins.

## MIG safety

MIG geometry changes can terminate or invalidate GPU workloads. nvlx therefore refuses profile application while compute processes are active and requires both `--maintenance` and `--yes`. The Kubernetes path remains declarative: GPU Operator MIG Manager watches `nvidia.com/mig.config` and handles node/pod coordination independently of the local CLI path.

## Immutable hosts

Direct source installation is intended for conventional mutable Linux hosts. On immutable/container-optimized systems, nvlx reports a deployment strategy instead of pretending host package mutation is safe. RHCOS should use the OpenShift GPU Operator path; other immutable platforms require their own validated driver/operator mechanism.

## Reproducible release model

`scripts/repro_release.py` normalizes archive ownership and timestamps and produces `SHA256SUMS`. `.github/workflows/release.yml` rebuilds the archive twice and uses GitHub artifact attestations before publishing a tag release. Driver baseline updates remain separate reviewable PRs and are never auto-merged.

## Safety invariants

1. Rollback versions must be available before a transaction begins.
2. Kernel module, user-space driver, GSP firmware, Fabric Manager, NVSDM, and related branch components remain release-aligned where applicable.
3. Recovery retries are bounded; persistent failures remain visible instead of looping forever.
4. MIG changes require a drained maintenance window.
5. Immutable hosts are not silently converted into mutable hosts.
6. GPU Operator integration is advisory and pinned; nvlx does not silently mutate a Kubernetes cluster.
7. NVSDM CLI output is not treated as a stable API contract while NVIDIA labels that tool experimental.
8. Tagged release artifacts must be byte-reproducible across two builds before attestation/publication.
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
