"""Approval-gated repair application for EVA-owned artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import atomic_write_json, atomic_write_text, ensure_vault, utc_now
from eva.proposers.propose_patches import record_outcome
from eva.repair.policies import is_deterministic_proposal_state_update
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
    if bundle.get("target_class") == "eva_proposal_state" and not _bundle_has_safe_state_policy(bundle):
        return _blocked(outcome, vault_path, "proposal-state update is not deterministic/evidence-keyed")

    for action in bundle.get("planned_actions", []):
        outcome["actions_attempted"].append(action)
        try:
            if action.get("action_type") == "write_review_packet":
                _apply_write_review_packet(bundle, action, outcome, vault_path)
            elif action.get("action_type") == "write_generated_artifact":
                _apply_write_generated_artifact(bundle, action, outcome, vault_path)
            elif action.get("action_type") == "update_proposal_state":
                _apply_update_proposal_state(bundle, action, outcome, vault_path)
            else:
                outcome["actions_failed"].append(
                    {"action_type": action.get("action_type"), "reason": "unsupported safe action"}
                )
        except Exception as exc:
            outcome["actions_failed"].append(
                {"action_type": action.get("action_type"), "reason": str(exc)}
            )
    outcome["status"] = (
        "applied" if outcome["actions_succeeded"] and not outcome["actions_failed"] else "failed"
    )
    outcome["finished_at"] = utc_now()
    return _write_outcome(outcome, vault_path)


def _apply_write_review_packet(
    bundle: dict[str, Any], action: dict[str, Any], outcome: dict[str, Any], vault_path: Path
) -> None:
    rel = action.get("target_path") or f"review-packets/{utc_now()[:10]}/{bundle['id']}.md"
    path = _safe_vault_path(vault_path, rel)
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


def _apply_write_generated_artifact(
    bundle: dict[str, Any], action: dict[str, Any], outcome: dict[str, Any], vault_path: Path
) -> None:
    rel = action.get("target_path") or f"repairs/generated/{utc_now()[:10]}/{bundle['id']}.md"
    path = _safe_vault_path(vault_path, rel)
    content = str(action.get("content") or bundle.get("summary") or "")
    if path.suffix == ".json":
        atomic_write_json(
            path,
            {
                "source_bundle_id": bundle.get("id"),
                "source_proposal_id": bundle.get("source_proposal_id"),
                "content": content,
            },
        )
    else:
        atomic_write_text(path, content if content.endswith("\n") else content + "\n")
    outcome["actions_succeeded"].append(
        {"action_type": "write_generated_artifact", "path": str(path.relative_to(vault_path))}
    )


def _apply_update_proposal_state(
    bundle: dict[str, Any], action: dict[str, Any], outcome: dict[str, Any], vault_path: Path
) -> None:
    proposal_id = str(action.get("proposal_id") or "")
    state = str(action.get("outcome") or "")
    note = str(action.get("note") or bundle.get("summary") or "EVA proposal-state auto-repair")
    if state == "applied":
        verification_artifact = action.get("verification_artifact")
        if not verification_artifact:
            raise ValueError("applied proposal-state updates require a verification artifact")
        verification_path = _safe_vault_path(vault_path, verification_artifact)
        if not verification_path.exists():
            raise FileNotFoundError(f"verification artifact not found: {verification_artifact}")
    target = record_outcome(proposal_id, state, vault_path, note)
    outcome["actions_succeeded"].append(
        {
            "action_type": "update_proposal_state",
            "proposal_id": proposal_id,
            "outcome": state,
            "path": str(target.relative_to(vault_path)),
        }
    )


def _bundle_has_safe_state_policy(bundle: dict[str, Any]) -> bool:
    proposal = {
        "id": bundle.get("source_proposal_id"),
        "kind": bundle.get("source_proposal_kind"),
        "evidence": bundle.get("evidence", []),
        "payload": {},
    }
    for action in bundle.get("planned_actions", []):
        if action.get("action_type") == "update_proposal_state":
            proposal["payload"] = {
                "target_proposal_id": action.get("proposal_id"),
                "outcome": action.get("outcome"),
                "replacement_proposal_id": action.get("replacement_proposal_id"),
                "verification_artifact": action.get("verification_artifact"),
                "false_positive": action.get("false_positive"),
                "rejection_reason": action.get("rejection_reason"),
            }
            return is_deterministic_proposal_state_update(proposal)
    return False


def _safe_vault_path(vault_path: Path, relative_path: Any) -> Path:
    raw = Path(str(relative_path))
    if raw.is_absolute():
        raise ValueError("target_path must be relative to the EVA vault")
    candidate = (vault_path / raw).resolve()
    vault_resolved = vault_path.resolve()
    if candidate != vault_resolved and vault_resolved not in candidate.parents:
        raise ValueError("target_path escapes the EVA vault")
    return candidate
