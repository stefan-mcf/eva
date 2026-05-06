# EVA Remediation Plan and Notifications Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a post-scan EVA feature that stores findings, generates an operator-visible checklisted remediation plan, and supports unattended scheduled notification without requiring an open terminal.

**Architecture:** Keep EVA proposal-only and read-mostly. `eva-loop` continues to scan durable runtime records and write only to the EVA vault; a new remediation-plan compiler consumes the combined scan/proposal bundle and writes vault-local plan artifacts. Notification remains adapter/scheduler-driven: EVA emits stable artifacts and stdout summaries; Hermes cron, launchd, systemd, or wrapper scripts deliver them.

**Tech Stack:** Python standard library, existing EVA CLI package, pytest, Ruff, Markdown/JSON vault artifacts, Hermes adapter docs/templates.

**Human Input Requirement:** None for Tranches 0-8. The plan is docs/code/test work only and must not mutate live Hermes profiles, live memories, live skills, credentials, scheduler state, delivery destinations, package registries, or external services. Final Tranche 9 is the only human/operator gate for approving real deployment, persistent scheduler setup, live notification destinations, package publishing, or pushing upstream.

**Side-effect Boundary:**
- Allowed: edit files inside `<repo-root>`; create tests, docs, examples, and source code; run local tests; create temporary directories under `/tmp`.
- Allowed in tests: write temporary EVA vaults using pytest temp paths.
- Forbidden without final human approval: mutate `~/.hermes`, named Hermes profiles, live EVA vaults, real scheduler jobs, real Telegram/Discord/SMS/email destinations, public GitHub visibility, package registries, or external services.

---

## Tranche 0: Baseline and Scope Lock

**Objective:** Capture current repo state, current behavior, and the exact feature boundary before changing code.

**Files:**
- Read: `README.md`
- Read: `docs/architecture.md`
- Read: `docs/cli.md`
- Read: `docs/hermes-adapter.md`
- Read: `docs/safety.md`
- Read: `src/eva/loop.py`
- Read: `src/eva/proposers/propose_patches.py`
- Read: `tests/test_eva_pipeline.py`

**Steps:**
1. Run `git status --short --branch` from repo root.
   - Expected: clean or only intentional plan file changes.
2. Run `PYTHONPATH=src python -m pytest -q`.
   - Expected: existing test suite passes before feature work.
3. Run `PYTHONPATH=src python -m ruff check .`.
   - Expected: no lint failures.
4. Read the listed docs/source files and verify the current invariant:
   - scan writes only vault artifacts;
   - proposals are drafts;
   - no auto-apply path exists;
   - unattended scheduling is documented only generically.
5. Add a short baseline note to the implementation branch/session notes if needed, but do not create runtime state.

**Verification:**
- Test/lint results captured in terminal.
- No files outside `<repo-root>` changed.

**Stop Boundary:** Baseline is known and the feature remains plan/artifact/notification-surface only, not an auto-fixer.

---

## Tranche 1: Define Remediation Plan Data Contract

**Objective:** Specify the JSON and Markdown contract for generated remediation plans.

**Files:**
- Create: `docs/remediation-plans.md`
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Test reference later: `tests/test_eva_remediation_plans.py`

**Plan Contract:**

`plans/latest-plan.json` should contain:

```json
{
  "schema": "eva-remediation-plan/v1",
  "generated_at": "2026-05-06T00:00:00+00:00",
  "source_scan_timestamp": "...",
  "summary": {
    "status": "ok|empty|degraded",
    "finding_counts": {},
    "proposal_count": 0,
    "tranche_count": 0
  },
  "artifacts": {
    "brief": "briefs/latest-brief.md",
    "scan": "briefs/latest-scan.json",
    "pending_proposals_dir": "proposals/pending"
  },
  "tranches": [
    {
      "id": "TR-0",
      "title": "Verify scan completeness",
      "objective": "Confirm the scan is safe to act on.",
      "risk": "low|medium|high",
      "approval_required": false,
      "commands": [],
      "checklist": [],
      "verification": [],
      "source_proposal_ids": []
    }
  ],
  "operator_inbox": [],
  "safety": {
    "auto_apply": false,
    "source_mutation_allowed": false,
    "notes": []
  }
}
```

