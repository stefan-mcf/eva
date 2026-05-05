# EVA — Evidence & Verification Agent

> The agent that watches all the other agents.

EVA is a framework-agnostic evidence operator. It observes how an agent system operates — memory, skills, session corrections, tool failures, config drift — and surfaces structured optimization proposals. It does **not** auto-apply changes. It reports to the operator.

First adapter: Hermes.

## Current capabilities

- Scans Hermes profile memory files for contradictions, stale/orphan references, duplicates, and topic distribution.
- Scans Hermes session SQLite stores for correction language, repeated tool failures, and skill patch signals.
- Scans skills across profiles for oversized files, staleness candidates, duplicate names, and patch-frequency hints.
- Scans profile configs for model/delegation/tooling drift across similar profile groups.
- Compiles an operator profile (`operator-profile.json` and `.md`) from evidence.
- Drafts pending optimization proposals in `eva-vault/proposals/pending/` for manual approval.
- Compiles a Telegram-readable brief.
- Can run as a dedicated Hermes profile with a scheduled scan.

## Install

```bash
git clone https://github.com/<owner>/eva.git
cd eva
python3 -m pip install -e .
```

EVA currently uses only the Python standard library at runtime. Development checks use `pytest` and `ruff`.

## Run locally

```bash
# Full loop: scan → profile → proposals → brief
python3 -m eva.loop

# Strict dry-run: print JSON and do not create or modify files
python3 -m eva.loop --no-write --json

# Explicit portable paths
python3 -m eva.loop \
  --profiles-dir ~/.hermes/profiles \
  --vault ~/.hermes/profiles/eva/workspace/eva-vault

# Individual scanners
python3 -m eva.scanners.scan_memory ~/.hermes/profiles
python3 -m eva.scanners.scan_sessions ~/.hermes/profiles
python3 -m eva.scanners.scan_skills ~/.hermes/profiles
python3 -m eva.scanners.scan_configs ~/.hermes/profiles

# Compile the latest brief
python3 -m eva.compilers.compile_brief \
  ~/.hermes/profiles/eva/workspace/eva-vault/briefs/latest-scan.json
```

## Configuration

Defaults are portable and can be overridden with environment variables:

- `EVA_HERMES_PROFILES_DIR`: Hermes profile root, default `~/.hermes/profiles`.
- `EVA_PROFILE_DIR`: EVA profile root, default `$EVA_HERMES_PROFILES_DIR/eva`.
- `EVA_VAULT_DIR`: EVA vault root, default `$EVA_PROFILE_DIR/workspace/eva-vault`.

Runtime thresholds live in `context/settings.json` inside the EVA vault. A generic template is provided at `adapters/hermes/settings.template.json`.

## Vault layout

```text
~/.hermes/profiles/eva/workspace/eva-vault/
  context/
    settings.json
    operator-profile.json
    operator-profile.md
  evidence/
    corrections.jsonl
    failures.jsonl
    successes.jsonl
  proposals/
    pending/
    applied/
    rejected/
  briefs/
  health/
```

## Safety model

EVA is read-mostly and proposal-only:

- It reads Hermes profile memory, sessions, skills, and config.
- It writes only to the EVA vault and proposal files during normal write mode.
- `--no-write` is a strict dry-run and does not create or modify files.
- It never edits memory, skills, configs, or other profiles automatically.
- Proposal outcomes can be recorded explicitly, but application is manual/operator-approved.

## Public-facing status

Pre-alpha but functional. Keep the repository private until the operator explicitly chooses publication. Before changing visibility, run a secret scan, private-data scan, attribution check, and CI/status verification against the exact release commit.
