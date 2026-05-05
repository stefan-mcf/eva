# Contributing

EVA is pre-alpha. Contributions should preserve the proposal-only safety model and keep runtime-specific behavior behind adapter boundaries.

## Setup

```bash
python3 -m pip install -e .
python3 -m pip install pytest ruff build twine
```

## Checks

```bash
python3 -m ruff check .
python3 -m pytest -q
python3 -m compileall -q src tests
python3 scripts/public_readiness_check.py
```

## Development standards

- Keep the core package portable and standard-library-only unless a dependency is clearly justified.
- Keep Hermes-specific details in `adapters/hermes/` or Hermes adapter docs.
- Do not commit generated vault data, live profile state, memory dumps, session databases, credentials, or local delivery targets.
- Prefer synthetic fixtures and examples.
- Document degraded-mode behavior for new scanners.

## Proposal-only invariant

Changes must not make EVA auto-apply proposals, edit source profiles, or modify runtime state outside the configured EVA vault. If a feature needs to apply a recommendation, it belongs in a separate explicitly approved workflow, not in the default EVA loop.
