---
name: eva
description: Use when operating, configuring, testing, reviewing, or documenting EVA from Hermes, including EVA MCP tools, vault artifacts, remediation plans, memory-provider boundaries, scheduler behavior, degraded scans, and public/private release checks.
version: 2.1.0
author: EVA maintainers
license: MIT
tags: [eva, hermes-adapter, mcp, evidence-review, remediation, safety]
metadata:
  hermes:
    tags: [eva, hermes-adapter, mcp, evidence-review, remediation, safety]
    related_skills: []
---

# EVA

## Overview

EVA (Evidence & Verification Agent) is a proposal-first evidence layer for agent runtimes. It reads durable runtime records, compiles evidence, drafts operator proposals, creates remediation plans, and writes reviewable artifacts to an EVA vault. It does not silently mutate memories, skills, configs, credentials, source repositories, scheduler state, or delivery destinations.

Use this skill as the Hermes-side doctrine for EVA. Use EVA MCP as the bounded capability surface.

```text
EVA MCP tools = scan/compile capability surface
EVA skill     = operating doctrine, interpretation, safety gates
EVA vault     = generated evidence/proposal/remediation artifacts
Scheduler     = unattended execution + delivery wrapper
Operator      = approval for human-gated changes
```

Core rule:

```text
inspect setup -> dry-run first -> explicit paths -> vault-only writes -> review artifacts -> report evidence, limits, next steps
```

## When to Use

Use for:

- EVA setup, configuration, or Hermes profile integration;
- `eva_scan_health`, `eva_compile_remediation`, `eva-loop`, `eva-repair`, scanner, proposal, brief, or remediation-plan work;
- choosing MCP versus CLI execution;
- interpreting empty, degraded, noisy, unsafe, or actionable output;
- reviewing generated vault artifacts before sharing;
- scheduler/notification and memory-provider boundary questions; and
- public-facing EVA repo docs/readiness checks.

Do not use to authorize automatic mutation of live runtime state. Memory, skill, profile config, operator profile, scheduler, credential, delivery destination, public-repo, and unknown targets remain human-gated unless a separate explicit approval workflow exists.

## Boundary Model

| Layer | Owns | Does not own |
| --- | --- | --- |
| EVA core | scans durable records; writes vault artifacts in write mode | live runtime mutation; delivery; memory writes |
| Hermes adapter | profile/session/skill/config conventions and public templates | live profile state, secrets, provider-specific defaults |
| MCP bridge | bounded read/proposal-first tool calls | operator doctrine or approval semantics |
| Scheduler/wrapper | unattended invocation and delivery of notification text | scanner correctness or proposal approval |
| Operator | target approval, redaction, publication judgment | implicit automation by default |

Memory-provider rule: EVA may inspect memory-provider evidence, but EVA core is not a Hermes memory provider. Public templates must not pin ShyftR, Mem0, built-in memory, or any operator-specific backend. Installed profiles may inherit the operator's configured/default Hermes memory backend unless locally overridden.

Notification rule: EVA does not require an open terminal when invoked by Hermes cron, cron, launchd, systemd, or another wrapper. EVA writes notification-ready text such as `health/latest-notification.txt`; the wrapper/gateway delivers it through an operator-approved destination.

## Safety Gates

1. Start with dry-run/no-write for a checkout, profile, or MCP connection.
2. Use explicit `profiles_dir` and `vault` paths for real scans.
3. Keep generated vaults outside the source repo unless using committed synthetic examples.
4. Treat source runtime/profile directories as read-only inputs.
5. Label empty/degraded/noisy/unsafe results accurately.
6. Review vault artifacts before sharing; assume they may contain private operational data.
7. Treat proposals and remediation plans as checklists, not applied changes.
8. Auto-apply only deterministic EVA-owned generated artifacts when policy/tooling explicitly permits it.
9. Human-gate memory, skill, profile config, operator profile, scheduler, credential, delivery, public-repo, and unknown targets.
10. Public docs/examples use generic paths and synthetic data only.

## Execution Workflow

### 1. Inspect setup

```bash
cd /path/to/eva
git status --short --branch
git remote -v
git log --oneline --decorate -5
python --version
```

Use Python 3.10+. For public-facing work, explain any dirty-tree state before closeout.

### 2. Run readiness gates when repo quality/public surface is in scope

```bash
python -m pip install -e '.[dev]'
python -m ruff check .
python -m pytest -q
python -m compileall -q src tests
python scripts/public_readiness_check.py
git diff --check
```

Expected readiness output:

```text
PASS public readiness local checks
```

### 3. Dry-run first

```bash
_tmp_vault=/tmp/eva-no-write-vault-$(date +%s)
eva-loop --vault "$_tmp_vault" --no-write --json >/tmp/eva-no-write.json
python -m json.tool /tmp/eva-no-write.json >/dev/null
test ! -e "$_tmp_vault"
```

With explicit Hermes profiles:

```bash
PROFILES_DIR=/path/to/hermes/profiles
_tmp_vault=/tmp/eva-no-write-vault-$(date +%s)
eva-loop --profiles-dir "$PROFILES_DIR" --vault "$_tmp_vault" --no-write --json >/tmp/eva-no-write.json
python -m json.tool /tmp/eva-no-write.json >/dev/null
test ! -e "$_tmp_vault"
```

### 4. Use MCP for bounded checks

Default to `write=false` unless the user explicitly wants vault artifacts and has supplied/accepted a vault path.

