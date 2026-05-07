"""Inert repair action drafters for EVA proposals."""
from __future__ import annotations

from typing import Any

HARDENING_KINDS = {"tool_failure_runbook", "session_skill_patch_review", "skill_duplicate_review", "skill_stale_review", "skill_rewrite", "skill_restructure"}


def draft_actions_for_proposal(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    kind = str(proposal.get("kind", "unknown"))
    evidence = proposal.get("evidence", []) if isinstance(proposal.get("evidence", []), list) else []
    if kind in {"tool_failure_triage", "session_correction_review", "session_skill_patch_review", "skill_duplicate_review", "skill_stale_review"}:
        return [{"action_type": "write_review_packet", "requires_approval": False, "summary": f"Write review packet for {kind}", "evidence_count": len(evidence)}]
    if kind == "tool_failure_runbook":
        return [{"action_type": "draft_skill_patch", "requires_approval": True, "summary": "Draft runbook/skill hardening patch from repeated tool failures", "evidence_count": len(evidence)}]
    if kind in {"skill_restructure", "skill_rewrite"}:
        return [{"action_type": "draft_skill_patch", "requires_approval": True, "summary": "Draft skill maintenance patch; no live skill mutation", "evidence_count": len(evidence)}]
    if kind in {"memory_merge", "memory_cleanup"}:
        return [{"action_type": "draft_memory_operation", "requires_approval": True, "operation": "review_only", "summary": "Draft inert memory operation candidates; no provider write", "evidence_count": len(evidence)}]
    if kind == "config_alignment":
        return [{"action_type": "draft_config_patch", "requires_approval": True, "summary": "Draft config diff candidates preserving intentional lane differences", "evidence_count": len(evidence)}]
    if kind == "operator_profile_review":
        return [{"action_type": "draft_operator_profile_decision", "requires_approval": True, "summary": "Draft promote/reject/defer decisions for operator profile", "evidence_count": len(evidence)}]
    return [{"action_type": "write_review_packet", "requires_approval": True, "summary": f"Unknown proposal kind {kind}; manual review required", "evidence_count": len(evidence)}]


def is_hardening_candidate(proposal: dict[str, Any]) -> bool:
    return str(proposal.get("kind", "")) in HARDENING_KINDS
