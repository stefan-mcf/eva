"""EVA proposal engine.

Drafts structured optimization proposals for operator approval. EVA never applies these
proposals automatically.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eva.common import (
    EVA_VAULT_DIR,
    atomic_write_json,
    ensure_vault,
    read_json,
    safe_snippet,
    utc_now,
)
from eva.settings import load_settings


def _slug(text: str) -> str:
    keep = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in keep:
        keep = keep.replace("--", "-")
    return keep.strip("-")[:80] or "proposal"


def _proposal(
    kind: str,
    title: str,
    evidence: list[dict[str, Any]],
    recommendation: str,
    payload: dict[str, Any] | None = None,
    *,
    confidence: str = "medium",
    false_positive_risk: str = "medium",
    requires_human_gate: bool = True,
    suggested_tranche: int | None = None,
    disposition: str = "operator_decision",
) -> dict[str, Any]:
    evidence_total = len(evidence)
    sampled = min(evidence_total, 10)
    created_at = utc_now()
    payload = dict(payload or {})
    return {
        "id": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{kind}-{_slug(title)}",
        "kind": kind,
        "status": "pending",
        "created_at": created_at,
        "title": title,
        "summary": recommendation,
        "evidence": evidence[:10],
        "evidence_count_total": evidence_total,
        "sampled_count": sampled,
        "confidence": confidence,
        "false_positive_risk": false_positive_risk,
        "requires_human_gate": requires_human_gate,
        "suggested_tranche": suggested_tranche,
        "disposition": disposition,
        "recommendation": recommendation,
        "payload": payload,
        "metadata": {
            "dedupe_key": f"{kind}:{title}",
            "baseline_timestamp": payload.get("baseline_timestamp"),
            "generated_at": created_at,
        },
        "safety": {
            "auto_apply": False,
            "operator_approval_required": requires_human_gate,
            "notes": "Review manually before changing memory, skills, config, or profile files.",
        },
    }


def _history(vault: str | Path = EVA_VAULT_DIR) -> dict[str, dict[str, int]]:
    vault = Path(vault)
    counts: dict[str, dict[str, int]] = {}
    for outcome in ("applied", "rejected"):
        for path in (vault / "proposals" / outcome).glob("*.json"):
            try:
                proposal = read_json(path)
            except Exception:
                continue
            kind = proposal.get("kind", "unknown")
            counts.setdefault(kind, {"applied": 0, "rejected": 0})[outcome] += 1
    return counts


def _score(kind: str, evidence_count: int, history: dict[str, dict[str, int]], settings: dict[str, Any]) -> float:
    h = history.get(kind, {})
    proposal_settings = settings.get("proposals", {})
    score = min(1.0, 0.35 + evidence_count / 20)
    score += h.get("applied", 0) * float(proposal_settings.get("acceptance_bonus", 0.2))
    score -= h.get("rejected", 0) * float(proposal_settings.get("rejection_penalty", 0.3))
    return round(max(0.0, min(score, 1.0)), 2)


def generate_proposals(
    scan_bundle: dict[str, Any],
    operator_profile: dict[str, Any] | None = None,
    vault: str | Path = EVA_VAULT_DIR,
) -> list[dict[str, Any]]:
    settings = load_settings(vault)
    history = _history(vault)
    memory = scan_bundle.get("memory", scan_bundle if scan_bundle.get("scanner") == "memory" else {})
    sessions = scan_bundle.get("sessions", {})
    skills = scan_bundle.get("skills", {})
    configs = scan_bundle.get("configs", {})
    proposals: list[dict[str, Any]] = []

    contradictions = memory.get("contradictions", [])
    if contradictions:
        proposals.append(
            _proposal(
                "memory_merge",
                "Review contradictory memory entries",
                contradictions,
                "Merge or rewrite contradictory memory entries so future sessions receive one clear rule.",
                {"candidate_count": len(contradictions)},
                confidence="medium",
                false_positive_risk="high",
                suggested_tranche=6,
                disposition="operator_decision",
            )
        )

    orphans = memory.get("orphan_references", [])
    if orphans:
        proposals.append(
            _proposal(
                "memory_cleanup",
                "Clean orphan or stale project references",
                orphans,
                "Remove, qualify, or update stale references that no longer reflect active project state.",
                {"candidate_count": len(orphans)},
                confidence="medium",
                false_positive_risk="medium",
                suggested_tranche=6,
                disposition="operator_decision",
            )
        )

    repeated_failures = sessions.get("repeated_failures", [])
    if repeated_failures:
        proposals.append(
            _proposal(
                "tool_failure_runbook",
                "Create runbooks for repeated tool failures",
                repeated_failures,
                "Add targeted troubleshooting notes or skills for tools that fail repeatedly across sessions.",
                {"top_tools": repeated_failures[:10]},
                confidence="medium",
                false_positive_risk="medium",
                suggested_tranche=8,
                disposition="operator_decision",
            )
        )

    oversized = skills.get("oversized_skills", [])
    if oversized:
        proposals.append(
            _proposal(
                "skill_restructure",
                "Restructure oversized skills into references",
                oversized,
                "Move long supporting material from oversized SKILL.md files into references/ and keep the main skill lean.",
                {"oversized_threshold_bytes": skills.get("health", {}).get("oversized_threshold_bytes")},
                confidence="high",
                false_positive_risk="low",
                suggested_tranche=7,
                disposition="operator_decision",
            )
        )

    high_patch = skills.get("high_patch_frequency", [])
    if high_patch:
        proposals.append(
            _proposal(
                "skill_rewrite",
                "Rewrite frequently patched skills",
                high_patch,
                "Consolidate heavily patched skills into cleaner procedures to reduce future patch churn.",
                confidence="low",
                false_positive_risk="high",
                suggested_tranche=7,
                disposition="operator_decision",
            )
        )

    drift = configs.get("drift", [])
    if drift:
        proposals.append(
            _proposal(
                "config_alignment",
                "Review cross-profile config drift",
                drift,
                "Align configs where profiles share a role and drift is accidental; preserve intentional model-lane differences.",
                {"drift_count": len(drift)},
                confidence="medium",
                false_positive_risk="medium",
                suggested_tranche=9,
                disposition="operator_decision",
            )
        )

    if operator_profile and operator_profile.get("preferences"):
        proposals.append(
            _proposal(
                "operator_profile_review",
                "Approve EVA operator-profile draft",
                [{"source": "operator-profile", "evidence": safe_snippet(json.dumps(operator_profile.get("preferences", {})), 500)}],
                "Review the generated operator profile and promote only stable, high-confidence items to durable memory or skills.",
                confidence="medium",
                false_positive_risk="medium",
                suggested_tranche=10,
                disposition="operator_decision",
            )
        )

    suppressed_kinds = set(settings.get("proposals", {}).get("suppressed_kinds", []))
    proposals = [proposal for proposal in proposals if proposal.get("kind") not in suppressed_kinds]

    for proposal in proposals:
        evidence_count = int(proposal.get("evidence_count_total") or len(proposal.get("evidence", [])) or proposal.get("payload", {}).get("candidate_count", 0) or 0)
        proposal["priority_score"] = _score(proposal.get("kind", "unknown"), evidence_count, history, settings)
        proposal["acceptance_history"] = history.get(proposal.get("kind", "unknown"), {"applied": 0, "rejected": 0})
    proposals.sort(key=lambda p: p.get("priority_score", 0), reverse=True)
    return proposals


def write_pending(proposals: list[dict[str, Any]], vault: str | Path = EVA_VAULT_DIR) -> list[Path]:
    vault = ensure_vault(Path(vault))
    pending_dir = vault / "proposals" / "pending"
    out = []
    for proposal in proposals:
        # Keep pending proposals professional and actionable: one open proposal per
        # kind/title. Re-running EVA refreshes evidence instead of accumulating
        # duplicate timestamped files.
        for existing in pending_dir.glob("*.json"):
            try:
                current = read_json(existing)
            except Exception:
                continue
            if current.get("kind") == proposal.get("kind") and current.get("title") == proposal.get("title"):
                existing.unlink(missing_ok=True)
        path = pending_dir / f"{proposal['id']}.json"
        atomic_write_json(path, proposal)
        out.append(path)
    return out


def record_outcome(proposal_id: str, outcome: str, vault: str | Path = EVA_VAULT_DIR, note: str = "") -> Path:
    vault = ensure_vault(Path(vault))
    src = vault / "proposals" / "pending" / f"{proposal_id}.json"
    if not src.exists():
        matches = list((vault / "proposals" / "pending").glob(f"*{proposal_id}*.json"))
        if not matches:
            raise FileNotFoundError(f"pending proposal not found: {proposal_id}")
        src = matches[0]
    proposal = read_json(src)
    proposal["status"] = outcome
    proposal["resolved_at"] = utc_now()
    proposal["operator_note"] = note
    target_dir = vault / "proposals" / ("applied" if outcome == "applied" else "rejected")
    target = target_dir / src.name
    atomic_write_json(target, proposal)
    src.unlink(missing_ok=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft or record EVA optimization proposals")
    parser.add_argument("scan", nargs="?", help="combined scan JSON; defaults to latest-scan.json")
    parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    parser.add_argument("--record-outcome", choices=["applied", "rejected"])
    parser.add_argument("--proposal-id")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    vault = ensure_vault(Path(args.vault))
    if args.record_outcome:
        if not args.proposal_id:
            parser.error("--proposal-id is required with --record-outcome")
        print(record_outcome(args.proposal_id, args.record_outcome, vault, args.note))
        return
    scan_path = Path(args.scan) if args.scan else vault / "briefs" / "latest-scan.json"
    bundle = read_json(scan_path)
    profile_path = vault / "context" / "operator-profile.json"
    profile = read_json(profile_path) if profile_path.exists() else None
    proposals = generate_proposals(bundle, profile)
    paths = write_pending(proposals, vault)
    print(json.dumps({"written": [str(p) for p in paths], "count": len(paths)}, indent=2))


if __name__ == "__main__":
    main()
