# Linux NVIDIA Drivers v0.6

`nvlx` is a Linux NVIDIA driver safety/control toolkit. v0.6 adds a cluster-aware `nvlx-fleet` surface for qualification, maintenance, diagnostics, quarantine, canary rollout, alerting, security gating, and supply-chain provenance.

> [!IMPORTANT]
> Host driver operations remain explicit and guarded. Cluster mutation is never implicit: drain, quarantine, uncordon, unquarantine, and diagnostic burn-in require deliberate operator actions.

## v0.6 highlights

- **Cluster-wide node qualification.** `nvlx-fleet qualify` checks Kubernetes Ready/schedulable state, GPU presence, GPU-driver upgrade labels, and disabled GPU Operator validators.
- **Maintenance/drain orchestration.** Preview or execute `cordon -> drain`; recovery is a separate explicit `uncordon` command.
- **GPU Operator ClusterPolicy validation.** Checks that `cluster-policy` exists, reconciles to a ready/success state, DCGM Exporter is enabled, and MIG strategy is recognized.
- **DCGM diagnostic burn-in.** Plans DCGM diagnostic levels 1-4 and executes them only with `--yes` and a bounded timeout.
- **GPU/NVSwitch fault quarantine.** Applies an `nvlx.io/quarantined=true` label plus a `NoSchedule` GPU-fault taint; unquarantine is explicit.
- **Prometheus alert rules.** Generates rules for host health, Xid events, uncorrected ECC, NVSwitch faults, and stale transactions.
- **Fleet upgrade waves/canaries.** Deterministic canary-first wave planning and a hard advancement gate for node qualification, diagnostics, security posture, and quarantine count.
- **Automatic NVIDIA PSIRT gating.** A daily/PR workflow diffs NVIDIA's public `product-security` repository from a reviewed baseline. New or changed bulletins mentioning managed GPU-driver/DCGM/GPU Operator/Fabric/NVSDM/NVSwitch/NVOS components fail the gate pending review.
- **SBOM + SLSA provenance.** Tagged reproducible releases generate an SPDX JSON SBOM, GitHub build-provenance attestation, and signed SBOM attestation after deterministic archive verification.

## Current ecosystem assumptions

The repository driver baseline remains **610.57.04**. GPU Operator planning targets **v26.7.0**. NVIDIA GPU Operator 26.7 manages the Device Plugin `ClusterPolicy` path and includes DCGM/DCGM Exporter/validator components; NVIDIA also documents DRA as a distinct `GPUCluster` path that must not coexist with `ClusterPolicy`.

The current security baseline pins NVIDIA `product-security` commit `6e8ef1666730b8906a3690505bb9f4311e68c228`. Updating that value is a security-review action, not an automated self-approval.

## Fleet commands

```bash
# qualification and policy
nvlx-fleet qualify
nvlx-fleet clusterpolicy

# maintenance
nvlx-fleet maintenance-plan gpu01 --timeout 10m
sudo -E nvlx-fleet drain gpu01 --timeout 10m --yes
sudo -E nvlx-fleet uncordon gpu01 --yes

# DCGM burn-in
nvlx-fleet diag-plan --level 3 --timeout-sec 900
sudo -E nvlx-fleet diag-run --level 3 --timeout-sec 900 --yes

# quarantine
nvlx-fleet quarantine-plan gpu01 "Xid 79"
sudo -E nvlx-fleet quarantine gpu01 "Xid 79" --yes
sudo -E nvlx-fleet unquarantine gpu01 --yes

# alert rules
nvlx-fleet alerts > nvlx-gpu-alerts.yaml

# canary/waves
nvlx-fleet waves gpu01 gpu02 gpu03 gpu04 --canaries 1 --wave-size 2
nvlx-fleet advance-check --qualified --diagnostics-passed --security-passed

# security
nvlx-fleet security-gate --dcgm-exporter-version 4.8.3
python scripts/check_nvidia_security.py
```

## Rollout model

```text
DISCOVER GPU NODES
       |
       v
QUALIFY + CLUSTERPOLICY VALIDATION
       |
       +---- fail ----> STOP
       |
       v
CANARY WAVE
       |
       v
CORDON + DRAIN
       |
       v
DRIVER / OPERATOR CHANGE
       |
       v
DCGM DIAGNOSTIC BURN-IN
       |
       +---- fault ----> QUARANTINE + STOP ADVANCEMENT
       |
       v
SECURITY GATE + HEALTH CHECK
       |
       +---- fail ----> STOP
       |
       v
UNCORDON CANARY
       |
       v
ADVANCE NEXT WAVE
```

## Security bulletin gate

NVIDIA began publishing PSIRT security bulletins on GitHub in human-readable and machine-readable formats. `scripts/check_nvidia_security.py` compares the reviewed baseline commit with current `NVIDIA/product-security` main, downloads changed Markdown bulletins, and fails if they mention managed NVIDIA fleet components. The gate fails closed if the explicit DCGM Exporter security check cannot establish a safe version/source state.

## Release provenance

The tag-release workflow:

1. builds the normalized source archive twice;
2. requires identical SHA-256 manifests;
3. generates an SPDX JSON SBOM with Syft/Anchore;
4. creates GitHub/Sigstore build provenance;
5. creates a signed SBOM attestation bound to the release archive;
6. publishes only after those gates complete.

GitHub artifact attestations provide SLSA v1.0 Build Level 2 provenance; stronger Build Level 3 isolation can be a future reusable-workflow hardening step.

## Safety invariants

1. No fleet rollout advances with failed node qualification, DCGM burn-in, security gate, or quarantined nodes.
2. Drain/quarantine operations require explicit `--yes`; recovery is separate and explicit.
3. Kubernetes evictions use normal `kubectl drain` semantics rather than force-deleting arbitrary workloads.
4. New NVIDIA security bulletins relevant to managed components block automated rollout until reviewed.
5. A PSIRT baseline is never advanced automatically by the same workflow that evaluates it.
6. Release artifacts must remain reproducible before provenance/SBOM attestation.
7. Host-level v0.1-v0.5 safety invariants remain in force.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## License

Project-authored orchestration code is MIT licensed. NVIDIA source, firmware, user-space components, trademarks, and redistributable packages remain subject to their respective NVIDIA licenses.