| Need | Tool call shape | Notes |
| --- | --- | --- |
| Quick all-up health | `eva_scan_health(scan="all", write=false)` | bounded summary |
| One scanner | `eva_scan_health(scan="memory"/"sessions"/"skills"/"configs", write=false)` | use for narrow triage |
| Memory-provider boundary | `eva_scan_health(scan="memory_provider", write=false)` | evidence only; no memory writes |
| Remediation summary | `eva_compile_remediation(write=false)` | checklist summary, not approval |
| Vault artifacts | same calls with `write=true`, explicit `vault` | review before sharing |
| More evidence | `include_details=true` or `include_bundle=true` | use sparingly; privacy/token risk |

If MCP is unavailable, use the equivalent CLI path (`eva-loop`, scanner commands, `eva-compile-plan`) and report the fallback.

### 5. Write-mode scan

```bash
PROFILES_DIR=/path/to/hermes/profiles
EVA_VAULT=/tmp/eva-vault-test-$(date +%Y%m%d-%H%M%S)
mkdir -p "$EVA_VAULT"
eva-loop --profiles-dir "$PROFILES_DIR" --vault "$EVA_VAULT" --json >/tmp/eva-run.json
python -m json.tool /tmp/eva-run.json >/dev/null
find "$EVA_VAULT" -maxdepth 4 -type f | sort
```

Expected vault families:

```text
evidence/*
context/operator-profile.{json,md}
proposals/pending/*
briefs/latest-{scan.json,brief.md}
plans/latest-plan.{json,md}
health/latest-notification.txt
repairs/*
review-packets/*
```

### 6. Source-mutation guard

If the profile source is a git checkout:

```bash
git -C "$PROFILES_DIR" status --short --branch || true
```

For non-git profile trees:

```bash
find "$PROFILES_DIR" -maxdepth 4 -type f -print | sort > /tmp/eva-source-before.txt
# run EVA
find "$PROFILES_DIR" -maxdepth 4 -type f -print | sort > /tmp/eva-source-after.txt
diff -u /tmp/eva-source-before.txt /tmp/eva-source-after.txt || true
```

Unexpected source mutation is a blocker: stop, preserve evidence, and do not continue write-mode testing until explained.

## Interpretation Rules

- **Healthy complete:** command succeeded; JSON/vault artifacts exist as expected; real inputs produced evidence; no unexplained degraded markers; source profiles unchanged; proposals preserve approval boundaries.
- **Empty:** acceptable for empty/synthetic/omitted inputs; not proof that a real profile was scanned. Report as empty, not healthy-complete.
- **Degraded:** missing, unreadable, malformed, permission-blocked, or unsupported input. Report component and safe path/context; do not claim full coverage.
- **Noisy:** classify as true positive, weak signal, false positive, or unsafe. Unsafe proposals/mutation attempts are bugs/design gaps.
- **Actionable:** evidence-backed and boundary-safe, but still needs operator review unless target class is explicitly auto-apply-safe.

Target-class policy: deterministic EVA-owned generated artifacts may be auto-applied only when policy/tooling allows. Hermes memory, Hermes skill, Hermes profile config, operator profile, scheduler, credential, delivery destination, public repo, and unknown targets are human-gated.

## Public Repo Documentation Rules

- Canonical skill path: `adapters/hermes/skills/eva/SKILL.md`.
- `docs/skills.md` documents install/doctrine; `docs/mcp.md` documents callable tool surface.
- Docs link to the canonical skill instead of duplicating the full body.
- Keep live vaults, memory files, session databases, profile configs, credentials, local scheduler IDs, and delivery destinations out of the repo.
- Use generic `/path/to/...` examples and committed synthetic fixtures only.
- Before public release: readiness script, tests, compileall, Ruff, and `git diff --check` must pass.

## Report Template

```text
EVA report
repo: <path>, commit <short-sha>, status <clean/dirty summary>
mode: <mcp/cli>, write: <false/true>, profiles_dir: <path/omitted>, vault: <path/omitted>
verification: ruff <pass/fail/not-run>; pytest <pass/fail/not-run>; compileall <pass/fail/not-run>; readiness <pass/fail/not-run>
result: <healthy/empty/degraded/noisy/unsafe/actionable>
evidence: <counts or concise summary>
artifacts: <paths generated/reviewed>
source mutation: <none/unexpected/not checked>
privacy review: <share-safe/needs redaction/private>
limits: <not scanned/not verified>
next steps: <manual review/rerun/fix scanner/safe to share>
```

## Common Pitfalls

1. Treating MCP as enough doctrine: MCP exposes tools; this skill defines safe operation.
2. Skipping dry-run/no-write before write-mode or scheduled runs.
3. Letting defaults accidentally scan private local profiles.
4. Creating a vault inside the source repo.
5. Reporting degraded output as complete.
6. Sharing raw vault artifacts without privacy review.
7. Assuming EVA sends notifications; delivery belongs to scheduler/wrapper/gateway.
8. Assuming EVA writes Hermes memory; EVA writes vault artifacts.
9. Hardcoding ShyftR/Mem0/built-in memory in public templates.
10. Treating a remediation plan as approval to apply changes.
11. Ignoring source mutation checks for real profile scans.
12. Leaving generated build/cache artifacts in public-facing diffs.

## Verification Checklist

- [ ] EVA skill loaded before operating/interpreting EVA.
- [ ] Repository status inspected when source/public docs are in scope.
- [ ] Dry-run/no-write verified before write-mode or scheduled run.
- [ ] Real scans used explicit `profiles_dir` and `vault` paths.
- [ ] Vault path outside source repo unless synthetic committed example.
- [ ] MCP calls used `write=false` by default.
- [ ] Generated artifacts listed and privacy-reviewed before sharing.
- [ ] Empty/degraded/noisy/unsafe/actionable results labeled correctly.
- [ ] Source runtime/profile files not unexpectedly modified.
- [ ] Memory-provider, scheduler, notification, and public/private boundaries preserved.
- [ ] Final report includes commands/tool calls, artifacts, limits, and next steps.
