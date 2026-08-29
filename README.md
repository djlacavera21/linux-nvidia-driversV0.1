# Linux NVIDIA Drivers v0.1

A Linux-first toolkit for detecting NVIDIA GPUs, validating the host, planning a compatible NVIDIA driver deployment, building NVIDIA's open GPU kernel modules, and diagnosing common installation failures.

> [!IMPORTANT]
> This repository is **not** a redistribution of NVIDIA's proprietary user-space driver stack. It is an orchestration, build, validation, and packaging layer designed to work with NVIDIA's official Linux driver releases and the open GPU kernel modules published at <https://github.com/NVIDIA/open-gpu-kernel-modules>.

## v0.1 goals

- Detect NVIDIA PCI devices directly from Linux sysfs.
- Report kernel, distribution, Secure Boot, Nouveau, and loaded NVIDIA module state.
- Generate a non-destructive deployment plan before changing the system.
- Pin an upstream NVIDIA open-kernel-module release in one configuration file.
- Fetch the official source release.
- Build the official modules against the running or selected kernel.
- Refuse obvious kernel-header and version-mismatch states early.
- Provide a guarded install command that requires explicit acknowledgement.
- Exercise hardware detection in CI without requiring a physical NVIDIA GPU.

## Current upstream baseline

The initial development baseline is NVIDIA open GPU kernel modules **610.57.04**. Upstream currently documents support for x86_64 and aarch64, Linux kernel 4.15+, and Turing-or-newer NVIDIA GPUs. The kernel modules must be paired with matching NVIDIA user-space components and GSP firmware from the same driver release.

The version is centralized in `config/driver-series.toml` so it can be updated without rewriting the tool.

## CLI

```bash
nvlx detect
nvlx doctor
nvlx plan
nvlx fetch
nvlx build --source ./vendor/open-gpu-kernel-modules
sudo nvlx install --source ./vendor/open-gpu-kernel-modules --yes
```

`detect`, `doctor`, and `plan` are non-destructive. `install` is deliberately guarded.

## Architecture

```text
Linux host
   |
   +-- PCI/sysfs detection -----------+
   +-- kernel/build environment ------+--> nvlx planner
   +-- Secure Boot / module state ----+        |
                                              +--> diagnostics
Official NVIDIA source ---------------------->+--> pinned fetch
                                              +--> module build
                                              +--> guarded install
                                              +--> distro packaging (next)
```

See `docs/ARCHITECTURE.md` for implementation boundaries and the roadmap.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
nvlx detect
python -m unittest discover -s tests -v
```

## Safety model

Kernel-driver installation can make a graphical Linux host temporarily unusable if modules, firmware, user-space libraries, or kernel ABI expectations do not match. v0.1 follows four rules:

1. inspect before changing;
2. keep the NVIDIA release version consistent across kernel and user-space components;
3. default to build and diagnostic operations instead of destructive module replacement;
4. require explicit acknowledgement before module installation.

## License

Project-authored orchestration code is MIT licensed. NVIDIA source, firmware, user-space components, trademarks, and redistributable packages remain subject to their respective NVIDIA licenses.
