# Remediation Plans

EVA remediation plans turn scan findings and pending proposal records into an operator-readable, checklisted plan. They are generated artifacts, not approval to change the source runtime.

## Purpose

A normal EVA loop now has this shape:

```text
Evidence Sources
  -> Scanners
  -> Evidence Bundle
  -> Operator Profile Compiler
  -> Proposal Engine
  -> Brief Compiler
  -> Remediation Plan Compiler
  -> Operator Review
```

The plan answers the operator questions that a brief alone does not:

- What should I inspect first?
- Which findings are low-risk review work vs approval-gated changes?
- Which exact artifacts should I open?
- What verification should happen before and after remediation?
- Which items require a separate approved workflow?

## Safety invariant

Remediation plans preserve EVA's proposal-only boundary:

- EVA scans durable records.
- EVA writes evidence, proposals, briefs, plans, and notification summaries to the selected vault.
- EVA does not edit memories, skills, profile configs, credentials, scheduler state, delivery destinations, source repositories, or external services.
- Any workflow that applies a plan item must be separate and explicitly approved by the operator.

## Vault artifacts

Write-mode `eva-loop` creates or refreshes these plan artifacts inside the configured vault:

```text
eva-vault/
  plans/
    latest-plan.json
    latest-plan.md
    plan-<timestamp>.json
    plan-<timestamp>.md
  health/
    latest-notification.txt
```

`latest-plan.json` is the machine-readable contract. `latest-plan.md` is the operator checklist. Timestamped copies make scan-to-plan history diffable.

## JSON contract

A remediation plan has this stable top-level shape:

```json
{
  "schema": "eva-remediation-plan/v1",
  "generated_at": "2026-05-06T00:00:00+00:00",
  "source_scan_timestamp": "2026-05-06T00:00:00+00:00",
  "summary": {
    "status": "ok",
    "finding_counts": {
      "memory_contradictions": 0,
      "memory_orphan_references": 0,
      "memory_duplicates": 0,
      "session_repeated_failures": 0,
      "session_tool_failures": 0,
      "skill_oversized": 0,
      "skill_high_patch_frequency": 0,
      "skill_stale": 0,
      "skill_duplicate_names": 0,
      "config_drift": 0
    },
    "proposal_count": 0,
    "tranche_count": 1,
    "total_findings": 0
  },
  "artifacts": {
    "brief": "briefs/latest-brief.md",
    "scan": "briefs/latest-scan.json",
    "pending_proposals_dir": "proposals/pending",
    "plan_markdown": "plans/latest-plan.md",
    "plan_json": "plans/latest-plan.json",
    "notification": "health/latest-notification.txt"
  },
  "tranches": [
    {
      "id": "TR-0",
      "title": "Verify scan completeness",
      "objective": "Confirm the scan is safe to act on before any remediation work starts.",
      "risk": "low",
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

## Standard tranches

The compiler emits tranches only when they are relevant, except for scan verification.

- `TR-0 Verify scan completeness` — always present.
- `TR-1 Review low-risk generated artifacts` — present when there are findings or proposals.
- `TR-2 Skill maintenance candidates` — oversized, stale, duplicate, or frequently patched skills.
- `TR-3 Tool failure runbook candidates` — repeated session/tool failures.
- `TR-4 Memory cleanup candidates` — contradictions, duplicates, stale memory references; approval required.
- `TR-5 Config drift review` — cross-profile drift; approval required.
- `TR-6 Operator profile review` — profile signals; approval required.
- `TR-7 Final verification and outcome recording` — rerun EVA and record proposal outcomes after approved work.

## Status values

- `empty` — no findings and no pending proposals.
- `ok` — findings/proposals exist and no degraded marker was detected.
- `degraded` — scan data contains degraded, partial, warning, or error markers.

A degraded plan is still useful, but it should not be treated as complete evidence until the degraded scanner/source is understood.

## Markdown contract

`latest-plan.md` contains:

- generated timestamp and source scan timestamp;
- scan, brief, proposal, plan, and notification artifact paths;
- finding counts;
- ordered tranches;
- checkbox items for review and verification;
- approval-required markers;
- source proposal IDs when available;
- an operator inbox section for gated items;
- a safety statement that EVA does not apply fixes automatically.

## Notification summary

`health/latest-notification.txt` is a short plain-text summary for schedulers or wrappers to send. It intentionally avoids requiring a parser for the full Markdown plan.

Example:

```text
EVA scan complete.
Status: ok
Findings: memory_contradictions=1, config_drift=2
Pending proposals: 3
Plan: /path/to/eva-vault/plans/latest-plan.md
Brief: /path/to/eva-vault/briefs/latest-brief.md
Next: review TR-0 scan completeness, then TR-1 artifact review.
```

External delivery is not part of EVA core. Hermes cron, cron, launchd, systemd, or a wrapper script may deliver this text through an operator-approved channel.