`plans/latest-plan.md` should contain:
- title and generated timestamp;
- source scan/brief/proposal paths;
- findings summary;
- ordered tranches with checkbox items;
- exact safe commands where possible;
- verification commands;
- operator review/inbox section;
- explicit statement that EVA does not apply fixes automatically.

**Steps:**
1. Write `docs/remediation-plans.md` with the contract above, examples, and safety boundary.
2. Update `docs/architecture.md` pipeline diagrams to include `Remediation Plan Compiler` after `Proposal Engine`/`Brief Compiler`.
3. Update `docs/configuration.md` vault layout to include:
   ```text
   plans/
     latest-plan.json
     latest-plan.md
   ```
4. Keep language runtime-agnostic where possible; put Hermes-specific delivery in adapter docs later.

**Verification:**
- `python -m compileall -q src tests` still passes.
- `git diff -- docs/remediation-plans.md docs/architecture.md docs/configuration.md` shows docs-only contract changes.

**Stop Boundary:** Contract is documented before implementation.

---

## Tranche 2: Add Remediation Plan Compiler Skeleton

**Objective:** Add a pure Python compiler that converts an existing scan bundle and proposals into an in-memory plan dictionary and Markdown string.

**Files:**
- Create: `src/eva/compilers/compile_remediation_plan.py`
- Modify: `src/eva/compilers/__init__.py` only if existing package style requires it
- Create: `tests/test_eva_remediation_plans.py`

**Implementation Shape:**

Create functions:

```python
def compile_remediation_plan(scan_bundle: dict[str, Any], vault: str | Path | None = None) -> dict[str, Any]:
    ...


def render_remediation_plan_markdown(plan: dict[str, Any]) -> str:
    ...
```

Do not write files in these functions. File writes are handled by `eva.loop` in a later tranche.

**Steps:**
1. Write a failing test that calls `compile_remediation_plan({"scanner": "combined", "timestamp": "..."})`.
   - Expected schema is `eva-remediation-plan/v1`.
   - Expected safety flags: `auto_apply: false`, `source_mutation_allowed: false`.
2. Run the targeted test and confirm it fails because the module does not exist.
3. Create `compile_remediation_plan.py` with minimal implementation.
4. Add `render_remediation_plan_markdown` with a minimal heading and safety statement.
5. Run targeted test again.
6. Run full tests.

**Verification Commands:**
```bash
PYTHONPATH=src python -m pytest tests/test_eva_remediation_plans.py -q
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m ruff check .
```

**Expected:** all pass.

**Stop Boundary:** Compiler exists, is pure, and has no filesystem side effects.

---

## Tranche 3: Map Findings and Proposals into Ordered Tranches

**Objective:** Make remediation plans useful by translating actual EVA finding/proposal categories into ordered operator tranches.

**Files:**
- Modify: `src/eva/compilers/compile_remediation_plan.py`
- Modify: `tests/test_eva_remediation_plans.py`

**Tranche Mapping:**

Generate these standard tranches when evidence exists:

1. `TR-0 Verify scan completeness`
   - Always present.
   - Checklist: validate latest scan JSON, inspect degraded markers, confirm vault/source paths.

2. `TR-1 Review low-risk generated artifacts`
   - Always present when proposals or findings exist.
   - Checklist: open latest brief, list pending proposals, inspect plan.

3. `TR-2 Skill maintenance candidates`
   - Present for oversized skills, duplicate skills, stale skills, high patch frequency.
   - Commands should be read-only by default, e.g. list proposal JSON and inspect skill paths.

4. `TR-3 Tool failure runbook candidates`
   - Present for repeated tool failures/session scanner findings.
   - Checklist: group failures, decide whether to patch existing skills or create runbook.

5. `TR-4 Memory cleanup candidates`
   - Present for contradictions, duplicates, orphan/stale memory references.
   - High risk; approval required.
   - No auto-write commands.

6. `TR-5 Config drift review`
   - Present for config drift findings.
   - Medium/high risk; approval required before mutation.

7. `TR-6 Operator profile review`
   - Present when operator profile proposals/signals exist.
   - Approval required.

8. `TR-7 Final verification and outcome recording`
   - Always present when anything actionable exists.
   - Commands: rerun `eva-loop --no-write --json`; rerun write-mode only with explicit vault if approved; record proposal outcomes using existing `eva-propose-patches --record-outcome` once work is actually applied/rejected.

