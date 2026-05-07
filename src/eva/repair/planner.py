"""Draft EVA repair bundles from proposals."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import utc_now
from eva.repair.drafters import draft_actions_for_proposal
from eva.repair.policies import classify_repair_policy
from eva.repair.schemas import REPAIR_BUNDLE_SCHEMA


def draft_repair_bundle(proposal: dict[str, Any], scan_bundle: dict[str, Any] | None = None, *, vault: str | Path | None = None) -> dict[str, Any]:
    policy = classify_repair_policy(proposal)
    pid = str(proposal.get("id", "proposal"))
    actions = draft_actions_for_proposal(proposal)
    review_packet_rel = f"review-packets/{utc_now()[:10]}/{pid}-repair-review.md"
    generated_artifact_rel = f"repairs/generated/{utc_now()[:10]}/{pid}-artifact.md"
    if policy["target_class"] in {"eva_review_packet", "unknown"}:
        for action in actions:
            action.setdefault("target_path", review_packet_rel)
    if policy["target_class"] == "eva_generated_artifact":
        for action in actions:
            action.setdefault("target_path", generated_artifact_rel)
    return {
        "schema": REPAIR_BUNDLE_SCHEMA,
        "id": f"{pid}-repair",
        "created_at": utc_now(),
        "source_scan_timestamp": (scan_bundle or {}).get("timestamp"),
        "source_proposal_id": pid,
        "source_proposal_kind": proposal.get("kind", "unknown"),
        "status": "drafted",
        "risk": policy["risk"],
        "target_class": policy["target_class"],
        "requires_human_gate": policy["requires_human_gate"],
        "auto_apply_allowed": policy["auto_apply_allowed"],
        "summary": proposal.get("summary") or proposal.get("recommendation") or proposal.get("title", ""),
        "evidence": proposal.get("evidence", []),
        "affected_paths": [a.get("target_path") for a in actions if a.get("target_path")],
        "planned_actions": actions,
        "preconditions": ["Bundle validates", "Source proposal evidence reviewed"],
        "rollback": ["Remove generated EVA-owned artifacts or restore preimage backup if persistent state is ever touched"],
        "verification": ["Validate written JSON/Markdown artifacts", "Record repair outcome"],
        "operator_decision": {"state": "required" if policy["requires_human_gate"] else "not_required", "approved_by": "", "note": ""},
    }
