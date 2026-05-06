---
name: eva
description: Use when operating, testing, or reviewing EVA from a Hermes profile. Enforces clean setup, dry-run-first scans, explicit profile/vault paths, source-state immutability, artifact review, degraded-scan handling, and concise evidence reports.
version: 1.2.0
author: EVA maintainers
license: MIT
tags: [eva, hermes-adapter, testing, safety, evidence-review]
metadata:
  hermes:
    tags: [eva, hermes-adapter, testing, safety, evidence-review]
    related_skills: []
---

# EVA

## Overview

EVA (Evidence & Verification Agent) reads durable agent-runtime records, compiles evidence, drafts reviewable proposals, and leaves changes to a human or explicitly approved workflow. Use this skill to operate, test, or review EVA safely from a Hermes profile.

Core operating rule:

```text
verify checkout → dry-run first → explicit paths → vault-only writes → artifact review → report evidence, limits, next steps
```

A successful EVA test proves that EVA can read inputs, produce understandable evidence, and respect its safety boundary. It does not prove that every proposal should be applied or that generated artifacts are safe to share without review.

## When to Use

Use for:

- local EVA checkout/setup verification;
- attaching EVA operation guidance to a Hermes profile;
- `eva-loop` dry-run or write-mode tests;
- scans against Hermes profile stores;
- empty/degraded/noisy scan diagnosis;
- source-mutation checks during write-mode tests;
- generated vault artifact review;
- remediation-plan and notification-summary review; and
- concise tester/operator reports.

Do not use for:

- auto-applying memory, skill, config, source-code, or profile changes;
- editing source runtime/profile directories during a test;
- sharing raw private runtime evidence;
- treating degraded output as complete evidence;
- bypassing repository readiness checks before sharing; or
- publishing packages, releases, or visibility changes.

## Non-Negotiable Safety Rules

1. Source runtime/profile directories are read-only inputs.
2. First run uses `--no-write --json`; a fresh vault path must not be created.
3. Real tests use explicit `--profiles-dir` and `--vault` paths.
4. Write-mode output goes only under the selected EVA vault, outside the source repo.
5. Generated artifacts are private until reviewed.
6. Degraded scans must be labeled degraded.
7. EVA proposals are drafts, not approved changes.
8. Reports cite commands, paths, artifact counts/names, limits, and next steps.

## Boundaries

Allowed reads, when explicitly pointed at them:

- Hermes profile directories;
- memory markdown files;
- session SQLite stores;
- skill directories;
- profile configuration files;
- committed synthetic examples in `examples/`;
- EVA vault context/settings files.

Allowed writes:

- only inside the selected `--vault` during write-mode runs;
- expected outputs include evidence bundles, compiled profiles, proposals, briefs, remediation plans, notification summaries, health/degraded-scan output, and latest pointers.

Forbidden writes:

- live memories;
- session databases;
- source skills;
- profile configs;
- auth/credential files;
- scheduler state;
- delivery destinations;
- source runtime/profile directories;
- the EVA source repo, unless the task is explicitly repo documentation/code maintenance.

## Workflow

### 1. Verify setup

Fresh clone:

```bash
git clone https://github.com/stefan-mcf/eva.git
cd eva
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Existing checkout:

```bash
cd /path/to/eva
git status --short --branch
git remote -v
git log --oneline --decorate -5
python --version
```

Use Python 3.10+. A shared/public test should start from a clean tree unless verifying a deliberate local change.

### 2. Run repository gates when repo cleanliness is in scope

```bash
python -m ruff check .
python -m pytest -q
python -m compileall -q src tests
python scripts/public_readiness_check.py
git diff --check
git status --short --branch
```

Expected readiness output:

```text
PASS public readiness local checks
```

Modified/deleted/untracked files must be explained as intentional work.

### 3. Public/private surface scan before sharing

Run before sharing the repo or generated artifacts:

```bash
git grep -n -I -E '/Users/|/home/|api[_-]?key|secret|password|token|PRIVATE KEY|chat_id|state\.db|latest-brief|MEMORY\.md|USER\.md|auth\.json|\.env' -- . || true
git ls-files --others --exclude-standard
git ls-files -ci --exclude-standard
```

Expected: grep hits are docs/tests/scanner patterns/ignore rules only; no unreviewed nonignored files; no tracked ignored files. Redact real secrets in reports: cite path + issue type, never value.

### 4. Prove no-write mode first

Use a fresh vault path:

```bash
_tmp_vault=/tmp/eva-no-write-vault-$(date +%s)
eva-loop --vault "$_tmp_vault" --no-write --json >/tmp/eva-no-write.json
python -m json.tool /tmp/eva-no-write.json >/dev/null
test ! -e "$_tmp_vault"
```

For explicit Hermes input:

```bash
eva-loop \
  --profiles-dir /path/to/hermes/profiles \
  --vault "$_tmp_vault" \
  --no-write \
  --json >/tmp/eva-no-write.json