**Steps:**
1. Write fixture scan bundle with memory contradictions, repeated failures, oversized skills, config drift, and proposal summary.
2. Assert plan includes relevant tranches in stable order.
3. Assert approval-required is true for memory/config/operator-profile tranches.
4. Assert no command mutates source files.
5. Implement mapping helpers:
   - `_finding_counts(scan_bundle)`
   - `_proposal_ids_by_kind(scan_bundle)`
   - `_standard_tranche(...)`
   - `_has_degraded_markers(scan_bundle)`
6. Render Markdown with checkboxes:
   ```markdown
   - [ ] Inspect `briefs/latest-brief.md`
   ```
7. Re-run targeted and full tests.

**Verification Commands:**
```bash
PYTHONPATH=src python -m pytest tests/test_eva_remediation_plans.py -q
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m ruff check .
```

**Stop Boundary:** Plans are actionable checklists but still non-mutating by default.

---

## Tranche 4: Persist Plan Artifacts from `eva-loop`

**Objective:** Integrate remediation plan generation into `eva-loop` write mode and JSON/stdout output.

**Files:**
- Modify: `src/eva/loop.py`
- Modify: `tests/test_eva_pipeline.py`
- Modify: `tests/test_eva_remediation_plans.py` if integration tests are separated

**Behavior:**
- In write mode, create/update:
  - `plans/latest-plan.json`
  - `plans/latest-plan.md`
  - timestamped `plans/plan-<stamp>.json`
  - timestamped `plans/plan-<stamp>.md`
- Add `remediation_plan` to the in-memory bundle.
- In `--json`, include the plan dictionary but not duplicate Markdown if output size becomes too large. Prefer a compact `remediation_plan` object plus written paths.
- In `--no-write`, compile in-memory plan but do not create a vault or plan files.

**Steps:**
1. Write a test that runs `run_all(..., write=False)` against a temp vault path and asserts the vault path does not exist and `remediation_plan` exists in returned bundle.
2. Write a test that runs `run_all(..., write=True)` and asserts `plans/latest-plan.json` and `plans/latest-plan.md` exist under the temp vault.
3. Implement integration in `src/eva/loop.py` after proposals and brief generation.
4. Ensure timestamp naming matches existing brief naming style.
5. Run targeted and full tests.

**Verification Commands:**
```bash
PYTHONPATH=src python -m pytest tests/test_eva_pipeline.py tests/test_eva_remediation_plans.py -q
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m ruff check .
```

**Stop Boundary:** `eva-loop` writes plan artifacts only inside selected vault, never source profiles.

---

## Tranche 5: Add CLI Surface for Plan Compilation and Inspection

**Objective:** Let operators generate or re-render a plan from an existing scan without rerunning all scanners.

**Files:**
- Modify: `pyproject.toml`
- Create or modify: `src/eva/compilers/compile_remediation_plan.py` CLI `main()`
- Modify: `docs/cli.md`
- Modify: `tests/test_eva_remediation_plans.py`

**CLI:**

Add console script:

```text
eva-compile-plan = eva.compilers.compile_remediation_plan:main
```

Supported usage:

```bash
eva-compile-plan /path/to/eva-vault/briefs/latest-scan.json --vault /path/to/eva-vault
eva-compile-plan /path/to/eva-vault/briefs/latest-scan.json --markdown
eva-compile-plan /path/to/eva-vault/briefs/latest-scan.json --json
```

Default can print Markdown to stdout. `--write` may write plan artifacts under vault, but default should be stdout-only unless the implementation chooses to mirror existing compiler conventions. If `--write` is added, require `--vault`.

**Steps:**
1. Write tests for CLI argument parsing via direct `main()` helper or subprocess if existing tests use subprocess.
2. Add console script in `pyproject.toml`.
3. Implement `main()`.
4. Update `docs/cli.md` with command purpose, inputs, outputs, read/write behavior, and examples.
5. Run package entrypoint smoke after editable install if needed.

**Verification Commands:**
```bash
python -m pip install -e '.[dev]'
eva-compile-plan --help
PYTHONPATH=src python -m pytest tests/test_eva_remediation_plans.py -q
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m ruff check .
```

