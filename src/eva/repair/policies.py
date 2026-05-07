"""Repair policy classification.

EVA auto-repair is intentionally narrow. The policy allows EVA to create or
update EVA-owned review/artifact/proposal-state files when the action is
low-risk and evidence-keyed. Live Hermes memory, skills, profile configs,
operator profiles, scheduler state, credentials, delivery destinations, public
repos, and unknown targets remain human-gated.
"""
from __future__ import annotations

from typing import Any

SAFE_REVIEW_PACKET_KINDS = {
    "tool_failure_triage",
    "session_correction_review",
    "session_skill_patch_review",
    "skill_duplicate_review",
    "skill_stale_review",
}

EVA_GENERATED_ARTIFACT_KINDS = {
    "eva_generated_artifact",
    "repair_ledger",
    "repair_closeout",
    "remediation_plan_artifact",
    "notification_summary_artifact",
}

PROPOSAL_STATE_KINDS = {
    "proposal_state_update",
    "proposal_superseded",
    "proposal_rejected",
    "proposal_applied",
}

HUMAN_GATED_KIND_POLICY = {
    "tool_failure_runbook": ("hermes_skill", "medium"),
    "skill_restructure": ("hermes_skill", "medium"),
    "skill_rewrite": ("hermes_skill", "medium"),
    "memory_merge": ("hermes_memory", "high"),
    "memory_cleanup": ("hermes_memory", "high"),
    "config_alignment": ("hermes_profile_config", "medium"),
    "operator_profile_review": ("operator_profile", "medium"),
}

SAFE_PROPOSAL_STATE_OUTCOMES = {"superseded", "rejected", "applied"}


def classify_repair_policy(proposal: dict[str, Any]) -> dict[str, Any]:
    """Classify a proposal into EVA's auto-repair policy envelope."""

    kind = str(proposal.get("kind", "unknown"))
    if kind in SAFE_REVIEW_PACKET_KINDS:
        return _policy("eva_review_packet", "low", human_gate=False, auto_apply=True)
    if kind in EVA_GENERATED_ARTIFACT_KINDS:
        return _policy("eva_generated_artifact", "low", human_gate=False, auto_apply=True)
    if kind in PROPOSAL_STATE_KINDS:
        auto_apply = is_deterministic_proposal_state_update(proposal)
        return _policy(
            "eva_proposal_state",
            "low" if auto_apply else "medium",
            human_gate=not auto_apply,
            auto_apply=auto_apply,
        )
    if kind in HUMAN_GATED_KIND_POLICY:
        target_class, risk = HUMAN_GATED_KIND_POLICY[kind]
        return _policy(target_class, risk, human_gate=True, auto_apply=False)
    return _policy("unknown", "forbidden", human_gate=True, auto_apply=False)


def is_deterministic_proposal_state_update(proposal: dict[str, Any]) -> bool:
    """Return True only for evidence-keyed, bounded proposal-state updates.

    Safe proposal-state auto-apply is limited to EVA vault bookkeeping:
    - superseded: exact replacement proposal id/key is present;
    - rejected: scanner evidence explicitly marks a false positive/no-op;
    - applied: verification artifact exists or is identified in payload/evidence.
    """

    payload = proposal.get("payload") if isinstance(proposal.get("payload"), dict) else {}
    outcome = str(payload.get("outcome") or outcome_from_kind(str(proposal.get("kind", "")))).lower()
    target_id = payload.get("target_proposal_id") or payload.get("proposal_id")
    if not target_id or outcome not in SAFE_PROPOSAL_STATE_OUTCOMES:
        return False
    evidence = proposal.get("evidence") if isinstance(proposal.get("evidence"), list) else []
    if not evidence:
        return False
    if outcome == "superseded":
        return bool(payload.get("replacement_proposal_id") or payload.get("replacement_dedupe_key"))
    if outcome == "rejected":
        return bool(
            payload.get("false_positive") is True
            or payload.get("rejection_reason") in {"false_positive", "deterministic_no_op"}
        )
    if outcome == "applied":
        return bool(payload.get("verification_artifact") or payload.get("verification_artifact_path"))
    return False


def outcome_from_kind(kind: str) -> str:
    if kind == "proposal_superseded":
        return "superseded"
    if kind == "proposal_rejected":
        return "rejected"
    if kind == "proposal_applied":
        return "applied"
    return ""


def _policy(target_class: str, risk: str, *, human_gate: bool, auto_apply: bool) -> dict[str, Any]:
    return {
        "target_class": target_class,
        "risk": risk,
        "requires_human_gate": human_gate,
        "auto_apply_allowed": auto_apply,
    }
