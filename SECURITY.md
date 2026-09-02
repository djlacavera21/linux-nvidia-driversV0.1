# Security Policy

## Scope

This repository contains orchestration and build tooling. Security reports about NVIDIA's driver source, firmware, or proprietary user-space components should be reported through NVIDIA's security channels rather than this repository.

Report issues here when they involve project-authored behavior such as:

- unsafe command construction;
- privilege-boundary mistakes;
- unintended file replacement;
- insecure temporary-file handling;
- incorrect driver-version validation;
- install behavior that can unexpectedly modify or disable the active graphics stack.

## Design rules

- No shell interpolation for external commands; commands are passed as argument vectors.
- Installation requires both root privileges and explicit `--yes` acknowledgement.
- v0.1 never automatically unloads Nouveau or NVIDIA modules.
- v0.1 never disables Secure Boot or enrolls a key.
- Source release alignment is checked before build and install.
- The NVIDIA source repository URL and release are explicit configuration values.

## Automated upstream monitoring

The scheduled security gate compares the pinned commit in
`config/security-baseline.json` with NVIDIA's public `product-security` main
branch. Dedicated bulletin documents are reviewed as complete security units;
cumulative indexes are evaluated from their changed lines so an unrelated new
bulletin cannot match an older managed-product entry. Missing upstream content,
non-ancestral baselines, and oversized comparisons fail closed for manual review.

Baseline advances require a recorded scope decision. The current review is
documented in
[`docs/security-reviews/2026-09-02-nvidia-psirt-5868.md`](docs/security-reviews/2026-09-02-nvidia-psirt-5868.md).

## Reporting

Please open a private security advisory in GitHub when possible. Avoid posting exploit details publicly before a fix is available.