**Stop Boundary:** Operators can inspect/rebuild plans without rerunning the scan.

---

## Tranche 6: Document Unattended Scheduling and Notification Semantics

**Objective:** Make it explicit that EVA does not require an active terminal when scheduled, and that notification is owned by the scheduler/wrapper/adapter.

**Files:**
- Create: `docs/scheduling-and-notifications.md`
- Modify: `README.md`
- Modify: `docs/hermes-adapter.md`
- Modify: `docs/architecture.md`
- Modify: `adapters/hermes/README.md`
- Modify: `adapters/hermes/skills/eva/SKILL.md`

**Required Documentation Points:**
- EVA is a CLI that runs, writes artifacts, prints output, and exits.
- A terminal only needs to stay open for a manual foreground run.
- For unattended runs, use Hermes cron, OS cron, launchd, systemd timer, or another scheduler.
- EVA itself does not send messages to Telegram/Discord/email/etc.; wrappers/schedulers do.
- Hermes cron can deliver the final agent response to the configured origin/channel if created with that delivery route.
- OS schedulers should redirect stdout/stderr to logs and optionally call a notifier script.
- If notification fails, vault artifacts remain the source of truth.
- Live delivery destinations and scheduler IDs are private runtime state and must not be committed.

**Example Sections:**
1. Manual foreground run.
2. Hermes cron conceptual setup.
3. OS cron example with log redirection.
4. macOS launchd notes.
5. Linux systemd timer notes.
6. Notification failure recovery.
7. Artifact paths to inspect.

**Steps:**
1. Draft `docs/scheduling-and-notifications.md` using placeholders only.
2. Link it from README and Hermes adapter docs.
3. Update bundled Hermes skill with a short scheduling section and pitfall list.
4. Ensure docs do not contain private chat IDs, local scheduler IDs, or live destination names.

**Verification Commands:**
```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m ruff check .
python scripts/public_readiness_check.py
```

**Stop Boundary:** A new user can understand whether a terminal must stay open and where notifications come from.

---

## Tranche 7: Add Notification Summary Artifact

**Objective:** Provide a concise, scheduler-friendly notification text that wrappers can send without parsing Markdown briefs.

**Files:**
- Modify: `src/eva/compilers/compile_remediation_plan.py` or create `src/eva/compilers/compile_notification.py`
- Modify: `src/eva/loop.py`
- Modify: `tests/test_eva_remediation_plans.py`
- Modify: `docs/scheduling-and-notifications.md`
- Modify: `docs/cli.md` if a CLI option is added

**Behavior:**
- Generate a short notification summary in write mode:
  - `health/latest-notification.txt` or `briefs/latest-notification.txt`
- Include:
  - scan complete status;
  - finding counts;
  - proposal count;
  - remediation plan path;
  - brief path;
  - degraded warning if present;
  - next recommended action.
- Keep it plain text and safe for terminal/chat display.

**Example Output:**

```text
EVA scan complete.
Status: ok
Findings: memory=4, sessions=3, skills=2, configs=17
Pending proposals: 5
Plan: /path/to/eva-vault/plans/latest-plan.md
Brief: /path/to/eva-vault/briefs/latest-brief.md
Next: review TR-0 scan completeness, then TR-1 artifact review.
```

**Steps:**
1. Write test that compiles a notification summary from a fixture plan.
2. Assert output is under a small line/character limit suitable for chat.
3. Integrate write-mode artifact into `eva-loop`.
4. Add docs showing wrappers should send this text, not raw private JSON.
5. Run tests.

**Verification Commands:**
```bash
PYTHONPATH=src python -m pytest tests/test_eva_remediation_plans.py tests/test_eva_pipeline.py -q
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m ruff check .
```

**Stop Boundary:** EVA produces a notification-ready artifact but still does not own external delivery.

---

## Tranche 8: Public Readiness, Examples, and Regression Gates

**Objective:** Ensure the new feature is documented, tested, public-safe, and easy to validate from a clean clone.

**Files:**
- Modify: `examples/` if adding synthetic plan examples
- Modify: `scripts/public_readiness_check.py` if it should require new docs/artifacts
- Modify: `docs/testing-quickstart.md`
- Modify: `README.md`

