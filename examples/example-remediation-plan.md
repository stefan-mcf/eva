# EVA Remediation Plan

Generated: `2026-05-06T00:00:00+00:00`
Source scan: `2026-05-06T00:00:00+00:00`
Status: `ok`

EVA does not apply fixes automatically. This plan is an operator checklist generated from scan evidence and pending proposals.

## Artifacts
- Scan JSON: `/path/to/eva-vault/briefs/latest-scan.json`
- Brief: `/path/to/eva-vault/briefs/latest-brief.md`
- Pending proposals: `/path/to/eva-vault/proposals/pending`
- Plan JSON: `/path/to/eva-vault/plans/latest-plan.json`
- Plan Markdown: `/path/to/eva-vault/plans/latest-plan.md`

## Findings Summary
- `config_drift`: 1
- `memory_contradictions`: 1
- `memory_duplicates`: 0
- `memory_orphan_references`: 0
- `session_repeated_failures`: 1
- `session_tool_failures`: 2
- `skill_duplicate_names`: 0
- `skill_high_patch_frequency`: 0
- `skill_oversized`: 1
- `skill_stale`: 0
- Pending proposals: 4
- Tranches: 8

## Tranches

## TR-0: Verify scan completeness

Objective: Confirm the scan is safe to act on before any remediation work starts.
Risk: `low`
Approval required: `false`

Commands:
- `python -m json.tool /path/to/eva-vault/briefs/latest-scan.json >/dev/null`
- `sed -n '1,160p' /path/to/eva-vault/briefs/latest-brief.md`

Checklist:
- [ ] Confirm the latest scan JSON parses successfully.
- [ ] Inspect the brief for degraded, partial, or missing-source warnings.
- [ ] Confirm profile/source paths and vault paths are the intended ones.
- [ ] Stop before remediation if the scan is degraded in a way that affects the target findings.

Verification:
- [ ] Validated scan JSON and reviewed the latest brief.

## TR-1: Review low-risk generated artifacts

Objective: Inspect generated EVA artifacts and identify which proposals need operator action.
Risk: `low`
Approval required: `false`

Commands:
- `find /path/to/eva-vault/proposals/pending -maxdepth 1 -type f -name '*.json' | sort`
- `sed -n '1,220p' /path/to/eva-vault/plans/latest-plan.md`

Checklist:
- [ ] Open the latest remediation plan and brief.
- [ ] List pending proposal JSON files.
- [ ] Classify findings as true positive, weak signal, false positive, or unsafe.

Verification:
- [ ] All generated artifacts were reviewed before any source mutation.

## TR-2: Skill maintenance candidates

Objective: Review oversized, stale, duplicate, or frequently patched skills and prepare safe maintenance work.
Risk: `low`
Approval required: `false`
Source proposals: `example-skill`

Commands:
- `find /path/to/eva-vault/proposals/pending -maxdepth 1 -type f -name '*skill*.json' | sort`

Checklist:
- [ ] Inspect skill-related proposal evidence.
- [ ] Prefer concise SKILL.md patches with supporting details moved into references/.
- [ ] Do not patch live skills until the relevant proposal is approved.

Verification:
- [ ] Skill maintenance candidates have explicit target files and review notes.

## TR-3: Tool failure runbook candidates

Objective: Convert repeated tool failures into targeted runbook or skill hardening proposals.
Risk: `low`
Approval required: `false`
Source proposals: `example-tool`

Commands:
- `find /path/to/eva-vault/proposals/pending -maxdepth 1 -type f -name '*tool*.json' | sort`

Checklist:
- [ ] Group repeated failures by tool and failure mode.
- [ ] Patch an existing troubleshooting skill when the failure is recurring and understood.
- [ ] Keep unknown/noisy failures as investigation notes until evidence is sufficient.

Verification:
- [ ] Each runbook candidate is backed by repeated evidence or explicitly deferred.

## TR-4: Memory cleanup candidates

Objective: Review memory contradictions, duplicates, and stale references behind a human approval gate.
Risk: `high`
Approval required: `true`
Source proposals: `example-memory`

Commands:
- `find /path/to/eva-vault/proposals/pending -maxdepth 1 -type f -name '*memory*.json' | sort`

Checklist:
- [ ] Inspect sampled evidence before changing durable memory.
- [ ] Merge or rewrite only stable facts that remain useful weeks later.
- [ ] Route ambiguous memory changes to operator review instead of auto-applying.

Verification:
- [ ] Approved memory changes are recorded separately from scan/plan generation.

## TR-5: Config drift review

Objective: Review cross-profile configuration drift and separate intentional lane differences from accidental drift.
Risk: `medium`
Approval required: `true`
Source proposals: `example-config`

Commands:
- `find /path/to/eva-vault/proposals/pending -maxdepth 1 -type f -name '*config*.json' | sort`

Checklist:
- [ ] Inspect drift evidence by profile role group.
- [ ] Preserve intentional model/tool/delegation lane differences.
- [ ] Require explicit approval before changing live profile configs.

Verification:
- [ ] Every config action is classified as intentional drift, safe alignment, or blocked.

## TR-6: Operator profile review

Objective: Review compiled operator-profile signals before promoting anything to durable memory or skills.
Risk: `medium`
Approval required: `true`

Commands:
- `sed -n '1,200p' /path/to/eva-vault/context/operator-profile.md`

Checklist:
- [ ] Review profile signals for stability and privacy.
- [ ] Promote only durable preferences or conventions.
- [ ] Reject transient task state or operational queue state.

Verification:
- [ ] Operator-profile outcomes are approved, rejected, or deferred.

## TR-7: Final verification and outcome recording

Objective: Rerun EVA and record proposal outcomes after approved remediation work is complete.
Risk: `low`
Approval required: `false`

Commands:
- `eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault --no-write --json >/tmp/eva-verify.json`
- `python -m json.tool /tmp/eva-verify.json >/dev/null`

Checklist:
- [ ] Rerun a strict no-write scan after remediation.
- [ ] Compare finding counts before and after approved changes.
- [ ] Record proposal outcomes as applied, rejected, or deferred only after review.

Verification:
- [ ] Post-remediation scan and proposal outcome records exist.

## Operator Inbox

- `TR-4` Memory cleanup candidates — approval required before mutation.
- `TR-5` Config drift review — approval required before mutation.
- `TR-6` Operator profile review — approval required before mutation.

## Safety
- Auto-apply: `false`
- Source mutation allowed by scan/plan generation: `false`
- Use a separate approved workflow for any changes to memories, skills, configs, credentials, scheduler state, or delivery destinations.
