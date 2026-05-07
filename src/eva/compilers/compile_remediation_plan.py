"""Compile EVA remediation plans and notification summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eva.common import EVA_VAULT_DIR, atomic_write_json, atomic_write_text, read_json, utc_now
from eva.repair.schemas import ALWAYS_HUMAN_GATED_TARGET_CLASSES, SAFE_AUTO_APPLY_TARGET_CLASSES
from eva.settings import load_settings
from eva.validators import validate_proposal_actionability, validate_scan_completeness

PLAN_SCHEMA = "eva-remediation-plan/v1"


PROPOSAL_KINDS_BY_TRANCHE = {
    "TR-2": {"skill_restructure", "skill_rewrite", "skill_duplicate_review", "skill_stale_review", "session_skill_patch_review"},
    "TR-3": {"tool_failure_runbook", "tool_failure_triage", "session_correction_review"},
    "TR-4": {"memory_merge", "memory_cleanup"},
    "TR-5": {"config_alignment"},
    "TR-6": {"operator_profile_review"},
}


def _rel_or_abs(vault: Path | None, relative: str) -> str:
    if vault is None:
        return relative
    return str(vault / relative)


def _len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _finding_counts(scan_bundle: dict[str, Any]) -> dict[str, int]:
    memory = scan_bundle.get("memory", {}) if isinstance(scan_bundle.get("memory", {}), dict) else {}
    sessions = scan_bundle.get("sessions", {}) if isinstance(scan_bundle.get("sessions", {}), dict) else {}
    skills = scan_bundle.get("skills", {}) if isinstance(scan_bundle.get("skills", {}), dict) else {}
    configs = scan_bundle.get("configs", {}) if isinstance(scan_bundle.get("configs", {}), dict) else {}
    session_summary = sessions.get("summary", {}) if isinstance(sessions.get("summary", {}), dict) else {}
    skill_summary = skills.get("summary", {}) if isinstance(skills.get("summary", {}), dict) else {}
    config_summary = configs.get("summary", {}) if isinstance(configs.get("summary", {}), dict) else {}
    return {
        "memory_contradictions": _len(memory.get("contradictions")),
        "memory_orphan_references": _len(memory.get("orphan_references")),
        "memory_duplicates": _len(memory.get("duplicates")),
        "session_corrections": int(session_summary.get("corrections_found", 0) or 0),
        "session_repeated_failures": _len(sessions.get("repeated_failures")),
        "session_skill_patches": int(session_summary.get("skill_patches_found", 0) or 0),
        "session_tool_failures": int(session_summary.get("tool_failures_found", 0) or 0),
        "skill_oversized": _len(skills.get("oversized_skills")),
        "skill_high_patch_frequency": _len(skills.get("high_patch_frequency")),
        "skill_stale": _len(skills.get("stale_skills")) or int(skill_summary.get("stale_count", 0) or 0),
        "skill_duplicate_names": _len(skills.get("duplicate_names")) or int(skill_summary.get("duplicate_name_count", 0) or 0),
        "config_drift": _len(configs.get("drift")) or int(config_summary.get("drift_findings", 0) or 0),
    }


def _proposal_list(scan_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    summary = scan_bundle.get("proposal_summary", {})
    if isinstance(summary, dict) and isinstance(summary.get("proposals"), list):
        return [p for p in summary["proposals"] if isinstance(p, dict)]
    if isinstance(scan_bundle.get("proposals"), list):
        return [p for p in scan_bundle["proposals"] if isinstance(p, dict)]
    return []


def _proposal_ids_for(proposals: list[dict[str, Any]], tranche_id: str) -> list[str]:
    kinds = PROPOSAL_KINDS_BY_TRANCHE.get(tranche_id, set())
    return [str(p.get("id")) for p in proposals if p.get("kind") in kinds and p.get("id")]


def _has_degraded_markers(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"degraded", "partial", "error", "errors", "warnings"} and item:
                return True
            if key_text == "status" and str(item).lower() in {"degraded", "partial", "error", "failed"}:
                return True
            if _has_degraded_markers(item):
                return True
    elif isinstance(value, list):
        return any(_has_degraded_markers(item) for item in value)
    return False


def _standard_tranche(
    tranche_id: str,
    title: str,
    objective: str,
    *,
    risk: str = "low",
    approval_required: bool = False,
    commands: list[str] | None = None,
    checklist: list[str] | None = None,
    verification: list[str] | None = None,
    source_proposal_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": tranche_id,
        "title": title,
        "objective": objective,
        "risk": risk,
        "approval_required": approval_required,
        "commands": commands or [],
        "checklist": checklist or [],
        "verification": verification or [],
        "source_proposal_ids": source_proposal_ids or [],
    }


def compile_remediation_plan(
    scan_bundle: dict[str, Any], vault: str | Path | None = None
) -> dict[str, Any]:
    """Compile a checklisted remediation plan without writing files."""
    vault_path = Path(vault).expanduser() if vault is not None else None
    counts = _finding_counts(scan_bundle)
    proposals = _proposal_list(scan_bundle)
    total_findings = sum(counts.values())
    degraded = _has_degraded_markers(scan_bundle)
    settings = load_settings(vault_path) if vault_path is not None else {}
    scan_validation = validate_scan_completeness(scan_bundle, expected_vault=str(vault_path) if vault_path else None)
    actionability_validation = validate_proposal_actionability(scan_bundle, settings)
    status = "degraded" if degraded else "ok" if total_findings or proposals else "empty"
    if scan_validation.get("status") == "failed" or actionability_validation.get("status") == "failed":
        status = "blocked" if actionability_validation.get("suppressed_active_kinds") else "degraded"
    tranches: list[dict[str, Any]] = [
        _standard_tranche(
            "TR-0",
            "Verify scan completeness",
            "Confirm the scan is safe to act on before any remediation work starts.",
            commands=[
                f"python -m json.tool {_rel_or_abs(vault_path, 'briefs/latest-scan.json')} >/dev/null",
                f"sed -n '1,160p' {_rel_or_abs(vault_path, 'briefs/latest-brief.md')}",
            ],
            checklist=[
                "Confirm the latest scan JSON parses successfully.",
                "Inspect the brief for degraded, partial, or missing-source warnings.",
                "Confirm profile/source paths and vault paths are the intended ones.",
                "Stop before remediation if the scan is degraded in a way that affects the target findings.",
            ],
            verification=["Validated scan JSON and reviewed the latest brief."],
        )
    ]
    if total_findings or proposals:
        tranches.append(
            _standard_tranche(
                "TR-1",
                "Review low-risk generated artifacts",
                "Inspect generated EVA artifacts and identify which proposals need operator action.",
                commands=[
                    f"find {_rel_or_abs(vault_path, 'proposals/pending')} -maxdepth 1 -type f -name '*.json' | sort",
                    f"sed -n '1,220p' {_rel_or_abs(vault_path, 'plans/latest-plan.md')}",
                ],
                checklist=[
                    "Open the latest remediation plan and brief.",
                    "List pending proposal JSON files.",
                    "Classify findings as true positive, weak signal, false positive, or unsafe.",
                ],
                verification=["All generated artifacts were reviewed before any source mutation."],
            )
        )
    if any(counts[key] for key in ("skill_oversized", "skill_high_patch_frequency", "skill_stale", "skill_duplicate_names")):
        tranches.append(
            _standard_tranche(
                "TR-2",
                "Skill maintenance candidates",
                "Review oversized, stale, duplicate, or frequently patched skills and prepare safe maintenance work.",
                commands=[f"find {_rel_or_abs(vault_path, 'proposals/pending')} -maxdepth 1 -type f -name '*skill*.json' | sort"],
                checklist=[
                    "Inspect skill-related proposal evidence.",
                    "Prefer concise SKILL.md patches with supporting details moved into references/.",
                    "Do not patch live skills until the relevant proposal is approved.",
                ],
                verification=["Skill maintenance candidates have explicit target files and review notes."],
                source_proposal_ids=_proposal_ids_for(proposals, "TR-2"),
            )
        )
    if counts["session_repeated_failures"] or counts["session_tool_failures"]:
        tranches.append(
            _standard_tranche(
                "TR-3",
                "Tool failure runbook candidates",
                "Convert repeated tool failures into targeted runbook or skill hardening proposals.",
                commands=[f"find {_rel_or_abs(vault_path, 'proposals/pending')} -maxdepth 1 -type f -name '*tool*.json' | sort"],
                checklist=[
                    "Group repeated failures by tool and failure mode.",
                    "Patch an existing troubleshooting skill when the failure is recurring and understood.",
                    "Keep unknown/noisy failures as investigation notes until evidence is sufficient.",
                ],
                verification=["Each runbook candidate is backed by repeated evidence or explicitly deferred."],
                source_proposal_ids=_proposal_ids_for(proposals, "TR-3"),
            )
        )
    if any(counts[key] for key in ("memory_contradictions", "memory_orphan_references", "memory_duplicates")):
        tranches.append(
            _standard_tranche(
                "TR-4",
                "Memory cleanup candidates",
                "Review memory contradictions, duplicates, and stale references behind a human approval gate.",
                risk="high",
                approval_required=True,
                commands=[f"find {_rel_or_abs(vault_path, 'proposals/pending')} -maxdepth 1 -type f -name '*memory*.json' | sort"],
                checklist=[
                    "Inspect sampled evidence before changing durable memory.",
                    "Merge or rewrite only stable facts that remain useful weeks later.",
                    "Route ambiguous memory changes to operator review instead of auto-applying.",
                ],
                verification=["Approved memory changes are recorded separately from scan/plan generation."],
                source_proposal_ids=_proposal_ids_for(proposals, "TR-4"),
            )
        )
    if counts["config_drift"]:
        tranches.append(
            _standard_tranche(
                "TR-5",
                "Config drift review",
                "Review cross-profile configuration drift and separate intentional lane differences from accidental drift.",
                risk="medium",
                approval_required=True,
                commands=[f"find {_rel_or_abs(vault_path, 'proposals/pending')} -maxdepth 1 -type f -name '*config*.json' | sort"],
                checklist=[
                    "Inspect drift evidence by profile role group.",
                    "Preserve intentional model/tool/delegation lane differences.",
                    "Require explicit approval before changing live profile configs.",
                ],
                verification=["Every config action is classified as intentional drift, safe alignment, or blocked."],
                source_proposal_ids=_proposal_ids_for(proposals, "TR-5"),
            )
        )
    if scan_bundle.get("operator_profile") or _proposal_ids_for(proposals, "TR-6"):
        tranches.append(
            _standard_tranche(
                "TR-6",
                "Operator profile review",
                "Review compiled operator-profile signals before promoting anything to durable memory or skills.",
                risk="medium",
                approval_required=True,
                commands=[f"sed -n '1,200p' {_rel_or_abs(vault_path, 'context/operator-profile.md')}"] if vault_path else [],
                checklist=[
                    "Review profile signals for stability and privacy.",
                    "Promote only durable preferences or conventions.",
                    "Reject transient task state or operational queue state.",
                ],
                verification=["Operator-profile outcomes are approved, rejected, or deferred."],
                source_proposal_ids=_proposal_ids_for(proposals, "TR-6"),
            )
        )
    if total_findings or proposals:
        tranches.append(
            _standard_tranche(
                "TR-7",
                "Final verification and outcome recording",
                "Rerun EVA and record proposal outcomes after approved remediation work is complete.",
                commands=[
                    "eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault --no-write --json >/tmp/eva-verify.json",
                    "python -m json.tool /tmp/eva-verify.json >/dev/null",
                ],
                checklist=[
                    "Rerun a strict no-write scan after remediation.",
                    "Compare finding counts before and after approved changes.",
                    "Record proposal outcomes as applied, rejected, or deferred only after review.",
                ],
                verification=["Post-remediation scan and proposal outcome records exist."],
            )
        )
    plan = {
        "schema": PLAN_SCHEMA,
        "generated_at": utc_now(),
        "source_scan_timestamp": scan_bundle.get("timestamp"),
        "summary": {
            "status": status,
            "finding_counts": counts,
            "proposal_count": len(proposals),
            "tranche_count": len(tranches),
            "total_findings": total_findings,
        },
        "artifacts": {
            "brief": _rel_or_abs(vault_path, "briefs/latest-brief.md"),
            "scan": _rel_or_abs(vault_path, "briefs/latest-scan.json"),
            "pending_proposals_dir": _rel_or_abs(vault_path, "proposals/pending"),
            "plan_markdown": _rel_or_abs(vault_path, "plans/latest-plan.md"),
            "plan_json": _rel_or_abs(vault_path, "plans/latest-plan.json"),
            "notification": _rel_or_abs(vault_path, "health/latest-notification.txt"),
            "repair_drafts_dir": _rel_or_abs(vault_path, "repairs/drafts"),
            "repair_ledger_json": _rel_or_abs(vault_path, "repairs/ledger/latest-ledger.json"),
            "repair_ledger_markdown": _rel_or_abs(vault_path, "repairs/ledger/latest-ledger.md"),
            "repair_closeout": _rel_or_abs(vault_path, "repairs/ledger/latest-closeout.md"),
        },
        "validation": {
            "scan_completeness": scan_validation,
            "proposal_actionability": actionability_validation,
        },
        "tranches": tranches,
        "operator_inbox": [
            tranche
            for tranche in tranches
            if tranche.get("approval_required") or tranche.get("risk") == "high"
        ],
        "safety": {
            "auto_apply": False,
            "source_mutation_allowed": False,
            "repair_module_available": True,
            "auto_draft_allowed": True,
            "auto_apply_allowed_target_classes": sorted(SAFE_AUTO_APPLY_TARGET_CLASSES),
            "always_human_gated_target_classes": sorted(ALWAYS_HUMAN_GATED_TARGET_CLASSES),
            "notes": [
                "EVA remediation plans are checklists, not approval to mutate source runtime state.",
                "EVA-Repair may draft bundles and may only auto-apply deterministic EVA-owned generated artifacts.",
                "Memory, skills, configs, credentials, scheduler state, delivery destinations, public repos, and operator-profile promotion remain human-gated.",
            ],
        },
    }
    plan["summary"]["tranche_count"] = len(plan["tranches"])
    return plan


def render_remediation_plan_markdown(plan: dict[str, Any]) -> str:
    """Render a remediation plan as operator-readable Markdown."""
    summary = plan.get("summary", {})
    artifacts = plan.get("artifacts", {})
    counts = summary.get("finding_counts", {}) if isinstance(summary.get("finding_counts"), dict) else {}
    lines = [
        "# EVA Remediation Plan",
        "",
        f"Generated: `{plan.get('generated_at', '')}`",
        f"Source scan: `{plan.get('source_scan_timestamp', '')}`",
        f"Status: `{summary.get('status', 'unknown')}`",
        "",
        "EVA does not apply fixes automatically. This plan is an operator checklist generated from scan evidence and pending proposals.",
        "",
        "## Artifacts",
        f"- Scan JSON: `{artifacts.get('scan', 'briefs/latest-scan.json')}`",
        f"- Brief: `{artifacts.get('brief', 'briefs/latest-brief.md')}`",
        f"- Pending proposals: `{artifacts.get('pending_proposals_dir', 'proposals/pending')}`",
        f"- Plan JSON: `{artifacts.get('plan_json', 'plans/latest-plan.json')}`",
        f"- Plan Markdown: `{artifacts.get('plan_markdown', 'plans/latest-plan.md')}`",
        f"- Repair drafts: `{artifacts.get('repair_drafts_dir', 'repairs/drafts')}`",
        f"- Repair ledger: `{artifacts.get('repair_ledger_markdown', 'repairs/ledger/latest-ledger.md')}`",
        f"- Repair closeout: `{artifacts.get('repair_closeout', 'repairs/ledger/latest-closeout.md')}`",
        "",
        "## Validation",
    ]
    validation = plan.get("validation", {}) if isinstance(plan.get("validation", {}), dict) else {}
    if validation:
        for name, result in validation.items():
            lines.append(f"- `{name}`: `{result.get('status', 'unknown')}`")
            missing = result.get("missing_proposal_kinds") or []
            suppressed = result.get("suppressed_active_kinds") or []
            if missing:
                lines.append("  - Missing proposal kinds: " + ", ".join(f"`{kind}`" for kind in missing))
            if suppressed:
                lines.append("  - Suppressed active kinds: " + ", ".join(f"`{kind}`" for kind in suppressed))
    else:
        lines.append("- No validator results available.")
    lines.extend([
        "",
        "## Findings Summary",
    ])
    if counts:
        for key in sorted(counts):
            lines.append(f"- `{key}`: {counts[key]}")
    else:
        lines.append("- No finding counts available.")
    lines.extend([
        f"- Pending proposals: {summary.get('proposal_count', 0)}",
        f"- Tranches: {summary.get('tranche_count', 0)}",
        "",
        "## Tranches",
    ])
    for tranche in plan.get("tranches", []):
        lines.extend(
            [
                "",
                f"## {tranche.get('id')}: {tranche.get('title')}",
                "",
                f"Objective: {tranche.get('objective')}",
                f"Risk: `{tranche.get('risk', 'unknown')}`",
                f"Approval required: `{str(tranche.get('approval_required', False)).lower()}`",
            ]
        )
        proposal_ids = tranche.get("source_proposal_ids") or []
        if proposal_ids:
            lines.append("Source proposals: " + ", ".join(f"`{pid}`" for pid in proposal_ids))
        commands = tranche.get("commands") or []
        if commands:
            lines.extend(["", "Commands:"])
            for command in commands:
                lines.append(f"- `{command}`")
        checklist = tranche.get("checklist") or []
        if checklist:
            lines.extend(["", "Checklist:"])
            for item in checklist:
                lines.append(f"- [ ] {item}")
        verification = tranche.get("verification") or []
        if verification:
            lines.extend(["", "Verification:"])
            for item in verification:
                lines.append(f"- [ ] {item}")
    inbox = plan.get("operator_inbox") or []
    lines.extend(["", "## Operator Inbox", ""])
    if inbox:
        for item in inbox:
            lines.append(f"- `{item.get('id')}` {item.get('title')} — approval required before mutation.")
    else:
        lines.append("No approval-gated items were generated.")
    lines.extend([
        "",
        "## Safety",
        "- Auto-apply: `false`",
        "- Source mutation allowed by scan/plan generation: `false`",
        "- EVA-Repair auto-draft allowed: `true`",
        "- EVA-Repair auto-apply allowed only for EVA-owned generated artifacts/review packets/proposal state.",
        "- Use a separate approved workflow for any changes to memories, skills, configs, credentials, scheduler state, or delivery destinations.",
        "",
    ])
    return "\n".join(lines)


def write_remediation_plan(
    plan: dict[str, Any], vault: str | Path = EVA_VAULT_DIR, stamp: str | None = None
) -> dict[str, str]:
    """Write latest and timestamped remediation plan artifacts under the EVA vault."""
    vault_path = Path(vault).expanduser()
    stamp = stamp or utc_now().replace(":", "").replace("+", "Z")
    markdown = render_remediation_plan_markdown(plan)
    paths = {
        "latest_json": vault_path / "plans" / "latest-plan.json",
        "latest_markdown": vault_path / "plans" / "latest-plan.md",
        "timestamped_json": vault_path / "plans" / f"plan-{stamp}.json",
        "timestamped_markdown": vault_path / "plans" / f"plan-{stamp}.md",
    }
    atomic_write_json(paths["latest_json"], plan)
    atomic_write_text(paths["latest_markdown"], markdown)
    atomic_write_json(paths["timestamped_json"], plan)
    atomic_write_text(paths["timestamped_markdown"], markdown)
    return {key: str(path) for key, path in paths.items()}


def compile_notification_summary(plan: dict[str, Any]) -> str:
    """Compile a short scheduler-friendly notification summary."""
    summary = plan.get("summary", {})
    artifacts = plan.get("artifacts", {})
    counts = summary.get("finding_counts", {}) if isinstance(summary.get("finding_counts"), dict) else {}
    nonzero = {key: value for key, value in counts.items() if value}
    if nonzero:
        finding_text = ", ".join(f"{key}={value}" for key, value in sorted(nonzero.items()))
    else:
        finding_text = "none"
    next_action = "review TR-0 scan completeness"
    tranches = plan.get("tranches") or []
    if len(tranches) > 1:
        next_action += ", then TR-1 artifact review"
    lines = [
        "EVA scan complete.",
        f"Status: {summary.get('status', 'unknown')}",
        f"Findings: {finding_text}",
        f"Pending proposals: {summary.get('proposal_count', 0)}",
        f"Plan: {artifacts.get('plan_markdown', 'plans/latest-plan.md')}",
        f"Brief: {artifacts.get('brief', 'briefs/latest-brief.md')}",
        f"Next: {next_action}.",
    ]
    if summary.get("status") == "degraded":
        lines.append("Warning: scan reported degraded or partial evidence; verify coverage before acting.")
    return "\n".join(lines) + "\n"


def write_notification_summary(
    plan: dict[str, Any], vault: str | Path = EVA_VAULT_DIR
) -> str:
    path = Path(vault).expanduser() / "health" / "latest-notification.txt"
    atomic_write_text(path, compile_notification_summary(plan))
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile an EVA remediation plan from a scan bundle")
    parser.add_argument("scan", help="combined scan JSON path")
    parser.add_argument("--vault", help="EVA vault path for artifact references and optional writes")
    parser.add_argument("--json", action="store_true", help="print plan JSON")
    parser.add_argument("--markdown", action="store_true", help="print plan Markdown (default)")
    parser.add_argument("--write", action="store_true", help="write plan artifacts under --vault")
    args = parser.parse_args()
    if args.write and not args.vault:
        parser.error("--vault is required with --write")
    bundle = read_json(Path(args.scan))
    plan = compile_remediation_plan(bundle, args.vault)
    if args.write:
        write_remediation_plan(plan, args.vault)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(render_remediation_plan_markdown(plan), end="")


if __name__ == "__main__":
    main()
