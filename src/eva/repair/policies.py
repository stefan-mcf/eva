"""Repair policy classification."""
from __future__ import annotations

from typing import Any

_POLICY_BY_KIND = {
    "tool_failure_runbook": ("hermes_skill", "medium", True, False),
    "tool_failure_triage": ("eva_review_packet", "low", False, True),
    "session_correction_review": ("eva_review_packet", "low", False, True),
    "session_skill_patch_review": ("eva_review_packet", "low", False, True),
    "skill_duplicate_review": ("eva_review_packet", "low", False, True),
    "skill_stale_review": ("eva_review_packet", "low", False, True),
    "skill_restructure": ("hermes_skill", "medium", True, False),
    "skill_rewrite": ("hermes_skill", "medium", True, False),
    "memory_merge": ("hermes_memory", "high", True, False),
    "memory_cleanup": ("hermes_memory", "high", True, False),
    "config_alignment": ("hermes_profile_config", "medium", True, False),
    "operator_profile_review": ("operator_profile", "medium", True, False),
}


def classify_repair_policy(proposal: dict[str, Any]) -> dict[str, Any]:
    kind = str(proposal.get("kind", "unknown"))
    target_class, risk, human_gate, auto_apply = _POLICY_BY_KIND.get(kind, ("unknown", "forbidden", True, False))
    return {"target_class": target_class, "risk": risk, "requires_human_gate": human_gate, "auto_apply_allowed": auto_apply}
