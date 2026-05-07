"""Closeout reports for EVA repairs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import atomic_write_json, atomic_write_text, read_json, utc_now


def _read_many(paths: list[Path]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in paths:
        try:
            item = read_json(path)
            item["_path"] = str(path)
            items.append(item)
        except Exception:
            continue
    return items


def _compile_residual_action_plan(
    drafts: list[dict[str, Any]],
    applied_outcomes: list[dict[str, Any]],
    failed_outcomes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    applied_ids = {str(outcome.get("bundle_id") or outcome.get("id") or "") for outcome in applied_outcomes}
    failed_by_id = {
        str(outcome.get("bundle_id") or outcome.get("id") or ""): outcome for outcome in failed_outcomes
    }
    residual: list[dict[str, Any]] = []
    for bundle in drafts:
        bundle_id = str(bundle.get("id") or "")
        if bundle_id in applied_ids:
            continue
        failed = failed_by_id.get(bundle_id)
        residual.append(
            {
                "bundle_id": bundle_id,
                "proposal_id": bundle.get("source_proposal_id"),
                "kind": bundle.get("source_proposal_kind"),
                "target_class": bundle.get("target_class"),
                "risk": bundle.get("risk"),
                "summary": bundle.get("summary"),
                "requires_human_gate": bool(bundle.get("requires_human_gate")),
                "auto_apply_allowed": bool(bundle.get("auto_apply_allowed")),
                "status": "blocked" if failed else "approval_required",
                "blocked_reason": (failed or {}).get("blocked_reason"),
                "next_action": _next_action(bundle, failed),
            }
        )
    return residual


def _next_action(bundle: dict[str, Any], failed: dict[str, Any] | None) -> str:
    if failed:
        reason = failed.get("blocked_reason") or "blocked by repair policy"
        return f"Leave blocked unless policy changes; reason: {reason}."
    target = bundle.get("target_class")
    if bundle.get("requires_human_gate"):
        return f"Human review required before mutating {target}; approve, reject, defer, or amend the proposal."
    if bundle.get("auto_apply_allowed"):
        return "Auto-apply candidate not yet applied; review outcome evidence and rerun apply if still valid."
    return "Review manually; this bundle is not marked auto-apply safe."


def _latest_scan(vault_path: Path) -> dict[str, Any]:
    path = vault_path / "briefs" / "latest-scan.json"
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _count(scan: dict[str, Any], section: str, key: str) -> int:
    value = scan.get(section, {}).get(key, [])
    return len(value) if isinstance(value, list) else 0


def _compile_findings(scan: dict[str, Any]) -> list[dict[str, Any]]:
    if not scan:
        return []
    findings = [
        ("config drift", _count(scan, "configs", "drift")),
        ("memory contradictions", _count(scan, "memory", "contradictions")),
        ("memory orphan/stale references", _count(scan, "memory", "orphan_references")),
        ("session repeated failures", _count(scan, "sessions", "repeated_failures")),
        ("session corrections sampled", _count(scan, "sessions", "corrections")),
        ("session skill patches sampled", _count(scan, "sessions", "skill_patches")),
        ("session tool failures sampled", _count(scan, "sessions", "tool_failures")),
        ("duplicate skill names sampled", _count(scan, "skills", "duplicate_skill_names")),
        ("high-patch-frequency skills", _count(scan, "skills", "high_patch_frequency")),
    ]
    return [{"label": label, "count": count} for label, count in findings if count]


def _compile_fixed(applied_outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixed: list[dict[str, Any]] = []
    for outcome in applied_outcomes:
        actions = outcome.get("actions_succeeded", [])
        fixed.append(
            {
                "bundle_id": outcome.get("bundle_id"),
                "actions": [action.get("action_type") for action in actions],
                "paths": [action.get("path") for action in actions if action.get("path")],
            }
        )
    return fixed


def compile_closeout_report(
    vault: str | Path,
    *,
    before_scan: dict[str, Any] | None = None,
    after_scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vault_path = Path(vault).expanduser()
    applied_paths = sorted((vault_path / "repairs" / "applied").glob("*outcome.json"))
    failed_paths = sorted((vault_path / "repairs" / "failed").glob("*outcome.json"))
    bundle_paths = []
    for state in ("drafts", "approved"):
        bundle_paths.extend(sorted((vault_path / "repairs" / state).glob("*.json")))
    applied_outcomes = _read_many(applied_paths)
    failed_outcomes = _read_many(failed_paths)
    drafts = _read_many(bundle_paths)
    human_gated = [bundle for bundle in drafts if bundle.get("requires_human_gate")]
    residual_plan = _compile_residual_action_plan(drafts, applied_outcomes, failed_outcomes)
    scan = _latest_scan(vault_path)
    findings = _compile_findings(scan)
    return {
        "schema": "eva-repair-closeout/v1",
        "generated_at": utc_now(),
        "summary": {
            "draft_bundles": len(drafts),
            "applied_outcomes": len(applied_outcomes),
            "failed_or_blocked_outcomes": len(failed_outcomes),
            "unresolved_human_gated": len(human_gated),
            "residual_actions": len(residual_plan),
        },
        "artifacts": {
            "vault": str(vault_path),
            "run_report_json": str(vault_path / "repairs" / "ledger" / "latest-run-report.json"),
            "run_report_markdown": str(vault_path / "repairs" / "ledger" / "latest-run-report.md"),
            "residual_plan_json": str(vault_path / "repairs" / "ledger" / "latest-residual-plan.json"),
            "residual_plan_markdown": str(vault_path / "repairs" / "ledger" / "latest-residual-plan.md"),
            "recommended_plan_markdown": str(vault_path / "repairs" / "ledger" / "latest-residual-plan.md"),
        },
        "before_scan_timestamp": (before_scan or {}).get("timestamp"),
        "after_scan_timestamp": (after_scan or {}).get("timestamp"),
        "findings": findings,
        "fixed": _compile_fixed(applied_outcomes),
        "residual_action_plan": residual_plan,
    }


def render_closeout_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    artifacts = report.get("artifacts", {})
    lines = [
        "# EVA Repair Closeout",
        "",
        f"Generated: `{report.get('generated_at', '')}`",
        "",
        "## Summary",
        f"- Draft bundles: {summary.get('draft_bundles', 0)}",
        f"- Applied outcomes: {summary.get('applied_outcomes', 0)}",
        f"- Failed/blocked outcomes: {summary.get('failed_or_blocked_outcomes', 0)}",
        f"- Unresolved human-gated: {summary.get('unresolved_human_gated', 0)}",
        f"- Residual actions: {summary.get('residual_actions', 0)}",
        "",
        "## Artifacts",
        f"- Residual action plan JSON: `{artifacts.get('residual_plan_json', '')}`",
        f"- Residual action plan Markdown: `{artifacts.get('residual_plan_markdown', '')}`",
        "",
        "## Residual Action Plan",
    ]
    residual_plan = report.get("residual_action_plan") or []
    if not residual_plan:
        lines.append("- No residual action items.")
    for item in residual_plan:
        lines.extend(
            [
                f"- `{item.get('bundle_id', '')}`",
                f"  - proposal: `{item.get('proposal_id', '')}`",
                f"  - kind: `{item.get('kind', '')}`",
                f"  - target: `{item.get('target_class', '')}`",
                f"  - status: `{item.get('status', '')}`",
                f"  - next action: {item.get('next_action', '')}",
                f"  - summary: {item.get('summary', '')}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def render_run_report_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    artifacts = report.get("artifacts", {})
    findings = report.get("findings") or []
    fixed = report.get("fixed") or []
    residual = report.get("residual_action_plan") or []
    lines = [
        "EVA run complete",
        "",
        "Found:",
    ]
    if findings:
        for item in findings[:8]:
            lines.append(f"- {item.get('count', 0)} {item.get('label', '')}")
    else:
        lines.append("- No scan findings were available in the closeout context.")
    lines.extend(["", "Fixed:"])
    if fixed:
        lines.append(f"- {summary.get('applied_outcomes', len(fixed))} safe EVA-owned repair(s) applied")
        for item in fixed[:4]:
            actions = ", ".join(item.get("actions") or []) or "applied"
            lines.append(f"  - {item.get('bundle_id', '')}: {actions}")
    else:
        lines.append("- 0 safe repairs applied")
    lines.extend(
        [
            "",
            "Recommended remediation plan:",
            f"- {artifacts.get('recommended_plan_markdown') or artifacts.get('residual_plan_markdown', '')}",
            "",
            "Remaining:",
        ]
    )
    if residual:
        for item in residual:
            lines.append(f"- {item.get('kind', '')}: {item.get('status', '')} ({item.get('target_class', '')})")
    else:
        lines.append("- No residual action items remain.")
    lines.extend(
        [
            "",
            "Status:",
            f"- {summary.get('failed_or_blocked_outcomes', 0)} blocked/failed; {summary.get('unresolved_human_gated', 0)} human-gated",
        ]
    )
    return "\n".join(lines) + "\n"


def render_residual_action_plan_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# EVA Residual Action Plan",
        "",
        f"Generated: `{report.get('generated_at', '')}`",
        "",
        "This is the post-repair operator plan. EVA-owned review packets and generated artifacts may be applied automatically; live memory, skills, profile configs, operator profile, scheduler, credentials, delivery destinations, public repos, and unknown targets remain human-gated.",
        "",
    ]
    residual_plan = report.get("residual_action_plan") or []
    if not residual_plan:
        lines.append("No residual action items remain.")
        lines.append("")
        return "\n".join(lines)
    for idx, item in enumerate(residual_plan, start=1):
        lines.extend(
            [
                f"## {idx}. {item.get('kind', '')}: {item.get('summary', '')}",
                "",
                f"- Bundle: `{item.get('bundle_id', '')}`",
                f"- Proposal: `{item.get('proposal_id', '')}`",
                f"- Target class: `{item.get('target_class', '')}`",
                f"- Risk: `{item.get('risk', '')}`",
                f"- Status: `{item.get('status', '')}`",
                f"- Approval required: `{str(item.get('requires_human_gate', False)).lower()}`",
                f"- Auto-apply allowed: `{str(item.get('auto_apply_allowed', False)).lower()}`",
                "",
                f"Next action: {item.get('next_action', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def write_closeout_report(
    report: dict[str, Any],
    vault: str | Path,
    stamp: str | None = None,
) -> dict[str, str]:
    vault_path = Path(vault).expanduser()
    stamp = stamp or utc_now().replace(":", "").replace("+", "Z")
    md = render_closeout_markdown(report)
    residual_md = render_residual_action_plan_markdown(report)
    run_report_md = render_run_report_markdown(report)
    residual_report = {
        "schema": "eva-residual-action-plan/v1",
        "generated_at": report.get("generated_at"),
        "summary": report.get("summary", {}),
        "items": report.get("residual_action_plan", []),
    }
    run_report = {
        "schema": "eva-run-report/v1",
        "generated_at": report.get("generated_at"),
        "summary": report.get("summary", {}),
        "findings": report.get("findings", []),
        "fixed": report.get("fixed", []),
        "recommended_plan_markdown": report.get("artifacts", {}).get("recommended_plan_markdown"),
        "remaining": report.get("residual_action_plan", []),
    }
    paths = {
        "latest_json": vault_path / "repairs" / "ledger" / "latest-closeout.json",
        "latest_markdown": vault_path / "repairs" / "ledger" / "latest-closeout.md",
        "timestamped_json": vault_path / "repairs" / "ledger" / f"closeout-{stamp}.json",
        "timestamped_markdown": vault_path / "repairs" / "ledger" / f"closeout-{stamp}.md",
        "latest_run_report_json": vault_path / "repairs" / "ledger" / "latest-run-report.json",
        "latest_run_report_markdown": vault_path / "repairs" / "ledger" / "latest-run-report.md",
        "timestamped_run_report_json": vault_path / "repairs" / "ledger" / f"run-report-{stamp}.json",
        "timestamped_run_report_markdown": vault_path / "repairs" / "ledger" / f"run-report-{stamp}.md",
        "latest_residual_plan_json": vault_path / "repairs" / "ledger" / "latest-residual-plan.json",
        "latest_residual_plan_markdown": vault_path / "repairs" / "ledger" / "latest-residual-plan.md",
        "timestamped_residual_plan_json": vault_path / "repairs" / "ledger" / f"residual-plan-{stamp}.json",
        "timestamped_residual_plan_markdown": vault_path / "repairs" / "ledger" / f"residual-plan-{stamp}.md",
    }
    atomic_write_json(paths["latest_json"], report)
    atomic_write_text(paths["latest_markdown"], md)
    atomic_write_json(paths["timestamped_json"], report)
    atomic_write_text(paths["timestamped_markdown"], md)
    atomic_write_json(paths["latest_run_report_json"], run_report)
    atomic_write_text(paths["latest_run_report_markdown"], run_report_md)
    atomic_write_json(paths["timestamped_run_report_json"], run_report)
    atomic_write_text(paths["timestamped_run_report_markdown"], run_report_md)
    atomic_write_json(paths["latest_residual_plan_json"], residual_report)
    atomic_write_text(paths["latest_residual_plan_markdown"], residual_md)
    atomic_write_json(paths["timestamped_residual_plan_json"], residual_report)
    atomic_write_text(paths["timestamped_residual_plan_markdown"], residual_md)
    return {key: str(value) for key, value in paths.items()}