python -m json.tool /tmp/eva-no-write.json >/dev/null
test ! -e "$_tmp_vault"
```

Empty summaries are acceptable when no profile records were supplied/found. They are not evidence that a real profile was scanned.

### 5. Smoke-test synthetic examples

```bash
eva-scan-memory --profiles-dir examples/minimal-profiles --json >/tmp/eva-memory.json
python -m json.tool /tmp/eva-memory.json >/dev/null
_eva_skills_dir=examples/minimal-profiles/example-profile/skills
eva-scan-skills --skills-dir "$_eva_skills_dir" --json >/tmp/eva-skills.json
python -m json.tool /tmp/eva-skills.json >/dev/null
```

Expected: successful exit, valid JSON, synthetic-only data, no writes beyond normal generated caches/build artifacts.

### 6. Run real profile scan

```bash
PROFILES_DIR=/path/to/hermes/profiles
EVA_VAULT=/tmp/eva-vault-test-$(date +%Y%m%d-%H%M%S)
mkdir -p "$EVA_VAULT"
eva-loop --profiles-dir "$PROFILES_DIR" --vault "$EVA_VAULT" --json >/tmp/eva-run.json
python -m json.tool /tmp/eva-run.json >/dev/null
```

Write-mode may create vault evidence/profile/proposal/brief/health files. It must not modify `PROFILES_DIR`.

Write-mode also creates remediation-plan and notification-summary artifacts under the vault:

```text
plans/latest-plan.json
plans/latest-plan.md
health/latest-notification.txt
```

EVA does not require an open terminal when scheduled by Hermes cron, cron, launchd, systemd, or another wrapper. EVA core does not deliver Telegram, Discord, email, or SMS messages by itself; the scheduler/wrapper should read `health/latest-notification.txt` and deliver it through an operator-approved destination.

### 7. Guard against source mutation

If `PROFILES_DIR` is a git checkout:

```bash
git -C "$PROFILES_DIR" status --short --branch || true
```

For non-git profile trees, compare inventory before/after:

```bash
find "$PROFILES_DIR" -maxdepth 4 -type f -print | sort > /tmp/eva-source-before.txt
# run EVA
find "$PROFILES_DIR" -maxdepth 4 -type f -print | sort > /tmp/eva-source-after.txt
diff -u /tmp/eva-source-before.txt /tmp/eva-source-after.txt || true
```

For high-sensitivity tests, hash contents:

```bash
find "$PROFILES_DIR" -maxdepth 4 -type f -print0 | sort -z | xargs -0 shasum -a 256 > /tmp/eva-source-before.sha256
# run EVA
find "$PROFILES_DIR" -maxdepth 4 -type f -print0 | sort -z | xargs -0 shasum -a 256 > /tmp/eva-source-after.sha256
diff -u /tmp/eva-source-before.sha256 /tmp/eva-source-after.sha256 || true
```

Any unexpected source mutation is a blocker. Stop, preserve evidence, and do not continue write-mode testing until explained.

### 8. Inspect vault artifacts

```bash
find "$EVA_VAULT" -maxdepth 4 -type f | sort
find "$EVA_VAULT" -maxdepth 4 -type f \( -name '*.md' -o -name '*.json' -o -name '*.txt' \) -print
```

Review before sharing for:

- raw live memory/session content;
- credentials, people, chat IDs, private work, delivery endpoints;
- local absolute paths;
- overconfident proposals from weak evidence;
- degraded scanner warnings;
- stale/private profile or project names;
- source-profile files copied wholesale into the vault.

If sensitive content appears, do not share. Redact, discard, or rerun with narrower inputs.

## Interpreting Results

Healthy complete scan:

- command succeeded;
- JSON is valid or vault files exist as expected;
- real inputs produced non-empty evidence;
- no unexpected degraded markers;
- no source mutation;
- proposals cite evidence;
- brief separates evidence, interpretation, recommendations.

Empty scan is normal when no `--profiles-dir` was supplied, the directory has no matching stores, or the test intentionally used empty/synthetic inputs. Report as empty, not failed, unless real inputs were expected.

Degraded scan means missing/unreadable/malformed input, permission failure, unsupported layout, or scanner exception. Report component + path/evidence. Do not claim full coverage.

Noisy proposals should be classified:

- true positive: repeated supporting evidence;
- weak signal: plausible but needs more examples;
- false positive: heuristic too broad;
- unsafe: would violate no-mutation/privacy boundary if applied.

Unsafe proposals are a bug/design gap.

## Report Template

```text
EVA local test report

