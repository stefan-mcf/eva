"""Approval-gated repair application for EVA-owned artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import atomic_write_json, atomic_write_text, ensure_vault, utc_now
from eva.repair.schemas import (
    REPAIR_OUTCOME_SCHEMA,
    SAFE_AUTO_APPLY_TARGET_CLASSES,
    validate_repair_bundle,
)


def _write_outcome(outcome: dict[str, Any], vault: Path) -> dict[str, Any]:
    dirname = "applied" if outcome["status"] == "applied" else "failed"
    path = vault / "repairs" / dirname / f"{outcome['bundle_id']}-outcome.json"
    atomic_write_json(path, outcome)
    outcome["outcome_path"] = str(path)
    return outcome


def _blocked(outcome: dict[str, Any], vault: Path, reason: str) -> dict[str, Any]:
    outcome["status"] = "blocked"
    outcome["blocked_reason"] = reason
    outcome["finished_at"] = utc_now()
    return _write_outcome(outcome, vault)


def apply_repair_bundle(
    bundle: dict[str, Any],
    *,
    vault: str | Path,
    require_approved: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    vault_path = ensure_vault(Path(vault).expanduser())
    outcome: dict[str, Any] = {
        "schema": REPAIR_OUTCOME_SCHEMA,
        "bundle_id": bundle.get("id"),
        "status": "failed",
        "started_at": utc_now(),
        "finished_at": "",
        "actions_attempted": [],
        "actions_succeeded": [],
        "actions_failed": [],
        "blocked_reason": "",
        "verification_results": [],
        "rollback_reference": "",
    }
    errors = validate_repair_bundle(bundle)
    if errors:
        return _blocked(outcome, vault_path, "; ".join(errors))
    if (
        require_approved
        and bundle.get("status") != "approved"
        and not bundle.get("auto_apply_allowed")
    ):
        return _blocked(outcome, vault_path, "bundle is not approved")
    if bundle.get("target_class") not in SAFE_AUTO_APPLY_TARGET_CLASSES:
        return _blocked(
            outcome,
            vault_path,
            f"target class {bundle.get('target_class')} is not auto-applicable",
        )
    if not bundle.get("auto_apply_allowed") and not force:
        return _blocked(outcome, vault_path, "auto_apply_allowed is false")

    for action in bundle.get("planned_actions", []):
        outcome["actions_attempted"].append(action)
        if action.get("action_type") == "write_review_packet":
            rel = action.get("target_path") or f"review-packets/{utc_now()[:10]}/{bundle['id']}.md"
            path = vault_path / rel
            text = "\n".join(
                [
                    f"# EVA Repair Review Packet: {bundle.get('source_proposal_id')}",
                    "",
                    f"Kind: `{bundle.get('source_proposal_kind')}`",
                    f"Risk: `{bundle.get('risk')}`",
                    f"Target class: `{bundle.get('target_class')}`",
                    "",
                    "## Summary",
                    str(bundle.get("summary", "")),
                    "",
                    "## Evidence",
                    f"Sampled records: {len(bundle.get('evidence', []))}",
                    "",
                ]
            )
            atomic_write_text(path, text)
            outcome["actions_succeeded"].append(
                {"action_type": "write_review_packet", "path": str(path.relative_to(vault_path))}
            )
        else:
            outcome["actions_failed"].append(
                {"action_type": action.get("action_type"), "reason": "unsupported safe action"}
            )
    outcome["status"] = (
        "applied" if outcome["actions_succeeded"] and not outcome["actions_failed"] else "failed"
    )
    outcome["finished_at"] = utc_now()
    return _write_outcome(outcome, vault_path)
