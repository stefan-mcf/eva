# Testing Quickstart

This guide is for external testers who want to clone EVA, verify that the repository is clean, and run a safe first scan without modifying any live agent runtime state.

EVA is pre-alpha. Treat it as a local evidence and proposal tool, not as an autonomous fixer.

## Requirements

- Python 3.10 or newer.
- Git.
- A shell with access to the local agent-runtime files you want EVA to inspect.
- No API keys or cloud credentials are required for the local dry-run path.

Optional for Hermes users:

- A Hermes profile directory to scan.
- A separate local EVA vault directory outside this repository for generated evidence and proposals.

## 1. Clone and install

Use a virtual environment so the test does not modify your global Python packages:

```bash
git clone https://github.com/stefan-mcf/eva.git
cd eva
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

If your platform uses `python` instead of `python3`, use the interpreter that reports Python 3.10 or newer:

```bash
python --version
```

## 2. Verify the local checkout

Run the same gates used for release-readiness checks:

```bash
python -m ruff check .
python -m pytest -q
python -m compileall -q src tests
python scripts/public_readiness_check.py
git diff --check
```

Expected final readiness output:

```text
PASS public readiness local checks
```

The readiness script also runs a strict no-write smoke test and package build check when the optional build tools are installed.

## 3. First safe smoke test

Run EVA in no-write mode first. This command prints JSON and must not create a vault:

```bash
eva-loop --no-write --json
```

A healthy result has this broad shape:

```json
{
  "scanner": "combined",
  "memory": {"scanner": "memory", "summary": {}},
  "sessions": {"scanner": "sessions", "summary": {}},
  "skills": {"scanner": "skills", "summary": {}},
  "configs": {"scanner": "configs", "summary": {}},
  "operator_profile": {"generated_at": "..."},
  "proposal_summary": {"proposals": [], "written": []}
}
```

Empty summaries are acceptable when no profile directory was supplied or when the supplied directory contains no matching runtime records.

## 4. Test against synthetic examples

The `examples/` tree contains only synthetic sample data. It is safe to inspect and use as a shape reference:

```bash
eva-scan-memory --profiles-dir examples/minimal-profiles --json
eva-scan-skills --skills-dir examples/minimal-profiles/example-profile/skills --json
```

## 5. Test against a real Hermes profile directory

Use explicit paths and put the generated vault outside the repository:

```bash
mkdir -p /tmp/eva-vault

eva-loop \
  --profiles-dir /path/to/hermes/profiles \
  --vault /tmp/eva-vault \
  --json
```

Review generated artifacts before sharing them. A write-mode run can create evidence, profile, proposal, brief, remediation-plan, notification-summary, and health files inside the vault you selected.

Expected plan artifacts after write mode include:

```text
/tmp/eva-vault/plans/latest-plan.json
/tmp/eva-vault/plans/latest-plan.md
/tmp/eva-vault/health/latest-notification.txt
```

## 6. Safety boundaries for testers

EVA should only read the source profile/runtime directories. It may write generated artifacts to the configured EVA vault, but it should not modify source memories, sessions, configs, skills, credentials, or runtime profiles.

Do not commit or share:

- live memory files;
- session databases;
- generated EVA vault artifacts;
- credentials, tokens, private keys, or local auth files;
- private chat IDs or delivery destinations; or
- local scheduler/runtime state.

## 7. Optional Hermes skill installation

A reusable Hermes skill for safe EVA operation lives at:

```text
adapters/hermes/skills/eva/SKILL.md
```

The full skill is committed as plain Markdown. Inspect it before installing:

```bash
less adapters/hermes/skills/eva/SKILL.md
```

Install it into a local Hermes skill directory when you want an agent to run the same workflow consistently:

```bash
mkdir -p "$HOME/.hermes/skills/eva"
cp adapters/hermes/skills/eva/SKILL.md "$HOME/.hermes/skills/eva/SKILL.md"
hermes --skills eva
```

See [skills.md](skills.md) for skill doctrine, profile-specific install paths, copy-vs-canonical-source guidance, and maintenance rules.

## Troubleshooting

### `python -m build` or `twine` is missing

Install development extras:

```bash
python -m pip install -e '.[dev]'
```

### `eva-loop --no-write --json` prints empty evidence

That is normal if no profile directory was supplied. Run with `--profiles-dir /path/to/hermes/profiles` when you want EVA to inspect actual runtime records.

### A scanner reports degraded coverage

Degraded coverage means EVA could not read part of the requested source tree. Check the path, permissions, and whether the runtime stores exist. Do not treat a degraded scan as complete evidence.

### A readiness check finds a possible private artifact

Stop and inspect the reported path. Remove generated state or private material before sharing the repository or any artifacts.
