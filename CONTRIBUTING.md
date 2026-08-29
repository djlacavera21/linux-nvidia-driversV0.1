# Contributing

## Principles

Changes should preserve the project's core safety and compatibility rules:

1. do not silently mutate the active graphics stack;
2. do not bypass Secure Boot or signature enforcement;
3. keep NVIDIA kernel modules, user-space components, and GSP firmware release-aligned;
4. prefer official upstream metadata over guessed GPU support tables;
5. keep read-only diagnostics usable without root;
6. make privileged operations explicit and reviewable.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

No physical NVIDIA GPU is required for the unit tests. Hardware detection tests use synthetic sysfs trees.

## Pull requests

Please include tests for detection, policy, parsing, or command behavior when applicable. Changes that add a new distro or install path should document rollback behavior and privilege requirements.