**Steps:**
1. Add synthetic examples if useful:
   - `examples/example-remediation-plan.json`
   - `examples/example-remediation-plan.md`
   - `examples/example-notification.txt`
2. Update testing quickstart to mention expected plan artifacts after write-mode run.
3. Update `public_readiness_check.py` to require `docs/remediation-plans.md` and `docs/scheduling-and-notifications.md` if consistent with existing readiness policy.
4. Run no-write smoke and verify no vault creation.
5. Run write-mode smoke against temp profiles/vault and verify plan/notification artifacts exist only in temp vault.
6. Run full release-readiness gate.

**Verification Commands:**
```bash
_tmp_vault=/tmp/eva-no-write-vault-$(date +%s)
PYTHONPATH=src eva-loop --vault "$_tmp_vault" --no-write --json >/tmp/eva-no-write.json
python -m json.tool /tmp/eva-no-write.json >/dev/null
test ! -e "$_tmp_vault"

_tmp_root=$(mktemp -d)
mkdir -p "$_tmp_root/profiles"
PYTHONPATH=src eva-loop --profiles-dir "$_tmp_root/profiles" --vault "$_tmp_root/vault" --json >/tmp/eva-write.json
python -m json.tool /tmp/eva-write.json >/dev/null
test -f "$_tmp_root/vault/plans/latest-plan.json"
test -f "$_tmp_root/vault/plans/latest-plan.md"
test -f "$_tmp_root/vault/briefs/latest-brief.md"

PYTHONPATH=src python -m ruff check .
PYTHONPATH=src python -m pytest -q
python -m compileall -q src tests
python scripts/public_readiness_check.py
git diff --check
```

**Stop Boundary:** Feature is covered by tests, docs, examples/readiness gates, and no-write/write-mode safety checks.

---

## Tranche 9: Human Review and Optional Deployment Gates

**Objective:** Collect all actions that require operator judgement or external side effects.

**Files:**
- No required code files.
- Optional local runtime files only after explicit approval.

**Human-Only Decisions:**
1. Approve pushing implementation branch/commit to remote.
2. Approve package publishing, release tagging, or repository visibility changes.
3. Approve installing updated EVA package into any live Hermes profile environment.
4. Approve creating or updating real Hermes cron jobs.
5. Approve creating launchd/systemd/cron scheduler entries.
6. Approve real delivery destination/channel for notifications.
7. Approve any future executor that applies remediation checklist items.
8. Approve mutation of live memories, skills, profile configs, or runtime state based on generated plans.

**Suggested Deployment Smoke After Approval:**
```bash
eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault --json >/tmp/eva-live-smoke.json
python -m json.tool /tmp/eva-live-smoke.json >/dev/null
sed -n '1,80p' /path/to/eva-vault/health/latest-notification.txt
sed -n '1,120p' /path/to/eva-vault/plans/latest-plan.md
```

**Hermes Cron Prompt Shape After Approval:**

```text
Run EVA unattended scan using explicit paths. Execute eva-loop with the configured profiles dir and vault. Read the generated latest-notification.txt and latest-plan.md paths. Deliver a concise operator notification that includes status, finding counts, pending proposal count, plan path, brief path, and next recommended tranche. Do not apply fixes or mutate source profiles.
```

**Stop Boundary:** No live deployment or external notification exists until explicitly approved.

---

## Final Acceptance Criteria

- `eva-loop --no-write --json` generates an in-memory remediation plan and creates no vault.
- `eva-loop --profiles-dir <tmp> --vault <tmp-vault> --json` writes:
  - `briefs/latest-scan.json`
  - `briefs/latest-brief.md`
  - `plans/latest-plan.json`
  - `plans/latest-plan.md`
  - notification summary artifact if Tranche 7 is implemented.
- Pending proposal JSON files remain proposal-only and include `auto_apply: false`.
- Remediation plans contain ordered, checklisted tranches and approval gates.
- Memory/config/profile mutation is never performed by EVA scan/plan generation.
- Docs clearly answer: no, a terminal does not need to stay open if a scheduler runs EVA; notifications are delivered by Hermes cron or an OS/wrapper scheduler, not by EVA core itself.
- Public readiness checks pass.
- All manual/external side effects are isolated in Tranche 9.