Repository:
  path: <repo path>
  commit: <git rev-parse --short HEAD>
  status: <git status --short --branch summary>

Environment:
  python: <python --version>
  os: <platform if relevant>

Verification:
  ruff: pass/fail/not run
  pytest: pass/fail/not run
  compileall: pass/fail/not run
  public_readiness_check: pass/fail/not run
  no-write JSON smoke: pass/fail/not run

Run:
  profiles_dir: <path or omitted>
  vault: <path or no-write only>
  mode: no-write/write-mode

Result:
  evidence: <empty/non-empty/degraded>
  proposals: <count or summary>
  brief: <path if generated>
  source mutations: none / unexpected / not checked

Artifact review:
  share-safe: yes/no/needs redaction
  notes: <redacted summary>

Limits:
  <anything not scanned or not verified>

Next steps:
  <manual review / rerun with paths / fix scanner / safe to share>
```

## One-Shot Commands

Verify checkout before sharing:

```bash
python -m pip install -e '.[dev]'
python -m ruff check .
python -m pytest -q
python -m compileall -q src tests
python scripts/public_readiness_check.py
git diff --check
git status --short --branch
git ls-files --others --exclude-standard
git ls-files -ci --exclude-standard
```

Run real profile scan and inspect artifacts:

```bash
PROFILES_DIR=/path/to/hermes/profiles
EVA_VAULT=/tmp/eva-vault-test-$(date +%Y%m%d-%H%M%S)
mkdir -p "$EVA_VAULT"
eva-loop --profiles-dir "$PROFILES_DIR" --vault "$EVA_VAULT" --json >/tmp/eva-run.json
python -m json.tool /tmp/eva-run.json >/dev/null
find "$EVA_VAULT" -maxdepth 4 -type f | sort
```

Clean generated local build/test artifacts after verification:

```bash
rm -rf build dist src/*.egg-info .pytest_cache .ruff_cache
find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
```

Do not remove evidence vaults unless they are clearly disposable test vaults.

## Common Pitfalls

1. **Skipping no-write mode.** Always prove no-write JSON and no vault creation first.
2. **Implicit defaults.** Defaults may point at the current user's profile; use explicit paths for tester workflows.
3. **Vault inside repo.** Generated vault artifacts are runtime output, not source.
4. **Degraded-as-complete reporting.** Label degraded/partial coverage.
5. **Raw artifact sharing.** Generated evidence may contain private operational details.
6. **Proposal confusion.** EVA drafts proposals; applying them needs separate approval.
7. **Generated build/cache churn.** Clean package/test artifacts before final git status or commit.
8. **Missed source mutation.** Capture before/after state for real profile write-mode tests.
9. **Secret leakage in reports.** Redact values; cite path and issue type only.
10. **Stale installed scripts.** After source edits, reinstall `.[dev]` or run with `PYTHONPATH=src`.

## Verification Checklist

- [ ] Python 3.10+ active.
- [ ] EVA installed with `.[dev]` or run from source with `PYTHONPATH=src`.
- [ ] Repository status inspected.
- [ ] Repository gates passed when cleanliness was in scope.
- [ ] No-write run emitted valid JSON.
- [ ] Fresh no-write vault path was not created.
- [ ] Real scan used explicit `--profiles-dir` and `--vault`.
- [ ] Vault path was outside the source repo.
- [ ] Generated artifacts were listed and reviewed before sharing.
- [ ] Empty/degraded/noisy results were labeled accurately.
- [ ] Source memories, sessions, configs, skills, credentials, and profiles were not modified.
- [ ] Final report includes commands, pass/fail status, artifact paths, limits, and next steps.
