"""Inert repair action drafters for EVA proposals."""
from __future__ import annotations

from typing import Any

from eva.repair.policies import (
    EVA_GENERATED_ARTIFACT_KINDS,
    PROPOSAL_STATE_KINDS,
    SAFE_REVIEW_PACKET_KINDS,
    outcome_from_kind,
)

HARDENING_KINDS = {
    "tool_failure_runbook",
    "session_skill_patch_review",
    "skill_duplicate_review",
    "skill_stale_review",
    "skill_rewrite",
    "skill_restructure",
}


def draft_actions_for_proposal(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    kind = str(proposal.get("kind", "unknown"))
    evidence = proposal.get("evidence", []) if isinstance(proposal.get("evidence", []), list) else []
    payload = proposal.get("payload") if isinstance(proposal.get("payload"), dict) else {}
    if kind in SAFE_REVIEW_PACKET_KINDS:
        return [
            {
                "action_type": "write_review_packet",
                "requires_approval": False,
                "summary": f"Write review packet for {kind}",
                "evidence_count": len(evidence),
            }
        ]
    if kind in EVA_GENERATED_ARTIFACT_KINDS:
        return [
            {
                "action_type": "write_generated_artifact",
                "requires_approval": False,
                "summary": f"Write EVA-generated artifact for {kind}",
                "artifact_name": payload.get("artifact_name") or f"{proposal.get('id', 'proposal')}.md",
                "content": payload.get("content") or proposal.get("summary") or proposal.get("title", ""),
                "evidence_count": len(evidence),
            }
        ]
    if kind in PROPOSAL_STATE_KINDS:
        target_proposal_id = payload.get("target_proposal_id") or payload.get("proposal_id")
        outcome = payload.get("outcome") or outcome_from_kind(kind)
        action = {
            "action_type": "update_proposal_state",
            "requires_approval": False,
            "summary": "Record deterministic EVA proposal-state outcome",
            "proposal_id": target_proposal_id,
            "outcome": outcome,
            "note": payload.get("note") or proposal.get("summary") or "EVA auto-repair policy bookkeeping",
            "replacement_proposal_id": payload.get("replacement_proposal_id"),
            "verification_artifact": payload.get("verification_artifact")
            or payload.get("verification_artifact_path"),
            "false_positive": payload.get("false_positive"),
            "rejection_reason": payload.get("rejection_reason"),
            "evidence_count": len(evidence),
        }
        if target_proposal_id and outcome:
            action["target_path"] = f"proposals/{outcome}/{target_proposal_id}.json"
        return [action]
    if kind == "tool_failure_runbook":
        return [
            {
                "action_type": "draft_skill_patch",
                "requires_approval": True,
                "summary": "Draft runbook/skill hardening patch from repeated tool failures",
                "evidence_count": len(evidence),
            }
        ]
    if kind in {"skill_restructure", "skill_rewrite"}:
        return [
            {
                "action_type": "draft_skill_patch",
                "requires_approval": True,
                "summary": "Draft skill maintenance patch; no live skill mutation",
                "evidence_count": len(evidence),
            }
        ]
    if kind in {"memory_merge", "memory_cleanup"}:
        return [
            {
                "action_type": "draft_memory_operation",
                "requires_approval": True,
                "operation": "review_only",
                "summary": "Draft inert memory operation candidates; no provider write",
                "evidence_count": len(evidence),
            }
        ]
    if kind == "config_alignment":
        return [
            {
                "action_type": "draft_config_patch",
                "requires_approval": True,
                "summary": "Draft config diff candidates preserving intentional lane differences",
                "evidence_count": len(evidence),
            }
        ]
    if kind == "operator_profile_review":
        return [
            {
                "action_type": "draft_operator_profile_decision",
                "requires_approval": True,
                "summary": "Draft promote/reject/defer decisions for operator profile",
                "evidence_count": len(evidence),
            }
        ]
    return [
        {
            "action_type": "write_review_packet",
            "requires_approval": True,
            "summary": f"Unknown proposal kind {kind}; manual review required",
            "evidence_count": len(evidence),
        }
    ]


def is_hardening_candidate(proposal: dict[str, Any]) -> bool:
    return str(proposal.get("kind", "")) in HARDENING_KINDS
